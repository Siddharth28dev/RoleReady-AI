"""
evaluation_service.py
──────────────────────
Pipeline (matches paper methodology exactly):

    Interview Question
          │
          ▼
    Generate Expected Answer (LLM)
          │
          ▼
    Generate Keywords (LLM)
          │
          ▼
    Candidate Answer
          │
          ▼
    Evaluate across 4 dimensions
          ├── Content Analysis
          ├── Language Quality
          ├── Completeness
          └── Keyword Matching
          │
          ▼
    Generate Personalized Feedback

Performance note:
  Expected-answer generation and keyword generation both use the same
  FLAN-T5 model as question generation. Calling generate() once per
  answer (2 calls x N answers) is what caused the axios timeout on
  /evaluate-all with CPU inference. Instead, this file BATCHES both
  generation steps: all N questions' expected-answers are produced in a
  single generate() call, and all N keyword-sets in a second single
  call - 2 forward passes total regardless of how many questions there
  are, instead of 2N. The pipeline order and LLM usage are unchanged
  from the diagram; only *how many times the model is invoked* changed.
"""

import os
import torch
from sentence_transformers import SentenceTransformer, util
from transformers import T5ForConditionalGeneration, T5Tokenizer

# See question_service.py for the full explanation — peft checks
# hasattr(torch.distributed, "tensor") without importing it first, which
# fails on torch versions where that submodule is lazy. This import is
# what makes the check pass; it's a no-op otherwise for CPU inference.
import torch.distributed.tensor  # noqa: F401

try:
    from peft import PeftModel
    _PEFT_AVAILABLE = True
except ImportError:
    _PEFT_AVAILABLE = False

# Same env var as question_service.py — keep both services pointed at the
# same adapter so question generation and answer/keyword generation never
# drift onto different model versions.
FINE_TUNED_MODEL_PATH = os.getenv(
    "FLAN_T5_ADAPTER_DIR",
    os.path.join(os.path.dirname(__file__), "..", "models", "flan_t5_interview_final_v5"),
)
BASE_MODEL_NAME = "google/flan-t5-base"
MAX_INPUT_LEN   = 256
MAX_TARGET_LEN  = 150


# ── Singletons ────────────────────────────────────────────────────────────────
_minilm       = None
_t5_model     = None
_t5_tokenizer = None


def _get_minilm() -> SentenceTransformer:
    global _minilm
    if _minilm is not None:
        return _minilm
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[MiniLM] Loading all-MiniLM-L6-v2 on {device}...")
    _minilm = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    print("[MiniLM] Ready")
    return _minilm


def _get_t5():
    """
    Loads the same fine-tuned FLAN-T5 + LoRA adapter used for question
    generation, so expected-answer/keyword generation is grounded in the
    same model family the paper describes ("LLM fine-tuned on interview
    question datasets"). Falls back to base flan-t5-base if the adapter
    isn't found, so evaluation still works even before/without the adapter.
    """
    global _t5_model, _t5_tokenizer
    if _t5_model is not None:
        return _t5_model, _t5_tokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    _t5_tokenizer = T5Tokenizer.from_pretrained(BASE_MODEL_NAME)
    base_model = T5ForConditionalGeneration.from_pretrained(BASE_MODEL_NAME)

    adapter_config = os.path.join(FINE_TUNED_MODEL_PATH, "adapter_config.json")
    if _PEFT_AVAILABLE and os.path.exists(adapter_config):
        print(f"[FLAN-T5] Loading fine-tuned LoRA adapter from {FINE_TUNED_MODEL_PATH}")
        _t5_model = PeftModel.from_pretrained(base_model, FINE_TUNED_MODEL_PATH)
    else:
        print("[FLAN-T5] Adapter not found - using base flan-t5-base")
        _t5_model = base_model

    _t5_model = _t5_model.to(device)
    _t5_model.eval()
    print("[FLAN-T5] Ready")
    return _t5_model, _t5_tokenizer


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_answer(
    question:         str,
    candidate_answer: str,
    question_type:    str = "technical",
    skill:            str = "",
    job_role:         str = "",
    expected_answer:  str = None,
    keywords:         list = None,
) -> dict:
    """
    Evaluate a single candidate answer against all 4 dimensions.

    `expected_answer` / `keywords` can be passed in pre-generated (used by
    evaluate_multiple_answers, which batches LLM generation up front). If
    omitted, they're generated here via a single-item LLM call - fine for
    one-off calls, just don't loop this for N answers (use
    evaluate_multiple_answers instead, which batches).
    """
    if not candidate_answer or len(candidate_answer.strip()) < 10:
        return {
            "score":            0.0,
            "rating":           "No Answer",
            "feedback":         "No answer was provided.",
            "similarity":       0.0,
            "expected_answer":  "",
            "keywords_used":    [],
            "keywords_missing": [],
            "dimensions":       {},
        }

    minilm = _get_minilm()

    # Step 1: Generate expected answer (LLM) - unless already batched upstream
    if expected_answer is None:
        expected_answer = _generate_expected_answers_batch(
            [{"question": question, "question_type": question_type,
              "skill": skill, "job_role": job_role}]
        )[0]

    # Step 2: Generate keywords (LLM) - unless already batched upstream
    if keywords is None:
        keywords = _generate_keywords_batch(
            [{"question": question, "question_type": question_type,
              "skill": skill, "job_role": job_role}]
        )[0]

    # Step 3: Encode with MiniLM
    expected_emb  = minilm.encode(expected_answer,  convert_to_tensor=True)
    candidate_emb = minilm.encode(candidate_answer, convert_to_tensor=True)

    # Step 4: Cosine similarity
    similarity = float(util.cos_sim(expected_emb, candidate_emb)[0][0])
    similarity = round(similarity, 4)
    score      = round(similarity * 100, 1)

    # Step 5: 4 evaluation dimensions
    dimensions = _evaluate_dimensions(
        question, candidate_answer, expected_answer,
        similarity, question_type, keywords
    )

    # Step 6: Rating + personalized feedback
    rating   = _get_rating(similarity)
    feedback = _generate_feedback(rating, dimensions, skill, question_type)

    # Step 7: Keyword hit/miss analysis
    candidate_lower  = candidate_answer.lower()
    keywords_used    = [k for k in keywords if k.lower() in candidate_lower]
    keywords_missing = [k for k in keywords if k.lower() not in candidate_lower]

    return {
        "score":            score,
        "similarity":       similarity,
        "rating":           rating,
        "expected_answer":  expected_answer,
        "feedback":         feedback,
        "keywords_used":    keywords_used,
        "keywords_missing": keywords_missing,
        "dimensions":       dimensions,
    }


def evaluate_multiple_answers(answers: list) -> dict:
    """
    Evaluate multiple question-answer pairs (the /evaluate-all path).

    LLM generation is BATCHED here: all expected-answers are produced in
    one generate() call, all keyword-sets in a second one - 2 T5 calls
    total for the whole batch, not 2 per answer. This is what keeps the
    diagram's "Generate Expected Answer (LLM) -> Generate Keywords (LLM)"
    steps from timing out on CPU when there are 8-12+ questions.
    """
    if not answers:
        return {
            "overall_score":      0.0,
            "overall_rating":     "No Answer",
            "total_questions":    0,
            "individual_results": [],
            "summary":            _overall_summary(0.0, []),
        }

    meta = [
        {
            "question":      item.get("question", ""),
            "question_type": item.get("question_type", "technical"),
            "skill":         item.get("skill", ""),
            "job_role":      item.get("job_role", ""),
        }
        for item in answers
    ]

    # -- Batch Step 1: Generate Expected Answer (LLM) - one call for all N --
    expected_answers = _generate_expected_answers_batch(meta)

    # -- Batch Step 2: Generate Keywords (LLM) - one call for all N ---------
    keyword_sets = _generate_keywords_batch(meta)

    results     = []
    total_score = 0.0

    for item, expected, kws in zip(answers, expected_answers, keyword_sets):
        result = evaluate_answer(
            question         = item.get("question", ""),
            candidate_answer = item.get("candidate_answer", ""),
            question_type    = item.get("question_type", "technical"),
            skill            = item.get("skill", ""),
            job_role         = item.get("job_role", ""),
            expected_answer  = expected,
            keywords         = kws,
        )
        result["question"] = item.get("question", "")
        results.append(result)
        total_score += result["score"]

    avg_score = round(total_score / len(results), 1) if results else 0.0

    return {
        "overall_score":      avg_score,
        "overall_rating":     _get_rating(avg_score / 100),
        "total_questions":    len(results),
        "individual_results": results,
        "summary":            _overall_summary(avg_score, results),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  LLM GENERATION - EXPECTED ANSWERS (batched)
# ══════════════════════════════════════════════════════════════════════════════

def _build_answer_prompt(item: dict) -> str:
    return (
        f"Provide a comprehensive answer to this {item['question_type']} interview "
        f"question about {item['skill']} for a {item['job_role']} position. "
        f"Question: {item['question']}"
    )


def _generate_expected_answers_batch(items: list) -> list:
    """
    One batched generate() call producing an expected answer for every
    item in `items`. Falls back to the template per-item if the model
    fails to load or a given output is too short/degenerate.
    """
    try:
        model, tokenizer = _get_t5()
        device = next(model.parameters()).device

        prompts = [_build_answer_prompt(it) for it in items]
        inputs = tokenizer(
            prompts,
            return_tensors="pt",
            max_length=MAX_INPUT_LEN,
            truncation=True,
            padding=True,
        ).to(device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens       = MAX_TARGET_LEN,
                num_beams            = 4,
                no_repeat_ngram_size = 2,
                early_stopping       = True,
            )

        decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)

        results = []
        for text, item in zip(decoded, items):
            text = text.strip()
            if len(text.split()) >= 20:
                results.append(text)
            else:
                results.append(_answer_template_fallback(
                    item["question_type"], item["skill"], item["job_role"]
                ))
        return results

    except Exception as e:
        print(f"[FLAN-T5 batch answer gen] Failed: {e} - using template fallback for all")
        return [
            _answer_template_fallback(it["question_type"], it["skill"], it["job_role"])
            for it in items
        ]


def _answer_template_fallback(question_type: str, skill: str, job_role: str) -> str:
    templates = {
        "technical": (
            f"A strong answer explains what {skill} is, its core concepts and architecture, "
            f"practical use cases in {job_role} projects, how it differs from alternatives, "
            f"and includes real-world examples with specific technical details."
        ),
        "behavioral": (
            "A strong STAR answer describes the Situation with clear context, "
            "the Task or challenge faced, the concrete Actions taken step by step "
            "with reasoning, and the measurable Result achieved. "
            "Be specific with examples and quantify impact where possible."
        ),
        "situational": (
            "A strong answer identifies the problem clearly, outlines a prioritized "
            "action plan with specific steps, mentions communicating with stakeholders, "
            "and demonstrates calm structured thinking under pressure with a clear outcome."
        ),
        "problem_solving": (
            "A strong answer follows a systematic approach: understand and reproduce "
            "the problem, investigate root cause using logs or debugging tools, "
            "implement and test a fix thoroughly, deploy carefully, and document the solution."
        ),
    }
    return templates.get(question_type, templates["technical"])


# ══════════════════════════════════════════════════════════════════════════════
#  LLM GENERATION - KEYWORDS (batched)
# ══════════════════════════════════════════════════════════════════════════════

def _build_keyword_prompt(item: dict) -> str:
    return (
        f"List 6 key technical terms expected in a good answer to this "
        f"interview question about {item['skill']} for a {item['job_role']} role. "
        f"Question: {item['question']} "
        f"Output only comma-separated terms, nothing else."
    )


def _generate_keywords_batch(items: list) -> list:
    """
    One batched generate() call producing a keyword list for every item.
    Falls back to the knowledge-bank per-item if output is too sparse.
    """
    try:
        model, tokenizer = _get_t5()
        device = next(model.parameters()).device

        prompts = [_build_keyword_prompt(it) for it in items]
        inputs = tokenizer(
            prompts,
            return_tensors="pt",
            max_length=MAX_INPUT_LEN,
            truncation=True,
            padding=True,
        ).to(device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens = 60,
                num_beams      = 4,
                early_stopping = True,
            )

        decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)

        results = []
        for text, item in zip(decoded, items):
            keywords = [k.strip().lower() for k in text.split(",") if len(k.strip()) > 2]
            if len(keywords) >= 3:
                results.append(keywords[:8])
            else:
                results.append(_keyword_fallback(item["skill"], item["question_type"]))
        return results

    except Exception as e:
        print(f"[FLAN-T5 batch keyword gen] Failed: {e} - using knowledge-bank fallback for all")
        return [
            _keyword_fallback(it["skill"], it["question_type"])
            for it in items
        ]


def _keyword_fallback(skill: str, question_type: str) -> list:
    """Fallback keyword bank - used only when FLAN-T5 output is insufficient."""
    KEYWORD_BANK = {
        "python":           ["functions", "classes", "libraries", "syntax", "interpreter", "pip", "modules"],
        "flask":            ["routes", "blueprints", "request", "response", "jinja2", "sqlalchemy", "decorator"],
        "django":           ["models", "views", "templates", "orm", "admin", "urls", "migrations"],
        "react":            ["components", "hooks", "state", "props", "virtual dom", "jsx", "useeffect"],
        "docker":           ["container", "image", "dockerfile", "compose", "volume", "network", "registry"],
        "aws":              ["ec2", "s3", "rds", "lambda", "iam", "cloudwatch", "vpc"],
        "mysql":            ["tables", "joins", "indexes", "transactions", "foreign key", "query", "acid"],
        "postgresql":       ["tables", "joins", "indexes", "transactions", "constraints", "query", "acid"],
        "mongodb":          ["collections", "documents", "bson", "aggregation", "indexes", "schema", "nosql"],
        "git":              ["commit", "branch", "merge", "pull request", "clone", "push", "rebase"],
        "machine learning": ["training", "testing", "model", "features", "accuracy", "overfitting", "validation"],
        "nlp":              ["tokenization", "embeddings", "transformers", "bert", "sentiment", "ner", "corpus"],
        "rest api":         ["endpoints", "http", "get", "post", "json", "authentication", "status codes"],
        "kubernetes":       ["pods", "nodes", "deployment", "service", "cluster", "namespace", "ingress"],
        "javascript":       ["variables", "functions", "async", "promises", "dom", "events", "closures"],
        "typescript":       ["types", "interfaces", "generics", "decorators", "strict", "compile", "classes"],
    }
    TYPE_KEYWORDS = {
        "behavioral":      ["situation", "task", "action", "result", "team", "challenge", "outcome"],
        "situational":     ["approach", "prioritize", "communicate", "resolve", "plan", "steps", "decision"],
        "problem_solving": ["debug", "analyze", "root cause", "solution", "test", "reproduce", "fix"],
    }
    skill_lower = skill.lower()
    if skill_lower in KEYWORD_BANK:
        return KEYWORD_BANK[skill_lower]
    return TYPE_KEYWORDS.get(question_type, ["explain", "example", "implement", "use", "benefit"])


# ══════════════════════════════════════════════════════════════════════════════
#  4 EVALUATION DIMENSIONS
# ══════════════════════════════════════════════════════════════════════════════

def _evaluate_dimensions(
    question:         str,
    candidate_answer: str,
    expected:         str,
    similarity:       float,
    question_type:    str,
    keywords:         list,
) -> dict:
    """
    Paper: 4 dimensions -
    1. Content analysis
    2. Language quality
    3. Completeness
    4. Keyword matching
    """
    minilm = _get_minilm()

    # 1. Content analysis - answer vs question relevance
    q_emb   = minilm.encode(question,         convert_to_tensor=True)
    ans_emb = minilm.encode(candidate_answer, convert_to_tensor=True)
    content_score = round(float(util.cos_sim(q_emb, ans_emb)[0][0]) * 100, 1)

    # 2. Completeness - word count proxy
    word_count = len(candidate_answer.split())
    if word_count >= 80:
        completeness_label, completeness_score = "Complete", 100
    elif word_count >= 40:
        completeness_label, completeness_score = "Adequate", 70
    elif word_count >= 15:
        completeness_label, completeness_score = "Brief", 40
    else:
        completeness_label, completeness_score = "Too Short", 10

    # 3. Language quality - filler words check
    filler_words = ["um", "uh", "like", "basically", "literally", "you know", "kind of"]
    filler_count = sum(candidate_answer.lower().count(w) for w in filler_words)
    language_score = max(0, 100 - (filler_count * 10))

    # 4. Keyword matching - LLM-generated keywords
    candidate_lower = candidate_answer.lower()
    if keywords:
        hits = [k for k in keywords if k.lower() in candidate_lower]
        keyword_score = round(len(hits) / len(keywords) * 100, 1)
    else:
        keyword_score = 50.0
        hits = []

    return {
        "content_relevance": {
            "score":       content_score,
            "label":       _score_label(content_score),
            "description": "How well the answer addresses the question",
        },
        "completeness": {
            "score":       completeness_score,
            "label":       completeness_label,
            "word_count":  word_count,
            "description": "Whether the answer is elaborated sufficiently",
        },
        "language_quality": {
            "score":        language_score,
            "label":        _score_label(language_score),
            "filler_count": filler_count,
            "description":  "Clarity and professional tone of the answer",
        },
        "keyword_coverage": {
            "score":          keyword_score,
            "label":          _score_label(keyword_score),
            "keywords_hit":   hits,
            "total_keywords": len(keywords),
            "description":    "Key concepts from expected answer covered",
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
#  RATING + PERSONALIZED FEEDBACK
# ══════════════════════════════════════════════════════════════════════════════

def _get_rating(similarity: float) -> str:
    if similarity >= 0.90: return "Excellent"
    if similarity >= 0.75: return "Good"
    if similarity >= 0.60: return "Average"
    return "Poor"


def _generate_feedback(
    rating:        str,
    dimensions:    dict,
    skill:         str,
    question_type: str,
) -> dict:
    strengths    = []
    improvements = []

    content_score = dimensions["content_relevance"]["score"]
    if content_score >= 70:
        strengths.append("Your answer is relevant and addresses the question well.")
    else:
        improvements.append("Try to more directly address what the question is asking.")

    comp_label = dimensions["completeness"]["label"]
    word_count = dimensions["completeness"]["word_count"]
    if comp_label in ["Complete", "Adequate"]:
        strengths.append(f"Good level of detail with {word_count} words.")
    else:
        improvements.append(
            f"Your answer is too brief ({word_count} words). "
            "Aim for at least 50-80 words with specific examples."
        )

    kw_score = dimensions["keyword_coverage"]["score"]
    kw_hit   = dimensions["keyword_coverage"]["keywords_hit"]
    if kw_score >= 60:
        strengths.append(f"Good use of technical terminology: {', '.join(kw_hit[:3])}.")
    else:
        improvements.append(
            f"Include more specific terminology related to {skill}. "
            "Use proper technical vocabulary in your answers."
        )

    lang_score = dimensions["language_quality"]["score"]
    if lang_score >= 80:
        strengths.append("Clear and professional communication style.")
    else:
        improvements.append("Avoid filler words and maintain a professional tone.")

    type_tips = {
        "technical":       "For technical questions, include examples, code concepts, or real use cases.",
        "behavioral":      "Use the STAR method: Situation -> Task -> Action -> Result.",
        "situational":     "Structure your answer: identify the issue -> list steps -> explain outcome.",
        "problem_solving": "Walk through your thought process step by step systematically.",
    }

    return {
        "overall_rating": rating,
        "strengths":      strengths,
        "improvements":   improvements,
        "tip":            type_tips.get(question_type, "Be specific and structured."),
    }


def _overall_summary(avg_score: float, results: list) -> dict:
    excellent = sum(1 for r in results if r["rating"] == "Excellent")
    good      = sum(1 for r in results if r["rating"] == "Good")
    average   = sum(1 for r in results if r["rating"] == "Average")
    poor      = sum(1 for r in results if r["rating"] == "Poor")

    if avg_score >= 90:
        verdict = "Outstanding performance! You are very well prepared for this interview."
    elif avg_score >= 75:
        verdict = "Good performance. Review the areas marked for improvement."
    elif avg_score >= 60:
        verdict = "Average performance. Focus on more detailed and structured answers."
    else:
        verdict = "Needs improvement. Practice with specific examples and technical depth."

    return {
        "verdict":   verdict,
        "breakdown": {
            "excellent": excellent,
            "good":      good,
            "average":   average,
            "poor":      poor,
        },
    }


def _score_label(score: float) -> str:
    if score >= 85: return "Excellent"
    if score >= 70: return "Good"
    if score >= 50: return "Average"
    return "Poor"