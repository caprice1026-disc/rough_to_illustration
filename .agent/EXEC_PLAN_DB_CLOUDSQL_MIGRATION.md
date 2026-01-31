# ローカル初期化とCloud SQL接続の安定化（PyMySQL）

このExecPlanはPLANS.md（./PLANS.md）の指針に従って維持される生きた文書である。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective`を常に最新に更新し、この文書だけで初学者が作業を完遂できるようにする。

## Purpose / Big Picture

ローカル開発で最初にデータベースとユーザーを作成する手順が明確になり、実際にエラーなく作成できる状態にする。さらに、Cloud Run から Cloud SQL（MySQL）へ PyMySQL で接続できる設定とコードを整備し、本番ではマイグレーションを安全に実行してから起動できる運用方針を提供する。変更後は、ローカルで `flask --app app.py init-db` または `flask --app app.py db upgrade` が成功し、Cloud Run では環境変数設定のみで接続文字列が構成され、READMEの手順通りに動作を確認できる。

## Progress

- [x] (2026-01-13 21:40Z) 既存コードとREADMEの現状を確認し、DB初期化の失敗点とCloud SQL運用の不足点を整理した。
- [x] (2026-01-13 21:55Z) マイグレーション基盤（alembic.ini と migrations）と初期スキーマを追加した。
- [x] (2026-01-13 21:55Z) 設定解決ロジックとCLIを更新し、PyMySQL/Cloud SQL向け接続の自動構築と初期化コマンドを追加した。
- [x] (2026-01-13 21:55Z) READMEと.env.exampleを更新し、ローカル初期化・本番マイグレーション・Cloud Run設定手順を最新化した。
- [x] (2026-01-13 22:05Z) 変更内容を見直し、ExecPlanの結果と学びを記録した。

## Surprises & Discoveries

現時点では特記事項なし。実装中に想定外の挙動があれば、短い根拠とともに追記する。

## Decision Log

- Decision: Flask-Migrate を正式なマイグレーション戦略として採用し、初期マイグレーションと alembic.ini をリポジトリに同梱する。
  Rationale: ローカルでの初回作成と本番の再現性を揃え、`flask db upgrade` だけで確実にスキーマを構築できるようにするため。
  Date/Author: 2026-01-13 / Codex
- Decision: Cloud SQL 接続は `DATABASE_URL` が未指定の場合に `DB_*` と `INSTANCE_CONNECTION_NAME` から PyMySQL 用URLを自動構築する。
  Rationale: Cloud Run での接続文字列管理を簡素化し、誤設定時の手戻りを減らすため。
  Date/Author: 2026-01-13 / Codex
- Decision: 初回セットアップ向けに `flask --app app.py init-db` を追加し、マイグレーション適用と初期ユーザー作成を一度に実行する。
  Rationale: ローカル開発の初回DB作成手順を単一コマンドにまとめ、テーブル未作成によるエラーを避けるため。
  Date/Author: 2026-01-13 / Codex

## Outcomes & Retrospective

ローカル初期化向けに `init-db` コマンドを追加し、`migrations/` と初期スキーマを同梱したことで、`flask --app app.py db upgrade` だけでテーブル作成できる状態になった。Cloud SQL向けには `DATABASE_URL` と `DB_*` の両方を受け付ける設定に変更し、PyMySQLでの接続方法がREADMEに明記された。テストは未実行のため、実環境で `init-db` と `flask --app app.py db upgrade` の動作確認が必要である。

## Context and Orientation

本リポジトリは Flask アプリで、`app.py` がアプリの生成と起動を担い、`config.py` が環境変数から設定を解決している。`extensions.py` で Flask-SQLAlchemy と Flask-Migrate を初期化し、`models.py` でユーザーやチャット関連のテーブルを定義している。現在は migrations フォルダや alembic.ini が存在しないため、`flask db upgrade` を実行できず、ローカルでの初回テーブル作成が手作業依存になっている。Cloud SQL との接続は README に断片的に記載があるが、PyMySQL を前提とした環境変数設計と運用手順が不足している。

## Plan of Work

まず `alembic.ini` と `migrations/` を追加し、モデル定義に対応した初期マイグレーションを作成する。次に `config.py` を更新して `DATABASE_URL` が未指定でも `DB_USER`、`DB_PASSWORD`、`DB_NAME`、`INSTANCE_CONNECTION_NAME` などから PyMySQL 用の接続URLを組み立てられるようにし、`app.py` に初期化用のCLIコマンドを追加する。最後に README と `.env.example` を更新して、ローカルでの初回DB作成、Cloud Run/Cloud SQL 運用時のマイグレーションと初期ユーザー作成の流れを明確にする。

## Concrete Steps

作業はリポジトリルート（`C:\Users\Hodaka\Downloads\div\rough_to_illustration`）で行う。`alembic.ini` と `migrations/env.py`、`migrations/script.py.mako`、`migrations/versions/<revision>_initial.py` を追加し、`models.py` のテーブルに合わせて `upgrade()` / `downgrade()` を記述する。`config.py` に PyMySQL 用URL構築ロジックを追加し、`app.py` に `flask --app app.py init-db` でマイグレーション適用と初期ユーザー作成が実行できるコマンドを追加する。README と `.env.example` には、ローカル開発時の `flask db upgrade` または `init-db` の手順、Cloud SQL で必要な環境変数と `DATABASE_URL` の例、Cloud Run でのデプロイ時にマイグレーションを先に実行する方針を追記する。

## Validation and Acceptance

ローカルで `flask --app app.py init-db` が成功し、SQLite の `user` テーブルが作成されることを確認できる。`flask --app app.py shell` で `User.query.first()` を実行した際に例外が出ず、初期ユーザーが作成されていれば `INITIAL_USER_*` が正しく反映されていることを確認できる。README の手順に従い、Cloud SQL で `DATABASE_URL` または `DB_*` を設定すれば接続文字列が正しく構築されることが分かる説明になっていることを確認する。

## Idempotence and Recovery

`flask db upgrade` と `init-db` は繰り返し実行しても安全であり、既存テーブルに対して破壊的な変更を行わない。万一不整合が起きた場合は、`migrations/versions` の初期マイグレーションと `alembic_version` を見直し、テスト用のSQLiteファイルを削除して再実行できる手順を記載する。

## Artifacts and Notes

必要に応じて、`flask db upgrade` の成功ログやマイグレーションファイルの短い抜粋をここに追記する。

## Interfaces and Dependencies

依存関係は `Flask-Migrate` と `PyMySQL` を前提とし、`config.py` に接続文字列構築関数、`app.py` に `init-db` CLI、`migrations/` に初期スキーマを追加する。README と `.env.example` は環境変数の名称と値の例を明示し、Cloud Run での接続方法とマイグレーション実行タイミングを説明する。

計画変更メモ: 2026-01-13 に全作業の完了と成果を記録した。
