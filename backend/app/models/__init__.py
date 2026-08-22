# models/__init__.py
# ------------------
# Only purpose: make all models importable as a package.
# create_app() lives in app/__init__.py — NOT here.
# Flask-Migrate needs all models imported so it can detect tables.

from app.models.user_model                import User
from app.models.resume_model              import Resume
from app.models.skill_model               import Skill, ResumeSkill
from app.models.role_model                import Role, RoleSkill
from app.models.skill_gap_model           import SkillGap
from app.models.interview_session_model   import InterviewSession
from app.models.interview_question_model  import InterviewQuestion, QuestionKeyword
from app.models.interview_response_model  import InterviewResponse
from app.models.response_evaluation_model import ResponseEvaluation
from app.models.feedback_model            import FeedbackReport
from app.models.todo_model                import TodoItem

__all__ = [
    "User", "Resume",
    "Skill", "ResumeSkill",
    "Role", "RoleSkill",
    "SkillGap",
    "InterviewSession",
    "InterviewQuestion", "QuestionKeyword",
    "InterviewResponse",
    "ResponseEvaluation",
    "FeedbackReport",
    "TodoItem",
]