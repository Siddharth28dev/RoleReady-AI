from app.services.question_service import generate_interview_questions
from app.services.evaluation_service import evaluate_answer, evaluate_multiple_answers
from app.extensions import db
from app.models import (
    InterviewSession, InterviewQuestion, InterviewResponse,
    ResponseEvaluation, Skill,
)


# question_service's internal type names -> InterviewQuestion.question_type Enum
_VALID_TYPES = {"technical", "behavioral", "situational", "problem_solving"}


def handle_generate_questions(data: dict) -> tuple[dict, int]:
    job_role           = data.get("job_role", "").strip()
    resume_text        = data.get("resume_text", "").strip()
    skill_gaps         = data.get("skill_gaps", [])
    matched_skills     = data.get("matched_skills", [])
    experience_level   = data.get("experience_level", "fresher")
    questions_per_type = int(data.get("questions_per_type", 3))

    # New — needed to persist the session. resume_id is required (every
    # session must belong to a real, saved resume); user_id/role_id come
    # from the authenticated request / role-selection stage.
    user_id   = data.get("user_id")
    resume_id = data.get("resume_id")
    role_id   = data.get("role_id")  # optional — nullable in the schema

    if not job_role:
        return {"success": False, "error": "job_role is required"}, 400
    if not resume_text:
        return {"success": False, "error": "resume_text is required"}, 400
    if not user_id:
        return {"success": False, "error": "user_id is required"}, 400
    if not resume_id:
        return {"success": False, "error": "resume_id is required (upload a resume first)"}, 400

    try:
        result = generate_interview_questions(
            job_role=job_role,
            resume_text=resume_text,
            skill_gaps=skill_gaps,
            matched_skills=matched_skills,
            experience_level=experience_level,
            questions_per_type=questions_per_type,
        )
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

    # ── Persist InterviewSession + InterviewQuestion rows ───────────────────
    try:
        session = InterviewSession(user_id=user_id, resume_id=resume_id, role_id=role_id)
        db.session.add(session)
        db.session.flush()

        order = 1
        for q_type, items in result["questions"].items():
            db_type = q_type if q_type in _VALID_TYPES else "technical"
            for item in items:
                skill_id = None
                skill_name = item.get("skill")
                if skill_name:
                    skill = Skill.query.filter_by(skill_name=skill_name).first()
                    if not skill:
                        skill = Skill(skill_name=skill_name)
                        db.session.add(skill)
                        db.session.flush()
                    skill_id = skill.id

                q_row = InterviewQuestion(
                    session_id     = session.id,
                    question_text  = item.get("question", ""),
                    question_type  = db_type,
                    difficulty     = item.get("difficulty") or "easy",
                    skill_id       = skill_id,
                    question_order = order,
                )
                db.session.add(q_row)
                db.session.flush()
                item["id"] = q_row.id  # frontend carries this through to /evaluate-all
                order += 1

        db.session.commit()
        result["session_id"] = session.id
    except Exception as e:
        db.session.rollback()
        # Candidate can still take the interview even if persistence fails —
        # just without a session_id, so evaluate-all will skip saving too.
        result["session_id"] = None
        result["persistence_error"] = str(e)

    return {"success": True, "data": result}, 200


def handle_evaluate_answer(data: dict) -> tuple[dict, int]:
    """Evaluate a single candidate answer."""
    question         = data.get("question", "").strip()
    candidate_answer = data.get("candidate_answer", "").strip()
    question_type    = data.get("question_type", "technical")
    skill            = data.get("skill", "")
    job_role         = data.get("job_role", "")

    if not question:
        return {"success": False, "error": "question is required"}, 400
    if not candidate_answer:
        return {"success": False, "error": "candidate_answer is required"}, 400

    try:
        result = evaluate_answer(
            question=question,
            candidate_answer=candidate_answer,
            question_type=question_type,
            skill=skill,
            job_role=job_role,
        )
        return {"success": True, "evaluation": result}, 200
    except Exception as e:
        return {"success": False, "error": str(e)}, 500


def _persist_response(question_id: int, answer_text: str, result: dict) -> None:
    """Save one InterviewResponse + its ResponseEvaluation."""
    response = InterviewResponse(question_id=question_id, answer_text=answer_text)
    db.session.add(response)
    db.session.flush()

    dims = result.get("dimensions", {})
    evaluation = ResponseEvaluation(
        response_id        = response.id,
        semantic_score      = result.get("score", 0),
        keyword_score        = dims.get("keyword_coverage", {}).get("score", 0),
        grammar_score        = dims.get("language_quality", {}).get("score", 0),
        completeness_score   = dims.get("completeness", {}).get("score", 0),
        final_score          = result.get("score", 0),
        rating                = result.get("rating", ""),
    )
    db.session.add(evaluation)


def handle_evaluate_multiple(data: dict) -> tuple[dict, int]:
    """
    Evaluate multiple answers at once, and persist each as an
    InterviewResponse + ResponseEvaluation if session_id/question ids
    were supplied (they are, once the frontend carries the ids through
    from /generate-questions).

    Body: { session_id?, answers: [ { question_id?, question,
            candidate_answer, question_type, skill, job_role } ] }
    """
    answers    = data.get("answers", [])
    session_id = data.get("session_id")

    if not answers or not isinstance(answers, list):
        return {"success": False, "error": "answers must be a non-empty list"}, 400

    try:
        result = evaluate_multiple_answers(answers)
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

    # ── Persist responses + evaluations, and roll up the session score ──────
    try:
        for item, individual in zip(answers, result.get("individual_results", [])):
            question_id = item.get("question_id")
            if question_id:
                _persist_response(question_id, item.get("candidate_answer", ""), individual)

        if session_id:
            from datetime import datetime
            session = db.session.get(InterviewSession, session_id)
            if session:
                session.total_score  = result.get("overall_score", 0)
                session.completed_at = datetime.utcnow()

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        result["persistence_error"] = str(e)

    return {"success": True, "data": result}, 200