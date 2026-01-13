# rough_to_illustration

ラフスケッチからイラストを生成するためのFlaskアプリケーションです。バックエンドはJSON APIを提供し、フロントエンドは静的なSingle Page Application (SPA) として配信されます。ログイン後、複数の生成モード（ラフ + 指示 / 参考画像 + ラフ / インペイント・アウトペイント）を切り替えながら、Gemini API を使った生成結果のプレビューとダウンロードができます。チャットモードも同じSPA内で利用できます。

## 主な機能
- Flask + SQLAlchemy + Flask-Login によるセッション認証付きJSON API
- 静的SPAによるフロントエンド（ページ遷移なしでモード切替）
- 生成モード切替（ラフ＋指示 / 完成絵参照＋ラフ / インペイント・アウトペイント）
- ラフ絵アップロードと色指定・ポーズ指示（任意のアスペクト比/解像度入力）
- 参考画像＋ラフの2枚画像モード（任意のアスペクト比/解像度入力）
- チャットセッションの履歴管理と生成結果の表示
- Gemini API を呼び出して生成した画像のプレビューとダウンロード

## ディレクトリ構成
- `app.py`: Flaskアプリのエントリポイント。API/SPAのBlueprint登録を担当。
- `config.py` / `extensions.py` / `models.py`: 設定値、拡張機能のインスタンス、ユーザーモデル。
- `services/`: プロンプト生成や画像生成処理のヘルパー。
- `views/api.py`: `/api` 配下のJSON APIを提供。
- `views/spa.py`: SPA配信用のルーティングを提供。
- `static/spa/`: SPAのHTML/CSS/JavaScript。
- `templates/`: 旧来のJinja2テンプレート（参考用として残置）。
- `old/streamlit/`: 旧Streamlitモックアップのコードを保管（現行アプリでは未使用）。

## 前提条件
- Python 3.10 以降（推奨）
- Gemini API のキー

## セットアップ
1. 依存関係のインストール
   ```bash
   pip install -r requirements.txt
   ```
2. `.env` に API キーなどを設定（ローカル開発専用）
   ```bash
   GEMINI_API_KEY="<GeminiのAPIキー>"     # 互換のため GOOGLE_API_KEY でも可
   SECRET_KEY="任意の秘密鍵"             # 必須: 未設定だと起動を停止します
   DATABASE_URL="sqlite:///app.db"      # ローカル用: 未指定ならSQLiteファイルを利用
   CHAT_IMAGE_STORAGE="local"           # local / gcs（ローカルはlocal推奨）
   CHAT_IMAGE_DIR="chat_images"         # local保存先（instance配下）
   CHAT_IMAGE_BUCKET="your-bucket"      # gcsの場合のみ必須
   APP_ENV="development"                # production で debug を強制無効化
   APP_DEBUG="true"                     # 任意: APP_ENV=production 時は無視
   MAX_CONTENT_LENGTH="33554432"        # 任意: アップロード上限 (32MB)
   MAX_FORM_MEMORY_SIZE="33554432"      # 任意: フォームメモリ上限 (32MB)
   ```
   - `.env` はローカル開発専用です。本番（Cloud Run など）では Secret Manager から環境変数へ注入してください。
3. データベース初期化（初回のみ）
   ```bash
   flask --app app.py init-db
   ```
   - `init-db` はマイグレーション適用（`flask --app app.py db upgrade`）と初期ユーザー作成をまとめて行います。
   - 既に `migrations/` を同梱しているため `flask db init` は不要です。
   - 初期化のみ行いたい場合は `flask --app app.py db upgrade` でも構いません。
4. 初回ユーザー作成（任意）
   ```bash
   flask --app app.py shell
   >>> from app import db, User
   >>> u = User(username="demo", email="demo@example.com")
   >>> u.set_password("password123")
   >>> db.session.add(u); db.session.commit(); exit()
   ```
   - `INITIAL_USER_USERNAME` / `INITIAL_USER_EMAIL` / `INITIAL_USER_PASSWORD` を設定している場合は、`init-db` 実行時に `ensure_initial_user` が自動実行されます（アプリ起動時の自動作成は行いません）。

## 起動方法
```bash
flask --app app.py run  # または python app.py
```
ブラウザで `http://localhost:5000/` にアクセスし、SPA上のログインフォームから認証してください。ログインしないとAPI/生成機能は利用できません。

## 使い方
1. ログイン後、SPAの「生成」タブまたは「チャット」タブを選択します。
2. 生成タブではモードに応じて画像と指示を入力し、必要に応じてアスペクト比・解像度を指定します。
   - ラフ→仕上げ（色・ポーズ指示）: ラフスケッチ1枚＋色/ポーズ指示
   - 完成絵参照→ラフ着色（2枚）: 参考（完成）画像1枚＋ラフスケッチ1枚
   - インペイント/アウトペイント: 編集元画像とマスク画像＋追加指示
3. 「生成をリクエスト」を押すと Gemini API に送信され、生成画像がプレビューされます。
4. 「ダウンロード」ボタンから生成画像を保存できます。

### UIのヒント
- 画面上部の「生成」「チャット」タブで画面を切り替えられます。
- 生成タブ内の「生成モード」セレクトで入力項目が切り替わります。
- 送信中はボタンが自動で無効化され、スピナーが表示されます。

## Dockerでの起動方法
```bash
docker build -t rough-to-illustration .
docker run --rm -p 8080:8080 \
  -e GEMINI_API_KEY="<GeminiのAPIキー>" \
  -e SECRET_KEY="任意の秘密鍵" \
  -e DATABASE_URL="sqlite:///app.db" \
  -e CHAT_IMAGE_BUCKET="your-bucket" \
  -e APP_ENV="production" \
  rough-to-illustration
```

### Docker起動時に指定する環境変数
- `GEMINI_API_KEY` または `GOOGLE_API_KEY`: 必須。Gemini API のキー。
- `SECRET_KEY`: 必須。Flaskのセッション暗号化に使用。
- `DATABASE_URL`: ローカルでは任意。本番では `DATABASE_URL` または `DB_*` が必須（未指定の場合は起動エラー）。
- `CHAT_IMAGE_STORAGE`: 任意。`local` または `gcs`（本番は `gcs` 推奨、検証は `local` 推奨）。
- `CHAT_IMAGE_DIR`: 任意。`local` の保存先（`instance` 配下の相対パスを推奨）。
- `CHAT_IMAGE_BUCKET`: `gcs` の場合に必須。チャット画像を保存するGCSバケット名。
- `APP_ENV`: 本番は `production` を必須。`production` で debug を無効化。
- `APP_DEBUG`: 任意。`APP_ENV=production` 時は無視。
- `MAX_CONTENT_LENGTH` / `MAX_FORM_MEMORY_SIZE`: 任意。アップロード/フォームのサイズ上限（デフォルトは32MB）。
- `INITIAL_USER_USERNAME` / `INITIAL_USER_EMAIL` / `INITIAL_USER_PASSWORD`: 任意。初回ユーザーを自動作成する場合に指定。

## 本番運用時の補足
### Cloud Runでの推奨設定
- `SECRET_KEY` / `GEMINI_API_KEY`（または `GOOGLE_API_KEY`）/ `DATABASE_URL` または `DB_*` / `CHAT_IMAGE_BUCKET` は Secret Manager から環境変数へ注入する構成を推奨します。
- `.env` はローカル開発専用です。本番では `.env` をコンテナ内に配置しない前提で運用してください（ローカルはSQLite、本番は外部DB + GCSバケットという差分を想定）。
- 本番は `APP_ENV=production` を必須にします（設定されていない場合は起動エラーになります）。
- `MAX_CONTENT_LENGTH` / `MAX_FORM_MEMORY_SIZE` のデフォルトは 32MB です。Cloud Run のリクエスト上限（32MB）に合わせ、必要に応じて32MB以下で調整してください。
- Cloud Run では `PORT` 環境変数が自動で設定されるため、Docker起動も `PORT` に追従する構成になっています。
- 画像保存は、本番は `CHAT_IMAGE_STORAGE=gcs`、検証環境は `CHAT_IMAGE_STORAGE=local` を推奨します。

### 検証環境（staging）の前提
- `APP_ENV=staging` を指定し、SQLite を使用します（`DATABASE_URL=sqlite:///app.db`）。
- 画像はローカル保存にします（`CHAT_IMAGE_STORAGE=local`、`CHAT_IMAGE_DIR=chat_images`）。
- 保存先は `instance/chat_images` になり、Cloud Run 上ではエフェメラルです（検証用途のみ想定）。

### HTTPS前提の設定
本番環境で `APP_ENV=production` を指定すると、以下のセキュリティ関連設定が有効になります。
- セッションCookieに `Secure` / `HttpOnly` を付与
- `PREFERRED_URL_SCHEME` を `https` に固定

HTTPS終端がロードバランサー側にある場合は、アプリケーション側でHTTPSが前提になっている点に注意してください。

### プロキシ配下での注意点
ロードバランサーやリバースプロキシ配下で動作させる場合、`X-Forwarded-*` ヘッダーを正しく反映するために `ProxyFix` を適用しています。

- `APP_ENV=production` のときのみ `ProxyFix` が有効になります。
- Cloud Run はロードバランサー経由で `X-Forwarded-Proto` / `X-Forwarded-For` / `X-Forwarded-Host` などを付与するため、この前提を満たします。
- それ以外のプロキシ構成では、同等の `X-Forwarded-*` ヘッダーを適切に付与してください。
- 直接アプリケーションにアクセスさせる構成では、プロキシヘッダーを付与しないようにしてください。

### データベース / Cloud SQL
- 本番では MySQL（PyMySQL）を前提とし、`DATABASE_URL` もしくは `DB_*` + `INSTANCE_CONNECTION_NAME` から接続情報を決定します（未設定の場合は起動エラーになります）。
- `DATABASE_URL` を使う場合の例:
  - MySQL/Unixソケット: `mysql+pymysql://USER:PASSWORD@/DBNAME?unix_socket=/cloudsql/INSTANCE_CONNECTION_NAME`
  - MySQL/TCP: `mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME`
- `DB_*` を使う場合の例（Cloud Run 推奨）:
  - `DB_USER` / `DB_PASSWORD` / `DB_NAME` / `INSTANCE_CONNECTION_NAME` を設定すると、`/cloudsql/<INSTANCE_CONNECTION_NAME>` のUnixソケットで接続します。
  - TCP接続が必要な場合は `DB_HOST` / `DB_PORT` を追加で設定してください。
  - 明示的なソケットパスを使いたい場合は `DB_SOCKET` を指定できます。
- `DATABASE_URL` が `mysql://` の場合は自動的に `mysql+pymysql://` に補正されます。
- 本番運用では `flask --app app.py db upgrade` を実行してから Cloud Run をデプロイしてください（初期ユーザーを作成する場合は `flask --app app.py init-db` を使用します）。
- MySQL のデータベース自体は事前に作成してください（`flask --app app.py db upgrade` はテーブル作成のみを行います）。
 - 検証環境（staging）は SQLite を使用するため、Cloud SQL への接続は不要です。

### マイグレーション運用
- マイグレーションの作成と適用は Flask-Migrate を利用します。
  ```bash
  flask --app app.py db migrate -m "describe change"
  flask --app app.py db upgrade
  ```
- 初回セットアップは `flask --app app.py db upgrade` だけで完了します（`db init` は不要です）。
- Cloud Run へ自動デプロイする前に、CI/CDの前段で `flask --app app.py db upgrade` を実行してスキーマを最新化してください。
- 初期ユーザー作成を自動化する場合は、CI/CDのマイグレーションステップで `flask --app app.py init-db` を一度実行し、完了後は `INITIAL_USER_*` を環境変数から外すことを推奨します。

### CI/CD（GitHub Push 自動デプロイ）の運用方針
- デプロイ前にマイグレーション専用ステップを必ず実行してください（Cloud Runの起動時に自動適用しません）。
- 本番: `flask --app app.py db upgrade`
- 検証: `flask --app app.py init-db`（SQLite + 初期ユーザー作成までまとめて実行）
- 初期ユーザー作成は一度だけ実行し、以降は環境変数 `INITIAL_USER_*` を外して再実行されないようにします。

### Cloud Run（GUI）デプロイ手順
1. 事前準備
   - Artifact Registry にリポジトリを作成
   - Cloud SQL インスタンスを作成（MySQL）
   - Secret Manager に以下を登録
     - `SECRET_KEY`
     - `GEMINI_API_KEY`
     - `DATABASE_URL` または `DB_USER` / `DB_PASSWORD` / `DB_NAME`
     - `INSTANCE_CONNECTION_NAME`（または `DB_SOCKET` を使う場合はその値）
     - `CHAT_IMAGE_BUCKET`
2. Cloud Run コンソールで「サービスを作成」
   - コンテナイメージを選択（Artifact Registry のイメージ）
3. 「接続」→「Cloud SQL 接続を追加」
   - 対象インスタンスを選択
   - いずれかを選択:
     - `DATABASE_URL` を使用する場合は Unix ソケット形式を設定（例: `mysql+pymysql://USER:PASSWORD@/DBNAME?unix_socket=/cloudsql/INSTANCE_CONNECTION_NAME`）
     - `DB_*` を使用する場合は `DB_USER` / `DB_PASSWORD` / `DB_NAME` / `INSTANCE_CONNECTION_NAME` を環境変数に設定
4. 「変数とシークレット」で環境変数/Secret を紐付け
   - `SECRET_KEY`, `GEMINI_API_KEY`, `DATABASE_URL` または `DB_*`, `CHAT_IMAGE_BUCKET` を Secret Manager から設定
5. サービスアカウントの権限付与
   - Cloud SQL Client 権限
   - `CHAT_IMAGE_BUCKET` 用に Storage Object Admin などの権限を付与
6. デプロイを実行

### チャット画像の保存先
- `CHAT_IMAGE_STORAGE` 未指定時は、`APP_ENV=production` の場合は `gcs`、それ以外は `local` になります。
- `CHAT_IMAGE_STORAGE=local` の場合は `instance/chat_images` に保存されます（検証・開発向け）。
- `CHAT_IMAGE_STORAGE=gcs` の場合は Cloud Storage に保存されます。バケット名は `CHAT_IMAGE_BUCKET` で指定します。
- GCSのオブジェクトパスは `chat_images/<image_id>` です。Cloud Run のサービスアカウントに読み書き権限を付与してください。

## 編集モード（インペイント/アウトペイント）
- 「編集」モードを選択し、編集対象画像をアップロードするとエディタが開きます。
- エディタで赤く塗った領域が編集対象です。インペイント/アウトペイントはボタンで切り替えます。
- 透明アルファ付きPNGをアップロードした場合、透明部分がマスクとして扱われます。
- 追加指示がない場合は、元の構図・色味・絵柄を維持したままマスク領域のみ編集します。

## 備考
- 画像やデータベースファイルは `.gitignore` に含めています。
- Gemini API の利用方法は [公式ドキュメント](https://ai.google.dev/gemini-api/docs/image-understanding?hl=ja) を参照してください。
