# StreamlitモックアップをFlask本番構成へ移行する

このExecPlanはPLANS.md (./PLANS.md) の指針に従って維持されるべき生きた文書である。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective` を常に最新に更新し、本計画だけで初心者が作業を完遂できるようにする。

## Purpose / Big Picture

現在はStreamlitによるモックアップ`main.py`でラフ絵アップロードと画像生成を行っているが、本番運用を念頭にFlaskへ移行し、SQLAlchemyによるDB管理とFlask-Loginによるログイン必須フローを整備する。これにより、利用者はWebサーバーを起動し、ログイン後にフォームからラフ絵・指示を送信して生成結果を閲覧・ダウンロードできる。本番に向けた認証と永続化の枠組みが整う。

## Progress

- [x] (2025-02-20 12:30Z) 現状コードと要件を確認し、Flask化と認証/DB移行が大規模な変更であることを把握した。
- [x] (2025-02-20 13:00Z) Flaskアプリの骨格を用意し、SQLAlchemyとFlask-Loginを初期化するコードを追加した。
- [x] (2025-02-20 13:15Z) ユーザーモデルとログイン/サインアップ/ログアウト画面を実装し、ログイン必須ルートを設定した。
- [x] (2025-02-20 13:35Z) StreamlitフォームをFlask用テンプレートに置き換え、画像生成処理・プレビュー・ダウンロードまでのフローをPOSTルートに組み込んだ。
- [x] (2025-02-20 13:55Z) READMEや依存関係、.gitignoreをFlask運用向けに更新し、`python -m compileall`で構文確認を行った。

## Surprises & Discoveries

- Observation: まだなし。
  Evidence: なし。

## Decision Log

- Decision: 生成画像はDBには保存せず、セッションにBase64文字列として保持し、ダウンロードルートで都度`BytesIO`化して返す。
  Rationale: 簡潔な実装でストレージ依存を避け、ログアウトで確実に破棄できるため。
  Date/Author: 2025-02-20 / Codex

## Outcomes & Retrospective

Flaskアプリに置き換え、ログイン必須の生成フローを完成させた。SQLAlchemyでユーザーを永続化し、セッションに生成画像を保持することで軽量なプレビュー/ダウンロードを提供している。READMEでセットアップ手順と初期ユーザー作成方法を明示し、依存関係をFlask向けに整理した。今後は実際のAPIキーを設定した環境でエンドツーエンド検証を追加するとより安心。

## Context and Orientation

リポジトリ直下にStreamlit用`main.py`(UI)と`illust.py`(Gemini API呼び出し)、`oauth.py`(Streamlit認証)がある。依存は`requirements.txt`に記載され、READMEはStreamlit前提の説明。Flask移行では`app.py`等にサーバー本体を置き、`templates/`にHTMLを配置、`models`と`extensions`としてSQLAlchemyとFlask-Loginを初期化する想定。SQLiteをデフォルトDBとし、ユーザー情報にハッシュ化パスワードを保存する。

## Plan of Work

1. Flaskアプリのエントリーポイントを新規作成し、`Flask`, `SQLAlchemy`, `LoginManager` を初期化する。設定クラスで`SECRET_KEY`と`SQLALCHEMY_DATABASE_URI`(SQLite)を定義し、`.env`を読み込む。`illust.generate_image`は既存を再利用する。
2. `User`モデルをSQLAlchemyで定義し、`flask_login.UserMixin`を継承する。`username`/`email`のユニーク制約と`password_hash`を保持し、Werkzeugの`generate_password_hash`/`check_password_hash`を使用する。データベース初期化用のCLIや自動作成を`app.py`起動時に用意する。
3. 認証ルート(`/login`, `/signup`, `/logout`)を追加し、Jinja2テンプレートでフォームを表示する。ログイン成功でセッションへリダイレクトし、`login_required`デコレータで生成機能へのアクセスを保護する。
4. 生成フォーム用ルート(`/`)をログイン必須にして、ラフ絵アップロード、色指示、ポーズ指示、アスペクト比、解像度をHTMLフォームで受け取る。POST時にファイルをPILで開き`generate_image`を呼び出し、結果のバイト列を`session`にBase64保存し、プレビュー用にData URLを生成してテンプレートへ渡す。
5. 生成画像のダウンロード用ルート(`/download`)を用意し、セッションにバイト列がなければ404を返す。テンプレートで生成結果とプロンプト表示、エラー時のメッセージ表示を行う。
6. `requirements.txt`にFlask関連依存を追加し、`.gitignore`で生成画像(PNG/JPEG)を除外する。READMEにFlask起動方法と初期ユーザー作成手順、ログインが必要なことを追記する。
7. `python -m compileall`や`flask --app app.py run`(または`python app.py`)で動作確認し、テスト結果を記録する。

## Concrete Steps

- 仮想環境は任意。`pip install -r requirements.txt`で依存を導入する。Flask追加後に再実行して不足がないことを確認する。
- DB初期化のため、`flask --app app.py shell`で`db.create_all()`を呼び出す、もしくはアプリ起動時に自動作成するロジックを用意する。
- サーバー起動は `flask --app app.py run` または `python app.py` を使用し、`http://localhost:5000/` にアクセスしてログイン→生成フォーム→画像プレビュー→ダウンロードを確認する。

## Validation and Acceptance

- 未ログイン状態で`/`へアクセスするとログインページへリダイレクトされ、認証後に生成フォームが表示される。
- ラフ絵と指示を送信するとGemini呼び出しが成功すれば生成画像が画面に表示され、`ダウンロード`ボタンからPNGが取得できる。セッションに結果がない場合は404相当の応答になる。
- DBにユーザーが保存され、再起動後もログインが継続する(セッション有効期限内)。

## Idempotence and Recovery

- DB作成やユーザー登録は繰り返し実行しても問題ないが、同一`username`/`email`はユニーク制約で拒否される。失敗したフォーム送信はエラーメッセージを表示し、入力を修正して再送できる。
- セッションに保持した画像は再度生成すると上書きされる。不要になればログアウトでセッションがクリアされる。

## Artifacts and Notes

- 動作確認時のサーバーログ抜粋、`python -m compileall`の結果、README更新内容を証跡として残す。

## Interfaces and Dependencies

- `app.py`: Flaskアプリの初期化、DB/ログイン管理、ルート定義。`generate_image`を呼び出す。`/download`で`send_file`を返す。
- `models.py`(または同等ファイル): `User`モデル。`id`, `username`, `email`, `password_hash`。`set_password`, `check_password`メソッドを提供する。
- `templates/`以下に`login.html`, `signup.html`, `index.html`, 共通レイアウト`base.html`を配置。日本語UIとする。
- 依存パッケージ: `Flask`, `Flask-Login`, `Flask-SQLAlchemy`, `python-dotenv`, `Werkzeug`(Flask同梱)。
