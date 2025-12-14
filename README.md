# rough_to_illustration

生成AIでラフ絵からイラストを作成するFlaskアプリケーション。ログイン後にラフ絵とプロンプトを送信し、Nano Banana(Gemini API)で生成したイラストをプレビュー・ダウンロードできます。アップロード時のプレビュー、文字数カウンタ、送信中のローディング表示などリッチなUIを備えています。

### 自分宛てのメモ
- プリセットの設定が200文字と300文字になっているので文字数の設定を緩和すること。modelsと、フロントエンドの設定を修正することで対応。
- フロントエンドに説明が追加されているが、不要な説明や間違っている説明が多いので(生成AIで作成したので)削除すること
- モード切替の実装(イメージ→イメージモードや、ほかのイラストを画風を元に生成するモード)

## 主な機能
- Flask + SQLAlchemy + Flask-Login によるログイン必須のWeb UI
- ラフ絵アップロードと色指定・ポーズ指示、任意のアスペクト比/解像度入力
- アップロードプレビュー、文字数カウンタ、送信中のローディング表示を備えたリッチUI
- Gemini API を呼び出して生成した画像のプレビューとダウンロード

## ディレクトリ構成
- `app.py`: Flaskアプリのエントリポイント。Blueprint登録のみを担当。
- `config.py` / `extensions.py` / `models.py`: 設定値、拡張機能のインスタンス、ユーザーモデル。
- `services/`: プロンプト生成や画像生成処理のヘルパー。
- `views/`: 認証とメイン画面のBlueprint。
- `templates/`: リッチなUIを定義したJinja2テンプレート。
- `old/streamlit/`: 旧Streamlitモックアップのコードを保管（現行アプリでは未使用）。

## 事前準備
1. 依存関係のインストール
   ```bash
   pip install -r requirements.txt
   ```
2. `.env` に API キーなどを設定
   ```bash
   GOOGLE_API_KEY="<GeminiのAPIキー>"
   SECRET_KEY="任意の秘密鍵"             # 省略時はデフォルト値を使用
   DATABASE_URL="sqlite:///app.db"      # 任意、未指定ならSQLiteファイルを利用
   ```
3. データベース初期化と初回ユーザー作成 (例)
   ```bash
   flask --app app.py shell
   >>> from app import db, User
   >>> db.create_all()
   >>> u = User(username="demo", email="demo@example.com")
   >>> u.set_password("password123")
   >>> db.session.add(u); db.session.commit(); exit()
   ```

## 起動方法
```bash
flask --app app.py run  # または python app.py
```
ブラウザで `http://localhost:5000/` にアクセスし、登録済みユーザーでログインしてください。ログインしないと生成フォームは利用できません。

### UIのヒント
- ラフ絵をアップロードするとプレビューが表示されます。不要になった場合は「画像をクリア」でリセットできます。
- テキスト入力には文字数カウンタがあり、推奨の文字数ガイドを併記しています。
- 送信中はボタンが自動で無効化され、スピナーが表示されます。

## 使い方
1. ログイン後、ラフ絵(PNG/JPEG)を選択します。
2. 着色イメージやポーズ指示を入力し、必要に応じてアスペクト比・解像度を指定します。
3. 「イラスト生成」を押すと Gemini API に送信され、生成画像がプレビューされます。
4. 「生成画像をダウンロード」ボタンからPNG形式で保存できます。

## 備考
- 画像やデータベースファイルは `.gitignore` に含めています。
- Gemini API の利用方法は [公式ドキュメント](https://ai.google.dev/gemini-api/docs/image-understanding?hl=ja) を参照してください。
