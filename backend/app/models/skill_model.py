from app.extensions import db


class Skill(db.Model):
    """
    Master skill table — every unique skill stored once.
    Referenced by ResumeSkill, RoleSkill, and SkillGap.
    """
    __tablename__ = "skills"

    id         = db.Column(db.Integer, primary_key=True)
    skill_name = db.Column(db.String(100), unique=True, nullable=False)

    # Relationships
    resume_skills = db.relationship("ResumeSkill", back_populates="skill")
    role_skills   = db.relationship("RoleSkill",   back_populates="skill")
    skill_gaps    = db.relationship("SkillGap",    back_populates="skill")

    def to_dict(self):
        return {"id": self.id, "skill_name": self.skill_name}


class ResumeSkill(db.Model):
    """
    Junction table — which skills does a resume have?
    """
    __tablename__ = "resume_skills"

    id        = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=False)
    skill_id  = db.Column(db.Integer, db.ForeignKey("skills.id"),  nullable=False)

    resume = db.relationship("Resume", back_populates="resume_skills")
    skill  = db.relationship("Skill",  back_populates="resume_skills")

    __table_args__ = (
        db.UniqueConstraint("resume_id", "skill_id", name="unique_resume_skill"),
    )

    def to_dict(self):
        return {
            "skill": self.skill.skill_name if self.skill else None,
        }
