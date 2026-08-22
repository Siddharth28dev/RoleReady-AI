from app.extensions import db
from datetime import datetime
from app.services.encryption_service import encrypt_if_not_empty, decrypt_if_not_empty


class Resume(db.Model):
    __tablename__ = "resumes"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    file_name    = db.Column(db.String(255))
    _resume_text = db.Column("resume_text", db.Text(4294967295))
    _education   = db.Column("education",   db.Text)
    _experience  = db.Column("experience",  db.Text)
    uploaded_at  = db.Column(db.DateTime, default=datetime.utcnow)

    user               = db.relationship("User",             back_populates="resumes")
    resume_skills      = db.relationship("ResumeSkill",      back_populates="resume", cascade="all, delete")
    skill_gaps         = db.relationship("SkillGap",         back_populates="resume", cascade="all, delete")
    interview_sessions = db.relationship("InterviewSession", back_populates="resume", cascade="all, delete")

    @property
    def resume_text(self) -> str:
        return decrypt_if_not_empty(self._resume_text)

    @resume_text.setter
    def resume_text(self, value: str):
        self._resume_text = encrypt_if_not_empty(value)

    @property
    def education(self) -> str:
        return decrypt_if_not_empty(self._education)

    @education.setter
    def education(self, value: str):
        self._education = encrypt_if_not_empty(value)

    @property
    def experience(self) -> str:
        return decrypt_if_not_empty(self._experience)

    @experience.setter
    def experience(self, value: str):
        self._experience = encrypt_if_not_empty(value)

    def to_dict(self):
        return {
            "id":          self.id,
            "user_id":     self.user_id,
            "file_name":   self.file_name,
            "education":   self.education,
            "experience":  self.experience,
            "uploaded_at": str(self.uploaded_at),
        }