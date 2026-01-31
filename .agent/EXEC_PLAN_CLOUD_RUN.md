# Cloud Run向けの運用整理とストレージ/設定更新

このExecPlanはPLANS.md (./PLANS.md) の指針に従って維持されるべき生きた文書である。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective` を常に最新に更新し、本計画だけで初心者が作業を完遂できるようにする。

## Purpose / Big Picture

Cloud Runで本番運用する際に必要な環境変数・Secret Managerの使い方・APP_ENVの必須化をREADMEで明確にし、チャット画像の保存先をローカルディスクからCloud Storageに切り替える。これにより、Cloud Runのエフェメラルなファイルシステムに依存せず、適切な制限値とポート設定で安全にデプロイできる。変更後は、READMEにCloud Run向けの設定差分がまとまり、`services/chat_service.py`がGCSに対して保存/取得を行い、Docker起動が`PORT`に追従することを確認できる。

## Progress

- [x] (2025-09-25 12:30Z) 現状の設定・チャット画像保存・Docker起動方法・READMEの運用記述を整理する。
- [x] (2025-09-25 12:45Z) `config.py`のアップロード制限値とDB接続の必須化を更新し、`app.py`で本番の必須チェックを追加する。
- [x] (2025-09-25 13:05Z) `services/chat_service.py`とAPI/ビューの画像取得をCloud Storageベースへ切り替える。
- [x] (2025-09-25 13:20Z) `requirements.txt`と`Dockerfile`を更新し、READMEにCloud Run運用の詳細を追記する。
- [x] (2025-09-25 13:25Z) 変更内容を簡易確認し、ExecPlanを完了状態へ更新する。

## Surprises & Discoveries

- Observation: なし（作業中に更新）。
  Evidence: なし。

## Decision Log

- Decision: チャット画像のGCSオブジェクトパスは `chat_images/<image_id>` に統一する。
  Rationale: 既存の `image_id` をそのままキーにでき、管理しやすいため。
  Date/Author: 2025-09-25 / Codex
- Decision: アップロード制限のデフォルト値は 32MB（Cloud Run の上限）に合わせる。
  Rationale: Cloud Run の制限を超えるデフォルト値を避け、運用時の事故を減らすため。
  Date/Author: 2025-09-25 / Codex
- Decision: 本番で `DATABASE_URL` 未設定時は起動を停止する。
  Rationale: SQLite への暗黙フォールバックを避け、運用上の誤設定を早期に検出するため。
  Date/Author: 2025-09-25 / Codex

## Outcomes & Retrospective

Cloud Run向けのREADME整備、アップロード制限の調整、GCSベースのチャット画像保存、`PORT`追従のDocker起動を完了した。テストは未実施のため、必要に応じて起動確認とAPIの画像取得確認を行う。

## Context and Orientation

本リポジトリはFlaskアプリで、設定は`config.py`の`Config`クラスに集約されている。`services/chat_service.py`ではチャット用画像を`instance_path/chat_images`に保存しており、`views/api.py`と`views/chat.py`がそのファイルを`send_file`で返している。`Dockerfile`はGunicornを5000番で固定起動する。READMEにはDocker起動と本番運用の補足があるが、Cloud Run向けのSecret Manager注入やAPP_ENV必須化、`.env`のローカル専用性の説明が不足している。

## Plan of Work

まず`config.py`で`MAX_CONTENT_LENGTH`と`MAX_FORM_MEMORY_SIZE`のデフォルト値を32MB以下に調整し、`DATABASE_URL`が本番環境で必須になるよう`app.py`にチェックを追加する。続いて`services/chat_service.py`のチャット画像保存・取得をCloud Storageに置き換え、`CHAT_IMAGE_BUCKET`からバケット名を取得し、オブジェクトパスを`chat_images/{image_id}`に統一する。`views/api.py`と`views/chat.py`はローカルファイルではなくバイト列を読み込んで`send_file`に渡す。依存関係として`google-cloud-storage`を`requirements.txt`に追加し、`Dockerfile`の起動ポートを`PORT`環境変数に追従させる。最後にREADMEへCloud Runの推奨設定、Secret Manager注入、APP_ENV=production必須化、ProxyFixの前提、`.env`のローカル専用性、Cloud SQL利用時の接続方針、アップロード制限とCHAT_IMAGE_BUCKETの説明を追記する。

## Concrete Steps

- `config.py`の`MAX_CONTENT_LENGTH`/`MAX_FORM_MEMORY_SIZE`のデフォルト値を32MBに変更し、`SQLALCHEMY_DATABASE_URI`の解決ロジックを本番必須に合わせる。
- `app.py`に本番環境で`DATABASE_URL`が未設定の場合に起動を停止するチェックを追加する。
- `services/chat_service.py`でGCSクライアントを使うヘルパーを追加し、`persist_chat_image`/`load_chat_image_bytes`をGCSに置き換える。
- `views/api.py`と`views/chat.py`でチャット画像の取得をバイト列に変更し、`send_file`には`BytesIO`を渡す。
- `requirements.txt`に`google-cloud-storage`を追加し、`Dockerfile`の`CMD`を`PORT`対応に更新する。
- READMEにCloud Run向けの設定・Secret Manager・`.env`の位置付け・DB/Cloud SQL方針・アップロード制限値・CHAT_IMAGE_BUCKETを追記する。

## Validation and Acceptance

- `flask --app app.py run`でローカル起動し、`/api/chat/images/<id>`および`/chat/images/<id>`がGCSから取得されることを確認できる（バケット設定が必要）。
- Cloud Run運用に必要な環境変数とSecret Manager注入がREADMEに明示され、APP_ENV=production必須とProxyFix前提が説明されている。
- Docker起動が`PORT`環境変数で待ち受けポートを変更できる。

## Idempotence and Recovery

設定値の変更とGCS導入は繰り返し適用しても安全である。問題が出た場合は`services/chat_service.py`とビューの変更を元に戻し、README/`requirements.txt`/`Dockerfile`の差分を取り消せば復旧できる。DBスキーマ変更はない。

## Artifacts and Notes

- 作業中に必要なログや差分を簡潔に記録する。

## Interfaces and Dependencies

- 依存ライブラリ: `google-cloud-storage`
- `config.py`: `MAX_CONTENT_LENGTH`/`MAX_FORM_MEMORY_SIZE`のデフォルト変更、`SQLALCHEMY_DATABASE_URI`の解決ロジック整理、`CHAT_IMAGE_BUCKET`追加。
- `app.py`: 本番で`DATABASE_URL`未設定時に起動を止めるチェック。
- `services/chat_service.py`: GCSヘルパー、`persist_chat_image`/`load_chat_image_bytes`のGCS化、オブジェクトパス`chat_images/{image_id}`。
- `views/api.py`/`views/chat.py`: `send_file`へ`BytesIO`を渡す処理へ変更。
- `README.md`: Cloud Run運用/Secret Manager/ProxyFix/.env/DB/制限値/CHAT_IMAGE_BUCKETの追記。
- `Dockerfile`: `PORT`に追従するGunicorn起動。

計画変更メモ: 2025-09-25 に進捗と決定事項、成果を更新した。
