# 画像アップロードのバリデーション強化と上限設定の導入

このExecPlanはPLANS.md (./PLANS.md) の指針に従って維持されるべき生きた文書である。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective` を常に最新に更新し、本計画だけで初心者が作業を完遂できるようにする。

## Purpose / Big Picture

アップロードされる画像に対して、ファイルサイズだけでなく幅・高さ・総ピクセル数を検査し、PNG/JPEG以外の形式を明確に拒否する。加えて、MIMEタイプと拡張子の不一致や実際の画像形式の不整合を検出してエラーを返し、PILの`MAX_IMAGE_PIXELS`制限を使って巨大画像の展開を抑止する。変更後は、制限超過時に分かりやすいエラーメッセージが返り、環境変数で上限を調整できる。`/api/generate/*`と`/api/chat/messages`の画像アップロードで同じ検証が行われることを、APIレスポンスとログで確認できる。

## Progress

- [x] (2026-01-07 01:20Z) 既存の画像デコードとアップロード処理の流れを整理する。
- [x] (2026-01-07 01:30Z) 環境変数で指定できる画像上限値を`config.py`に追加し、.envの例を更新する。
- [x] (2026-01-07 01:40Z) `services/generation_service.py`でMIME/拡張子/形式/サイズの共通検証とデコードを実装する。
- [x] (2026-01-07 01:45Z) `services/chat_service.py`のアップロード保存処理を共通デコードに統合する。
- [ ] (2026-01-07 01:50Z) 簡易テストや手動確認手順を実行する（未実施: python -m pytest）。

## Surprises & Discoveries

- Observation: なし（作業中に更新）。
  Evidence: なし。

## Decision Log

- Decision: 許可形式をPNG/JPEGに限定し、MIMEエイリアス`image/jpg`は`image/jpeg`へ正規化して一致判定を行う。
  Rationale: 既存の拡張子処理と互換性を保ちつつ、実体とメタ情報の不一致を検知するため。
  Date/Author: 2026-01-07 / Codex
- Decision: デフォルト上限は幅/高さ8192px、総ピクセル数67,108,864（64 * 1024 * 1024）とする。
  Rationale: 4K相当を許容しつつ、極端な画像のメモリ消費を抑制するため。必要に応じて環境変数で調整できる。
  Date/Author: 2026-01-07 / Codex

## Outcomes & Retrospective

実装完了後に追記する（現在はテスト未実施）。

## Context and Orientation

本リポジトリはFlaskアプリで、画像アップロードのデコードは`services/generation_service.py`の`decode_uploaded_image`/`decode_uploaded_image_raw`/`decode_data_url_image`に集約されている。`services/chat_service.py`にはチャット用のアップロード保存処理`save_uploaded_image`があり、ここでPILの読み込みを独自に行っている。APIは`views/api.py`からこれらのサービス関数を呼び出し、`GenerationError`をJSONエラーとして返している。設定値は`config.py`の`Config`クラスで環境変数から読み込まれ、`MAX_CONTENT_LENGTH`は既に設定済みである。

## Plan of Work

まず`config.py`に画像の幅・高さ・総ピクセル数上限を追加し、環境変数で上書きできるようにする。次に`services/generation_service.py`へ、PNG/JPEGのみ許可するためのMIMEタイプ・拡張子・実際の画像形式の整合チェックと、`PIL.Image.MAX_IMAGE_PIXELS`設定および幅・高さ・ピクセル数の検証を共通化したデコード関数を実装する。既存の`decode_uploaded_image`と`decode_uploaded_image_raw`はこの共通処理に統一し、データURLのデコードにも同じ検証を適用する。最後に`services/chat_service.py`の`save_uploaded_image`を共通デコード処理へ寄せ、チャット経由のアップロードでも同じ検証が動くようにする。必要に応じて`.env.example`に新しい環境変数を追加し、簡易な手動確認手順を記録する。

## Concrete Steps

- `config.py`に`MAX_IMAGE_WIDTH`、`MAX_IMAGE_HEIGHT`、`MAX_IMAGE_PIXELS`を追加し、環境変数から読み込む。
- `services/generation_service.py`に許可形式の定義、MIME/拡張子/形式の整合チェック、サイズ検証、`PIL.Image.MAX_IMAGE_PIXELS`設定を含む共通デコード関数を追加する。
- 既存の`decode_uploaded_image`/`decode_uploaded_image_raw`/`decode_data_url_image`が共通デコード関数を使うように修正する。
- `services/chat_service.py`の`save_uploaded_image`を共通デコード関数に置き換え、保存時のMIMEタイプは実際の画像形式に合わせる。
- `.env.example`に新しい環境変数の例を追記する。

## Validation and Acceptance

- `flask --app app.py run`で起動し、`/api/generate/rough`や`/api/chat/messages`にPNG/JPEG以外の画像や拡張子/実体が不一致の画像を送ると、JSONで分かりやすいエラーメッセージが返る。
- 幅・高さ・ピクセル数の上限を超える画像を送ると、上限値を含むエラーメッセージで拒否される。
- PNG/JPEGの正しい画像は従来通り生成/チャットが実行される。
- 可能なら`python -m pytest`を実行し、既存テストが通ることを確認する（失敗した場合は理由を記録する）。

## Idempotence and Recovery

設定追加やデコード処理の変更は繰り返し適用しても安全である。問題が出た場合は`services/generation_service.py`と`services/chat_service.py`の変更を元に戻し、`config.py`と`.env.example`の追加設定を削除すれば復旧できる。DBスキーマ変更はない。

## Artifacts and Notes

- なし（作業中に必要なら短いログや差分をここに記録する）。

## Interfaces and Dependencies

- 依存ライブラリ: `PIL` (Pillow)
- `config.py`: `MAX_IMAGE_WIDTH`/`MAX_IMAGE_HEIGHT`/`MAX_IMAGE_PIXELS`を追加。
- `services/generation_service.py`: 共通デコード関数、MIME/拡張子/形式整合チェック、サイズ検証、`PIL.Image.MAX_IMAGE_PIXELS`設定。
- `services/chat_service.py`: `save_uploaded_image`で共通デコード関数を使用し、保存時のMIMEタイプを正規化。
- `.env.example`: 新しい環境変数の例を追加。

計画変更メモ: 進捗と決定事項を更新し、テスト未実施を記録。
