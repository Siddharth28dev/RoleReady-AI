from flask import Blueprint, request, jsonify
from app.services.bias_service import (
    audit_job_description,
    audit_feedback,
    audit_score_consistency,
    generate_transparency_report,
)

bias_bp = Blueprint("bias", __name__)


@bias_bp.route("/audit-jd", methods=["POST"])
def audit_jd():
    """
    POST /api/bias/audit-jd
    Audit job description for biased language.
    Body: { jd_text: string }
    """
    data = request.get_json()
    if not data or not data.get("jd_text"):
        return jsonify({"success": False, "error": "jd_text is required"}), 400
    result = audit_job_description(data["jd_text"])
    return jsonify({"success": True, "audit": result}), 200


@bias_bp.route("/audit-feedback", methods=["POST"])
def audit_fb():
    """
    POST /api/bias/audit-feedback
    Audit generated feedback for biased language.
    Body: { feedback_text: string }
    """
    data = request.get_json()
    if not data or not data.get("feedback_text"):
        return jsonify({"success": False, "error": "feedback_text is required"}), 400
    result = audit_feedback(data["feedback_text"])
    return jsonify({"success": True, "audit": result}), 200


@bias_bp.route("/score-consistency", methods=["POST"])
def score_consistency():
    """
    POST /api/bias/score-consistency
    Check score consistency across profiles.
    Body: { scores: [{ profile_id, overall_score }] }
    """
    data = request.get_json()
    if not data or not data.get("scores"):
        return jsonify({"success": False, "error": "scores array is required"}), 400
    result = audit_score_consistency(data["scores"])
    return jsonify({"success": True, "consistency": result}), 200


@bias_bp.route("/transparency", methods=["POST"])
def transparency():
    """
    POST /api/bias/transparency
    Explain how overall score was calculated.
    Body: { resume_score, skill_score, interview_score, overall_score }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    result = generate_transparency_report(
        resume_score    = data.get("resume_score",    0),
        skill_score     = data.get("skill_score",     0),
        interview_score = data.get("interview_score", 0),
        overall_score   = data.get("overall_score",   0),
    )
    return jsonify({"success": True, "report": result}), 200


@bias_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "Bias audit service is up"}), 200
# EOF
# echo "bias_routes.py created ✅"