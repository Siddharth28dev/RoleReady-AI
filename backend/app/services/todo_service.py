"""
todo_service.py
────────────────
Paper: "Recommendation generation creates personalized to-do checklists
        specifying concrete actions candidates can take."

Paper: "The to-do list employs priority ranking to help candidates focus
        on high-impact improvements first."

Paper: "Estimated time commitments and difficulty levels help candidates
        plan development activities realistically."

Paper: "Progress tracking functionality allows candidates to mark
        completed items, creating momentum."

Paper: "Items are sequenced logically, with foundational improvements
        preceding advanced refinements."

Paper: "Average of 8-12 concrete action items per report."
"""


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def generate_todo_list(
    resume_feedback:    dict,
    skill_gap_data:     dict,
    interview_feedback: dict,
    job_role:           str = "",
) -> list:
    """
    Generate prioritized to-do list from all 3 feedback sources.
    Target: 8-12 items as per paper.

    Returns list of todo dicts sorted by priority (high → medium → low).
    Each item has: task, category, priority, estimated_hours,
                   difficulty, resource_url, resource_note
    """
    todos = []

    # Source 1 — Resume improvement todos
    todos += _resume_todos(resume_feedback)

    # Source 2 — Skill gap todos (core gaps first)
    todos += _skill_gap_todos(skill_gap_data)

    # Source 3 — Interview improvement todos
    todos += _interview_todos(interview_feedback)

    # Sort: high → medium → low, then by estimated_hours (quick wins first)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    todos.sort(key=lambda x: (
        priority_order.get(x["priority"], 1),
        x["estimated_hours"]
    ))

    # Paper: 8-12 items — cap at 12, ensure at least 8
    todos = todos[:12]

    # Add order number for frontend display
    for i, todo in enumerate(todos, 1):
        todo["order"] = i

    return todos


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 1 — RESUME TODOS
# ══════════════════════════════════════════════════════════════════════════════

def _resume_todos(resume_feedback: dict) -> list:
    """
    Paper: "Resume recommendations might suggest adding quantifiable
            achievements, restructuring sections for better readability,
            or incorporating relevant keywords."
    """
    todos    = []
    details  = resume_feedback.get("details", {})
    weaknesses = resume_feedback.get("weaknesses", [])

    # Check each weakness and map to actionable todo
    weakness_text = " ".join(weaknesses).lower()

    if "email" in weakness_text:
        todos.append(_make_todo(
            task="Add your professional email address to the resume contact section.",
            category="resume",
            priority="high",
            estimated_hours=0.25,
            difficulty="easy",
            resource_url=None,
            resource_note="Use a professional email format: firstname.lastname@gmail.com",
        ))

    if "phone" in weakness_text:
        todos.append(_make_todo(
            task="Add your phone number to the resume contact section.",
            category="resume",
            priority="high",
            estimated_hours=0.25,
            difficulty="easy",
        ))

    if "linkedin" in weakness_text:
        todos.append(_make_todo(
            task="Create or update your LinkedIn profile and add the URL to your resume.",
            category="resume",
            priority="medium",
            estimated_hours=2.0,
            difficulty="easy",
            resource_url="https://www.linkedin.com",
            resource_note="Complete your LinkedIn profile with skills and experience.",
        ))

    if "github" in weakness_text:
        todos.append(_make_todo(
            task="Create a GitHub profile, pin your best projects, and add the URL to your resume.",
            category="resume",
            priority="medium",
            estimated_hours=2.0,
            difficulty="easy",
            resource_url="https://github.com",
            resource_note="Pin 3-5 best repositories with README files.",
        ))

    skills_count = details.get("skills_count", 0)
    if skills_count < 10:
        todos.append(_make_todo(
            task=f"Expand your skills section from {skills_count} to 10+ relevant technical skills.",
            category="resume",
            priority="high",
            estimated_hours=1.0,
            difficulty="easy",
            resource_note="List programming languages, frameworks, databases, and tools you know.",
        ))

    if not details.get("education"):
        todos.append(_make_todo(
            task="Add a clearly labeled Education section with degree, institution, and graduation year.",
            category="resume",
            priority="high",
            estimated_hours=0.5,
            difficulty="easy",
        ))

    projects_count = details.get("projects", 0)
    if projects_count < 3:
        todos.append(_make_todo(
            task=f"Add {3 - projects_count} more project(s) to your resume with description and tech stack used.",
            category="resume",
            priority="medium",
            estimated_hours=3.0,
            difficulty="medium",
            resource_note="Include project name, technologies used, and key outcome/impact.",
        ))

    # Always suggest quantifiable achievements
    todos.append(_make_todo(
        task="Add quantifiable achievements to your experience section (e.g. 'Improved API response time by 30%').",
        category="resume",
        priority="medium",
        estimated_hours=1.5,
        difficulty="medium",
        resource_note="Use numbers, percentages, and metrics to describe your impact.",
    ))

    return todos


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 2 — SKILL GAP TODOS
# ══════════════════════════════════════════════════════════════════════════════

def _skill_gap_todos(skill_gap_data: dict) -> list:
    """
    Paper: "Skill development recommendations direct candidates to
            relevant learning resources, certification programs,
            or practical project ideas."
    Paper: "Core gaps = high priority, Preferred gaps = lower priority."
    """
    todos = []

    recommendations = skill_gap_data.get("recommendations", [])
    core_gaps       = skill_gap_data.get("missing_core_skills", [])
    preferred_gaps  = skill_gap_data.get("missing_preferred_skills", [])

    # Build resource lookup from recommendations
    resource_lookup = {
        r["skill"]: {"url": r["resource"], "note": r["note"]}
        for r in recommendations
    }

    # Core gaps → HIGH priority
    for skill in core_gaps[:4]:   # cap at 4 core skills
        res = resource_lookup.get(skill, {})
        todos.append(_make_todo(
            task=f"Learn {skill.title()} — this is a CORE requirement for the target role.",
            category="skill_development",
            priority="high",
            estimated_hours=_estimate_learning_hours(skill),
            difficulty=_estimate_difficulty(skill),
            resource_url=res.get("url"),
            resource_note=res.get("note"),
        ))

    # Preferred gaps → MEDIUM priority
    for skill in preferred_gaps[:3]:   # cap at 3 preferred skills
        res = resource_lookup.get(skill, {})
        todos.append(_make_todo(
            task=f"Learn {skill.title()} — this is a preferred skill for the target role.",
            category="skill_development",
            priority="medium",
            estimated_hours=_estimate_learning_hours(skill),
            difficulty=_estimate_difficulty(skill),
            resource_url=res.get("url"),
            resource_note=res.get("note"),
        ))

    return todos


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 3 — INTERVIEW TODOS
# ══════════════════════════════════════════════════════════════════════════════

def _interview_todos(interview_feedback: dict) -> list:
    """
    Paper: "Interview preparation recommendations include practicing
            responses to specific question types, studying particular
            technical concepts, or developing storytelling skills
            for behavioral questions."
    """
    todos = []

    if interview_feedback.get("rating") == "Not Attempted":
        todos.append(_make_todo(
            task="Complete at least one full mock interview session using the Interview Simulator.",
            category="interview",
            priority="high",
            estimated_hours=1.0,
            difficulty="medium",
            resource_note="Answer all question types: technical, behavioral, situational, problem-solving.",
        ))
        return todos

    overall_score = interview_feedback.get("score", 0)
    breakdown     = interview_feedback.get("breakdown", {})

    # Low overall score
    if overall_score < 60:
        todos.append(_make_todo(
            task="Practice structured interview answers using the STAR method (Situation, Task, Action, Result).",
            category="interview",
            priority="high",
            estimated_hours=3.0,
            difficulty="medium",
            resource_url="https://www.themuse.com/advice/star-interview-method",
            resource_note="Use STAR for all behavioral and situational questions.",
        ))

    # Poor answers exist
    if breakdown.get("poor", 0) > 0:
        todos.append(_make_todo(
            task=f"Re-attempt the {breakdown['poor']} Poor-rated question(s) with more detailed, structured answers.",
            category="interview",
            priority="high",
            estimated_hours=2.0,
            difficulty="medium",
            resource_note="Aim for 80+ words per answer with specific examples.",
        ))

    # Average answers exist
    if breakdown.get("average", 0) > 0:
        todos.append(_make_todo(
            task=f"Improve your {breakdown['average']} Average-rated answer(s) by adding more technical terminology and examples.",
            category="interview",
            priority="medium",
            estimated_hours=1.5,
            difficulty="medium",
            resource_note="Include role-specific technical terms in your answers.",
        ))

    # Always add general interview practice
    todos.append(_make_todo(
        task="Practice speaking answers aloud — record yourself and review for clarity and professional tone.",
        category="interview",
        priority="low",
        estimated_hours=2.0,
        difficulty="easy",
        resource_note="Avoid filler words (um, uh, like, basically) and maintain professional tone.",
    ))

    return todos


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _make_todo(
    task:            str,
    category:        str   = "skill_development",
    priority:        str   = "medium",
    estimated_hours: float = 1.0,
    difficulty:      str   = "medium",
    resource_url:    str   = None,
    resource_note:   str   = None,
) -> dict:
    return {
        "task":            task,
        "category":        category,
        "priority":        priority,
        "estimated_hours": estimated_hours,
        "difficulty":      difficulty,
        "resource_url":    resource_url,
        "resource_note":   resource_note,
        "status":          "pending",
    }


def _estimate_learning_hours(skill: str) -> float:
    """Rough estimate of hours to learn a skill to working level."""
    quick  = {"git", "html", "css", "sql", "linux", "agile", "scrum"}
    medium = {"python", "javascript", "react", "flask", "django",
              "mysql", "mongodb", "docker", "rest api", "nodejs"}
    hard   = {"machine learning", "deep learning", "nlp", "kubernetes",
              "aws", "tensorflow", "pytorch", "system design"}

    if skill.lower() in quick:  return 8.0
    if skill.lower() in medium: return 20.0
    if skill.lower() in hard:   return 40.0
    return 15.0


def _estimate_difficulty(skill: str) -> str:
    """Estimate difficulty level of learning a skill."""
    easy   = {"git", "html", "css", "sql", "linux", "agile", "scrum", "rest api"}
    hard   = {"machine learning", "deep learning", "nlp", "kubernetes",
              "system design", "tensorflow", "pytorch", "microservices"}

    if skill.lower() in easy: return "easy"
    if skill.lower() in hard: return "hard"
    return "medium"
