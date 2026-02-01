# Streamlit Community Cloud デプロイガイド

## 事前準備

以下のファイルが正しく設定されていることを確認してください：

- [x] `.streamlit/config.toml` - テーマ・サーバー設定
- [x] `requirements.txt` - 必要なライブラリ
- [x] `.gitignore` - 除外ファイル設定
- [x] `app.py` - Streamlit Secrets 対応済み

---

## デプロイ手順（3ステップ）

### Step 1: GitHub にリポジトリを作成＆Push

```bash
# 1. プロジェクトフォルダに移動
cd /Users/keita/shopee-taiwan-research

# 2. Git リポジトリを初期化（まだの場合）
git init

# 3. すべてのファイルをステージング
git add .

# 4. 初回コミット
git commit -m "Initial commit: Shopee Taiwan Research Dashboard"

# 5. GitHub で新しいリポジトリを作成後、リモートを追加
git remote add origin https://github.com/あなたのユーザー名/shopee-taiwan-research.git

# 6. Push
git branch -M main
git push -u origin main
```

### Step 2: Streamlit Community Cloud で連携

1. **[share.streamlit.io](https://share.streamlit.io/)** にアクセス
2. **「Sign in with GitHub」** でログイン
3. **「New app」** をクリック
4. 以下を設定：
   - **Repository**: `あなたのユーザー名/shopee-taiwan-research`
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. **「Deploy!」** をクリック

### Step 3: Secrets の設定（AI機能を使う場合）

1. デプロイ後、アプリの **「Settings」** を開く
2. 左メニューの **「Secrets」** をクリック
3. 以下を入力して **「Save」**：

```toml
ANTHROPIC_API_KEY = "sk-ant-xxxxx-your-actual-api-key"
```

> ⚠️ **注意**: API キーは絶対にコードに直接書かないでください！

---

## デプロイ後の確認

- アプリURL: `https://あなたのアプリ名.streamlit.app`
- 「データを更新」ボタンでサンプルデータを取得
- 「AI出品支援」タブで説明文生成を確認

---

## トラブルシューティング

### ❌ デプロイに失敗する場合

1. `requirements.txt` の記述を確認
2. Python バージョンの互換性を確認（3.8以上推奨）

### ❌ AI説明文が生成されない場合

1. Secrets に `ANTHROPIC_API_KEY` が正しく設定されているか確認
2. API キーが有効か確認

### ❌ データが表示されない場合

1. 「サンプルデータ（デモ用）」モードでデータを更新
2. API モードは台湾IPが必要なため、Cloud環境では動作しません

---

## ローカル開発時のSecrets設定

```bash
# テンプレートをコピー
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# エディタで開いてAPIキーを設定
# secrets.toml は .gitignore で除外されています
```

---

## ファイル構成

```
shopee-taiwan-research/
├── app.py                 # メインアプリ
├── scraper.py             # スクレイパー
├── config.py              # 設定
├── sample_data.py         # サンプルデータ
├── main.py                # CLI版
├── requirements.txt       # 依存ライブラリ
├── .gitignore             # Git除外設定
├── .streamlit/
│   ├── config.toml        # Streamlit設定
│   └── secrets.toml.example  # Secretsテンプレート
├── run_web.sh             # ローカル起動スクリプト
└── DEPLOY.md              # このファイル
```
