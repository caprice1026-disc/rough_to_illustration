# rough_to_illustration

生成AIでラフ絵からイラストを作成するFlaskアプリケーション。ログイン後にラフ絵とプロンプトを送信し、Nano Banana(Gemini API)で生成したイラストをプレビュー・ダウンロードできます。

## 主な機能
- Flask + SQLAlchemy + Flask-Login によるログイン必須のWeb UI
- ラフ絵アップロードと色指定・ポーズ指示、任意のアスペクト比/解像度入力
- Gemini API を呼び出して生成した画像のプレビューとダウンロード

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

## 使い方
1. ログイン後、ラフ絵(PNG/JPEG)を選択します。
2. 着色イメージやポーズ指示を入力し、必要に応じてアスペクト比・解像度を指定します。
3. 「イラスト生成」を押すと Gemini API に送信され、生成画像がプレビューされます。
4. 「生成画像をダウンロード」ボタンからPNG形式で保存できます。

## 備考
- 画像やデータベースファイルは `.gitignore` に含めています。
- Gemini API の利用方法は [公式ドキュメント](https://ai.google.dev/gemini-api/docs/image-understanding?hl=ja) を参照してください。
