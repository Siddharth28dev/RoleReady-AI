import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY          = os.getenv("SECRET_KEY", "dev-secret-key")
    # JWT auth — identifies the logged-in user on every request.
    # CHANGE JWT_SECRET_KEY in production (.env), same as SECRET_KEY.
    JWT_SECRET_KEY          = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION       = ["headers"]
    UPLOAD_FOLDER       = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH  = int(os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))
    ALLOWED_EXTENSIONS  = set(os.getenv("ALLOWED_EXTENSIONS", "pdf,docx,txt").split(","))
    SPACY_MODEL         = os.getenv("SPACY_MODEL", "en_core_web_sm")
    SQLALCHEMY_DATABASE_URI     = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/ai_resume_analyzer")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config_map = {"development": DevelopmentConfig, "production": ProductionConfig}

def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)