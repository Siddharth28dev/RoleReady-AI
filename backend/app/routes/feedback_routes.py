from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controllers.feedback_controller import (
    handle_generate_feedback,
    handle_generate_todo,
    handle_delete_user_data,
)

feedback_bp = Blueprint("feedback", __name__)


@feedback_bp.route("/generate", methods=["POST"])
@jwt_required()
def generate_feedback():
    """
    POST /api/feedback/generate  (requires auth)
    Body: { resume_data, skill_gap_data, interview_data?, job_role, session_id? }
    Persists the report + to-do list when session_id is given.
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_generate_feedback(data)
    return jsonify(result), status


@feedback_bp.route("/todo", methods=["POST"])
@jwt_required()
def generate_todo():
    """
    POST /api/feedback/todo  (requires auth)
    Generate prioritized to-do list (standalone, not persisted).
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_generate_todo(data)
    return jsonify(result), status


@feedback_bp.route("/delete-account", methods=["DELETE"])
@jwt_required()
def delete_user_data():
    """
    DELETE /api/feedback/delete-account  (requires auth)
    Paper: "Candidates retain ownership of their information
            and can request deletion at any time."
    SECURITY FIX: the user to delete is taken from the JWT identity,
    not a body field — previously this endpoint accepted a raw
    user_id in the request body with no check that it belonged to
    the caller, letting anyone delete anyone else's account.
    """
    user_id = int(get_jwt_identity())
    result, status = handle_delete_user_data(user_id)
    return jsonify(result), status


@feedback_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "Feedback service is up"}), 200