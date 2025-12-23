# インペイント/アウトペイント編集モードを追加しGUIを最適化する

このExecPlanはPLANS.md (./PLANS.md) の指針に従って維持されるべき生きた文書である。`Progress`、`Surprises & Discoveries`、`Decision Log`、`Outcomes & Retrospective` を常に最新に更新し、本計画だけで初学者でも作業を完遂できるようにする。

## Purpose / Big Picture

この変更により、ユーザーはラフ生成モードに加えて、アップロードした画像をGUI上のエディタでマスク指定し、インペイントまたはアウトペイントで編集できるようになる。すでにマスク済みの画像（透明アルファを含むPNG）をそのままアップロードして変換でき、追加の指示もプロンプトで与えられる。実装後は、ログインして「編集（インペイント/アウトペイント）」モードを選び、画像をアップロードしてエディタを開き、マスクを描いて送信すると、元の構図や色味を保ちながら指定領域だけが編集された結果がプレビューに表示されることを確認できる。

## Progress

- [x] (2025-12-23 15:30Z) 既存構成を調査し、編集モード追加のためのExecPlan草稿を作成した。
- [x] (2025-12-23 15:48Z) 編集モードのバックエンド（modes、prompt、生成サービス、Gemini edit_image 呼び出し）を実装した。
- [x] (2025-12-23 15:48Z) 編集モード用のフロントエンド（入力欄、エディタ、モード切替、JS連携）を実装した。
- [x] (2025-12-23 15:48Z) レイアウト/スタイルを最適化し、編集モードと既存モードのUI整合を取った。
- [ ] READMEと手動検証を実施してProgressに反映する（完了: README追記、`python -m compileall` 実行 / 残り: ブラウザでの手動検証）。

## Surprises & Discoveries

現時点で特記事項はない。実装中に予期せぬ挙動や制約が見つかった場合は、ここに観察と証拠を追記する。

## Decision Log

- Decision: 画像編集は `google.genai` の `client.models.edit_image` を使用し、RawReferenceImage と MaskReferenceImage の組み合わせでインペイント/アウトペイントを実行する。
  Rationale: 既存の `generate_content` ではマスク編集が扱いづらいため、公式SDKが提供する編集APIに統一した方が安定し、インペイント/アウトペイントの切替も明確になる。
  Date/Author: 2025-12-23 / Codex
- Decision: マスク指定は「エディタの描画マスク」「アップロード済みマスク画像」「ベース画像のアルファチャンネル」の順で優先し、マスクが無い場合はエラーとして扱う。
  Rationale: 要件にあるGUI編集とマスク済み画像アップロードの両方を満たしつつ、曖昧なセマンティックマスクに頼らずユーザーの意図を明確に反映するため。
  Date/Author: 2025-12-23 / Codex
- Decision: 編集モードでは出力サイズはマスク/ベース画像のキャンバスに従うため、解像度オプションは表示しないか無効化する。
  Rationale: EditImage API は解像度指定よりもキャンバスサイズに依存するため、UIで誤解を招かないようにする。
  Date/Author: 2025-12-23 / Codex
- Decision: エディタはキャンバスを拡張したベース画像とマスクをData URLで送信し、サーバ側はData URLを優先して処理する。
  Rationale: アウトペイント時のキャンバス拡張をフロントエンド側で確定し、ベースとマスクのサイズ不一致を避けるため。
  Date/Author: 2025-12-23 / Codex

## Outcomes & Retrospective

未記入。主要マイルストーン完了後に結果と学びを追記する。

## Context and Orientation

このリポジトリはFlaskアプリで、`app.py` がアプリ生成とBlueprint登録を行い、`views/main.py` が `/` へのGET/POSTと画像生成フローを担当する。モード定義は `services/modes.py`、プロンプト生成は `services/prompt_builder.py`、画像生成ロジックは `services/generation_service.py` と `illust.py` に分離されている。UIは `templates/index.html` と `static/js/index.js`、`static/css/index.css` で構成され、モード切替は `data-mode-visible` 属性とJSの `initModeSwitch` で制御される。

本計画で追加する「編集モード」は、元画像（ベース画像）とマスク画像を用意し、マスクの白（非ゼロ）領域だけを編集する。インペイントは既存キャンバス内の指定領域を置換し、アウトペイントはキャンバス外側を拡張して新規領域を生成する。マスクはエディタで塗るか、既存のマスク画像をアップロードする。ベース画像が透明アルファを含む場合は、そのアルファをマスクとして扱い、透明部分を編集対象にする。

## Plan of Work

まずバックエンドに編集モードのためのAPI呼び出しを追加する。`illust.py` に `edit_image` 用の関数を増やし、`google.genai.types.RawReferenceImage` と `MaskReferenceImage` を作成して `client.models.edit_image` に渡す。`services/generation_service.py` には、ベース画像、マスク画像、インペイント/アウトペイントの切替、追加指示文を受け取る新しい生成関数を追加し、画像サイズの整合チェックとマスク抽出（アルファ抽出を含む）を行う。`services/prompt_builder.py` には、元の構図・色・絵柄を維持することを明示した編集用プロンプトを組み込み、ユーザーの追加指示を安全に連結する。

次にフロントエンドを更新し、新しい編集モードを `services/modes.py` に追加して有効化する。`templates/index.html` には編集モード専用の入力セクションを追加し、ベース画像のアップロード、マスク画像の任意アップロード、インペイント/アウトペイント切替ボタン、追加指示テキストエリア、エディタを開くボタンを用意する。エディタはモーダル内のキャンバスで実装し、ブラシサイズ、消しゴム、リセット、アウトペイント時の拡張倍率設定を提供する。JSではアップロード時にエディタを開き、マスクを描いたらPNGのData URLとして hidden input に保存し、送信時にバックエンドへ渡す。

最後にCSSを調整してレイアウトを最適化する。編集モードは「入力」「エディタ」「結果」の導線が分かるようにカード内のセクション構造を整え、既存モードのフォームと干渉しないように `data-mode-visible` の表示制御を整理する。READMEには新モードの使い方（マスク描画、透明PNGの扱い、アウトペイントのキャンバス拡張）を追記し、手動検証の結果をProgressに反映する。

## Concrete Steps

作業ディレクトリはリポジトリ直下（`C:\Users\Hodaka\Downloads\div\rough_to_illustration`）とする。編集APIの動作を確認するため、最初に `illust.py` と `services/generation_service.py` を更新し、Flask経由で実行できる状態を作る。次に `services/modes.py`、`templates/index.html`、`static/js/index.js`、`static/css/index.css` を順に編集し、最後にREADMEを更新する。

編集後は以下のコマンドで動作確認を行う。

    python -m compileall

    flask --app app.py run

ブラウザで `http://localhost:5000/` を開き、ログインして編集モードを選択する。画像をアップロードしてエディタを開き、マスクを描いて送信するとプレビューが更新されることを確認する。

## Validation and Acceptance

ログイン後に「編集（インペイント/アウトペイント）」モードを選択し、ベース画像をアップロードするとエディタが開く。エディタでマスクを描き、インペイントを選択して追加指示（例: 「帽子を赤いリボンに変更」）を入力して送信すると、元の構図と色味を保ったままマスク領域だけが編集された画像がプレビューに表示される。

アウトペイントでは拡張倍率を設定してキャンバスを広げ、拡張領域にマスクが自動作成される。送信後、元画像が中央に残り、拡張領域が自然に補完された画像がプレビューに表示される。マスク済みPNG（透明アルファ）をアップロードした場合、透明部分が編集対象になり、マスク画像の追加アップロードなしでも編集できることを確認する。

## Idempotence and Recovery

エディタのマスク描画は何度でもやり直せるようにリセット機能を用意し、送信前に再調整できる。生成失敗時はフラッシュメッセージを表示し、同じ入力で再送信しても安全に再実行できる。セッションの生成結果は上書き保存されるため、過去の結果を明示的に削除する必要はない。

## Artifacts and Notes

編集モードの送信時に生成されたData URL（ベース画像/マスク）と、エディタの状態（ブラシサイズ、アウトペイント倍率）を確認できる短いログやUI表示を残すと、トラブルシュートに役立つ。必要であれば `current_app.logger.debug` を使ってマスクサイズとベースサイズを一時的に出力する。

## Interfaces and Dependencies

`illust.py` に編集用関数を追加する。関数は `edit_image_with_mask(prompt: str, base_image: PIL.Image, mask_image: PIL.Image, edit_mode: str) -> GeneratedImage` を想定し、`google.genai.types.Image` にPNG bytesとして渡す。`edit_mode` は `EditMode.EDIT_MODE_INPAINT_INSERTION` と `EditMode.EDIT_MODE_OUTPAINT` を切り替える。`RawReferenceImage` は `reference_id=1`、`MaskReferenceImage` は `reference_id=2` を固定し、`MaskReferenceConfig(mask_mode="MASK_MODE_USER_PROVIDED")` を使う。返却値は既存の `GeneratedImage` データクラスに揃える。

`services/generation_service.py` に `run_edit_generation` を追加する。引数は `base_file`、`mask_file`、`mask_data`、`base_data`、`edit_mode`、`edit_instruction` を受け取り、Data URLのデコード、マスク抽出（アルファチャンネル優先）、サイズ検証、プロンプト生成を行う。`services/prompt_builder.py` には `build_edit_prompt(user_instruction: str, edit_mode: str) -> str` を追加し、「指定領域以外は変更しない」「色や絵柄は維持する」を必須文として付与する。

`services/modes.py` には `MODE_INPAINT_OUTPAINT` を追加し、`ALL_MODES` に含めて有効化する。`views/main.py` のPOST処理は新モード時に `run_edit_generation` を呼ぶよう分岐を追加する。

`templates/index.html` には編集モード用の入力セクションとモーダルエディタを追加し、hidden inputで `edit_mask_data` と `edit_base_data` を送信できるようにする。`static/js/index.js` は新しいモードIDを受け取り、モード切替時の表示制御とエディタの起動、マスク描画、Data URL格納、アウトペイント拡張処理を実装する。`static/css/index.css` はエディタのキャンバス、ツールバー、プレビュー表示の見た目を整える。

## Plan Change Note

2025-12-23: 新規の編集モード追加依頼に対応するため、このExecPlanを初版として作成した。
2025-12-23: 実装内容と進捗を反映し、Progress/Decision Logを更新した。
