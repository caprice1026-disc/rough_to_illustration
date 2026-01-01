# GUIチャットモードを追加し既存モードをメニュー経由で利用できるようにする

このExecPlanは生きたドキュメントです。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective`の各セクションは作業の進行に合わせて常に更新する必要があります。

このリポジトリのルートにPLANS.mdが存在するため、本ドキュメントは`PLANS.md`に従って更新・維持します。

## Purpose / Big Picture

ユーザーがGUI上でテキストと画像を混ぜたチャット形式のやり取りを行い、既存の生成・編集機能をチャットのメニューから呼び出せるようにします。実装後は、同じページで「モード切替」からチャットモードを選び、会話履歴を保持したままテキストチャットやラフ→仕上げ、参照着色、インペイント/アウトペイントを実行できることを確認できます。

## Progress

- [x] (2025-10-02 01:10Z) 既存のモード定義・テンプレート・JSの構成を調査し、チャットモードに必要な差分を洗い出す。
- [x] (2025-10-02 01:40Z) チャット履歴をセッションに保存し、Gemini向けのテキスト応答生成ロジックを追加する。
- [x] (2025-10-02 02:15Z) チャットUI（会話履歴表示、入力欄、メニュー選択、追加フォーム）を実装し、既存モードをメニュー経由で実行できるようにする。
- [x] (2025-10-02 02:40Z) 既存の生成・編集機能とチャットモードの連携を仕上げ、テストを追加する。
- [x] (2025-10-02 03:10Z) 動作確認・テスト実行・スクリーンショット取得を行い、ExecPlanの更新を完了する。

## Surprises & Discoveries

- Observation: pytest実行時にSQLAlchemyのLegacyAPIWarningが発生したが、挙動自体は問題なくテストは完了した。
  Evidence: pytest実行ログにLegacyAPIWarningが出力された。

- Observation: スクリーンショット取得時はFlaskのデバッグ起動では接続が不安定だったため、0.0.0.0の通常起動で撮影した。
  Evidence: playwrightのERR_EMPTY_RESPONSEを回避するため起動方法を変更した。

## Decision Log

- Decision: チャット履歴はセッションに「画像IDのみ」を保存し、画像本体は既存の一時保存ディレクトリへ格納する方式を採用する。
  Rationale: クッキーサイズ制限を避け、既存の画像保存ロジックと整合させるため。
  Date/Author: 2025-10-02 / Agent

- Decision: チャットモードの編集はマスク画像のアップロードで行い、専用のエディタは追加しない。
  Rationale: 既存UIを壊さずにメニュー経由で編集機能を使えることを優先し、実装コストを抑えるため。
  Date/Author: 2025-10-02 / Agent

## Outcomes & Retrospective

チャットモードはテキスト会話と既存の画像生成/編集メニューを統合し、会話履歴を保持できるようになった。今後はチャット専用のマスクエディタ統合や履歴の永続化が追加改善ポイントとなる。

## Context and Orientation

Flaskアプリは`app.py`の`create_app`で初期化され、`views/main.py`の`index`がメイン画面を描画します。モード定義は`services/modes.py`にあり、`templates/index.html`と`static/js/index.js`でフォーム表示の切替を行います。生成処理は`services/generation_service.py`が担い、Gemini API連携は`illust.py`にまとまっています。チャットモードは新しいGenerationModeとして追加し、GUIは既存のモードUIを残したまま追加する必要があります。

## Plan of Work

まず`services/modes.py`にチャット用の`GenerationMode`を追加し、`views/main.py`の`index`でチャット用POST処理を分岐できるようにする。次に`illust.py`にテキスト応答生成関数を追加し、`services/chat_service.py`（新規）でセッション履歴の保存・読み出し・Gemini向けコンテンツ構築を行う。`templates/index.html`にチャットUI（会話履歴、入力欄、メニュー、モード別入力欄）を追加し、`static/js/index.js`でチャットメニューの選択や表示切替を制御する。最後にpytestベースのテストを追加し、チャットモードと既存モードの分岐が壊れていないことを確認する。

## Concrete Steps

`/workspace/rough_to_illustration`で作業を行う。

1. `services/modes.py`にチャットモード定義を追加する。
2. `illust.py`にテキストチャット用のGemini呼び出し関数を追加し、レスポンスからテキストを抽出する。
3. `services/chat_service.py`を新規作成し、セッションにチャット履歴を保存するヘルパーと、履歴からGemini入力を構築する関数を実装する。
4. `views/main.py`にチャットモードのPOST処理（テキストチャット、既存モード実行、履歴クリア）を追加し、テンプレートへチャット履歴を渡す。
5. `templates/index.html`にチャットUIを追加し、既存のフォームは削除せずに切替対象として残す。
6. `static/js/index.js`にチャットモードのメニュー選択やフォーム切替処理を追加する。
7. `tests/`配下にpytestテストを追加し、チャットモードのGET/POSTと既存モードの分岐が動くことを確認する。
8. テストを実行し、必要なら調整する。

## Validation and Acceptance

アプリを起動してログイン後、モード選択で「チャット（GUI）」を選択できることを確認する。チャット画面でテキストを送信すると履歴に追加され、次の送信で履歴が保持されていることを確認する。メニューから既存モードを選択し、必要な画像やテキストを入力して送信すると、チャット履歴に画像生成結果が表示されることを確認する。`pytest`を実行し、新規テストがパスすることを確認する。

## Idempotence and Recovery

チャット履歴の初期化は「履歴クリア」操作で行い、何度でも安全に実行できるようにする。画像保存は既存の一時保存パスを再利用し、不要な画像は適宜削除する。問題が起きた場合はチャット履歴を削除して再実行できる。

## Artifacts and Notes

主要な変更は`services/chat_service.py`と`templates/index.html`、`views/main.py`に集中している。pytest実行ログで5件のテストが成功したことを確認し、`chat_mode.png`でGUIの見た目を記録した。

## Interfaces and Dependencies

`illust.py`にテキスト応答生成関数`generate_chat_response`を追加する。`services/chat_service.py`に`load_chat_history`、`save_chat_history`、`append_chat_message`、`build_chat_contents`などの関数を追加する。`views/main.py`の`index`にチャットモード分岐を追加し、チャット用フォームの入力名を明記する。依存ライブラリとしてpytestを`requirements.txt`に追加する。

変更履歴: 2025-10-02 / Agent により進捗・意思決定・発見事項を更新。
