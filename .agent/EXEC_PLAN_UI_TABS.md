# UIタブ化と画像ペースト対応の実装

このExecPlanは生きたドキュメントです。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective`の各セクションは作業の進行に合わせて更新し続けます。

リポジトリ直下の`PLANS.md`に従って本ドキュメントを維持・更新します。

## Purpose / Big Picture

ユーザーがモード切り替えをタブで行い、入力フォームをコンパクトに把握できるようにします。さらに、画像アップロードがドラッグ＆ドロップだけでなくコピー＆ペーストでも行えるようにして、入力の手間を減らします。実装後は、生成画面の上部にタブが表示され、選択中モードの概要がコンパクトなカードで確認でき、任意の画像ドロップゾーンにフォーカスしてペーストすると画像プレビューが更新されることを確認できます。

## Progress

- [x] (2025-02-14 10:20Z) 既存UIの構造とスタイルを確認し、タブ化に必要な差分を洗い出す。
- [x] (2025-02-14 10:35Z) `templates/index.html`でモード選択をタブUIに変更し、概要カードを配置する。
- [x] (2025-02-14 10:40Z) `static/css/index.css`でタブUIと概要カード、フォーカス状態のスタイルを追加する。
- [x] (2025-02-14 10:50Z) `static/js/index.js`でタブ切り替えと画像ペースト受付のロジックを実装する。
- [x] (2025-02-14 11:00Z) 動作確認と必要なスクリーンショット取得を実施し、結果を記録する。

## Surprises & Discoveries

- Observation: Playwrightのスクリーンショット取得時に`127.0.0.1`バインドでは応答が返らず、`0.0.0.0`で起動する必要があった。
  Evidence: `Page.goto: net::ERR_EMPTY_RESPONSE`が発生し、`python -c \"from app import app; app.run(host='0.0.0.0', port=5000, debug=True)\"`で解消。

## Decision Log

- Decision: 画像ペーストはドロップゾーンをフォーカスした状態で受け付ける方式にする。
  Rationale: どの入力欄に貼り付けるかをユーザーが明確に選択でき、誤った入力欄への貼り付けを防げるため。
  Date/Author: 2025-02-14 / ChatGPT

## Outcomes & Retrospective

モード切り替えをタブ表示に変更し、概要カードで用途・必要画像・結果を整理できるようになった。画像ドロップゾーンはフォーカス時にペーストを受け付け、視覚的にもフォーカスが分かるようになった。追加の改善点としては、将来的にペースト対象の自動選択やガイドツールチップの強化を検討できる。

## Context and Orientation

本リポジトリの生成画面は`templates/index.html`で定義され、見た目の詳細は`static/css/index.css`で管理されています。画面上のモード切り替えや入力フォームの表示切替は`static/js/index.js`の`initModeSwitch`関数が担っています。画像アップロードのプレビューやドラッグ＆ドロップは同ファイルの`bindImageUploader`関数で処理されています。今回の作業は、これら3ファイルに限定して行い、タブUIの追加と画像ペースト受付を実装します。

## Plan of Work

まず`templates/index.html`の「モード選択」セクションをタブ構造に置き換え、モード説明・用途・必要画像・結果を表示する概要カードを配置します。タブボタンには`data-mode`、`data-mode-description`、`data-mode-usage`、`data-mode-required`、`data-mode-result`、`data-mode-label`を付与し、`initModeSwitch`がこれらを読み取れるようにします。次に`static/css/index.css`でタブの横並び、アクティブ状態、概要カード、ドロップゾーンのフォーカス強調を追加します。最後に`static/js/index.js`でタブ選択時のUI更新処理を新しいDOM構造に合わせ、`bindImageUploader`にペースト受付の処理を追加して、フォーカスしたドロップゾーンに貼り付けられるようにします。変更後は生成画面を開き、タブ切り替えと画像ペーストの動作を確認します。

## Concrete Steps

作業ディレクトリはリポジトリルートです。

1. `templates/index.html`のモード選択セクションを編集し、タブと概要カードを追加します。
2. `static/css/index.css`にタブ関連のスタイルとドロップゾーンのフォーカススタイルを追加します。
3. `static/js/index.js`の`initModeSwitch`をタブ構造向けに更新し、`bindImageUploader`にペースト処理を追加します。
4. 必要ならローカルでアプリを起動し、タブ切り替えと画像ペーストを確認します。

想定コマンドの例:

  pwd
  python app.py

## Validation and Acceptance

ブラウザで生成画面を開き、上部にタブが表示されることを確認します。タブ切り替え時にモード説明と用途/必要画像/結果の情報が更新され、該当するフォームのみが表示されることが確認できれば合格です。さらに、画像アップロードのドロップゾーンをクリックしてフォーカスした状態で画像をコピー＆ペーストした際にプレビューが更新され、アップロード状態が「選択済み」になることを確認できれば受け入れ可能です。

## Idempotence and Recovery

本作業はHTML/CSS/JSの変更のみであり、同じ変更を複数回適用しても問題ありません。もし表示が崩れる場合は、タブと概要カードに関する変更箇所のみを一時的に元に戻し、段階的に再適用してください。

## Artifacts and Notes

作業中に確認した差分やスクリーンショットがあれば、後続のレビューに必要な最小限の内容のみ記録します。

## Interfaces and Dependencies

`static/js/index.js`の`initModeSwitch`は`data-mode`属性を持つ要素群を切り替える関数です。タブボタンに対して`data-mode`と各種説明属性を持たせること、`templates/index.html`内に`modeDescription`、`modeUsage`、`modeRequired`、`modeResult`の各要素IDが存在することが前提になります。`bindImageUploader`はファイル入力・プレビュー・ドロップゾーンを受け取る関数であり、ペースト用のイベントハンドラを追加しても既存のドラッグ＆ドロップ動作を壊さないことを要件とします。

変更履歴: 初版作成。タブUIと画像ペースト対応の実装方針を明文化。進捗と意思決定を追記。
