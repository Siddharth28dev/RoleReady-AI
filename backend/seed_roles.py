"""
seed_roles.py
─────────────
Paper §3 "Role Mapping and Skill Assessment":
  "Job role definitions are constructed from a curated database of position
   descriptions covering common roles across multiple industries. Each role
   specification enumerates required technical skills, soft skills,
   educational qualifications, and experience levels."

Paper §5 "Target Role Selection":
  "Users select their desired job role from a categorized database spanning
   multiple industries and seniority levels."

Populates Role / RoleSkill / Skill so /api/analysis/roles has something to
serve and /api/analysis/skill-gap-by-role has data to match against.
Idempotent — safe to re-run (skips roles/skills that already exist).

Usage:
    python seed_roles.py
"""

from app import create_app
from app.extensions import db
from app.models import Role, Skill, RoleSkill

# Reusable soft-skill sets, layered in alongside technical skills below —
# this is what was missing before: seed data had ZERO soft skills despite
# the paper (and the RoleSkill docstring) explicitly promising them as part
# of every role specification.
IC_SOFT_SKILLS_PREFERRED   = ["communication", "teamwork", "problem solving"]
LEAD_SOFT_SKILLS_CORE      = ["leadership", "communication", "problem solving"]
LEAD_SOFT_SKILLS_PREFERRED = ["mentoring", "teamwork"]

# role_name -> (description, industry, experience_level, education_requirement,
#               core_skills, preferred_skills)
ROLES = [
    (
        "Backend Developer",
        "Builds server-side APIs, business logic, and database layers for web applications.",
        "Software Engineering", "fresher",
        "Bachelor's degree in Computer Science, IT, or related field (or equivalent practical experience)",
        ["python", "flask", "mysql", "rest api", "git", "problem solving"],
        ["postgresql", "redis", "aws", "ci/cd", "docker"] + IC_SOFT_SKILLS_PREFERRED,
    ),
    (
        "Frontend Developer",
        "Builds user interfaces, client-side logic, and interactive web experiences.",
        "Software Engineering", "fresher",
        "Bachelor's degree in Computer Science, IT, or related field (or equivalent practical experience)",
        ["javascript", "html", "css", "react", "git"],
        ["typescript", "tailwind", "webpack", "rest api"] + IC_SOFT_SKILLS_PREFERRED,
    ),
    (
        "Full Stack Developer",
        "Handles both frontend and backend development across the full web application stack.",
        "Software Engineering", "mid",
        "Bachelor's degree in Computer Science or related field; 2+ years professional experience",
        ["python", "javascript", "react", "flask", "mysql", "git", "rest api", "problem solving"],
        ["docker", "aws", "typescript", "nodejs", "mongodb"] + IC_SOFT_SKILLS_PREFERRED,
    ),
    (
        "Data Scientist",
        "Analyzes data and builds statistical/machine learning models to drive decisions.",
        "Data & AI", "mid",
        "Bachelor's/Master's in Computer Science, Statistics, Mathematics, or related quantitative field",
        ["python", "machine learning", "pandas", "numpy", "sql", "problem solving"],
        ["deep learning", "tensorflow", "pytorch", "scikit-learn"] + IC_SOFT_SKILLS_PREFERRED,
    ),
    (
        "ML Engineer",
        "Deploys, scales, and optimizes machine learning models in production systems.",
        "Data & AI", "mid",
        "Bachelor's/Master's in Computer Science, Data Science, or related field; 2+ years experience",
        ["python", "machine learning", "pytorch", "docker", "rest api", "problem solving"],
        ["kubernetes", "aws", "tensorflow", "ci/cd"] + IC_SOFT_SKILLS_PREFERRED,
    ),
    (
        "DevOps Engineer",
        "Manages CI/CD pipelines, cloud infrastructure, and deployment automation.",
        "Infrastructure", "mid",
        "Bachelor's degree in Computer Science, IT, or related field; 2+ years infrastructure experience",
        ["docker", "kubernetes", "ci/cd", "linux", "git", "problem solving"],
        ["aws", "terraform", "ansible", "python"] + IC_SOFT_SKILLS_PREFERRED,
    ),
    # ── Senior-level roles ─────────────────────────────────────────────────
    # Paper explicitly says the role database should span "seniority levels"
    # (plural) — prior seed data only ever populated fresher/mid, never senior.
    (
        "Senior Backend Developer / Tech Lead",
        "Leads backend architecture decisions, mentors junior engineers, and owns "
        "system design for high-scale services.",
        "Software Engineering", "senior",
        "Bachelor's/Master's in Computer Science or related field; 5+ years professional experience",
        ["python", "flask", "mysql", "rest api", "microservices", "system design"] + LEAD_SOFT_SKILLS_CORE,
        ["docker", "kubernetes", "aws", "ci/cd"] + LEAD_SOFT_SKILLS_PREFERRED,
    ),
    (
        "Senior Data Scientist / ML Lead",
        "Leads end-to-end ML initiatives, sets technical direction for the data team, "
        "and translates business problems into modeling strategy.",
        "Data & AI", "senior",
        "Master's/PhD in Computer Science, Statistics, or related quantitative field; 5+ years experience",
        ["python", "machine learning", "deep learning", "system design"] + LEAD_SOFT_SKILLS_CORE,
        ["tensorflow", "pytorch", "aws", "docker"] + LEAD_SOFT_SKILLS_PREFERRED,
    ),
]


def seed():
    app = create_app()
    with app.app_context():
        for role_name, description, industry, exp_level, education, core, preferred in ROLES:
            role = Role.query.filter_by(role_name=role_name).first()
            if not role:
                role = Role(
                    role_name=role_name, description=description,
                    industry=industry, experience_level=exp_level,
                    education_requirement=education,
                )
                db.session.add(role)
                db.session.flush()
                print(f"[seed] Created role: {role_name} ({exp_level})")
            else:
                # Backfill education_requirement on existing rows from an
                # earlier seed run that predates this column.
                if not role.education_requirement:
                    role.education_requirement = education
                print(f"[seed] Role already exists, skipping creation: {role_name}")

            for skill_list, gap_type in [(core, "core"), (preferred, "preferred")]:
                for skill_name in skill_list:
                    skill = Skill.query.filter_by(skill_name=skill_name).first()
                    if not skill:
                        skill = Skill(skill_name=skill_name)
                        db.session.add(skill)
                        db.session.flush()

                    exists = RoleSkill.query.filter_by(role_id=role.id, skill_id=skill.id).first()
                    if not exists:
                        db.session.add(RoleSkill(role_id=role.id, skill_id=skill.id, gap_type=gap_type))

        db.session.commit()

        by_level = {}
        for r in Role.query.all():
            by_level[r.experience_level] = by_level.get(r.experience_level, 0) + 1
        print(f"[seed] Done. {Role.query.count()} roles, {Skill.query.count()} skills in DB.")
        print(f"[seed] Seniority spread: {by_level}")


if __name__ == "__main__":
    seed()