from app.extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.services.encryption_service import encrypt_if_not_empty, decrypt_if_not_empty, blind_index


class User(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    _name         = db.Column("name",  db.String(255), nullable=False)
    _email        = db.Column("email", db.String(500), nullable=False)
    # Blind index: deterministic HMAC hash of the normalized email.
    # This — NOT the encrypted `email` column — is what gets queried and
    # what carries the real UNIQUE constraint, since Fernet ciphertext is
    # non-deterministic (random IV per call) and unsuitable for lookups.
    email_index   = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    resumes            = db.relationship("Resume",           back_populates="user", cascade="all, delete")
    interview_sessions = db.relationship("InterviewSession", back_populates="user", cascade="all, delete")

    @property
    def name(self) -> str:
        return decrypt_if_not_empty(self._name)

    @name.setter
    def name(self, value: str):
        self._name = encrypt_if_not_empty(value)

    @property
    def email(self) -> str:
        return decrypt_if_not_empty(self._email)

    @email.setter
    def email(self, value: str):
        self._email = encrypt_if_not_empty(value)
        self.email_index = blind_index(value)

    @classmethod
    def find_by_email(cls, email: str):
        """
        Look up a user by email via the blind index — NEVER compare
        against the encrypted `email` column directly; ciphertext is
        non-deterministic and a direct equality check will never match.
        """
        return cls.query.filter_by(email_index=blind_index(email)).first()

    def set_password(self, plain_password: str):
        self.password_hash = generate_password_hash(plain_password)

    def check_password(self, plain_password: str) -> bool:
        return check_password_hash(self.password_hash, plain_password)

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "email":      self.email,
            "created_at": str(self.created_at),
        }