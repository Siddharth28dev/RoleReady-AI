"""
similarity_service.py
─────────────────────
Paper: "AI-Based Resume Analyzer and Interview Simulator"

Flow (as per paper):
  1. User uploads resume → parser_service extracts skills
  2. User pastes Job Description text
  3. THIS SERVICE:
     a) Extracts required skills FROM the JD using MiniLM semantic matching
     b) Computes overall JD ↔ Resume semantic similarity
     c) Semantically matches resume skills vs JD skills
     d) Returns: match score + matched + missing + severity-categorized gaps
     e) Generates learning resource recommendations

Paper fix: gap_type (core/preferred) categorization added.
Kaggle dataset removed — paper says JD text itself defines required skills.
"""

import re
import torch
from sentence_transformers import SentenceTransformer, util


# ── Model singleton ───────────────────────────────────────────────────────────

_model = None

def _get_model() -> SentenceTransformer:
    global _model
    if _model is not None:
        return _model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[MiniLM] Loading all-MiniLM-L6-v2 on {device}...")
    _model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    print(f"[MiniLM] Ready on {device}")
    return _model


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def analyze(
    jd_text: str,
    resume_text: str,
    resume_skills: list,
    experience_level: str = None,
) -> dict:
    """
    Core analysis as per research paper.

    Step 1: Extract skills required from JD text (semantic matching vs vocab)
    Step 2: Compute overall JD ↔ Resume semantic similarity
    Step 3: Match resume skills against JD skills semantically
    Step 4: Categorize missing skills as core or preferred
    Step 5: Generate recommendations for missing skills
    """
    model = _get_model()

    # Step 1: Extract required skills from JD
    jd_skills = _extract_skills_from_jd(jd_text, model)

    # Step 2: Overall semantic similarity (JD text vs Resume text)
    jd_emb     = model.encode(jd_text,     convert_to_tensor=True)
    resume_emb = model.encode(resume_text, convert_to_tensor=True)
    overall_sim = round(float(util.cos_sim(jd_emb, resume_emb)[0][0]) * 100, 1)

    # Step 3 & 4: Semantic skill matching with gap categorization
    match_result = _match_skills(resume_skills, jd_skills, model)

    # Step 5: Combined score
    combined = round((overall_sim + match_result["skill_score"]) / 2, 1)

    # Step 6: Recommendations
    recommendations = _build_recommendations(match_result["missing_skills"])

    return {
        "scores": {
            "overall_similarity": overall_sim,
            "skill_match_score":  match_result["skill_score"],
            "combined_score":     combined,
            "rating":             _rating(combined),
            "interpretation":     _interpretation(combined),
        },
        "jd_required_skills":   sorted(jd_skills),
        "matched_skills":        match_result["matched"],
        "missing_skills":        match_result["missing_skills"],
        "missing_core_skills":   match_result["missing_core"],
        "missing_preferred_skills": match_result["missing_preferred"],
        "semantic_pairs":        match_result["pairs"],
        "recommendations":       recommendations,
        "total_required":        len(jd_skills),
        "total_matched":         len(match_result["matched"]),
        "total_missing":         len(match_result["missing_skills"]),
    }


def jd_resume_score(jd_text: str, resume_text: str) -> dict:
    """Quick overall semantic similarity score."""
    model      = _get_model()
    jd_emb     = model.encode(jd_text,     convert_to_tensor=True)
    resume_emb = model.encode(resume_text, convert_to_tensor=True)
    score      = round(float(util.cos_sim(jd_emb, resume_emb)[0][0]) * 100, 1)
    return {
        "similarity_score": score,
        "rating":           _rating(score),
        "interpretation":   _interpretation(score),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  ROLE-BASED ANALYSIS (uses curated Role/RoleSkill DB tables)
# ══════════════════════════════════════════════════════════════════════════════
#
# Paper §3 "Role Mapping and Skill Assessment":
#   "Job role definitions are constructed from a curated database of position
#    descriptions... Each role specification enumerates required technical
#    skills... Skill matching employs semantic similarity scoring."
# Paper §5 "Target Role Selection":
#   "Users select their desired job role from a categorized database spanning
#    multiple industries and seniority levels. The system displays role
#    requirements and expected competencies."
#
# This is the flow that paragraph actually describes: candidate SELECTS a
# role (not pastes a JD), and matching runs against that role's stored
# RoleSkill rows (with real core/preferred gap_type from the DB, not a
# hardcoded PREFERRED_SKILLS guess-list). The JD-paste flow in analyze()
# above still exists as a secondary/advanced option for ad-hoc job postings
# that aren't in the curated database yet.

def analyze_by_role(
    role_skills:   list,   # [{"skill": "python", "gap_type": "core"}, ...] — from RoleSkill table
    resume_text:   str,
    resume_skills: list,
    role_description: str = "",
    threshold: float = 0.60,
) -> dict:
    """
    Match a candidate's resume against a curated Role's required skills
    (pulled from the RoleSkill table by the controller), instead of a
    freeform pasted JD. gap_type (core/preferred) comes directly from the
    DB — no keyword-list guessing.
    """
    model = _get_model()

    role_skill_names = [rs["skill"] for rs in role_skills]
    gap_type_map      = {rs["skill"]: rs.get("gap_type", "core") for rs in role_skills}

    # Overall similarity: resume vs role description + required skill list
    # (stands in for "JD text" when there's no pasted JD — same metric the
    # paper describes, just sourced from the curated role record instead).
    virtual_jd_text = (role_description or "") + " " + ", ".join(role_skill_names)
    overall_sim = round(
        float(util.cos_sim(
            model.encode(virtual_jd_text, convert_to_tensor=True),
            model.encode(resume_text,     convert_to_tensor=True),
        )[0][0]) * 100, 1
    )

    match_result = _match_skills_against_role(resume_skills, role_skill_names, gap_type_map, model, threshold)

    combined = round((overall_sim + match_result["skill_score"]) / 2, 1)
    recommendations = _build_recommendations(match_result["missing_skills"])

    return {
        "scores": {
            "overall_similarity": overall_sim,
            "skill_match_score":  match_result["skill_score"],
            "combined_score":     combined,
            "rating":             _rating(combined),
            "interpretation":     _interpretation(combined),
        },
        "role_required_skills":     sorted(role_skill_names),
        "matched_skills":           match_result["matched"],
        "missing_skills":           match_result["missing_skills"],
        "missing_core_skills":      match_result["missing_core"],
        "missing_preferred_skills": match_result["missing_preferred"],
        "gaps":                     match_result["gaps"],   # includes severity, for SkillGap persistence
        "semantic_pairs":           match_result["pairs"],
        "recommendations":          recommendations,
        "total_required":           len(role_skill_names),
        "total_matched":            len(match_result["matched"]),
        "total_missing":            len(match_result["missing_skills"]),
    }


def _severity(gap_type: str, similarity: float) -> str:
    """
    Paper: "The system categorizes gaps by severity based on whether they
    represent core requirements or preferred qualifications."
    Matches the exact rule documented in skill_gap_model.py:
        core      + similarity < 0.3  -> high
        core      + similarity < 0.6  -> medium
        preferred + any similarity    -> low
    """
    if gap_type != "core":
        return "low"
    if similarity < 0.3:
        return "high"
    return "medium"


def _match_skills_against_role(
    resume_skills:  list,
    role_skills:    list,
    gap_type_map:   dict,
    model,
    threshold: float = 0.60,
) -> dict:
    """Same semantic-matching approach as _match_skills, but gap_type comes
    from the DB (gap_type_map) instead of a hardcoded keyword set."""
    if not role_skills:
        return {
            "matched": resume_skills, "missing_skills": [],
            "missing_core": [], "missing_preferred": [],
            "pairs": [], "gaps": [], "skill_score": 100.0,
        }
    if not resume_skills:
        gaps = [
            {"skill": s, "gap_type": gap_type_map.get(s, "core"),
             "severity": _severity(gap_type_map.get(s, "core"), 0.0), "similarity": 0.0}
            for s in role_skills
        ]
        return {
            "matched": [],
            "missing_skills":    role_skills,
            "missing_core":      [s for s in role_skills if gap_type_map.get(s) == "core"],
            "missing_preferred": [s for s in role_skills if gap_type_map.get(s) == "preferred"],
            "pairs": [], "gaps": gaps, "skill_score": 0.0,
        }

    res_embs   = model.encode(resume_skills, convert_to_tensor=True)
    role_embs  = model.encode(role_skills,   convert_to_tensor=True)
    sim_matrix = util.cos_sim(role_embs, res_embs)

    matched, missing_skills, missing_core, missing_preferred = [], [], [], []
    pairs, gaps = [], []

    for i, role_skill in enumerate(role_skills):
        best_score     = float(sim_matrix[i].max())
        best_res_idx   = int(sim_matrix[i].argmax())
        best_res_skill = resume_skills[best_res_idx]
        gap_type       = gap_type_map.get(role_skill, "core")

        if best_score >= threshold:
            matched.append(role_skill)
            pairs.append({
                "required":     role_skill,
                "matched_with": best_res_skill,
                "score":        round(best_score * 100, 1),
                "type":         "exact" if role_skill == best_res_skill else "semantic",
            })
        else:
            missing_skills.append(role_skill)
            severity = _severity(gap_type, best_score)
            gaps.append({
                "skill": role_skill, "gap_type": gap_type,
                "severity": severity, "similarity": round(best_score, 4),
            })
            if gap_type == "core":
                missing_core.append(role_skill)
            else:
                missing_preferred.append(role_skill)

    skill_score = round(len(matched) / len(role_skills) * 100, 1)

    return {
        "matched":            sorted(matched),
        "missing_skills":     sorted(missing_skills),
        "missing_core":       sorted(missing_core),
        "missing_preferred":  sorted(missing_preferred),
        "pairs":              sorted(pairs, key=lambda x: -x["score"]),
        "gaps":               gaps,
        "skill_score":        skill_score,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  PRIVATE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

# Common technical skills vocabulary for JD extraction
TECH_SKILLS_VOCAB = [
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "golang",
    "kotlin", "swift", "ruby", "php", "bash", "shell", "r", "scala", "dart",
    # Web
    "html", "css", "react", "angular", "vue", "nextjs", "nodejs", "express",
    "tailwind", "bootstrap", "sass", "webpack", "vite", "jquery",
    # Backend
    "flask", "django", "fastapi", "spring", "laravel", "asp.net", "rails",
    # Databases
    "mysql", "postgresql", "mongodb", "redis", "sqlite", "oracle",
    "dynamodb", "elasticsearch", "firebase", "sql", "nosql",
    # Cloud & DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "git", "github",
    "linux", "ci/cd", "jenkins", "terraform", "ansible", "nginx",
    # ML/AI
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "transformers", "hugging face", "llm", "bert",
    # Concepts
    "rest api", "graphql", "microservices", "agile", "scrum",
    "oop", "data structures", "algorithms", "system design",
    "unit testing", "devops", "cloud computing",
    # Soft skills
    "communication", "teamwork", "problem solving", "leadership",
]

# Skills considered "core" vs "preferred"
# Paper: "core requirements or preferred qualifications"
PREFERRED_SKILLS = {
    "agile", "scrum", "communication", "teamwork",
    "leadership", "problem solving", "docker", "kubernetes",
    "ci/cd", "terraform", "ansible",
}


def _extract_skills_from_jd(jd_text: str, model) -> list:
    """
    Extract required skills from JD by semantic matching
    against TECH_SKILLS_VOCAB. Threshold = 0.50.
    """
    jd_sentences = [
        s.strip() for s in re.split(r'[\n.•\-\*]+', jd_text)
        if len(s.strip()) > 5
    ]
    if not jd_sentences:
        jd_sentences = [jd_text]

    jd_embs    = model.encode(jd_sentences,      convert_to_tensor=True, batch_size=64)
    skill_embs = model.encode(TECH_SKILLS_VOCAB, convert_to_tensor=True, batch_size=64)

    sim_matrix = util.cos_sim(skill_embs, jd_embs)

    extracted = []
    for i, skill in enumerate(TECH_SKILLS_VOCAB):
        max_score = float(sim_matrix[i].max())
        if max_score >= 0.50:
            extracted.append(skill)

    return extracted


def _match_skills(
    resume_skills: list,
    jd_skills: list,
    model,
    threshold: float = 0.60,
) -> dict:
    """
    Semantically match resume skills vs JD required skills.
    Categorizes missing skills as core or preferred.
    Paper: "core requirements or preferred qualifications"
    """
    if not jd_skills:
        return {
            "matched": resume_skills, "missing_skills": [],
            "missing_core": [], "missing_preferred": [],
            "pairs": [], "skill_score": 100.0,
        }
    if not resume_skills:
        return {
            "matched": [],
            "missing_skills":    jd_skills,
            "missing_core":      [s for s in jd_skills if s not in PREFERRED_SKILLS],
            "missing_preferred": [s for s in jd_skills if s in PREFERRED_SKILLS],
            "pairs": [], "skill_score": 0.0,
        }

    res_embs   = model.encode(resume_skills, convert_to_tensor=True)
    jd_embs    = model.encode(jd_skills,     convert_to_tensor=True)
    sim_matrix = util.cos_sim(jd_embs, res_embs)

    matched          = []
    missing_skills   = []
    missing_core     = []
    missing_preferred = []
    pairs            = []

    for i, jd_skill in enumerate(jd_skills):
        best_score     = float(sim_matrix[i].max())
        best_res_idx   = int(sim_matrix[i].argmax())
        best_res_skill = resume_skills[best_res_idx]

        if best_score >= threshold:
            matched.append(jd_skill)
            pairs.append({
                "required":     jd_skill,
                "matched_with": best_res_skill,
                "score":        round(best_score * 100, 1),
                "type":         "exact" if jd_skill == best_res_skill else "semantic",
            })
        else:
            missing_skills.append(jd_skill)
            # Paper fix: categorize as core or preferred
            if jd_skill in PREFERRED_SKILLS:
                missing_preferred.append(jd_skill)
            else:
                missing_core.append(jd_skill)

    skill_score = round(len(matched) / len(jd_skills) * 100, 1)

    return {
        "matched":            sorted(matched),
        "missing_skills":     sorted(missing_skills),
        "missing_core":       sorted(missing_core),
        "missing_preferred":  sorted(missing_preferred),
        "pairs":              sorted(pairs, key=lambda x: -x["score"]),
        "skill_score":        skill_score,
    }


def _build_recommendations(missing_skills: list) -> list:
    resource_map = {
        "python":           ("https://docs.python.org/3/tutorial/",                   "Official Python Tutorial"),
        "java":             ("https://dev.java/learn/",                                "Oracle Java Tutorials"),
        "javascript":       ("https://javascript.info",                                "Modern JavaScript Tutorial"),
        "typescript":       ("https://www.typescriptlang.org/docs/",                  "TypeScript Docs"),
        "react":            ("https://react.dev/learn",                                "React Official Docs"),
        "nodejs":           ("https://nodejs.org/en/learn",                            "Node.js Docs"),
        "express":          ("https://expressjs.com",                                  "Express.js Guide"),
        "flask":            ("https://flask.palletsprojects.com/tutorial/",            "Flask Tutorial"),
        "django":           ("https://docs.djangoproject.com/intro/tutorial01/",      "Django Tutorial"),
        "fastapi":          ("https://fastapi.tiangolo.com/tutorial/",                "FastAPI Tutorial"),
        "postgresql":       ("https://www.postgresql.org/docs/current/tutorial.html", "PostgreSQL Tutorial"),
        "mongodb":          ("https://learn.mongodb.com",                              "MongoDB University (Free)"),
        "mysql":            ("https://dev.mysql.com/doc/refman/8.0/en/tutorial.html", "MySQL Tutorial"),
        "docker":           ("https://docs.docker.com/get-started/",                  "Docker Getting Started"),
        "kubernetes":       ("https://kubernetes.io/docs/tutorials/",                 "Kubernetes Tutorials"),
        "aws":              ("https://aws.amazon.com/training/",                       "AWS Training (Free)"),
        "git":              ("https://git-scm.com/book/en/v2",                         "Pro Git Book (Free)"),
        "machine learning": ("https://www.coursera.org/learn/machine-learning",        "Andrew Ng ML Course"),
        "deep learning":    ("https://www.deeplearning.ai",                            "DeepLearning.AI"),
        "nlp":              ("https://huggingface.co/learn/nlp-course/",              "HuggingFace NLP Course"),
        "tensorflow":       ("https://www.tensorflow.org/tutorials",                  "TensorFlow Tutorials"),
        "pytorch":          ("https://pytorch.org/tutorials/",                         "PyTorch Tutorials"),
        "linux":            ("https://linuxjourney.com",                               "Linux Journey (Free)"),
        "rest api":         ("https://restfulapi.net",                                 "RESTful API Tutorial"),
        "agile":            ("https://www.atlassian.com/agile",                        "Atlassian Agile Guide"),
        "sql":              ("https://sqlzoo.net",                                      "SQLZoo (Free)"),
        "c++":              ("https://cplusplus.com/doc/tutorial/",                    "cplusplus.com Tutorial"),
    }
    recs = []
    for skill in missing_skills:
        url, note = resource_map.get(skill, (
            f"https://www.google.com/search?q=learn+{skill.replace(' ', '+')}+tutorial",
            "Search for tutorials and courses",
        ))
        recs.append({"skill": skill, "resource": url, "note": note})
    return recs


def _rating(score: float) -> str:
    if score >= 80: return "Excellent"
    if score >= 65: return "Good"
    if score >= 50: return "Fair"
    if score >= 35: return "Weak"
    return "Poor"


def _interpretation(score: float) -> str:
    if score >= 80: return "Excellent match! Your profile aligns very well with this role."
    if score >= 65: return "Good match. Minor improvements could strengthen your profile."
    if score >= 50: return "Moderate match. Consider tailoring your resume to the job description."
    if score >= 35: return "Weak match. Significant skill gaps exist for this role."
    return "Poor match. This role requires a very different skill set."