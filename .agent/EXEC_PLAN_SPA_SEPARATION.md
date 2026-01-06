# SPA化とフロントエンド/バックエンド分離を実現する

このExecPlanはPLANS.md (./PLANS.md) の指針に従って維持されるべき生きた文書である。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective` を常に最新に更新し、本計画だけで初心者が作業を完遂できるようにする。

## Purpose / Big Picture

サーバー側テンプレートに依存したUIをやめ、静的なSingle Page Application (SPA) を提供し、API経由で認証・生成・チャット・プリセット管理を行えるようにする。これによりフロントエンドは静的配信のみで運用でき、バックエンドはJSON APIに専念できる。利用者は `http://localhost:5000/` にアクセスするだけで、ログイン、生成、チャットを単一画面内で切り替えられることを確認できる。

## Progress

- [x] (2026-01-07 00:40Z) 既存コードと要求を確認し、SPA化とAPI分離が大規模変更であることを把握した。
- [x] (2026-01-07 02:05Z) API用BlueprintとSPA配信用ルートを実装した。
- [x] (2026-01-07 02:20Z) 認証、生成、プリセット、チャットのAPIを設計・実装し、既存ロジックを再利用できるように整理した。
- [x] (2026-01-07 02:30Z) SPAの静的フロントエンドを追加し、APIと接続して画面遷移なしで操作できるようにした。
- [x] (2026-01-07 02:45Z) テストとREADMEを更新し、`python -m compileall .` で構文確認を行った。

## Surprises & Discoveries

- Observation: なし。
  Evidence: なし。

## Decision Log

- Decision: 認証は既存のFlask-Loginセッションを継続利用し、APIはJSONで応答する。
  Rationale: 既存のログイン状態管理を維持しつつ、SPA側からCookie認証でAPIを呼べるため。
  Date/Author: 2026-01-07 / Codex
- Decision: SPAは `static/spa/` で静的配信し、`/api` プレフィックスでバックエンドAPIを分離する。
  Rationale: フロントとバックの責務を明確化し、将来的なフロント差し替えを容易にするため。
  Date/Author: 2026-01-07 / Codex
- Decision: 編集モードはマスク画像ファイルも受け取れるようにし、SPAから直接アップロードできるようにする。
  Rationale: 旧UIのキャンバス編集に依存せず、SPAで最低限の編集フローを維持するため。
  Date/Author: 2026-01-07 / Codex

## Outcomes & Retrospective

SPA配信とJSON APIを分離し、ログイン/生成/プリセット/チャットを単一ページで操作できる構成に刷新した。既存のサービス層を再利用し、APIからの利用に合わせて編集モードのマスク入力も拡張した。テストとREADMEを更新し、`python -m compileall .` で構文確認を実施した。今後は実際のAPIキーを使ったブラウザ検証と、UIの細かな体験調整を行うとより安心。

## Context and Orientation

既存のFlaskアプリは `app.py` で `views/auth.py`, `views/main.py`, `views/chat.py` のBlueprintを登録し、`templates/` のJinja2テンプレートでページをレンダリングしている。`services/generation_service.py` と `services/chat_service.py` が画像生成やチャット生成の主要ロジックを担い、`models.py` はユーザー、プリセット、チャット履歴を保存する。今回の変更ではサーバー側テンプレートに依存せず、JSON APIと静的SPAに分離するため、`views/api.py` を新設してAPIを集約し、`views/spa.py` でSPAを配信する。

## Plan of Work

1. APIの共通応答とシリアライザを `views/api.py` に実装し、`/api` 配下に以下のエンドポイントを用意する。認証はセッションベースのため、`/api/auth/login` と `/api/auth/logout` でログイン/ログアウトを行い、`/api/me` でログイン状態を返す。モード一覧、オプション、プリセット、生成、チャットの各機能はJSONで応答する。
2. SPA配信用のBlueprintを `views/spa.py` に追加し、`static/spa/index.html` を返す。`/api` と `/static` には干渉しないようルートを制御する。
3. 生成APIでは既存の `services/generation_service.py` を利用しつつ、編集モードでマスク画像ファイルも受け取れるよう拡張する。プリセットのバリデーションは既存のルールを踏襲する。
4. チャットAPIは `services/chat_service.py` のロジックを使ってセッション作成、メッセージ送信、画像取得をJSONで提供する。
5. SPAフロントエンドを `static/spa/` に実装し、ログイン後に「生成」「チャット」ビューを単一ページ内で切り替えられるようにする。API呼び出しは `fetch` + Cookieで行い、結果画像はData URLで表示しダウンロードできるようにする。
6. `app.py` でAPIとSPAのBlueprintのみを登録し、必要であれば旧Blueprintは登録から外す。READMEとテストもAPI/SPA前提に更新する。

## Concrete Steps

- `views/api.py` と `views/spa.py` を追加し、`app.py` のBlueprint登録を更新する。
- `services/generation_service.py` の `run_edit_generation` をマスク画像ファイル入力にも対応させる。
- `static/spa/index.html`, `static/spa/app.js`, `static/spa/app.css` を作成し、既存の `static/css/*.css` と併用する。
- `tests/test_chat.py` をAPI/SPA前提に更新し、必要なら新規APIテストを追加する。
- READMEの利用方法と構成説明をSPA/API向けに書き換える。

## Validation and Acceptance

- `flask --app app.py run` で起動し、`http://localhost:5000/` にアクセスするとSPAが表示される。
- 未ログイン状態でAPIを叩くとJSONで401が返り、ログイン後は `/api/me` がユーザー情報を返す。
- 生成モードで画像と指示を送信するとJSONで生成結果が返り、SPA上でプレビュー表示される。
- チャットでテキストを送ると応答が追加され、セッション一覧が更新される。
- `python -m pytest` または `python -m compileall` を実行し、エラーなく完了する。

## Idempotence and Recovery

API追加とSPA配置は何度実行しても問題ない。問題が発生した場合は `app.py` のBlueprint登録と新規ファイルの追加状況を確認し、`git checkout -- <file>` で元に戻せる。DB内容は既存モデルを利用するため破壊的変更は発生しない。

## Artifacts and Notes

- `python -m compileall .` を実行し、構文エラーがないことを確認した。

## Interfaces and Dependencies

- `views/api.py`: `api_bp` を定義し、`/api/auth/*`, `/api/me`, `/api/modes`, `/api/options`, `/api/presets`, `/api/generate/*`, `/api/chat/*` を実装する。
- `views/spa.py`: `spa_bp` を定義し、`/` と任意パスでSPAの `index.html` を返す。
- `services/generation_service.py`: 編集モードのマスク入力をファイル/データURL両対応にする。
- `static/spa/app.js`: API呼び出し、画面切替、生成/プリセット/チャットUIのロジックをまとめる。
- `static/spa/app.css`: SPA専用のレイアウト調整。
- 依存パッケージは既存のFlask/SQLAlchemy/Flask-Loginを継続利用する。

計画変更メモ: SPA/API実装とテスト更新の進捗を反映し、完了内容と決定事項を追記した。
