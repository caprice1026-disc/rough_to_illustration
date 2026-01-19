# Cloud Run + Cloud SQL（本番）GUIデプロイ手順

このメモは、GCPコンソール（GUI）だけで本番環境を用意し、Cloud Run から Cloud SQL（MySQL）へ接続して運用するための詳細手順です。  
自動デプロイ（Cloud Build Trigger）とマイグレーション実行（Cloud Run Job）まで含めます。

---

## 0. 前提

- GCPプロジェクト作成済み
- Billing有効
- 目的のリージョンを決定済み（例: `asia-northeast1`）
- このリポジトリに `cloudbuild.yaml` が追加済み
- GitHub連携済み（Cloud Build Trigger が作れる状態）

---

## 1. Cloud SQL（MySQL）の作成

1. **Cloud SQL** → **インスタンスを作成**
2. **MySQL** を選択（推奨: MySQL 8）
3. **リージョン**は Cloud Run と合わせる（例: `asia-northeast1`）
4. インスタンス名を入力
5. ルートパスワード設定
6. **作成** をクリック

### データベースとユーザー作成
1. インスタンス詳細 → **データベース** → **データベースを作成**
   - 例: `app_db`
2. インスタンス詳細 → **ユーザー** → **ユーザーを作成**
   - 例: `app_user`
   - パスワードを設定

### INSTANCE_CONNECTION_NAME を控える
インスタンス詳細の **「接続」** にある  
`INSTANCE_CONNECTION_NAME` を控えておきます。

---

## 2. Secret Manager の準備

**Secret Manager** で以下を作成します（値は本番用）。

- `SECRET_KEY`
- `GEMINI_API_KEY`（または `GOOGLE_API_KEY`）
- `DB_PASSWORD`（DBユーザーのパスワード）
- もしくは `DATABASE_URL` を使う場合はそれも登録

※ `DB_USER` / `DB_NAME` は文字列なので環境変数でもOKです（Secretでも可）。

---

## 3. Cloud Storage（チャット画像用）バケット作成

1. **Cloud Storage** → **バケットを作成**
2. リージョンは Cloud Run と同じにする
3. バケット名を控える（例: `rough-chat-images`）

---

## 4. サービスアカウントと権限

Cloud Run の実行用サービスアカウントを作成（または既存を使用）し、以下を付与：

- **Cloud SQL Client**
- **Secret Manager Secret Accessor**
- **Storage Object Admin**（バケットに対して）

※ Cloud Build 側のサービスアカウントにも以下が必要：
- **Cloud Run Admin**
- **Service Account User**
- **Cloud Run Job Admin**

---

## 5. Cloud Run Job（マイグレーション用）作成

Cloud Run Job は **一度だけ作成**しておきます。

1. **Cloud Run** → **ジョブ** → **ジョブを作成**
2. 名前: `rough-to-illustration-migrate`
3. **コンテナイメージ**は Artifact Registry から選択
   - 初回は任意の既存イメージでOK（後で Cloud Build が更新します）
4. **コマンド/引数**
   - コマンド: `flask`
   - 引数: `--app,app.py,db,upgrade`
5. **接続** → **Cloud SQL 接続を追加**
   - 先ほど作成したインスタンスを選択
6. **環境変数 / シークレット**
   - `APP_ENV=production`
   - `CHAT_IMAGE_STORAGE=gcs`
   - `CHAT_IMAGE_BUCKET=<バケット名>`
   - `DB_USER=app_user`
   - `DB_NAME=app_db`
   - `INSTANCE_CONNECTION_NAME=<控えた値>`
   - `DB_PASSWORD` は Secret Manager から注入
7. **サービスアカウント** を設定（上で作成したもの）
8. 作成

### 初回ユーザー作成（1回だけ）
初回ユーザーを自動作成したい場合、**一度だけ**以下に変更してジョブを実行します。

1. Job を編集
2. 引数を `--app,app.py,init-db` に変更
3. `INITIAL_USER_USERNAME` / `INITIAL_USER_EMAIL` / `INITIAL_USER_PASSWORD` を環境変数に追加
4. **実行**
5. 実行後、引数を `db,upgrade` に戻し、初期ユーザーの環境変数は削除

---

## 6. Cloud Build Trigger（cloudbuild.yaml方式）

1. **Cloud Build** → **トリガー** → 対象トリガーを編集
2. 構成を **Cloud Build 構成ファイル（yaml/json）** に変更
3. **ロケーション: リポジトリ**
4. **パス: `/cloudbuild.yaml`**
5. 保存

`cloudbuild.yaml` は **ビルド → Job更新/実行 → Cloud Runデプロイ** の順で動きます。

---

## 7. Cloud Run サービス作成（本番）

1. **Cloud Run** → **サービスを作成**
2. コンテナイメージ: Artifact Registry の最新イメージ
3. **接続** → **Cloud SQL 接続を追加**
4. **環境変数 / シークレット**（Jobと同じ内容）
5. **サービスアカウント**を設定
6. 作成

---

## 8. 動作確認

1. Cloud Build トリガーで push → build が動くか確認
2. Cloud Build ログに以下が出ることを確認
   - `run jobs update`
   - `run jobs execute`
   - `run deploy`
3. Cloud Run のURLにアクセスして動作を確認

---

## 補足

- **Cloud Run で SQLite は非推奨**です（データは永続化されません）。
- 本番は **Cloud SQL（MySQL）必須**です。
- 画像は `CHAT_IMAGE_STORAGE=gcs` を推奨します。

