from __future__ import annotations

from flask import Flask, jsonify, redirect, request
from flask_wtf.csrf import CSRFError
from sqlalchemy import inspect
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import csrf, db, login_manager
from models import User
from views.api import api_bp
from views.spa import spa_bp


def create_app(config_object: object | None = None) -> Flask:
    """Flaskアプリケーションを生成し、Blueprintを登録する。"""

    app = Flask(__name__)
    app.config.from_object(Config)
    if config_object:
        if isinstance(config_object, dict):
            app.config.update(config_object)
        else:
            app.config.from_object(config_object)

    apply_proxy_fix(app)
    ensure_secret_key(app)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "spa.index"
    register_auth_handlers()
    register_security_handlers(app)

    with app.app_context():
        if should_create_tables(app):
            db.create_all()
        if is_user_table_ready():
            ensure_initial_user(app)
        else:
            app.logger.info("データベース未初期化のためイニシャルユーザー作成をスキップしました。")

    register_blueprints(app)
    return app


def apply_proxy_fix(app: Flask) -> None:
    """リバースプロキシ配下で X-Forwarded-* ヘッダーを反映する。"""

    if not is_production(app):
        return

    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1,
        x_prefix=1,
    )


def ensure_secret_key(app: Flask) -> None:
    """SECRET_KEY が設定されていない場合は起動を停止する。"""

    secret_key = app.config.get("SECRET_KEY")
    if not secret_key:
        app.logger.critical("SECRET_KEY is not set. Set it in .env before starting.")
        raise RuntimeError("SECRET_KEY is not set. Set it in .env before starting.")


def is_production(app: Flask) -> bool:
    """APP_ENV が production かどうかを判定する。"""

    return app.config.get("APP_ENV", "").strip().lower() == "production"


def should_create_tables(app: Flask) -> bool:
    """本番環境以外でのみテーブル作成を行う。"""

    return not is_production(app)


def is_user_table_ready() -> bool:
    """User テーブルが存在するかを確認する。"""

    inspector = inspect(db.engine)
    return inspector.has_table(User.__tablename__)


def ensure_initial_user(app: Flask) -> None:
    """環境変数からイニシャルユーザーを作成する。"""

    username = app.config.get("INITIAL_USER_USERNAME")
    email = app.config.get("INITIAL_USER_EMAIL")
    password = app.config.get("INITIAL_USER_PASSWORD")
    if not username or not email or not password:
        app.logger.info("イニシャルユーザーの環境変数が未設定のため作成をスキップしました。")
        return

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return

    if User.query.first() is not None:
        app.logger.warning("既存ユーザーが存在するためイニシャルユーザーの作成をスキップしました。")
        return

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    app.logger.info("イニシャルユーザーを作成しました。")


def register_blueprints(app: Flask) -> None:
    """Blueprintをまとめて登録するヘルパー。"""

    app.register_blueprint(api_bp)
    app.register_blueprint(spa_bp)


def register_auth_handlers() -> None:
    """API向けの未認証応答をJSONで返す。"""

    @login_manager.unauthorized_handler
    def unauthorized():  # type: ignore[override]
        if request.path.startswith("/api/"):
            return jsonify({"error": "認証が必要です。"}), 401
        return redirect("/")


def register_security_handlers(app: Flask) -> None:
    """Register CSRF and origin enforcement for API requests."""

    @app.before_request
    def enforce_api_origin():
        if not request.path.startswith("/api/"):
            return None
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None

        host_url = request.host_url.rstrip("/")
        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")

        if origin and not origin.startswith(host_url):
            return jsonify({"error": "Invalid request origin."}), 403
        if not origin and referer and not referer.startswith(host_url):
            return jsonify({"error": "Invalid request origin."}), 403
        return None

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error: CSRFError):  # type: ignore[override]
        if request.path.startswith("/api/"):
            return jsonify({"error": "CSRF token missing or invalid."}), 400
        return "CSRF token missing or invalid.", 400


app = create_app()


if __name__ == "__main__":
    debug_enabled = bool(app.config.get("DEBUG"))
    app.run(debug=debug_enabled)
