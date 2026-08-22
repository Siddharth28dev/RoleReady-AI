from app.extensions import db

class InterviewQuestion(db.Model):
    __tablename__ = "interview_questions"

    id              = db.Column(db.Integer, primary_key=True)
    session_id      = db.Column(db.Integer, db.ForeignKey("interview_sessions.id"), nullable=False)
    question_text   = db.Column(db.Text, nullable=False)
    question_type   = db.Column(db.Enum("technical", "behavioral", "situational", "problem_solving"), nullable=False)
    difficulty      = db.Column(db.Enum("easy", "medium", "hard"), default="easy")
    expected_answer = db.Column(db.Text(4294967295))  # LONGTEXT
    skill_id        = db.Column(db.Integer, db.ForeignKey("skills.id"), nullable=True)
    question_order  = db.Column(db.Integer, default=1)

    # Relationships
    session   = db.relationship("InterviewSession",  back_populates="questions")
    skill     = db.relationship("Skill")
    keywords  = db.relationship("QuestionKeyword",   back_populates="question", cascade="all, delete")
    responses = db.relationship("InterviewResponse", back_populates="question", cascade="all, delete")

    def to_dict(self):
        return {
            "id":             self.id,
            "session_id":     self.session_id,
            "question_text":  self.question_text,
            "question_type":  self.question_type,
            "difficulty":     self.difficulty,
            "skill":          self.skill.skill_name if self.skill else None,
            "order":          self.question_order,
        }


class QuestionKeyword(db.Model):
    __tablename__ = "question_keywords"

    id          = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("interview_questions.id"), nullable=False)
    keyword     = db.Column(db.String(100), nullable=False)

    question = db.relationship("InterviewQuestion", back_populates="keywords")