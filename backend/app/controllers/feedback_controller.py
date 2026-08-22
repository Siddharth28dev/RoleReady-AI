from app.services.feedback_service import generate_feedback
from app.services.todo_service     import generate_todo_list
from app.extensions import db
from app.models import FeedbackReport, TodoItem


def handle_generate_feedback(data: dict) -> tuple[dict, int]:
    """
    Synthesize complete feedback report from 3 sources, and persist it
    (plus the generated to-do list) if a session_id is supplied.
    """
    resume_data    = data.get("resume_data",    {})
    skill_gap_data = data.get("skill_gap_data", {})
    interview_data = data.get("interview_data", {})
    job_role       = data.get("job_role", "")
    session_id     = data.get("session_id")

    if not resume_data:
        return {"success": False, "error": "resume_data is required"}, 400
    if not skill_gap_data:
        return {"success": False, "error": "skill_gap_data is required"}, 400

    try:
        feedback = generate_feedback(
            resume_data    = resume_data,
            skill_gap_data = skill_gap_data,
            interview_data = interview_data,
        )

        todos = generate_todo_list(
            resume_feedback    = feedback["resume_section"],
            skill_gap_data     = skill_gap_data,
            interview_feedback = feedback["interview_section"],
            job_role           = job_role,
        )
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

    # ── Persist FeedbackReport + TodoItem rows ───────────────────────────────
    persisted_todos = todos
    if session_id:
        try:
            report = FeedbackReport(
                session_id      = session_id,
                strengths       = "; ".join(
                    (feedback.get("resume_section", {}).get("strengths") or [])
                    + (feedback.get("skill_section", {}).get("strengths") or [])
                    + (feedback.get("interview_section", {}).get("strengths") or [])
                ),
                weaknesses      = "; ".join(
                    (feedback.get("resume_section", {}).get("weaknesses") or [])
                    + (feedback.get("skill_section", {}).get("weaknesses") or [])
                    + (feedback.get("interview_section", {}).get("weaknesses") or [])
                ),
                recommendations = "; ".join(t.get("task", "") for t in todos),
            )
            db.session.add(report)
            db.session.flush()

            todo_rows = []
            for t in todos:
                row = TodoItem(
                    feedback_id     = report.id,
                    task            = t.get("task", ""),
                    category        = t.get("category", "skill_development"),
                    priority        = t.get("priority", "medium"),
                    estimated_hours = t.get("estimated_hours", 1.0),
                    difficulty      = t.get("difficulty", "medium"),
                    resource_url    = t.get("resource_url"),
                    resource_note   = t.get("resource_note"),
                )
                db.session.add(row)
                db.session.flush()
                todo_rows.append(row.to_dict())

            db.session.commit()
            persisted_todos = todo_rows  # now includes real DB ids
        except Exception as e:
            db.session.rollback()
            feedback["persistence_error"] = str(e)

    return {
        "success":   True,
        "feedback":  feedback,
        "todo_list": persisted_todos,
        "todo_count": len(persisted_todos),
    }, 200


def handle_generate_todo(data: dict) -> tuple[dict, int]:
    """Generate to-do list independently (no persistence — used standalone)."""
    resume_feedback    = data.get("resume_feedback",    {})
    skill_gap_data     = data.get("skill_gap_data",     {})
    interview_feedback = data.get("interview_feedback", {})
    job_role           = data.get("job_role", "")

    if not skill_gap_data:
        return {"success": False, "error": "skill_gap_data is required"}, 400

    try:
        todos = generate_todo_list(
            resume_feedback    = resume_feedback,
            skill_gap_data     = skill_gap_data,
            interview_feedback = interview_feedback,
            job_role           = job_role,
        )
        return {
            "success":    True,
            "todo_list":  todos,
            "todo_count": len(todos),
        }, 200

    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def handle_delete_user_data(user_id: int) -> tuple[dict, int]:
    """
    Paper: "Candidates retain ownership of their information
            and can request deletion at any time."
    Deletes all data for the AUTHENTICATED user (taken from the JWT,
    not from the request body — previously this trusted a body user_id,
    which meant anyone could delete anyone else's account by ID).
    """
    try:
        from app.extensions import db
        from app.models     import User

        user = db.session.get(User, user_id)
        if not user:
            return {"success": False, "error": f"User {user_id} not found"}, 404

        db.session.delete(user)
        db.session.commit()

        return {
            "success": True,
            "message": f"All data for user {user_id} has been permanently deleted.",
        }, 200

    except Exception as e:
        return {"success": False, "error": str(e)}, 500