import os
import threading
from flask import Flask
from app.config import get_config
from app.extensions import cors, db, migrate, jwt


def _warm_up_models():
    """
    Load FLAN-T5 (base model + fine-tuned LoRA adapter) into memory at
    startup instead of waiting for the first real request to pay the
    cold-start cost. This is what was causing the frontend's "Evaluation
    failed: timeout of 60000ms exceeded" error — the first interview
    request had to both load the model AND generate, blowing past the
    60s (now increased to 180s, but still: users shouldn't wait on this).
    Runs in a background thread so /api/health responds immediately.
    """
    try:
        from app.services.question_service import _get_model as _load_question_model
        from app.services.evaluation_service import _get_t5 as _load_eval_model
        print("[warm-up] Loading FLAN-T5 models into memory...")
        _load_question_model()
        _load_eval_model()
        print("[warm-up] Models loaded — ready for fast inference.")
    except Exception as e:
        print(f"[warm-up] Model warm-up failed (will lazy-load on first request instead): {e}")


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    with app.app_context():
        from app.models import (               # noqa: F401
            User, Resume,
            Skill, ResumeSkill,
            Role, RoleSkill,
            SkillGap,
            InterviewSession,
            InterviewQuestion, QuestionKeyword,
            InterviewResponse,
            ResponseEvaluation,
            FeedbackReport,
            TodoItem,
        )

    # Blueprints
    from app.routes.auth_routes      import auth_bp
    from app.routes.resume_routes    import resume_bp
    from app.routes.analysis_routes  import analysis_bp
    from app.routes.interview_routes import interview_bp
    from app.routes.feedback_routes  import feedback_bp
    from app.routes.bias_routes      import bias_bp

    app.register_blueprint(auth_bp,      url_prefix="/api/auth")
    app.register_blueprint(resume_bp,    url_prefix="/api/resume")
    app.register_blueprint(analysis_bp,  url_prefix="/api/analysis")
    app.register_blueprint(interview_bp, url_prefix="/api/interview")
    app.register_blueprint(feedback_bp,  url_prefix="/api/feedback")
    app.register_blueprint(bias_bp,      url_prefix="/api/bias")

    @app.route("/api/health")
    def health():
        return {
            "status":  "ok",
            "message": "AI Resume Analyzer API is running",
            "routes": [
                "POST /api/auth/register",
                "POST /api/auth/login",
                "GET  /api/auth/me",
                "POST /api/resume/upload",
                "GET  /api/analysis/roles",
                "POST /api/analysis/skill-gap-by-role",
                "POST /api/analysis/skill-gap",
                "POST /api/analysis/similarity",
                "POST /api/interview/generate-questions",
                "POST /api/interview/evaluate",
                "POST /api/interview/evaluate-all",
                "POST /api/feedback/generate",
                "POST /api/feedback/todo",
                "DELETE /api/feedback/delete-account",
                "POST /api/bias/audit-jd",
                "POST /api/bias/audit-feedback",
                "POST /api/bias/score-consistency",
                "POST /api/bias/transparency",
            ]
        }, 200
    
    from sqlalchemy import text

    try:
       with app.app_context():
          db.session.execute(text("SELECT 1"))
          print("Database connection successful!")
    except Exception as e:
       print("Database connection failed!")
       print(e)

    # Warm up FLAN-T5 in the background so the first real interview request
    # is fast. The WERKZEUG_RUN_MAIN check avoids loading the model twice —
    # Flask's debug reloader spawns a parent watcher process and a child
    # worker process; only the child (which actually serves requests) needs
    # the model loaded.
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=_warm_up_models, daemon=True).start()

    return app