from __future__ import annotations

import base64
import os
from io import BytesIO
from typing import Optional

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
from werkzeug.security import check_password_hash, generate_password_hash

from illust import generate_image

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()


class Config:
    """アプリ全体の設定値。"""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class User(db.Model, UserMixin):
    """アプリ利用者を表すモデル。"""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def set_password(self, raw_password: str) -> None:
        """平文パスワードを安全なハッシュに変換して保存する。"""

        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """入力パスワードと保存済みハッシュを照合する。"""

        return check_password_hash(self.password_hash, raw_password)


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """ログインセッションからユーザーを復元する。"""

    if user_id is None:
        return None
    return User.query.get(int(user_id))


def build_prompt(color_instruction: str, pose_instruction: str) -> str:
    """色指定とポーズ指示を組み合わせたプロンプトを生成する。"""

    base_prompt = (
        "Using the provided image of my rough drawing, create a detailed and polished illustration "
        "in the style of a high-quality anime. Pay close attention to the fidelity of the original sketch, "
        "fill in missing lines cleanly, and follow these color instructions to finish the artwork: {colors} "
        "Follow these pose instructions to position the character: {pose}"
    )
    return base_prompt.format(
        colors=color_instruction.strip() or "No specific colors were provided.",
        pose=pose_instruction.strip() or "Please maintain the pose of the original image.",
    )


def create_app() -> Flask:
    """Flaskアプリケーションを生成するファクトリ。"""

    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"

    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


def register_routes(app: Flask) -> None:
    """ビュー関数をFlaskアプリに登録する。"""

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")

            if not username or not email or not password:
                flash("すべての項目を入力してください。", "error")
                return render_template("signup.html")

            if User.query.filter((User.username == username) | (User.email == email)).first():
                flash("同じユーザー名またはメールアドレスが既に使われています。", "error")
                return render_template("signup.html")

            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("ユーザー登録が完了しました。", "success")
            return redirect(url_for("index"))

        return render_template("signup.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                login_user(user)
                flash("ログインに成功しました。", "success")
                next_url = request.args.get("next")
                return redirect(next_url or url_for("index"))

            flash("ユーザー名またはパスワードが正しくありません。", "error")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        session.clear()
        flash("ログアウトしました。", "info")
        return redirect(url_for("login"))

    @app.route("/", methods=["GET", "POST"])
    @login_required
    def index():
        image_data = None
        prompt_text = None

        if request.method == "POST":
            file = request.files.get("rough_image")
            color_instruction = request.form.get("color_instruction", "")
            pose_instruction = request.form.get("pose_instruction", "")
            aspect_ratio_label = request.form.get("aspect_ratio") or "auto"
            resolution_label = request.form.get("resolution") or "auto"

            if not file or file.filename == "":
                flash("ラフ絵ファイルを選択してください。", "error")
            else:
                try:
                    raw_bytes = file.read()
                    image = Image.open(BytesIO(raw_bytes)).convert("RGB")
                except Exception as exc:  # noqa: BLE001
                    flash(f"画像の読み込みに失敗しました: {exc}", "error")
                else:
                    aspect_ratio = None if aspect_ratio_label == "auto" else aspect_ratio_label
                    resolution = None if resolution_label == "auto" else resolution_label
                    prompt = build_prompt(color_instruction, pose_instruction)

                    try:
                        generated = generate_image(
                            prompt=prompt,
                            image=image,
                            aspect_ratio=aspect_ratio,
                            resolution=resolution,
                        )
                    except Exception as exc:  # noqa: BLE001
                        flash(f"画像生成に失敗しました: {exc}", "error")
                    else:
                        encoded = base64.b64encode(generated.raw_bytes).decode("utf-8")
                        session["generated_image"] = encoded
                        session["generated_mime"] = generated.mime_type
                        session["generated_prompt"] = generated.prompt
                        image_data = f"data:{generated.mime_type};base64,{encoded}"
                        prompt_text = generated.prompt
                        flash("イラストの生成が完了しました。", "success")

        if not image_data and session.get("generated_image"):
            mime_type = session.get("generated_mime", "image/png")
            encoded = session.get("generated_image")
            image_data = f"data:{mime_type};base64,{encoded}"
            prompt_text = session.get("generated_prompt")

        return render_template(
            "index.html",
            image_data=image_data,
            prompt_text=prompt_text,
            aspect_ratio_options=["auto", "1:1", "4:5", "16:9"],
            resolution_options=["auto", "1K", "2K", "4K"],
        )

    @app.route("/download")
    @login_required
    def download():
        encoded = session.get("generated_image")
        mime_type = session.get("generated_mime", "image/png")
        if not encoded:
            abort(404)

        raw_bytes = base64.b64decode(encoded)
        return send_file(
            BytesIO(raw_bytes),
            mimetype=mime_type,
            as_attachment=True,
            download_name="generated_image.png",
        )


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
