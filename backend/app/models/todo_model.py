from app.extensions import db
from datetime import datetime


class TodoItem(db.Model):
    """
    Personalized to-do checklist item.

    Paper: "Recommendation generation creates personalized to-do checklists
            specifying concrete actions candidates can take to address identified issues."

    Paper: "Estimated time commitments and difficulty levels help candidates
            plan development activities realistically."

    Paper: "Progress tracking functionality allows candidates to mark completed items."
    """
    __tablename__ = "todo_items"

    id              = db.Column(db.Integer, primary_key=True)
    feedback_id     = db.Column(db.Integer, db.ForeignKey("feedback_reports.id"), nullable=False)
    task            = db.Column(db.Text, nullable=False)
    category        = db.Column(
        db.Enum("resume", "interview", "skill_development"), default="skill_development"
    )
    priority        = db.Column(db.Enum("high", "medium", "low"),      default="medium")
    status          = db.Column(db.Enum("pending", "completed"),        default="pending")

    # Paper fix: time estimates + difficulty
    estimated_hours = db.Column(db.Float, default=1.0)
    difficulty      = db.Column(db.Enum("easy", "medium", "hard"),      default="medium")

    resource_url    = db.Column(db.String(500))
    resource_note   = db.Column(db.String(200))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    feedback = db.relationship("FeedbackReport", back_populates="todo_items")

    def to_dict(self):
        return {
            "id":              self.id,
            "task":            self.task,
            "category":        self.category,
            "priority":        self.priority,
            "status":          self.status,
            "estimated_hours": self.estimated_hours,
            "difficulty":      self.difficulty,
            "resource_url":    self.resource_url,
            "resource_note":   self.resource_note,
        }
