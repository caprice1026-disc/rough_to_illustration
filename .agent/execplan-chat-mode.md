# チャットモード追加と履歴保存を備えたマルチターン生成

このExecPlanは生きたドキュメントです。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective`の各セクションは作業中に更新し続ける必要があります。

このリポジトリのルートにあるPLANS.mdに従って維持します。

## Purpose / Big Picture

ユーザーはGUI上の新しいチャットモードで、テキスト会話や画像生成の依頼をチャット形式で行えるようになります。チャット欄のメニューから既存の生成モードを選択し、会話の流れに沿って複数ターンの編集や追加指示を行えます。履歴はアカウントに紐づいて保存され、ログアウト後もセッション一覧から再参照できます。ブラウザでチャット画面を開き、テキスト送信や画像生成のやり取りが履歴に残ることを確認することで動作を確認できます。

## Progress

- [x] (2026-01-02 13:40Z) 既存構成の調査とチャットモードの設計方針を確定した。
- [x] (2026-01-02 13:46Z) チャットセッション/メッセージを保持するDBモデルと保存ロジックを追加した。
- [x] (2026-01-02 13:50Z) チャット用の生成処理（テキスト応答・画像応答・既存モードへの委譲）を実装した。
- [x] (2026-01-02 13:55Z) チャットUI（テンプレート・CSS・JS）と既存GUIへのモード追加を実装した。
- [x] (2026-01-02 13:58Z) テスト実装と既存機能の動作確認を行い、ExecPlanの記録を更新した。

## Surprises & Discoveries

- Observation: テスト実行時にFlask本体が未インストールだったため、依存関係のインストールが必要だった。
  Evidence: `pytest`実行時の`ModuleNotFoundError: No module named 'flask'`。

## Decision Log

- Decision: チャット機能は専用の`/chat`画面として追加し、チャット入力欄のメニューで既存モードを選べるUI構成にした。
  Rationale: 既存の生成フォームを保持しつつ、チャット特化の操作と履歴表示を明確に分離できるため。
  Date/Author: 2026-01-02 / ChatGPT
- Decision: チャットの画像履歴は`instance/chat_images`配下に保存し、メッセージに複数添付を持たせるモデルを採用した。
  Rationale: 1メッセージに複数画像が必要なモード（完成絵参照など）に対応するため。
  Date/Author: 2026-01-02 / ChatGPT
- Decision: マルチターン編集は「前の結果を追加編集」モードを用意し、直近の生成画像を入力に再利用する方式にした。
  Rationale: 既存のインペイント/アウトペイントとは別に、チャットだけでの追加指示を成立させるため。
  Date/Author: 2026-01-02 / ChatGPT

## Outcomes & Retrospective

チャットモードのUIとバックエンド、履歴保存、セッション編集モードを実装し、テストで基本動作を確認した。今後の改善として、チャットUIでのマスク編集機能や履歴検索などを追加するとさらに便利になる。

## Context and Orientation

アプリのエントリポイントは`app.py`で、`create_app()`内でFlask拡張とBlueprintが登録される。既存の生成モードは`services/modes.py`で定義され、`views/main.py`と`templates/index.html`でGUIに反映されている。画像生成の実体は`services/generation_service.py`が`illust.py`のGemini API呼び出しをラップしている。静的UIロジックは`static/js/index.js`と`static/css/index.css`にある。これらに加え、新しいチャット画面と永続的な履歴保存用のモデル・ビュー・サービスを追加する必要がある。

## Plan of Work

まず、チャット履歴を保存できるように`models.py`へチャットセッションとメッセージのモデルを追加する。メッセージはテキストと画像の両方を保持できるようにし、画像は`instance`配下に保存したパスとMIMEタイプを記録する。次に、チャットの生成処理を担う`services/chat_service.py`を新設し、テキスト応答（Geminiのテキストモデル呼び出し）と、既存の画像生成モードへの委譲をまとめる。マルチターン編集のため、直近のアシスタント画像を取得して再利用できるようにする。

続いて`views/chat.py`を追加し、`/chat`画面の表示、セッション一覧の取得、メッセージ送信APIを実装する。`app.py`でBlueprint登録も追加する。`templates/chat.html`と`static/js/chat.js`、`static/css/chat.css`を作成し、チャット欄のメニューから既存モードを選択できるUIと、テキスト/画像の送受信表示を実装する。既存の`templates/index.html`にはモード追加の説明や遷移ボタンを加えて、従来のモードが消えない形でチャットモードを追加する。

最後にテスト基盤として`pytest`を導入し、チャットセッション作成、履歴保存、モード委譲の最低限のテストを追加する。ローカルでテストコマンドを実行し、結果をExecPlanに記録する。

## Concrete Steps

1. リポジトリルートで`models.py`にチャット用のモデルを追加し、画像保存用のヘルパーを作る。
2. `services/chat_service.py`を追加し、テキスト応答と画像生成委譲を実装する。
3. `views/chat.py`とテンプレート、静的ファイルを追加し、UIから送信できるようにする。
4. `services/modes.py`と`templates/index.html`を更新してチャットモードを追加する。
5. `pytest`とテストコードを追加し、`pytest`コマンドを実行する。

## Validation and Acceptance

- `flask --app app.py run`で起動し、`/chat`を開くとチャット履歴一覧と入力欄が表示される。
- チャット欄のメニューで既存モードを選択し、画像生成を依頼すると返信が表示され、履歴に保存される。
- ログアウト後に再ログインして`/chat`を開いても過去のセッションが参照できる。
- `pytest`を実行すると追加したテストがパスし、変更前は失敗することを確認できる。

## Idempotence and Recovery

各ステップは追加・更新中心であり、同じ手順を繰り返しても安全に再実行できる。DBに新しいテーブルが追加されるため、テスト時は一時的なSQLiteを用意し、失敗時はDBファイルを削除して再作成できるようにする。

## Artifacts and Notes

完了時にチャット送信の画面例やテスト結果の短い抜粋を記録する。

## Interfaces and Dependencies

- `models.ChatSession`と`models.ChatMessage`を追加し、`ChatSession.messages`でメッセージ一覧を参照できるようにする。
- `services.chat_service`で`generate_text_reply`と`run_rough_mode`などのモード委譲関数を提供する。
- `views/chat.py`で`/chat`（GET）と`/chat/messages`（POST）を実装する。
- `static/js/chat.js`で送信処理とUI更新を実装する。

---

更新メモ: 2026-01-02に進捗と意思決定を更新し、実装完了の状態に合わせて内容を整理した。
