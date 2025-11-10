import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    _database_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if not _database_url:
        _database_url = "sqlite:///saffron.db"
    if _database_url and _database_url.startswith("postgres://"):
        _database_url = _database_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ASSISTANT_PROMPT = os.getenv("ASSISTANT_PROMPT", "You are a helpful AI sales assistant.")
    SHOP_NAME = os.getenv("SHOP_NAME", "Saffron Shop")
    BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
    DB_SCHEMA = os.getenv("DB_SCHEMA")
    _schema = os.getenv("DB_SCHEMA")
    _options = []
    if _schema:
        _options.append(f"-c search_path={_schema},public")
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "connect_args": {"options": " ".join(_options)} if _options else {},
    }
