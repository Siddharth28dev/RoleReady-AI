from flask import Blueprint, request, jsonify
from app.controllers.analysis_controller import (
    handle_skill_gap,
    handle_similarity,
    handle_list_roles,
    handle_skill_gap_by_role,
)

analysis_bp = Blueprint("analysis", __name__)


@analysis_bp.route("/roles", methods=["GET"])
def list_roles():
    """
    GET /api/analysis/roles
    Paper §5 "Target Role Selection": categorized database of job roles
    with their required skills, for the frontend's role-selection dropdown.
    """
    result, status = handle_list_roles()
    return jsonify(result), status


@analysis_bp.route("/skill-gap-by-role", methods=["POST"])
def skill_gap_by_role():
    """
    POST /api/analysis/skill-gap-by-role
    Paper-primary flow: skill gap analysis against a curated Role's
    RoleSkill requirements (not a pasted JD).
    Body: { role_id, resume_text, resume_skills, resume_id? }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_skill_gap_by_role(data)
    return jsonify(result), status


@analysis_bp.route("/skill-gap", methods=["POST"])
def skill_gap():
    """
    POST /api/analysis/skill-gap
    Freeform-JD-paste semantic skill gap analysis (MiniLM powered).
    Secondary/advanced option — see /skill-gap-by-role for the paper's
    primary curated-role-selection flow.
    Body: { jd_text, resume_text, resume_skills, experience_level? }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_skill_gap(data)
    return jsonify(result), status


@analysis_bp.route("/similarity", methods=["POST"])
def similarity():
    """
    POST /api/analysis/similarity
    Quick JD vs resume semantic similarity score.
    Body: { jd_text, resume_text }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result, status = handle_similarity(data)
    return jsonify(result), status


@analysis_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "Analysis service is up"}), 200