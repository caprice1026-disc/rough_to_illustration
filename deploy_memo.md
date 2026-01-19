# Cloud Run + Cloud SQL 本番GUIデプロイ手順（現在の構成）
このメモは、GCP コンソール（GUI）だけで本番環境を用意し、Cloud Run から Cloud SQL（MySQL）に接続して運用する手順です。
Cloud Build Trigger と Cloud Run Job による **ビルド → マイグレーション → デプロイ** の流れも含めます。

---

## 0. 前提

- GCP プロジェクト作成済み / Billing 有効
- 目標リージョン決定済み（例: `asia-northeast1`）
- このリポジトリに `cloudbuild.yaml` が存在
- GitHub 連携済み（Cloud Build Trigger が作れる状態）

---

## 1. Cloud SQL（MySQL）の作成

1. **Cloud SQL** → **インスタンスを作成**
2. **MySQL 8** を選択
3. **リージョン**は Cloud Run と合わせる（例: `asia-northeast1`）
4. インスタンス名とルートパスワードを設定して作成

### DB とユーザー
- データベース: `app_db`
- ユーザー: `app_user`（パスワード設定）

### 接続名を控える
インスタンス詳細の **接続** セクションにある
`INSTANCE_CONNECTION_NAME` を控えておきます。

---

## 2. Secret Manager の準備

以下の Secret を作成します（値は本番用）。

- `SECRET_KEY`（必須）
- `GEMINI_API_KEY`（互換のため `GOOGLE_API_KEY` でも可）
- `DB_PASSWORD`（`DB_USER` 用）
- もしくは `DATABASE_URL` を使う場合は `DATABASE_URL`

`DB_USER` / `DB_NAME` などは Secret でなく環境変数でもOKです。

`DATABASE_URL` を使う場合の例（Cloud SQL / Unix ソケット）:

```
mysql+pymysql://USER:PASSWORD@/DBNAME?unix_socket=/cloudsql/INSTANCE_CONNECTION_NAME
```

---

## 3. Cloud Storage（チャット画像）バケット作成

1. **Cloud Storage** → **バケットを作成**
2. リージョンは Cloud Run と同じ
3. バケット名を控える（例: `rough-chat-images`）

本番は `CHAT_IMAGE_STORAGE=gcs` を推奨します。

---

## 4. サービスアカウントと権限

### Cloud Run 用（サービス / Job 共通）
- **Cloud SQL Client**
- **Secret Manager Secret Accessor**
- **Storage Object Admin**（対象バケット）
- （カスタム SA を使う場合）**Artifact Registry Reader**

### Cloud Build 用
- **Cloud Run Admin**
- **Cloud Run Job Admin**
- **Service Account User**
- **Artifact Registry Writer**

---

## 5. Cloud Run Job（マイグレーション用）

Cloud Run Job は **一度だけ作成**します。

1. **Cloud Run** → **ジョブ** → **ジョブを作成**
2. 名前: `rough-to-illustration-migrate`（`cloudbuild.yaml` の `_MIGRATION_JOB` と一致させる）
3. コンテナイメージ: Artifact Registry の任意イメージ（初回は何でもOK）
4. **コマンド / 引数**
   - コマンド: `flask`
   - 引数: `--app,app.py,db,upgrade`（`cloudbuild.yaml` の `_MIGRATION_ARGS` と一致）
5. **接続** → **Cloud SQL 接続を追加**
6. **環境変数 / シークレット**
   - `APP_ENV=production`
   - `CHAT_IMAGE_STORAGE=gcs`（推奨）
   - `CHAT_IMAGE_BUCKET=<バケット名>`
   - `DB_USER=app_user`
   - `DB_NAME=app_db`
   - `INSTANCE_CONNECTION_NAME=<控えた値>`
   - `DB_PASSWORD` を Secret から注入
   - ※ `DATABASE_URL` 方式を使うなら `DB_*` は不要
7. **サービスアカウント** を設定
8. 作成

### 初回ユーザー作成（必要な場合のみ）
最初の 1 回だけ `init-db` を使って初期ユーザーを作成できます。

- `cloudbuild.yaml` の `_MIGRATION_ARGS` を一時的に
  `--app,app.py,init-db` に変更して実行
- Job / Service に `INITIAL_USER_USERNAME` / `INITIAL_USER_EMAIL` / `INITIAL_USER_PASSWORD` を追加
- 実行後は `_MIGRATION_ARGS` を `db,upgrade` に戻し、`INITIAL_USER_*` を削除

---

## 6. Cloud Build Trigger（cloudbuild.yaml 方式）

1. **Cloud Build** → **トリガー**
2. Build configuration を **Cloud Build config file** に変更
3. リポジトリ: 本リポジトリ
4. パス: `/cloudbuild.yaml`
5. 保存

`cloudbuild.yaml` 内の置換変数は環境に合わせて調整します。
- `_REGION`
- `_SERVICE_NAME`
- `_MIGRATION_JOB`
- `_AR_REPO`
- `_IMAGE_NAME`
- `_MIGRATION_ARGS`

---

## 7. Cloud Run サービス作成（本番）

1. **Cloud Run** → **サービスを作成**
2. コンテナイメージ: Artifact Registry の最新イメージ
3. **接続** → **Cloud SQL 接続を追加**
4. **環境変数 / シークレット**（Job と同じ）
5. **サービスアカウント** を設定
6. 作成

---

## 8. 動作確認

1. GitHub に push して Cloud Build が動くことを確認
2. Cloud Build ログに以下が出ることを確認
   - `run jobs update`
   - `run jobs execute`
   - `run deploy`
3. Cloud Run の URL にアクセスして動作確認

---

## 補足

- 本番 `APP_ENV=production` では **SQLite は禁止**です。`DATABASE_URL` もしくは `DB_*` を必ず設定してください。
- `CHAT_IMAGE_STORAGE` 未設定時は、`production` なら `gcs`、それ以外は `local` になります。
- `APP_DEBUG` は `APP_ENV=production` では無視されます。
- TCP 接続が必要な場合は `DB_HOST` / `DB_PORT` を追加してください。
- 明示的なソケットパスを使う場合は `DB_SOCKET` を指定できます。
