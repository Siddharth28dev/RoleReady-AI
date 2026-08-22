from flask_jwt_extended import create_access_token
from app.services.auth_service import register_user, authenticate_user, AuthError


def handle_register(data: dict) -> tuple[dict, int]:
    try:
        user = register_user(data["name"], data["email"], data["password"])
    except AuthError as e:
        return {"success": False, "error": str(e)}, 409
    except Exception as e:
        return {"success": False, "error": f"Registration failed: {str(e)}"}, 500

    # identity must be a string for flask-jwt-extended
    token = create_access_token(identity=str(user.id))
    return {"success": True, "token": token, "user": user.to_dict()}, 201


def handle_login(data: dict) -> tuple[dict, int]:
    try:
        user = authenticate_user(data["email"], data["password"])
    except AuthError as e:
        return {"success": False, "error": str(e)}, 401
    except Exception as e:
        return {"success": False, "error": f"Login failed: {str(e)}"}, 500

    token = create_access_token(identity=str(user.id))
    return {"success": True, "token": token, "user": user.to_dict()}, 200


def handle_me(user_id: str) -> tuple[dict, int]:
    from app.extensions import db
    from app.models import User

    user = db.session.get(User, int(user_id))
    if not user:
        return {"success": False, "error": "User not found"}, 404
    return {"success": True, "user": user.to_dict()}, 200