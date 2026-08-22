from app.extensions import db


class Role(db.Model):
    """
    Represents a job role / position.
    Paper: "Job role definitions are constructed from a curated database
            of position descriptions covering common roles across multiple industries."
    """
    __tablename__ = "roles"

    id                     = db.Column(db.Integer, primary_key=True)
    role_name              = db.Column(db.String(150), unique=True, nullable=False)
    description            = db.Column(db.Text)
    industry               = db.Column(db.String(100))
    experience_level       = db.Column(
        db.Enum("fresher", "mid", "senior"), default="fresher"
    )
    # Paper: "...enumerates required technical skills, soft skills,
    # EDUCATIONAL QUALIFICATIONS, and experience levels." — this column was
    # previously missing entirely; the role spec had no way to express it.
    education_requirement  = db.Column(db.String(255))

    # Relationships
    role_skills        = db.relationship("RoleSkill",        back_populates="role", cascade="all, delete")
    interview_sessions = db.relationship("InterviewSession", back_populates="role")

    def to_dict(self):
        return {
            "id":                    self.id,
            "role_name":             self.role_name,
            "description":           self.description,
            "industry":              self.industry,
            "experience_level":      self.experience_level,
            "education_requirement": self.education_requirement,
        }


class RoleSkill(db.Model):
    """
    Junction table — which skills does a role require?
    Paper: "Each role specification enumerates required technical skills,
            soft skills, educational qualifications, and experience levels."
    gap_type distinguishes CORE vs PREFERRED requirements.
    Paper: "The system categorizes gaps by severity based on whether they
            represent core requirements or preferred qualifications."
    """
    __tablename__ = "role_skills"

    id       = db.Column(db.Integer, primary_key=True)
    role_id  = db.Column(db.Integer, db.ForeignKey("roles.id"),   nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id"),  nullable=False)
    gap_type = db.Column(
        db.Enum("core", "preferred"), default="core", nullable=False
    )

    role  = db.relationship("Role",  back_populates="role_skills")
    skill = db.relationship("Skill", back_populates="role_skills")

    __table_args__ = (
        db.UniqueConstraint("role_id", "skill_id", name="unique_role_skill"),
    )

    def to_dict(self):
        return {
            "skill":    self.skill.skill_name if self.skill else None,
            "gap_type": self.gap_type,
        }