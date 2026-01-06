# 生成モード別ルート/テンプレート分割の実装計画

このExecPlanはPLANS.md(./PLANS.md)の指針に従って維持される生きた文書である。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective`を常に最新に更新し、この文書だけで初心者が作業を完遂できるようにする。

## Purpose / Big Picture
生成モードを専用ルートと専用テンプレートに分割し、不要なフォーム項目を送信しない構成へ改善する。利用者は「ラフ」「参照」「編集」の各ページで必要な入力だけを見ながら生成リクエストを送信でき、モード選択後の遷移先も一元管理されたマッピングで安定して動作する。

## Progress
- [x] (2025-02-14 01:20Z) 現行ルーティング/テンプレート/JSの依存関係を整理し、分割対象の共通パーツを把握する。
- [x] (2025-02-14 01:35Z) モード別ルートとPOSTハンドラを追加し、モードID→ルートの辞書を導入する。
- [x] (2025-02-14 01:55Z) `templates/index.html`を分割して`templates/modes/`配下に専用テンプレートを作成する。
- [x] (2025-02-14 02:20Z) 画面遷移の整合性を確認し、必要に応じて動作確認/スクリーンショットを取得する。

## Surprises & Discoveries
- Observation: なし。
  Evidence: なし。

## Decision Log
- Decision: モード別テンプレートは`templates/modes/base.html`と共通パーシャルで構成し、結果表示とモード概要を共通化する。
  Rationale: 3モード間の共通UIを保持しつつ、不要なセクションは各テンプレートで排除するため。
  Date/Author: 2025-02-14 / Codex

## Outcomes & Retrospective
モード別ルートとテンプレート分割を完了し、専用ページで必要な入力のみが表示される状態を確認した。スクリーンショットも取得済み。今後は実環境のAPIキーを入れて生成フローを確認するとより安心。

## Context and Orientation
- 生成UIのルートは`views/main.py`の`index`(GET/POST)に集約されており、テンプレートは`templates/index.html`でモード切替UIを条件表示する構成になっている。
- 生成モード定義は`services/modes.py`にあり、`id`がフォーム送信やモード選択に使われている。
- 画面の表示切替やアップローダー初期化は`static/js/index.js`が担っており、IDベースで要素を参照するため要素が存在しない場合は処理をスキップできる。

## Plan of Work
1. `views/main.py`にモードID→ルートの辞書とURL生成ヘルパーを追加し、`/`はデフォルトモードへリダイレクトする。`/generate/rough`、`/generate/reference`、`/generate/edit`を追加し、それぞれのPOSTハンドラで必要なフォームだけ受け取る。
2. `templates/index.html`の共通要素を分割し、`templates/modes/`配下に`rough.html`、`reference.html`、`edit.html`を作成する。共通の結果表示やヘッダーはパーシャル化し、各テンプレートには必要なセクションのみ残す。
3. `templates/mode_select.html`はモードID→ルート辞書を参照してリンクを生成するよう調整し、モード選択後の遷移先を一元管理する。
4. 必要であればスクリーンショットを取得し、`Progress`/`Decision Log`/`Outcomes & Retrospective`を更新する。

## Concrete Steps
- ルートの追加に伴い`views/main.py`で`render_template`に渡す共通コンテキストを整理する。共通化できる変数はヘルパー関数にまとめる。
- `templates/modes/`に共通パーツ(結果表示、マスクエディタなど)を`_`始まりのパーシャルとして配置し、各モードテンプレートで`include`する。
- `static/js/index.js`のID参照が欠けても安全に動作することを確認し、足りないIDがあればテンプレート側で補う。
- `python -m compileall`で構文チェックを行い、必要なら`flask --app app.py run`で目視確認する。

## Validation and Acceptance
- `/`へアクセスするとデフォルトモード(ラフ)へリダイレクトされること。
- `/generate/rough`、`/generate/reference`、`/generate/edit`でそれぞれ必要な入力のみが表示され、不要なフォーム項目が送信されないこと。
- モード選択画面でカードを選ぶと対応する専用ルートへ遷移すること。
- `python -m compileall`がエラーなしで完了すること。

## Idempotence and Recovery
- テンプレート分割は`git checkout -- <file>`で簡単に巻き戻せる。ルート名のミスがあれば`url_for`の例外ログを手がかりに修正する。
- 変更を複数回適用しても重複ルートが発生しないよう、`views/main.py`のBlueprint内での定義を一意に保つ。

## Artifacts and Notes
- 画面確認時のURLやスクリーンショットの保存先をここに追記する。

## Interfaces and Dependencies
- `views/main.py`: `MODE_ROUTE_MAP`(仮)を定義し、`/generate/rough`などのルートと紐づける。`render_template`に`current_mode`/`mode_routes`などを渡す。
- `templates/modes/*.html`: `current_mode`、`image_data`、`user_presets`、`presets_payload`などのコンテキストを使う。
- `templates/mode_select.html`: `mode_routes`辞書を参照してリンクを作る。

計画変更メモ: 動作確認とアウトカムの更新を反映。
