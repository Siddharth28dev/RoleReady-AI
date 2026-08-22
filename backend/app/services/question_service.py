"""
question_service.py
────────────────────
Paper: "AI-Based Resume Analyzer and Interview Simulator"
§4 Interview Question Generation:

  "Dynamic interview question generation distinguishes our system
   from static question bank approaches. The generation process
   considers three primary inputs: the selected job role, the
   candidate's resume content, and identified skill gaps."

  "Question generation employs a large language model fine-tuned
   on interview question datasets [Ref 7]. Prompts to the model
   specify the role, required skills, and candidate experience level."

  "The system generates diverse question types spanning technical
   knowledge, problem-solving scenarios, and situational judgment."

Architecture:
  ┌─────────────────────────────────────────────┐
  │  Fine-tuned FLAN-T5 (LoRA adapter)          │
  │  Input:  role + skill + level + type        │
  │  Output: interview question                 │
  └─────────────────────────────────────────────┘
  Fallback → dynamic templates (if model not found)

Model path:
  Place fine-tuned model at:
  backend/app/models/flan_t5_interview/
    ├── adapter_config.json
    ├── adapter_model.safetensors
    ├── tokenizer_config.json
    ├── tokenizer.json
    └── model_config.json
"""

import os
import json
import random
import re
import itertools
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer

# ── Try importing PEFT (for LoRA adapter loading) ────────────────────────────
try:
    from peft import PeftModel
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False
    print("[question_service] WARNING: peft not installed. Run: pip install peft")

# ── Model paths ───────────────────────────────────────────────────────────────

# Fine-tuned LoRA adapter directory (set after training)
# Override with env var FLAN_T5_ADAPTER_DIR if the trained adapter folder
# name changes (e.g. after retraining a new version) — avoids silent
# fallback to the base (untrained) model when folder names drift.
_BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINETUNED_DIR = os.getenv(
    "FLAN_T5_ADAPTER_DIR",
    os.path.join(_BASE_DIR, "models", "flan_t5_interview_final_v5"),
)
BASE_MODEL    = "google/flan-t5-base"

# ── Singletons ────────────────────────────────────────────────────────────────

_model     = None
_tokenizer = None
_use_finetuned = False   # Will be True after fine-tuned model loads

MAX_INPUT_LEN  = 128
MAX_TARGET_LEN = 64

# ═══════════════════════════════════════════════════════════════════════════════
#  MODEL LOADER
# ═══════════════════════════════════════════════════════════════════════════════

def _get_model():
    """
    Load model with priority:
      1. Fine-tuned LoRA adapter (paper-compliant)
      2. Base FLAN-T5 (fallback, still paper-referenced model)
    """
    global _model, _tokenizer, _use_finetuned

    if _model is not None:
        return _model, _tokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    adapter_config = os.path.join(FINETUNED_DIR, "adapter_config.json")

    # ── Path 1: Load fine-tuned LoRA adapter ─────────────────────────────────
    if PEFT_AVAILABLE and os.path.exists(adapter_config):
        print(f"[FLAN-T5] Loading fine-tuned LoRA adapter from: {FINETUNED_DIR}")
        try:
            # Load tokenizer from adapter dir (may contain custom tokenizer)
            _tokenizer = T5Tokenizer.from_pretrained(FINETUNED_DIR)

            # Load base model
            base = T5ForConditionalGeneration.from_pretrained(
                BASE_MODEL,
                torch_dtype=torch.float32,
            )

            # Apply LoRA adapter on top
            _model = PeftModel.from_pretrained(base, FINETUNED_DIR)
            _model = _model.to(device)
            _model.eval()

            _use_finetuned = True
            print(f"[FLAN-T5] ✓ Fine-tuned model ready on {device}")
            print(f"[FLAN-T5] LoRA adapter applied — paper-compliant question generation active")
            return _model, _tokenizer

        except Exception as e:
            print(f"[FLAN-T5] Fine-tuned load failed: {e}")
            print(f"[FLAN-T5] Falling back to base model...")
            _model = None
            _tokenizer = None

    # ── Path 2: Base FLAN-T5 (fallback) ──────────────────────────────────────
    if not os.path.exists(adapter_config):
        print(f"[FLAN-T5] Fine-tuned model not found at: {FINETUNED_DIR}")
        print(f"[FLAN-T5] Run fine-tuning notebook first, then place model in that directory.")
        print(f"[FLAN-T5] Loading base FLAN-T5 with template generation as fallback...")

    _tokenizer = T5Tokenizer.from_pretrained(BASE_MODEL)
    _model     = T5ForConditionalGeneration.from_pretrained(BASE_MODEL).to(device)
    _model.eval()
    _use_finetuned = False
    print(f"[FLAN-T5] Base model ready on {device} (templates will be used for generation)")
    return _model, _tokenizer


# ═══════════════════════════════════════════════════════════════════════════════
#  CORE: AI QUESTION GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

# ── Model-output quality gate ─────────────────────────────────────────────
#
# The original gate only checked length + terminal punctuation, which a lot
# of grammatically-fine-but-wrong output passes. In practice the LoRA
# adapter (google/flan-t5-base + a fairly small fine-tune) leaks two
# specific failure modes when sampling gives it room to wander instead of
# always taking the same greedy path:
#
#   1. Third-person "about the role" trivia instead of a question addressed
#      TO the candidate — "What are the job requirements for a Full stack
#      developer?", "Which skill level does the candidate need to possess?"
#   2. Outright SQuAD/TriviaQA-flavored reading-comprehension artifacts
#      bleeding through from FLAN-T5's base pretraining mix — "Which
#      project did C-Peter work for?", "What was the outcome of the
#      interview?" — these aren't malformed, they're just answering a
#      different task than "ask the candidate an interview question".
#
# Neither is catchable by a length/punctuation check. This adds: (a) a
# requirement that the question actually addresses the candidate in second
# person ("you"/"your"), which most genuine interview-question phrasings
# do and both failure modes above generally don't; (b) a denylist of the
# specific artifact phrasings observed so far. This is a stopgap, not a
# fix for the adapter itself — it's pattern-matching known bad outputs,
# not verifying the question is actually good. See question_service.py's
# module docstring / the LoRA re-training note for the real fix.
_SECOND_PERSON_RE = re.compile(r"\b(you|your|you're|you've|you'll|you'd)\b", re.IGNORECASE)

_GENERIC_QA_ARTIFACT_PATTERNS = [
    re.compile(r"\bdid\s+[A-Z][\w-]*\s+work\s+for\b"),         # "did C-Peter work for"
    re.compile(r"\boutcome of the interview\b", re.IGNORECASE),
    re.compile(r"\bwhere does this position\b", re.IGNORECASE),
    re.compile(r"\bpreferred by\b", re.IGNORECASE),
    re.compile(r"\bwhat kind of position does this apply to\b", re.IGNORECASE),
    re.compile(r"\bwould you be interviewing\b", re.IGNORECASE),   # role-reversal: candidate framed as the interviewer
    re.compile(r"\byou are going to be interviewing\b", re.IGNORECASE),
]


def _looks_grammatical(text: str) -> bool:
    """
    Reject clauses whose syntactic ROOT isn't a verb — e.g. "When did your
    interview in a fast-paced environment?" parses with "interview" (a
    NOUN) as the sentence root and "did" left dangling as an orphaned aux,
    because there's no actual verb in the sentence for "did" to attach to.
    That's a different failure mode from the denylist patterns above: it's
    not a recognizable bad phrasing, it's a genuinely broken sentence, and
    no fixed regex list will anticipate every way this model can produce
    one. Checking that every sentence has a VERB/AUX root is a general
    grammatical-validity check instead of matching specific known outputs.

    A naive "does the text contain any VERB-tagged token" check isn't
    reliable here — spaCy's tagger mistags "paced" (from "fast-paced") as
    VERB in the broken example above, so it would wrongly pass. The ROOT
    dependency is a much stronger signal: peripheral tagging errors on
    adjectives/modifiers don't get to be ROOT, only the clause's actual
    main verb (or its stand-in AUX, e.g. "Tell me about a time...") does.

    Reuses parser_service's spaCy singleton rather than loading a second
    copy of en_core_web_sm — it's already loaded for resume parsing, and
    the EntityRuler it adds doesn't affect POS/dependency tagging.
    Fails open (returns True) on any NLP error so a spaCy hiccup degrades
    to "less strict", not "no questions generate at all".
    """
    try:
        from app.services.parser_service import _get_nlp
        doc = _get_nlp()(text)
        sentences = list(doc.sents)
        if not sentences:
            return False
        return all(
            any(tok.dep_ == "ROOT" and tok.pos_ in ("VERB", "AUX") for tok in sent)
            for sent in sentences
        )
    except Exception as e:
        print(f"[question_service] grammar check failed, allowing through: {e}")
        return True


def _passes_quality_gate(generated: str) -> bool:
    word_count = len(generated.split())
    if word_count < 6 or word_count > 60:
        return False
    if not ("?" in generated or generated[-1] in ".!?"):
        return False
    if not _SECOND_PERSON_RE.search(generated):
        return False
    if any(p.search(generated) for p in _GENERIC_QA_ARTIFACT_PATTERNS):
        return False
    if not _looks_grammatical(generated):
        return False
    return True


def _generate_one_question(
    job_role:         str,
    skill:            str,
    experience_level: str,
    question_type:    str,
) -> str | None:
    """
    Paper §4: "Prompts to the model specify the role, required skills,
               and candidate experience level."

    Uses fine-tuned FLAN-T5 when available.
    Returns None if model output is unusable (will trigger template fallback).
    """
    model, tokenizer = _get_model()

    # Same prompt format used during fine-tuning (prepare_dataset.py)
    prompt = (
        f"Generate a {question_type} interview question for a {job_role} role. "
        f"Skill: {skill}. Experience level: {experience_level}. "
        f"Question:"
    )

    try:
        device = next(model.parameters()).device
        inputs = tokenizer(
            prompt,
            return_tensors = "pt",
            max_length     = MAX_INPUT_LEN,
            truncation     = True,
        ).to(device)

        with torch.no_grad():
            # do_sample=True so `temperature` actually does something — it
            # was previously set alongside do_sample=False, which makes
            # HF's generate() ignore temperature entirely and always run
            # deterministic beam search. That meant even when the
            # fine-tuned model DID produce output (rather than falling
            # back to a template), the exact same prompt always generated
            # the exact same question — contributing to "same questions on
            # a second attempt" just as much as the template path did.
            # top_p/top_k add real variety between calls; no_repeat_ngram
            # and repetition_penalty still guard against degenerate,
            # repeated-phrase output within a single generation.
            outputs = model.generate(
                **inputs,
                max_new_tokens       = 64,
                do_sample            = True,
                top_p                = 0.92,
                top_k                = 50,
                temperature          = 0.8 if _use_finetuned else 1.0,
                no_repeat_ngram_size = 4,
                repetition_penalty   = 1.5,
            )

        generated = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

        if _passes_quality_gate(generated):
            if not generated.endswith("?"):
                generated = generated.rstrip(".!") + "?"
            return generated

    except Exception as e:
        print(f"[FLAN-T5 generation] Error: {e}")

    return None   # Signal to use template fallback


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def generate_interview_questions(
    job_role:           str,
    resume_text:        str,
    skill_gaps:         list,
    matched_skills:     list,
    experience_level:   str = "fresher",
    questions_per_type: int = 3,
) -> dict:
    """
    Paper §4: Generate dynamic interview questions using fine-tuned FLAN-T5.

    Three primary inputs (paper-exact):
      1. job_role          — selected target role
      2. resume_text       — parsed resume content (for context & experience detection,
                              AND as a genuine question-content source — see
                              _extract_resume_topics/_build_source_plan below)
      3. skill_gaps        — identified gaps (drive question focus)

    Previously resume_text was only used for experience-level detection —
    every question, across all 4 types, was generated from skill_gaps +
    matched_skills alone. That collapsed badly when skill_gaps was short
    (e.g. [AWS, Cloud computing, Azure]): all 12 generated questions ended
    up about those same 2-3 skills regardless of type. Each type now
    draws from a genuine MIX of sources (skill gap / resume content /
    role-general / matched skill) via _build_source_plan — see its
    docstring for the full reasoning.

    Returns 4 question types: technical, problem_solving, behavioral, situational
    """
    # Load model on first call
    _get_model()

    exp_level = _detect_experience(resume_text, experience_level)
    level_key = _normalize_level(exp_level)

    gap_skills    = skill_gaps[:4]
    matched_list  = matched_skills[:4]
    gap_skill_set = set(skill_gaps)
    resume_topics = _extract_resume_topics(resume_text)

    technical       = _generate_type("technical",       job_role, gap_skills, matched_list, resume_topics, level_key, questions_per_type, gap_skill_set, resume_text)
    problem_solving = _generate_type("problem_solving", job_role, gap_skills, matched_list, resume_topics, level_key, questions_per_type, gap_skill_set, resume_text)
    behavioral      = _generate_type("behavioral",      job_role, gap_skills, matched_list, resume_topics, level_key, questions_per_type, gap_skill_set, resume_text)
    situational     = _generate_type("situational",     job_role, gap_skills, matched_list, resume_topics, level_key, questions_per_type, gap_skill_set, resume_text)

    total = len(technical) + len(problem_solving) + len(behavioral) + len(situational)

    return {
        "job_role":           job_role,
        "experience_level":   exp_level,
        "total_questions":    total,
        "generation_method":  "finetuned_lora" if _use_finetuned else "template_fallback",
        "questions": {
            "technical":       technical,
            "problem_solving": problem_solving,
            "behavioral":      behavioral,
            "situational":     situational,
        },
        "skill_gaps_covered": skill_gaps[:5],
        "focus_skills":       matched_skills[:5],
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  QUESTION TYPE GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
#  QUESTION-CONTENT SOURCE DIVERSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════
#
# Paper §4 states question generation "considers three primary inputs:
# the selected job role, the candidate's resume content, and identified
# skill gaps." The original _generate_type only ever used skill_gaps +
# matched_skills as content for EVERY question, in EVERY type — resume
# content was received but never used to generate a question, and there
# was no role-fit question untied to a specific skill. Confirmed in
# testing: a resume/JD where skill_gaps=[AWS, Cloud computing, Azure]
# produced 12/12 generated questions about those same 2-3 skills,
# regardless of whether the label said "technical", "behavioral",
# "situational", or "problem_solving" — the type only changed the
# question's grammatical shape, never its subject.
#
# _build_source_plan gives each of a type's `count` questions one of 4
# sources: skill_gap, resume_content, role_general, or matched_skill.
# resume_content and role_general are deliberately TEMPLATE-ONLY, not
# routed through the fine-tuned model: the LoRA adapter was fine-tuned
# on a fixed prompt shape (role + a SKILL + level + type). Feeding it a
# raw resume snippet or a "no specific skill" prompt is exactly the kind
# of out-of-distribution input that produced the AWS/Azure hallucinations
# ("aural features", "CID") diagnosed earlier in this project — templates
# sidestep that risk entirely rather than needing another retrain.

_PROJECT_LINE_RE = re.compile(
    r"\b(built|developed|designed|implemented|created|led|architected|"
    r"engineered|launched|deployed|optimized|automated)\b",
    re.IGNORECASE,
)


def _extract_resume_topics(resume_text: str, max_topics: int = 5) -> list:
    """
    Pulls a handful of candidate-written project/experience lines out of
    the raw resume text, so a resume-content question can reference the
    candidate's OWN words ("Your resume mentions: '...'") instead of a
    generic skill name. Deliberately simple — line length + one action-
    verb keyword — rather than a full NLP pipeline: resume formatting
    varies too much for a stricter parser to be reliable, and this only
    needs to surface plausible candidates, not classify every line
    perfectly. Fails open to an empty list, which _build_source_plan
    treats as "no resume_content source available" and routes around.
    """
    if not resume_text:
        return []
    topics = []
    for line in resume_text.splitlines():
        line = line.strip(" \t•-*·")
        if not (20 <= len(line) <= 160):
            continue
        if not _PROJECT_LINE_RE.search(line):
            continue
        topics.append(line)
        if len(topics) >= max_topics:
            break
    return topics


# Role-fit questions untied to any specific skill — the "job role" input
# the paper names, used directly instead of only as a template variable
# inside skill-specific questions.
#
# Each (type, level) bucket needs at least `questions_per_type` (default
# 3) unique phrasings — role_general is the guaranteed fallback source
# when NO skill gaps, matched skills, or resume topics exist at all
# (e.g. an empty/unparseable resume), so if this pool ran dry before
# hitting `count`, generation would silently come up short. Confirmed by
# a smoke test that exercised exactly that all-empty-inputs case.
_ROLE_GENERAL_TEMPLATES = {
    "technical": {
        "fresher": [
            "What technical skill are you most confident in right now, and how did you build that confidence?",
            "How do you usually approach learning a new technology you haven't used before?",
            "What's a technical concept you had to teach yourself, and how did you go about learning it?",
        ],
        "mid": [
            "How do you decide which technologies are worth adopting versus avoiding in a {role} project?",
            "How do you keep your technical skills current as a {role}?",
            "How do you approach reviewing another engineer's code as a {role}?",
        ],
        "senior": [
            "How do you evaluate whether a new technology is mature enough to introduce into a {role} team's stack?",
            "How do you balance technical debt against delivery pressure as a {role}?",
            "How do you set technical standards for a {role} team without slowing everyone down?",
        ],
    },
    "behavioral": {
        "fresher": [
            "What made you want to become a {role}?",
            "Tell me about a time you had to ask for help. How did you approach it?",
            "Tell me about a time you received critical feedback. How did you respond?",
        ],
        "mid": [
            "Tell me about a time your understanding of the {role} role changed based on real project experience.",
            "Describe a time you had to balance multiple priorities as a {role}. How did you decide what came first?",
            "Tell me about a time you had to give a teammate difficult feedback.",
        ],
        "senior": [
            "Tell me about a time you had to make a difficult trade-off between speed and quality as a {role}.",
            "Describe how your approach to being a {role} has changed over your career.",
            "Tell me about a time you had to say no to a stakeholder's request. How did you handle it?",
        ],
    },
    "situational": {
        "fresher": [
            "If you joined a new {role} team and their codebase looked nothing like what you're used to, what would you do first?",
            "If you didn't understand a task your manager assigned, how would you handle it?",
            "If you disagreed with a code review comment, how would you respond?",
        ],
        "mid": [
            "If you were given a {role} project with unclear requirements, how would you proceed?",
            "If you noticed a teammate was struggling but hadn't asked for help, what would you do?",
            "If you had to choose between two equally valid technical approaches, how would you decide?",
        ],
        "senior": [
            "If you inherited a {role} team with low morale, what would your first month look like?",
            "If leadership asked you to cut your project timeline in half, how would you respond?",
            "If two of your reports had a persistent conflict, how would you address it?",
        ],
    },
    "problem_solving": {
        "fresher": [
            "How would you approach a {role} task you've genuinely never seen before, with no one available to ask?",
            "Walk me through how you'd break down a large, vague {role} task into a plan.",
            "How would you figure out why your code works on your machine but not a teammate's?",
        ],
        "mid": [
            "How would you investigate a {role} production issue with no clear error message or logs?",
            "How would you decide between fixing a root cause now versus a quick patch under deadline pressure?",
            "How would you approach a task that turns out to be much bigger than originally scoped?",
        ],
        "senior": [
            "How would you diagnose a {role} system that has gradually gotten slower over months with no single obvious cause?",
            "How would you approach a technical disagreement between two engineers you lead, where both have valid points?",
            "How would you decide whether a recurring production issue needs a rewrite or another patch?",
        ],
    },
}

# Resume-content questions — genuinely reference the candidate's own
# resume text (via _extract_resume_topics), not a skill name at all.
_RESUME_CONTENT_TEMPLATES = {
    "technical": [
        "Your resume mentions: \"{topic}\" — what was the most technically challenging part of that?",
        "You wrote: \"{topic}\" — what technology choices did you make there, and why?",
    ],
    "behavioral": [
        "Your resume mentions: \"{topic}\" — tell me about a specific obstacle you ran into while doing that.",
        "You listed: \"{topic}\" — what was your individual contribution versus the team's?",
    ],
    "situational": [
        "You wrote: \"{topic}\" — if you had to rebuild that today with what you know now, what would you change?",
        "Your resume mentions: \"{topic}\" — if a new teammate had to take that project over tomorrow, what would you tell them?",
    ],
    "problem_solving": [
        "Your resume mentions: \"{topic}\" — walk me through a specific bug or blocker you hit there and how you resolved it.",
        "You wrote: \"{topic}\" — what tradeoffs did you consider before landing on your approach?",
    ],
}


def _generate_role_general_question(question_type: str, job_role: str, level_key: str):
    tmpl_group = _ROLE_GENERAL_TEMPLATES.get(question_type)
    if not tmpl_group:
        return None
    tmpl_list = tmpl_group.get(level_key, tmpl_group["fresher"])
    text = random.choice(tmpl_list).format(role=job_role)
    return text.rstrip(".!?") + "?"


def _generate_resume_content_question(question_type: str, topics: list):
    if not topics:
        return None
    tmpl_list = _RESUME_CONTENT_TEMPLATES.get(question_type, _RESUME_CONTENT_TEMPLATES["technical"])
    topic = random.choice(topics)
    text = random.choice(tmpl_list).format(topic=topic)
    return text.rstrip(".!?") + "?"


def _build_source_plan(count: int, has_gaps: bool, has_matched: bool, has_topics: bool) -> list:
    """
    Decides which content source each of the `count` questions for a
    type should draw from. Priority mirrors the paper's stated inputs:
    skill gaps first ("gaps inform interview questions"), then the
    candidate's own resume content, then general role fit — matched
    (non-gap) skills fill any remaining slots. role_general never needs
    external data, so it's always a legal fallback; the other three
    sources are only ever placed in the plan when their backing data
    actually exists — the caller never has to guess whether a slot can
    be fulfilled.
    """
    preferred = []
    if has_gaps:
        preferred.append("skill_gap")
    if has_topics:
        preferred.append("resume_content")
    preferred.append("role_general")
    if has_matched:
        preferred.append("matched_skill")
    if has_gaps:
        preferred.append("skill_gap")  # a 2nd gap-driven slot if count > len(preferred)

    plan = []
    i = 0
    while len(plan) < count:
        plan.append(preferred[i % len(preferred)])
        i += 1
    return plan


def _generate_type(
    question_type:  str,
    job_role:       str,
    gap_skills:     list,
    matched_skills: list,
    resume_topics:  list,
    level_key:      str,
    count:          int,
    gap_skill_set:  set,
    resume_text:    str,
) -> list:
    """
    Paper §4: "Template-based constraints ensure questions follow
               effective interviewing practices."
    Paper §4: "considers three primary inputs: the selected job role,
               the candidate's resume content, and identified skill gaps."

    Each of the `count` questions is assigned a content source by
    _build_source_plan (skill gap / resume content / role-general /
    matched skill) instead of every question drawing from the same
    skill pool regardless of type — see that function's docstring.
    skill_gap/matched_skill sources still try the fine-tuned model
    first, falling back to templates on a bad output, same as before;
    resume_content/role_general are template-only (see the module note
    above _extract_resume_topics for why).
    """
    questions  = []
    seen_texts = set()

    plan = _build_source_plan(
        count,
        has_gaps    = bool(gap_skills),
        has_matched = bool(matched_skills),
        has_topics  = bool(resume_topics),
    )

    gap_cycle     = itertools.cycle(gap_skills)     if gap_skills     else None
    matched_cycle = itertools.cycle(matched_skills) if matched_skills else None

    def _try_add(text, skill, is_gap, source) -> bool:
        if not text:
            return False
        key = text.lower()[:40]
        if key in seen_texts:
            return False
        seen_texts.add(key)
        questions.append(_build_q_dict(text, question_type, skill, level_key, is_gap, source))
        return True

    for source in plan:
        if len(questions) >= count:
            break

        if source in ("skill_gap", "matched_skill"):
            skill = next(gap_cycle) if source == "skill_gap" else next(matched_cycle)

            model_q = _generate_one_question(
                job_role         = job_role,
                skill            = skill,
                experience_level = level_key,
                question_type    = question_type.replace("_", " "),
            )
            if _try_add(model_q, skill, skill in gap_skill_set, "model"):
                continue

            # Tag with the skill the question text actually mentions (may
            # differ from `skill` — see _template_fallback's docstring).
            template_q, template_skill = _template_fallback(
                question_type = question_type,
                job_role      = job_role,
                skill         = skill,
                level_key     = level_key,
                resume_text   = resume_text,
                skill_gaps    = list(gap_skill_set),
            )
            _try_add(template_q, template_skill, template_skill in gap_skill_set, "template")

        elif source == "resume_content":
            text = _generate_resume_content_question(question_type, resume_topics)
            # Tagged with job_role rather than a fabricated placeholder —
            # keeps evaluation_service's answer/keyword prompts
            # ("...about {skill} for a {job_role} position") coherent
            # instead of interpolating a non-skill string into them.
            _try_add(text, job_role, False, "resume_content")

        elif source == "role_general":
            text = _generate_role_general_question(question_type, job_role, level_key)
            _try_add(text, job_role, False, "role_general_template")

    # Backstop: top up with role-general templates if any slot above
    # produced nothing (e.g. resume_content had no extractable topics).
    # role_general always has content, so it's the safe way to still
    # hit `count`. A single miss (random.choice re-picking an already-used
    # phrasing) does NOT mean the pool is exhausted — keep retrying up to
    # a generous guard bound rather than bailing on the first duplicate,
    # which previously left this short by several questions whenever
    # role_general was the ONLY available source (e.g. an empty/
    # unparseable resume with no skill gaps or matched skills at all —
    # caught by a smoke test before this shipped).
    guard = 0
    max_guard = max(count * 8, 20)
    while len(questions) < count and guard < max_guard:
        guard += 1
        text = _generate_role_general_question(question_type, job_role, level_key)
        _try_add(text, job_role, False, "role_general_template")

    return questions


def _build_q_dict(question, question_type, skill, level_key, is_gap, source) -> dict:
    q = question if question.endswith("?") else question + "?"
    d = {
        "question":   q,
        "skill":      skill,
        "type":       question_type,
        "difficulty": level_key,
        "is_gap":     is_gap,
        "source":     source,   # "model" or "template" — useful for eval
    }
    if question_type == "behavioral":
        d["format"] = "STAR (Situation, Task, Action, Result)"
    return d


# ═══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE FALLBACK (paper: "template-based constraints")
# ═══════════════════════════════════════════════════════════════════════════════

_SKILL_DESC = {
    "python": "Python programming", "flask": "Flask web framework",
    "django": "Django web framework", "fastapi": "FastAPI framework",
    "react": "React.js", "angular": "Angular", "vue": "Vue.js",
    "nodejs": "Node.js", "javascript": "JavaScript", "typescript": "TypeScript",
    "java": "Java", "mysql": "MySQL", "postgresql": "PostgreSQL",
    "mongodb": "MongoDB", "docker": "Docker", "kubernetes": "Kubernetes",
    "aws": "AWS cloud services", "git": "Git version control",
    "rest api": "REST API design", "machine learning": "Machine Learning",
    "nlp": "Natural Language Processing", "sql": "SQL",
}

def _desc(skill: str) -> str:
    return _SKILL_DESC.get(skill.lower(), skill)


def _template_fallback(
    question_type: str,
    job_role:      str,
    skill:         str,
    level_key:     str,
    resume_text:   str,
    skill_gaps:    list,
) -> tuple[str, str] | None:
    """
    Dynamic templates as fallback when model output fails quality check.

    Returns (question_text, skill_used) instead of a bare string.
    skill_used is the RAW skill name actually embedded in the question
    text — for problem_solving/situational templates that's gap1/gap2
    (a fixed skill drawn from skill_gaps), NOT the `skill` argument this
    function was called with. Previously the caller tagged every question
    with the loop's `skill` regardless of which skill the sentence
    actually mentioned, so a question that literally asked about "azure"
    could be filed under skill="ci/cd" — which then fed the WRONG skill
    into evaluation_service's expected-answer/keyword-generation prompts
    for that question (built from the stored skill tag, not the question
    text), and mislabeled is_gap. Callers must use the returned skill_used
    for both.
    """

    skill_d  = _desc(skill)
    gap1_raw = skill_gaps[0] if skill_gaps else skill
    gap2_raw = skill_gaps[1] if len(skill_gaps) > 1 else gap1_raw
    gap1     = _desc(gap1_raw)
    gap2     = _desc(gap2_raw)

    # Each entry is (question_text, raw_skill_actually_mentioned).
    TEMPLATES = {
        "technical": {
            "fresher": [
                (f"What is {skill_d} and why is it important for a {job_role}?", skill),
                (f"Explain the core concepts of {skill_d} with a practical example.", skill),
                (f"What are the key features of {skill_d} that every {job_role} should know?", skill),
            ],
            "mid": [
                (f"How have you used {skill_d} in a real-world {job_role} project?", skill),
                (f"What are the best practices for using {skill_d} in production?", skill),
                (f"How would you optimize performance when working with {skill_d}?", skill),
            ],
            "senior": [
                (f"How would you design a scalable architecture using {skill_d}?", skill),
                (f"What are the trade-offs of using {skill_d} at scale in a {job_role} system?", skill),
                (f"How does {skill_d} fit into a microservices or distributed system?", skill),
            ],
        },
        "problem_solving": {
            "fresher": [
                (f"How would you debug an issue in your {job_role} project where {gap1} returns unexpected results?", gap1_raw),
                (f"Your {job_role} application works locally but fails in production when using {gap1}. What steps would you take?", gap1_raw),
                (f"As a {job_role}, how would you approach implementing {gap1} for the first time?", gap1_raw),
            ],
            "mid": [
                (f"A {gap1}-related query in your {job_role} system is causing production timeouts. How would you diagnose and fix it?", gap1_raw),
                (f"Your {job_role} application using {gap1} is experiencing memory leaks. Walk through your debugging process.", gap1_raw),
                (f"How would you refactor existing {job_role} code to integrate {gap2} without breaking current functionality?", gap2_raw),
            ],
            "senior": [
                (f"How would you architect a {job_role} system that scales to 1M users while using {gap1} effectively?", gap1_raw),
                (f"A critical security vulnerability is found in your {gap1} implementation. What is your complete response plan?", gap1_raw),
                (f"How would you lead a team migration to an architecture using {gap1} and {gap2}?", gap1_raw),
            ],
        },
        "behavioral": {
            "fresher": [
                (f"Tell me about a time during your project or internship when you faced a difficult technical challenge. What did you do and what was the outcome?", skill),
                (f"Describe a situation where you had to learn {skill_d} quickly to complete a task. How did you approach it?", skill),
                (f"Tell me about a time you collaborated with a team on a technical problem. What was your role?", skill),
            ],
            "mid": [
                (f"Tell me about a time you significantly improved the performance of a system. What steps did you take?", skill),
                (f"Describe a situation where you disagreed with a technical decision. How did you handle it professionally?", skill),
                (f"Tell me about a time you delivered an important feature under a very tight deadline. What was your approach?", skill),
            ],
            "senior": [
                (f"Tell me about a time you led a team through a major technical challenge. What was your leadership approach?", skill),
                (f"Describe a situation where you convinced stakeholders to adopt a better technical solution. How did you build the case?", skill),
                (f"Tell me about a time you mentored a junior developer who was struggling. What did you do?", skill),
            ],
        },
        "situational": {
            "fresher": [
                (f"If your project deadline is tomorrow and the feature requires {gap1} which you have never used before, what would you do?", gap1_raw),
                (f"If your manager asks you to build a {job_role} feature using {gap2} in 2 days, how would you approach it?", gap2_raw),
                (f"If you discover a critical bug right before an important client demo, what steps would you take?", skill),
            ],
            "mid": [
                (f"If a client urgently requests a change requiring {gap1} that contradicts your current {job_role} architecture, how would you handle it?", gap1_raw),
                (f"If you discover a security vulnerability in your {gap2} integration in production, what is your immediate response?", gap2_raw),
                (f"If your team lead is suddenly unavailable during a critical production outage, how would you respond?", skill),
            ],
            "senior": [
                (f"If the CTO asks you to evaluate and adopt {gap1} for the entire {job_role} team in one month, what is your process?", gap1_raw),
                (f"If two senior engineers fundamentally disagree on using {gap1} versus {gap2}, how do you resolve it?", gap1_raw),
                (f"If the business demands a {gap1}-based feature in 2 weeks but your engineering estimate is 2 months, how do you respond?", gap1_raw),
            ],
        },
    }

    tmpl_group = TEMPLATES.get(question_type, TEMPLATES["technical"])
    tmpl_list  = tmpl_group.get(level_key, tmpl_group["fresher"])

    # Randomize which template is used, instead of the previous
    # `tmpl_list[idx % len(tmpl_list)]`. That was fully deterministic: for
    # the same resume + same JD, skill_gaps/matched_skills are identical
    # (semantic matching has no randomness), so `idx` and `skill` land on
    # the exact same value every regeneration — and nothing else in this
    # fallback path had any source of variation either. That combination
    # is why a second interview attempt on the same resume/role produced
    # byte-identical questions. random.choice breaks that determinism;
    # _generate_type's existing seen_texts dedup still protects against
    # two picks colliding within one request.
    text, used_skill = random.choice(tmpl_list)

    # Normalize ending punctuation without double-punctuating. Previously
    # `q + "?"` was appended whenever q didn't already end in "?" — but
    # several templates end in "." (e.g. "...with a practical example."),
    # so the result was "...with a practical example.?". Strip any
    # existing terminal punctuation first, then always end in exactly one.
    text = text.rstrip(".!?") + "?"
    return text, used_skill


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_experience(resume_text: str, default: str) -> str:
    text = resume_text.lower()
    if any(w in text for w in ["5+ years", "6 years", "7 years", "senior", "lead", "architect"]):
        return "senior"
    if any(w in text for w in ["3 years", "4 years", "mid-level"]):
        return "mid"
    if any(w in text for w in ["intern", "fresher", "b.tech", "entry", "graduate"]):
        return "fresher"
    return default or "fresher"


def _normalize_level(exp_level: str) -> str:
    return {
        "fresher": "fresher", "entry": "fresher", "junior": "fresher",
        "mid": "mid", "mid-level": "mid",
        "senior": "senior", "lead": "senior", "principal": "senior",
    }.get(exp_level.lower(), "fresher")


def is_finetuned_model_loaded() -> bool:
    """Utility for health check endpoint — returns True if LoRA adapter is active."""
    return _use_finetuned


def get_model_info() -> dict:
    """Return model info for transparency report."""
    return {
        "model":          BASE_MODEL,
        "finetuned":      _use_finetuned,
        "adapter_path":   FINETUNED_DIR if _use_finetuned else None,
        "generation":     "LoRA fine-tuned FLAN-T5" if _use_finetuned else "Base model + templates",
        "paper_compliant": _use_finetuned,
    }