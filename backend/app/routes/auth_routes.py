from flask import Blueprint, request, jsonify
from marshmallow import ValidationError
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.controllers.auth_controller import handle_register, handle_login, handle_me
from app.schemas.auth_schema import RegisterSchema, LoginSchema

auth_bp = Blueprint("auth", __name__)
register_schema = RegisterSchema()
login_schema    = LoginSchema()


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    POST /api/auth/register
    Body: { name, email, password }
    Returns a JWT immediately — no separate login required after signup.
    """
    data = request.get_json() or {}
    try:
        clean = register_schema.load(data)
    except ValidationError as err:
        return jsonify({"success": False, "errors": err.messages}), 400

    result, status = handle_register(clean)
    return jsonify(result), status


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    POST /api/auth/login
    Body: { email, password }
    """
    data = request.get_json() or {}
    try:
        clean = login_schema.load(data)
    except ValidationError as err:
        return jsonify({"success": False, "errors": err.messages}), 400

    result, status = handle_login(clean)
    return jsonify(result), status


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """GET /api/auth/me — resolve the current user from the JWT."""
    user_id = get_jwt_identity()
    result, status = handle_me(user_id)
    return jsonify(result), status


@auth_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "Auth service is up"}), 200