from app.services.similarity_service import (
    analyze,
    jd_resume_score,
    analyze_by_role,
)
from app.models import Role, RoleSkill, SkillGap, Skill, Resume
from app.extensions import db


def handle_skill_gap(data: dict) -> tuple[dict, int]:
    """
    POST /api/analysis/skill-gap
    Body: { jd_text, resume_text, resume_skills, experience_level? }
    Uses MiniLM semantic matching — no keyword matching.

    NOTE: this is the freeform-JD-paste path. For the paper's primary flow
    ("Users select their desired job role from a categorized database" —
    §5 Target Role Selection), use handle_skill_gap_by_role instead, which
    matches against the curated Role/RoleSkill DB tables.
    """
    jd_text          = data.get("jd_text", "").strip()
    resume_text      = data.get("resume_text", "").strip()
    resume_skills    = data.get("resume_skills", [])
    experience_level = data.get("experience_level", None)

    if not jd_text:
        return {"success": False, "error": "jd_text is required"}, 400
    if not resume_text:
        return {"success": False, "error": "resume_text is required"}, 400
    if not resume_skills or not isinstance(resume_skills, list):
        return {"success": False, "error": "resume_skills must be a non-empty list"}, 400

    try:
        result = analyze(jd_text, resume_text, resume_skills, experience_level)
        return {"success": True, "analysis": result}, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def handle_similarity(data: dict) -> tuple[dict, int]:
    """
    POST /api/analysis/similarity
    Body: { jd_text, resume_text }
    Quick overall semantic similarity score.
    """
    jd_text     = data.get("jd_text", "").strip()
    resume_text = data.get("resume_text", "").strip()

    if not jd_text or not resume_text:
        return {"success": False, "error": "jd_text and resume_text are required"}, 400

    try:
        result = jd_resume_score(jd_text, resume_text)
        return {"success": True, "similarity": result}, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def handle_list_roles() -> tuple[dict, int]:
    """
    GET /api/analysis/roles
    Paper §5 "Target Role Selection": "Users select their desired job role
    from a categorized database spanning multiple industries and seniority
    levels. The system displays role requirements and expected competencies."
    """
    try:
        roles = Role.query.order_by(Role.industry, Role.role_name).all()
        return {
            "success": True,
            "roles": [
                {
                    **r.to_dict(),
                    "required_skills": [rs.to_dict() for rs in r.role_skills],
                }
                for r in roles
            ],
        }, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def handle_skill_gap_by_role(data: dict) -> tuple[dict, int]:
    """
    POST /api/analysis/skill-gap-by-role
    Body: { role_id, resume_text, resume_skills, resume_id? }

    Paper-primary flow: matches the candidate's resume against a curated
    Role's RoleSkill requirements (core/preferred pulled straight from the
    DB), rather than a freeform pasted JD. If resume_id is given, the
    resulting gaps are persisted to the skill_gaps table (paper: "The
    system categorizes gaps by severity... enabling prioritization of
    development efforts" — question_service reads these back later).
    """
    role_id       = data.get("role_id")
    resume_text   = data.get("resume_text", "").strip()
    resume_skills = data.get("resume_skills", [])
    resume_id     = data.get("resume_id")  # optional — enables persistence

    if not role_id:
        return {"success": False, "error": "role_id is required"}, 400
    if not resume_text:
        return {"success": False, "error": "resume_text is required"}, 400
    if not resume_skills or not isinstance(resume_skills, list):
        return {"success": False, "error": "resume_skills must be a non-empty list"}, 400

    role = Role.query.get(role_id)
    if not role:
        return {"success": False, "error": f"Role {role_id} not found"}, 404

    role_skills = [rs.to_dict() for rs in role.role_skills]  # [{"skill":, "gap_type":}, ...]
    if not role_skills:
        return {"success": False, "error": f"Role '{role.role_name}' has no configured required skills"}, 400

    try:
        result = analyze_by_role(
            role_skills       = role_skills,
            resume_text       = resume_text,
            resume_skills     = resume_skills,
            role_description  = role.description or "",
        )

        if resume_id:
            _persist_skill_gaps(resume_id, result["gaps"])

        result["role"] = role.to_dict()
        return {"success": True, "analysis": result}, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def _persist_skill_gaps(resume_id: int, gaps: list) -> None:
    """
    Replace any existing skill_gaps rows for this resume with the freshly
    computed set — idempotent re-analysis (e.g. after resume re-upload).
    """
    resume = Resume.query.get(resume_id)
    if not resume:
        return  # silently skip persistence if resume_id is invalid; analysis result is still returned

    SkillGap.query.filter_by(resume_id=resume_id).delete()

    for gap in gaps:
        skill = Skill.query.filter_by(skill_name=gap["skill"]).first()
        if not skill:
            skill = Skill(skill_name=gap["skill"])
            db.session.add(skill)
            db.session.flush()  # get skill.id before using it below

        db.session.add(SkillGap(
            resume_id = resume_id,
            skill_id  = skill.id,
            gap_type  = gap["gap_type"],
            severity  = gap["severity"],
        ))

    db.session.commit()