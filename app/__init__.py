from datetime import datetime
from typing import Optional

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from sqlalchemy import event, text

from config import Config

# Shared extensions

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "admin.login"


def _configure_postgres_schema(app: Flask) -> None:
    schema = app.config.get("DB_SCHEMA")
    if not schema:
        return

    with app.app_context():
        engine = db.engine
        if engine.dialect.name != "postgresql":
            return

        def _set_search_path(dbapi_connection, connection_record):  # pragma: no cover - driver integration
            cursor = dbapi_connection.cursor()
            cursor.execute(f'SET search_path TO "{schema}", public')
            cursor.close()

        event.listen(engine, "connect", _set_search_path)
        with engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            connection.execute(text(f'SET search_path TO "{schema}", public'))


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    _configure_postgres_schema(app)

    from app.models import User  # noqa: WPS433 (import inside function to avoid circular import)

    @login_manager.user_loader
    def load_user(user_id: str) -> Optional[User]:
        if user_id is None:
            return None
        return User.query.get(int(user_id))

    from app.routes import admin, assistant, main, shop

    app.register_blueprint(main.bp)
    app.register_blueprint(shop.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(assistant.bp)

    @app.context_processor
    def inject_globals():
        return {
            "shop_name": app.config.get("SHOP_NAME", "Voloskyi Saffron"),
            "base_url": app.config.get("BASE_URL", ""),
            "stripe_public_key": app.config.get("STRIPE_PUBLIC_KEY", ""),
            "current_year": datetime.utcnow().year,
        }

    from app.utils import start_scheduler

    start_scheduler(app)

    return app
