from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.interview_controller import (
    handle_generate_questions,
    handle_evaluate_answer,
    handle_evaluate_multiple,
)

interview_bp = Blueprint("interview", __name__)


@interview_bp.route("/generate-questions", methods=["POST"])
@jwt_required()
def generate_questions():
    """
    POST /api/interview/generate-questions  (requires auth)
    Body: { job_role, resume_text, resume_id, role_id?, skill_gaps,
            matched_skills, experience_level?, questions_per_type? }

    Persists an InterviewSession + InterviewQuestion rows for the
    logged-in user, tied to the given resume_id.
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    data["user_id"] = int(get_jwt_identity())
    result, status = handle_generate_questions(data)
    return jsonify(result), status


@interview_bp.route("/evaluate", methods=["POST"])
@jwt_required()
def evaluate():
    """
    POST /api/interview/evaluate  (requires auth)
    Evaluate a single answer.
    Body: { question, candidate_answer, question_type, skill, job_role }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_evaluate_answer(data)
    return jsonify(result), status


@interview_bp.route("/evaluate-all", methods=["POST"])
@jwt_required()
def evaluate_all():
    """
    POST /api/interview/evaluate-all  (requires auth)
    Evaluate all answers at once and persist them.
    Body: { session_id?, answers: [ { question_id?, question,
            candidate_answer, question_type, skill, job_role } ] }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_evaluate_multiple(data)
    return jsonify(result), status


@interview_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "Interview service is up"}), 200