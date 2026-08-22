from app.extensions import db
from datetime import datetime
from app.services.encryption_service import encrypt_if_not_empty, decrypt_if_not_empty


class InterviewResponse(db.Model):
    __tablename__ = "interview_responses"

    id            = db.Column(db.Integer, primary_key=True)
    question_id   = db.Column(db.Integer, db.ForeignKey("interview_questions.id"), nullable=False)
    _answer_text  = db.Column("answer_text", db.Text(4294967295))
    audio_path    = db.Column(db.String(500))
    response_time = db.Column(db.Integer)
    answered_at   = db.Column(db.DateTime, default=datetime.utcnow)

    question   = db.relationship("InterviewQuestion",  back_populates="responses")
    evaluation = db.relationship("ResponseEvaluation", back_populates="response",
                                  cascade="all, delete", uselist=False)

    @property
    def answer_text(self) -> str:
        return decrypt_if_not_empty(self._answer_text)

    @answer_text.setter
    def answer_text(self, value: str):
        self._answer_text = encrypt_if_not_empty(value)

    def to_dict(self):
        return {
            "id":            self.id,
            "question_id":   self.question_id,
            "answer_text":   self.answer_text,
            "response_time": self.response_time,
            "answered_at":   str(self.answered_at),
        }