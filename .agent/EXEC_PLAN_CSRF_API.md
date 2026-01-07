# APIのCSRF保護とフロント送信対応を追加する

このExecPlanはPLANS.md (./PLANS.md) の指針に従って維持されるべき生きた文書である。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective` を常に最新に更新し、本計画だけで初心者が作業を完遂できるようにする。

## Purpose / Big Picture

APIのPOST/DELETEエンドポイントをCSRF（Cross-Site Request Forgery: 認証済みユーザーのブラウザを悪用して意図しない操作を実行させる攻撃）から保護し、SPAフロントエンドがトークンを送信して安全に利用できるようにする。変更後は、`/api/auth/login` などの状態変更APIがCSRFトークン必須となり、SPAは自動でトークンを取得してヘッダー送信する。加えて、Origin/Referer検証とSameSite設定でAPI利用の安全性を高める。ブラウザでログイン・生成・チャット操作が従来通り行えること、かつCSRFトークンなしのPOSTが拒否されることを確認できる。

## Progress

- [x] (2026-01-07 03:20Z) 既存API/SPA構成、認証フロー、CSRF関連の依存関係を確認し、変更対象を洗い出す。
- [x] (2026-01-07 03:28Z) CSRFProtectの導入と初期化、CSRFエラー時のJSON応答を追加した。
- [x] (2026-01-07 03:31Z) `/api/csrf` を追加し、SPAの非GETリクエストにCSRFヘッダー送信を組み込んだ。
- [x] (2026-01-07 03:33Z) Origin/Referer検証とSameSite設定を反映した。
- [x] (2026-01-07 03:35Z) テストをCSRF対応に更新し、pytest実行を試行した（環境にpytestが未インストールのため失敗）。

## Surprises & Discoveries

- Observation: `python -m pytest` が `No module named pytest` で失敗した。
  Evidence: `python -m pytest` 実行時に `No module named pytest` と表示。

## Decision Log

- Decision: CSRFトークンはFlask-WTFのCSRFProtectを使用し、SPAは`/api/csrf`から取得したトークンを`X-CSRFToken`ヘッダーで送信する。
  Rationale: フォーム送信とJSON送信の両方に対応でき、既存APIの変更を最小化できるため。
  Date/Author: 2026-01-07 / Codex
- Decision: 追加緩和として、APIの状態変更メソッドに対するOrigin/Referer検証を導入し、SameSiteをLaxに設定する。
  Rationale: トークン送信が困難なケースやブラウザ挙動差を補完し、セッションCookieの漏洩リスクを下げるため。
  Date/Author: 2026-01-07 / Codex

## Outcomes & Retrospective

APIのPOST/DELETEにCSRF保護を追加し、SPAがCSRFトークンを取得してヘッダー送信するようになった。Origin/Referer検証とSameSite設定を追加し、セッションベースのCSRF耐性を強化した。テストはCSRFヘッダー対応まで更新したが、pytest未インストールのためローカル検証は未実施。次は依存関係を入れてpytestを再実行する。

## Context and Orientation

本リポジトリはFlaskアプリで、`app.py` がアプリ生成とBlueprint登録を行う。APIは `views/api.py` の `api_bp` に集約され、SPAフロントは `static/spa/app.js` から `/api/*` に対して `fetch` を行う。拡張は `extensions.py` に `SQLAlchemy` と `LoginManager` を定義している。CSRF保護は新たにFlask-WTFの `CSRFProtect` を導入し、`config.py` に関連設定を追加する。テストは `tests/test_chat.py` がAPIのPOST操作を行うため、CSRFトークン付与を追加する必要がある。

## Plan of Work

まず `requirements.txt` にFlask-WTFを追加し、`extensions.py` に `CSRFProtect` インスタンスを定義する。`app.py` のアプリ初期化で `csrf.init_app(app)` を呼び、CSRFエラーをAPI向けJSONで返すエラーハンドラを登録する。次に `views/api.py` に `/api/csrf` を追加し、`generate_csrf()` でトークンを返す。`static/spa/app.js` では非GETリクエスト前にトークンを取得し、`X-CSRFToken` ヘッダーに付与する。加えて `app.py` または共通のフックで、`/api` のPOST/DELETE/PUT/PATCHに対してOrigin/Refererが自ホストであることを確認し、不一致ならJSONで403を返す。`config.py` に `SESSION_COOKIE_SAMESITE = "Lax"` や `WTF_CSRF_HEADERS` を追加し、ブラウザからのCSRF耐性を高める。最後に `tests/test_chat.py` をCSRF対応のヘッダー送信に更新する。

## Concrete Steps

- `requirements.txt` に `Flask-WTF` を追加する。
- `extensions.py` に `csrf = CSRFProtect()` を追加し、`app.py` で初期化する。
- `app.py` にCSRFエラーハンドラ（APIではJSON 400）と、API用Origin/Refererチェックのbefore_requestを追加する。
- `views/api.py` に `/api/csrf` エンドポイントを追加する。
- `static/spa/app.js` にCSRFトークン取得とヘッダー付与を追加する。
- `config.py` にSameSiteとCSRFヘッダー設定を追加する。
- `tests/test_chat.py` のPOSTリクエストにCSRFトークンヘッダーを付与する。

## Validation and Acceptance

- `python -m pytest` を実行し、既存テストが成功する。
- ブラウザで `http://localhost:5000/` を開き、ログイン後に生成・チャット・プリセット作成/削除が従来通り動作する。
- CSRFトークンなしで `/api/auth/login` にPOSTするとHTTP 400（JSONでCSRFエラー）が返る。
- `/api/csrf` のレスポンスに `csrf_token` が含まれ、SPAが非GETリクエストでヘッダー送信している。

## Idempotence and Recovery

追加した設定・エンドポイント・フロントの変更は何度適用しても安全である。問題が起きた場合は `requirements.txt` と `extensions.py` のCSRF追加を取り消し、`app.py` の初期化/エラーハンドラ/Originチェックを元に戻すことで復旧できる。DBスキーマの変更はないためデータ破壊の心配はない。

## Artifacts and Notes

- なし（作業中に必要なら短いログや差分をここに記録する）。

## Interfaces and Dependencies

- 依存ライブラリ: `Flask-WTF`（CSRFProtectと`generate_csrf` を使用）
- `extensions.py`: `csrf` インスタンスを定義する。
- `app.py`: `csrf.init_app(app)`、CSRFエラーハンドラ、Origin/Refererチェックのbefore_requestを追加する。
- `views/api.py`: `@api_bp.get("/csrf")` を追加し `{"csrf_token": <token>}` を返す。
- `static/spa/app.js`: 非GETの`fetch`前にトークンを取得し `X-CSRFToken` ヘッダーに追加する。
- `config.py`: `SESSION_COOKIE_SAMESITE` と `WTF_CSRF_HEADERS` を設定する。
- `tests/test_chat.py`: `/api/auth/login` と `/api/chat/messages` のPOSTにCSRFヘッダーを追加する。

計画変更メモ: なし（初版）。
計画変更メモ: 進捗完了とpytest未インストールによるテスト未実施を追記。
