from app.extensions import db

class ResponseEvaluation(db.Model):
    __tablename__ = "response_evaluations"

    id                 = db.Column(db.Integer, primary_key=True)
    response_id        = db.Column(db.Integer, db.ForeignKey("interview_responses.id"), nullable=False)
    semantic_score     = db.Column(db.Numeric(5, 2), default=0.00)   # MiniLM cosine * 100
    keyword_score      = db.Column(db.Numeric(5, 2), default=0.00)   # keyword coverage %
    grammar_score      = db.Column(db.Numeric(5, 2), default=0.00)   # language quality
    completeness_score = db.Column(db.Numeric(5, 2), default=0.00)   # answer detail
    final_score        = db.Column(db.Numeric(5, 2), default=0.00)   # weighted average
    rating             = db.Column(db.String(20))                    # Excellent/Good/Average/Poor

    response = db.relationship("InterviewResponse", back_populates="evaluation")

    def to_dict(self):
        return {
            "id":                 self.id,
            "semantic_score":     float(self.semantic_score),
            "keyword_score":      float(self.keyword_score),
            "grammar_score":      float(self.grammar_score),
            "completeness_score": float(self.completeness_score),
            "final_score":        float(self.final_score),
            "rating":             self.rating,
        }