# Cloud BuildトリガーにマイグレーションJobを組み込む

このExecPlanはPLANS.md（./PLANS.md）の指針に従って維持される生きた文書である。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective`を常に最新に更新し、この文書だけで初学者が作業を完遂できるようにする。

## Purpose / Big Picture

GitHubのPushを起点にCloud Buildが自動でCloud Runへデプロイする運用に合わせ、デプロイ前に必ずマイグレーションを実行できる仕組みを用意する。これにより、アプリ起動時にDBが未更新で落ちることを防ぎ、初回ユーザー作成も安全に一度だけ行える。変更後は、`cloudbuild.yaml` を使ったパイプラインで「ビルド → マイグレーションJob実行 → デプロイ」が完結し、READMEに運用手順が明確になる。

## Progress

- [x] (2026-01-13 22:30Z) 既存のCloud Buildログとリポジトリ構成を確認し、Dockerfileビルドであることとマイグレーション未実行の課題を整理した。
- [x] (2026-01-13 22:45Z) `cloudbuild.yaml` を追加し、ビルド/プッシュ/マイグレーションJob実行/デプロイの順序を定義した。
- [x] (2026-01-13 22:45Z) READMEにCloud Buildトリガーの設定変更、Cloud Run Job作成、初回ユーザー作成の運用方針を追記した。
- [x] (2026-01-13 22:45Z) 変更内容を見直し、ExecPlanの結果と学びを記録した。

## Surprises & Discoveries

現時点では特記事項なし。実装中に想定外の挙動があれば、短い根拠とともに追記する。

## Decision Log

- Decision: Cloud Buildトリガーを `cloudbuild.yaml` 方式に切り替え、Cloud Run Jobでマイグレーションを実行する。
  Rationale: Triggerだけの自動デプロイではマイグレーションを挟めないため、明示的なビルド構成で制御する必要がある。
  Date/Author: 2026-01-13 / Codex
- Decision: マイグレーションは常時 `db upgrade` を実行し、初回ユーザー作成は `init-db` を一度だけ実行する運用を推奨する。
  Rationale: 既存ユーザーの上書きを避けつつ、初回だけ安全にユーザーを作成するため。
  Date/Author: 2026-01-13 / Codex

## Outcomes & Retrospective

Cloud Buildトリガー用の `cloudbuild.yaml` を追加し、マイグレーションJob更新→実行→デプロイの順序を明示した。READMEにはトリガーの切り替え方法、Jobの作成例、初回ユーザー作成の扱い、SQLite検証環境の注意点を追記した。実環境での実行確認は未実施のため、Trigger設定変更後にビルドログでJob実行が挟まることを確認する必要がある。

## Context and Orientation

本リポジトリはFlaskアプリで、`Dockerfile` を使ってCloud Buildがイメージを作成し、Cloud Runへ自動デプロイしている。現在のTriggerは暗黙のビルド手順で動作しており、デプロイ前に `flask db upgrade` を実行する手段がない。`app.py` には `init-db` CLIがあり、`db upgrade` と初期ユーザー作成を一度に行える。Cloud SQL接続はUnixソケットを前提にしている。

## Plan of Work

まず `cloudbuild.yaml` を追加して、Dockerビルドとプッシュの後にCloud Run Jobを更新・実行し、その後にCloud Runへデプロイする流れを定義する。次にREADMEへ、Triggerの設定変更手順、Cloud Run Jobの作成方法、初回ユーザー作成を一度だけ実行する方法を追記する。最後に全体を見直し、ExecPlanの進捗と成果を更新する。

## Concrete Steps

作業はリポジトリルートで行う。`cloudbuild.yaml` を追加し、`_REGION`・`_SERVICE_NAME`・`_MIGRATION_JOB` などの置換変数を定義する。Cloud Run Jobは既存の設定（Cloud SQL接続やSecret）を保持する前提で、ビルドごとにイメージ更新→Job実行→デプロイの順で進める。READMEにはTrigger設定を `cloudbuild.yaml` に切り替える手順、Job作成コマンドの例、初回ユーザー作成の推奨手順を追加する。

## Validation and Acceptance

READMEに従ってCloud Buildトリガー設定を切り替えた場合、ビルドが `cloudbuild.yaml` の順序で実行されることが分かる説明になっていることを確認する。Cloud Run Jobを作成し、`db upgrade` が実行されてからCloud Runへデプロイされる流れが明確になっていれば完了とする。

## Idempotence and Recovery

`db upgrade` は繰り返し実行しても安全である。問題が起きた場合は `cloudbuild.yaml` を元のTrigger方式へ戻し、Jobの実行を手動に戻せるようにする。

## Artifacts and Notes

必要に応じて、Cloud Buildログや `cloudbuild.yaml` の要点をここに追記する。

## Interfaces and Dependencies

追加するファイルは `cloudbuild.yaml`。更新対象は `README.md`。Cloud Run Jobは `gcloud run jobs create` で作成し、`db upgrade` と `init-db` を用途で使い分ける。JobがCloud SQLへ接続できるようにCloud SQL接続設定とSecretを付与する。

計画変更メモ: 2026-01-13 に `cloudbuild.yaml` 追加とREADME更新の完了を反映した。
