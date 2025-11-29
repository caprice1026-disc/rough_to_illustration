# oauth.py
from __future__ import annotations

import streamlit as st
import streamlit_authenticator as stauth


def _build_credentials_from_secrets() -> dict:
    '''st.secrets から streamlit-authenticator 用の credentials を組み立てる。'''
    users_conf = st.secrets["auth"]["users"]

    # streamlit_authenticator が要求する形式に変換
    credentials = {"usernames": {}}

    for key, user in users_conf.items():
        # username は secrets 側で明示してもいいし、キー名(key)をそのまま使ってもよい
        username = user.get("username", key)

        # 平文パスワード → 実行時にハッシュ化
        raw_password = user["password"]
        hashed_password = stauth.Hasher([raw_password]).generate()[0]

        credentials["usernames"][username] = {
            "name": user["name"],
            "email": user["email"],
            "password": hashed_password,
        }

    return credentials


def _create_authenticator() -> stauth.Authenticate:
    '''st.secrets を元に Authenticate インスタンスを生成する。'''
    credentials = _build_credentials_from_secrets()
    cookie_conf = st.secrets["auth"]["cookie"]

    authenticator = stauth.Authenticate(
        credentials,
        cookie_conf["name"],
        cookie_conf["key"],
        cookie_conf["expiry_days"],
    )
    return authenticator


def require_login():
    '''ログインが成功するまで以降の処理を実行させない。成功したら (name, username, authenticator) を返す。'''
    authenticator = _create_authenticator()
    name, auth_status, username = authenticator.login("ログイン", "main")

    if auth_status:
        # サイドバーにログイン情報とログアウトボタンを出す
        st.sidebar.write(f"ログイン中: {name}")
        authenticator.logout("ログアウト", "sidebar")
        return name, username, authenticator

    elif auth_status is False:
        st.error("ユーザー名かパスワードが違います")
        # 認証失敗時点でアプリ本体は止める
        st.stop()

    else:
        # まだ何も入力していない状態など
        st.info("機能を利用するにはログインしてください。")
        st.stop()
