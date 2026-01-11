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
   CHAT_IMAGE_BUCKET="your-bucket"      # チャット画像の保存先(GCS)
   APP_ENV="development"                # production で debug を強制無効化
   APP_DEBUG="true"                     # 任意: APP_ENV=production 時は無視
   MAX_CONTENT_LENGTH="33554432"        # 任意: アップロード上限 (32MB)
   MAX_FORM_MEMORY_SIZE="33554432"      # 任意: フォームメモリ上限 (32MB)
   ```
   - `.env` はローカル開発専用です。本番（Cloud Run など）では Secret Manager から環境変数へ注入してください。
3. データベース初期化と初回ユーザー作成（例）
   ```bash
   flask --app app.py shell
   >>> from app import db, User
   >>> db.create_all()
   >>> u = User(username="demo", email="demo@example.com")
   >>> u.set_password("password123")
   >>> db.session.add(u); db.session.commit(); exit()
   ```

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
- `DATABASE_URL`: ローカルでは任意。本番では必須（未指定の場合は起動エラー）。
- `CHAT_IMAGE_BUCKET`: 必須。チャット画像を保存するGCSバケット名。
- `APP_ENV`: 本番は `production` を必須。`production` で debug を無効化。
- `APP_DEBUG`: 任意。`APP_ENV=production` 時は無視。
- `MAX_CONTENT_LENGTH` / `MAX_FORM_MEMORY_SIZE`: 任意。アップロード/フォームのサイズ上限（デフォルトは32MB）。
- `INITIAL_USER_USERNAME` / `INITIAL_USER_EMAIL` / `INITIAL_USER_PASSWORD`: 任意。初回ユーザーを自動作成する場合に指定。

## 本番運用時の補足
### Cloud Runでの推奨設定
- `SECRET_KEY` / `GEMINI_API_KEY`（または `GOOGLE_API_KEY`）/ `DATABASE_URL` / `CHAT_IMAGE_BUCKET` は Secret Manager から環境変数へ注入する構成を推奨します。
- `.env` はローカル開発専用です。本番では `.env` をコンテナ内に配置しない前提で運用してください（ローカルはSQLite、本番は外部DB + GCSバケットという差分を想定）。
- 本番は `APP_ENV=production` を必須にします（設定されていない場合は起動エラーになります）。
- `MAX_CONTENT_LENGTH` / `MAX_FORM_MEMORY_SIZE` のデフォルトは 32MB です。Cloud Run のリクエスト上限（32MB）に合わせ、必要に応じて32MB以下で調整してください。
- Cloud Run では `PORT` 環境変数が自動で設定されるため、Docker起動も `PORT` に追従する構成になっています。

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
- `DATABASE_URL` は本番で必須です（未設定の場合は起動エラーになります）。
- Cloud SQL を利用する場合は、SQLAlchemy が理解できる接続文字列を `DATABASE_URL` に設定してください。
  - 例: Cloud Run の Cloud SQL 接続機能を使う場合は `/cloudsql/<INSTANCE_CONNECTION_NAME>` のUnixソケットを使った接続文字列を指定します。
  - 例: 専用のPythonコネクタを使う場合は `cloud-sql-python-connector` を `requirements.txt` に追加し、`app.py` または `extensions.py` 側でエンジン生成ロジックを実装してください。
- 現状は `app.py` の `db.create_all()` で初期化しています。本番運用ではマイグレーションツール（例: Flask-Migrate）の導入を検討してください。

### チャット画像の保存先
- チャット画像は Cloud Storage に保存されます。バケット名は `CHAT_IMAGE_BUCKET` で指定します。
- オブジェクトパスは `chat_images/<image_id>` です。Cloud Run のサービスアカウントに読み書き権限を付与してください。

## 編集モード（インペイント/アウトペイント）
- 「編集」モードを選択し、編集対象画像をアップロードするとエディタが開きます。
- エディタで赤く塗った領域が編集対象です。インペイント/アウトペイントはボタンで切り替えます。
- 透明アルファ付きPNGをアップロードした場合、透明部分がマスクとして扱われます。
- 追加指示がない場合は、元の構図・色味・絵柄を維持したままマスク領域のみ編集します。

## 備考
- 画像やデータベースファイルは `.gitignore` に含めています。
- Gemini API の利用方法は [公式ドキュメント](https://ai.google.dev/gemini-api/docs/image-understanding?hl=ja) を参照してください。
