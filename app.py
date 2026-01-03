from __future__ import annotations

from flask import Flask

from config import Config
from extensions import db, login_manager
from models import User
from views.auth import auth_bp
from views.chat import chat_bp
from views.main import main_bp


def create_app(config_object: object | None = None) -> Flask:
    """Flaskアプリケーションを生成し、Blueprintを登録する。"""

    app = Flask(__name__)
    app.config.from_object(Config)
    if config_object:
        if isinstance(config_object, dict):
            app.config.update(config_object)
        else:
            app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    with app.app_context():
        db.create_all()
        ensure_initial_user(app)

    register_blueprints(app)
    return app


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

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(main_bp)


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
