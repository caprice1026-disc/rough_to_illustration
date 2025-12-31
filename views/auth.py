from __future__ import annotations

from typing import Optional

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models import User


auth_bp = Blueprint("auth", __name__)


def _get_next_url() -> Optional[str]:
    """ログイン後のリダイレクト先を取得する。"""

    return request.args.get("next")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if not current_user.is_authenticated:
        flash("新規登録はイニシャルユーザーでログインした場合のみ利用できます。", "error")
        return redirect(url_for("auth.login"))

    if not current_user.is_initial_user:
        flash("新規登録はイニシャルユーザーのみ利用できます。", "error")
        return redirect(url_for("main.index"))

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
        flash("ユーザー登録が完了しました。", "success")
        return redirect(url_for("main.index"))

    return render_template("signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("ログインに成功しました。", "success")
            next_url = _get_next_url()
            return redirect(next_url or url_for("main.index"))

        flash("ユーザー名またはパスワードが正しくありません。", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("ログアウトしました。", "info")
    return redirect(url_for("auth.login"))
