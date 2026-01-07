from __future__ import annotations

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

# アプリ全体で共有する拡張機能のインスタンスをここで定義する
# 実際の初期化は create_app 内で行う

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
