from app.extensions import db
from datetime import datetime

class FeedbackReport(db.Model):
    __tablename__ = "feedback_reports"

    id              = db.Column(db.Integer, primary_key=True)
    session_id      = db.Column(db.Integer, db.ForeignKey("interview_sessions.id"), nullable=False)
    strengths       = db.Column(db.Text)
    weaknesses      = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    session    = db.relationship("InterviewSession", back_populates="feedbacks")
    todo_items = db.relationship("TodoItem",         back_populates="feedback", cascade="all, delete")

    def to_dict(self):
        return {
            "id":              self.id,
            "session_id":      self.session_id,
            "strengths":       self.strengths,
            "weaknesses":      self.weaknesses,
            "recommendations": self.recommendations,
            "created_at":      str(self.created_at),
        }