from app.extensions import db
from datetime import datetime

class InterviewSession(db.Model):
    __tablename__ = "interview_sessions"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"),   nullable=False)
    resume_id    = db.Column(db.Integer, db.ForeignKey("resumes.id"),  nullable=False)
    role_id      = db.Column(db.Integer, db.ForeignKey("roles.id"),    nullable=True)
    total_score  = db.Column(db.Numeric(5, 2), default=0.00)
    started_at   = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    user       = db.relationship("User",   back_populates="interview_sessions")
    resume     = db.relationship("Resume", back_populates="interview_sessions")
    role       = db.relationship("Role",   back_populates="interview_sessions")
    questions  = db.relationship("InterviewQuestion", back_populates="session", cascade="all, delete")
    feedbacks  = db.relationship("FeedbackReport",    back_populates="session", cascade="all, delete")

    def to_dict(self):
        return {
            "id":           self.id,
            "user_id":      self.user_id,
            "resume_id":    self.resume_id,
            "role_id":      self.role_id,
            "total_score":  float(self.total_score) if self.total_score else 0,
            "started_at":   str(self.started_at),
            "completed_at": str(self.completed_at) if self.completed_at else None,
        }