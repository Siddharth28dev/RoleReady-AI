"""
auth_service.py
────────────────
This was the missing piece that made the whole DB schema decorative:
User rows were never created anywhere. This module is the only place
that creates or authenticates a User.

User.find_by_email() already existed (blind-index lookup) and
set_password()/check_password() already existed (werkzeug hashing) —
they were just never called by anything.
"""

from app.extensions import db
from app.models import User


class AuthError(Exception):
    """Raised for expected auth failures (bad credentials, duplicate email)."""
    pass


def register_user(name: str, email: str, password: str) -> User:
    if User.find_by_email(email):
        raise AuthError("An account with this email already exists.")

    user = User(name=name, email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()
    return user


def authenticate_user(email: str, password: str) -> User:
    user = User.find_by_email(email)
    if not user or not user.check_password(password):
        # Deliberately vague — don't reveal whether the email exists.
        raise AuthError("Invalid email or password.")
    return user