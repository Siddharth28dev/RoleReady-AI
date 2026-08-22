from app.extensions import db


class SkillGap(db.Model):
    """
    Records skills present in JD but missing/weak in candidate resume.

    Paper: "The system categorizes gaps by severity based on whether they
            represent core requirements or preferred qualifications,
            enabling prioritization of development efforts."

    gap_type  → 'core' (must-have) or 'preferred' (good-to-have)
    severity  → 'high' / 'medium' / 'low'  (based on semantic similarity score)

    Logic:
        core     + similarity < 0.3  → severity = high
        core     + similarity < 0.6  → severity = medium
        preferred + any similarity   → severity = low
    """
    __tablename__ = "skill_gaps"

    id        = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=False)
    skill_id  = db.Column(db.Integer, db.ForeignKey("skills.id"),  nullable=False)

    # Paper Problem 1 fix: core vs preferred distinction
    gap_type  = db.Column(db.Enum("core", "preferred"), default="core", nullable=False)
    severity  = db.Column(db.Enum("high", "medium", "low"), default="medium", nullable=False)

    resume = db.relationship("Resume", back_populates="skill_gaps")
    skill  = db.relationship("Skill",  back_populates="skill_gaps")

    def to_dict(self):
        return {
            "id":       self.id,
            "skill":    self.skill.skill_name if self.skill else None,
            "gap_type": self.gap_type,
            "severity": self.severity,
        }
