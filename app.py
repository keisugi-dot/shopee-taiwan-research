"""Shopee台湾リサーチ ダッシュボード（AI出品支援機能付き）"""

import os
from datetime import datetime
import pandas as pd
import streamlit as st

# スクレイパーをインポート
from scraper import ShopeeScraper
from config import SEARCH_KEYWORDS

# Anthropic APIを試みる
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# ページ設定
st.set_page_config(
    page_title="Shopee台湾リサーチ",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #EE4D2D;
        text-align: center;
        margin-bottom: 1rem;
    }
    .ai-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
    }
    .price-card {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .description-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 1.5rem;
        font-size: 1.1rem;
        line-height: 1.8;
    }
    .hashtag-container {
        background-color: #e3f2fd;
        border-radius: 10px;
        padding: 1rem;
    }
    .hashtag {
        display: inline-block;
        background-color: #2196f3;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        margin: 0.2rem;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# データファイルパス
DATA_FILE = "research_results.csv"


@st.cache_data
def load_data():
    """CSVデータを読み込む"""
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
        return df
    return pd.DataFrame()


def run_scraper(use_sample: bool = False):
    """スクレイパーを実行してデータを更新"""
    scraper = ShopeeScraper()
    scraper.run(keywords=SEARCH_KEYWORDS, use_sample=use_sample)


def recalculate_profit(df, exchange_rate, fee_rate, fixed_cost, cost_rate):
    """利益を再計算"""
    df = df.copy()
    df["price_jpy_sim"] = df["price"] * exchange_rate
    df["revenue_after_fee"] = df["price_jpy_sim"] * (1 - fee_rate)
    df["estimated_cost_sim"] = df["price_jpy_sim"] * cost_rate
    df["estimated_profit_sim"] = df["revenue_after_fee"] - df["estimated_cost_sim"] - fixed_cost
    return df


def calculate_premium_price(current_price_twd, df, keyword, premium_rate=0.08):
    """プレミアム価格を計算（競合最安値 + 5-10%）"""
    # 同ジャンルの最安値を取得
    same_genre = df[df["keyword"] == keyword]
    if not same_genre.empty:
        min_price = same_genre["price"].min()
        avg_price = same_genre["price"].mean()
    else:
        min_price = current_price_twd
        avg_price = current_price_twd

    # プレミアム価格 = 最安値 × (1 + プレミアム率)
    premium_price_twd = min_price * (1 + premium_rate)

    return {
        "min_price_twd": min_price,
        "avg_price_twd": avg_price,
        "premium_price_twd": premium_price_twd,
    }


def is_food_product(name, keyword):
    """食品かどうかを判定"""
    food_keywords = ["零食", "泡麵", "調味料", "咖啡", "食品", "餅乾", "糖果",
                     "お菓子", "ラーメン", "カップ麺", "コーヒー", "食べ物"]
    name_lower = name.lower()
    return any(kw in keyword or kw in name_lower for kw in food_keywords)


def get_anthropic_api_key():
    """Anthropic API キーを取得（Streamlit Secrets または環境変数から）"""
    # 1. Streamlit Secrets から取得を試みる（Cloud デプロイ用）
    try:
        if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
            return st.secrets['ANTHROPIC_API_KEY']
    except Exception:
        pass

    # 2. 環境変数から取得（ローカル開発用）
    return os.environ.get("ANTHROPIC_API_KEY")


def generate_product_description_ai(product, exchange_rate):
    """AIを使って商品説明文を生成"""
    api_key = get_anthropic_api_key()

    if not ANTHROPIC_AVAILABLE or not api_key:
        return generate_product_description_template(product, exchange_rate)

    try:
        client = anthropic.Anthropic(api_key=api_key)

        is_food = is_food_product(product["name"], product["keyword"])

        prompt = f"""
あなたは台湾Shopeeで商品を販売する日本の出品者です。
以下の商品について、台湾の消費者向けに繁体字中国語で魅力的な商品説明文を作成してください。

商品名: {product["name"]}
カテゴリ: {product["keyword"]}
価格: NT${product["price"]:,.0f}

以下の構成で作成してください：

【商品特點】
商品の魅力・メリットを3-4点。絵文字を多用して親しみやすく。

【產品規格】
サイズ・容量などのスペック（推測で構いません）

【為什麼選擇我們】
以下の差別化ポイントを必ず含めてください：
- 日本正規店購入（日本通路代購）
{"- 最新賞味期限（最新效期）" if is_food else ""}
- 空輸で直送（空運直送）
- 丁寧な梱包（包裝嚴實）

台湾のShopeeで好まれる絵文字を多用し、親しみやすいトーンで書いてください。
"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text

    except Exception as e:
        st.warning(f"AI生成エラー: {e}")
        return generate_product_description_template(product, exchange_rate)


def generate_product_description_template(product, exchange_rate):
    """テンプレートベースで商品説明文を生成"""
    name = product["name"]
    keyword = product["keyword"]
    price = product["price"]

    is_food = is_food_product(name, keyword)

    # カテゴリに応じた特徴
    category_features = {
        "日本 零食": ["日本超人氣零食", "獨特風味", "精緻包裝適合送禮"],
        "日本 泡麵": ["日本國民美食", "濃郁湯頭", "道地日式風味"],
        "日本 調味料": ["專業主廚愛用", "提升料理層次", "天然食材製成"],
        "日本 咖啡": ["嚴選咖啡豆", "香醇順口", "日本職人烘焙"],
        "日本 生活用品": ["日本製造品質保證", "設計精美實用", "耐用度高"],
        "日本 美容": ["日本熱銷商品", "溫和配方", "適合亞洲肌膚"],
    }

    features = category_features.get(keyword, ["日本品質", "人氣商品", "值得信賴"])

    # 食品用の賞味期限文言
    food_notice = """
🗓️ 最新效期保證
   我們只販售最新批次商品！
""" if is_food else ""

    description = f"""
✨【商品特點】✨

🎌 {features[0]}
💝 {features[1]}
⭐ {features[2]}
🇯🇵 100%日本原裝進口

{food_notice}
📦【產品規格】

📍 商品名稱：{name[:50]}
💰 售價：NT${price:,.0f}
�icing 產地：日本
📐 規格：標準規格（詳見商品圖片）

🌟【為什麼選擇我們】🌟

✅ 日本通路代購 - 日本正規店舖購入，品質有保障！
✅ 空運直送 - 從日本空運直達，新鮮送到您手中！
✅ 包裝嚴實 - 層層保護，確保商品完整無損！
✅ 快速出貨 - 付款後3-5天內寄出！
{"✅ 最新效期 - 保證最新批次，請安心購買！" if is_food else "✅ 正品保證 - 假一賠十，請安心購買！"}

💬 有任何問題歡迎聊聊詢問喔～
❤️ 感謝您的支持！祝購物愉快！
"""
    return description


def generate_hashtags(product):
    """推奨ハッシュタグを生成"""
    keyword = product["keyword"]
    name = product["name"]

    # 基本ハッシュタグ
    base_tags = [
        "#日本代購",
        "#日本直送",
        "#空運直送",
        "#日本正品",
        "#日本購入",
    ]

    # カテゴリ別ハッシュタグ
    category_tags = {
        "日本 零食": ["#日本零食", "#日本餅乾", "#日本糖果", "#進口零食", "#日本伴手禮"],
        "日本 泡麵": ["#日本泡麵", "#日本拉麵", "#即食麵", "#日本美食", "#宵夜首選"],
        "日本 調味料": ["#日本調味料", "#日本醬油", "#料理必備", "#日本廚房", "#美味秘訣"],
        "日本 咖啡": ["#日本咖啡", "#即溶咖啡", "#咖啡控", "#早安咖啡", "#辦公室必備"],
        "日本 生活用品": ["#日本生活", "#日本雜貨", "#居家用品", "#質感生活", "#日系風格"],
        "日本 美容": ["#日本美妝", "#日本保養", "#美容聖品", "#日本藥妝", "#護膚推薦"],
    }

    tags = base_tags + category_tags.get(keyword, ["#日本商品", "#優質商品"])

    return tags[:10]


def calculate_final_profit(premium_price_twd, exchange_rate, fee_rate, fixed_cost, cost_rate):
    """推奨価格での最終利益を計算"""
    price_jpy = premium_price_twd * exchange_rate
    revenue_after_fee = price_jpy * (1 - fee_rate)
    estimated_cost = price_jpy * cost_rate
    profit = revenue_after_fee - estimated_cost - fixed_cost
    return {
        "price_jpy": price_jpy,
        "revenue_after_fee": revenue_after_fee,
        "estimated_cost": estimated_cost,
        "profit": profit,
    }


def render_ai_analysis_section(product, df, exchange_rate, fee_rate, fixed_cost, cost_rate):
    """AI分析セクションをレンダリング"""

    st.markdown("---")
    st.subheader(f"🤖 AI出品支援: {product['name'][:40]}...")

    # タブで機能を分ける
    ai_tab1, ai_tab2, ai_tab3, ai_tab4 = st.tabs([
        "💰 価格分析",
        "📝 商品説明文",
        "🏷️ ハッシュタグ",
        "📊 利益シミュレーション"
    ])

    # === 価格分析タブ ===
    with ai_tab1:
        st.markdown("### 💰 価格分析・推奨価格")

        # プレミアム率選択
        premium_rate = st.slider(
            "プレミアム率（安心料込み）",
            min_value=0.05,
            max_value=0.15,
            value=0.08,
            step=0.01,
            format="%.0f%%",
            key="premium_rate"
        )

        price_info = calculate_premium_price(
            product["price"], df, product["keyword"], premium_rate
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "台湾最安値",
                f"NT${price_info['min_price_twd']:,.0f}",
                help="同ジャンルの最安値"
            )

        with col2:
            st.metric(
                "競合平均価格",
                f"NT${price_info['avg_price_twd']:,.0f}",
                help="同ジャンルの平均価格"
            )

        with col3:
            st.metric(
                "推奨販売価格",
                f"NT${price_info['premium_price_twd']:,.0f}",
                delta=f"+{premium_rate*100:.0f}%",
                help="最安値にプレミアムを加算"
            )

        # 価格の根拠説明
        st.info(f"""
        **価格設定の根拠：**
        - 日本正規店購入の信頼性
        - 空輸直送による鮮度・品質保証
        - 丁寧な梱包・迅速な対応
        - これらの付加価値で +{premium_rate*100:.0f}% のプレミアム価格が妥当です
        """)

        # ターゲット層分析
        st.markdown("### 🎯 ターゲット層分析")

        if "零食" in product["keyword"] or "泡麵" in product["keyword"]:
            target = "20-35歳の日本文化好き、SNSで話題の商品を求める層"
            buying_motivation = "Instagram/小紅書で見た商品を試したい、日本旅行の思い出"
        elif "調味料" in product["keyword"]:
            target = "30-50歳の料理好き主婦/主夫、本格的な日本料理を作りたい層"
            buying_motivation = "家庭で本格的な日本の味を再現したい"
        elif "咖啡" in product["keyword"]:
            target = "25-45歳のオフィスワーカー、コーヒー愛好家"
            buying_motivation = "日本のカフェ文化への憧れ、品質の良いコーヒーを手軽に"
        elif "美容" in product["keyword"]:
            target = "20-40歳の美容意識の高い女性"
            buying_motivation = "日本コスメへの信頼、SNSでの口コミ"
        else:
            target = "25-45歳の日本製品を好む品質重視層"
            buying_motivation = "日本製品の品質への信頼"

        st.success(f"""
        **メインターゲット:** {target}

        **購買動機:** {buying_motivation}
        """)

    # === 商品説明文タブ ===
    with ai_tab2:
        st.markdown("### 📝 台湾向け商品説明文（繁体字中国語）")

        if st.button("🤖 説明文を生成", type="primary", key="generate_desc"):
            with st.spinner("説明文を生成中..."):
                description = generate_product_description_ai(product, exchange_rate)
                st.session_state["generated_description"] = description

        if "generated_description" in st.session_state:
            st.markdown('<div class="description-box">', unsafe_allow_html=True)
            st.text_area(
                "生成された説明文（コピーしてご利用ください）",
                st.session_state["generated_description"],
                height=400,
                key="desc_textarea"
            )
            st.markdown('</div>', unsafe_allow_html=True)

            # コピーボタン
            st.download_button(
                label="📋 テキストファイルとしてダウンロード",
                data=st.session_state["generated_description"],
                file_name=f"product_description_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )

    # === ハッシュタグタブ ===
    with ai_tab3:
        st.markdown("### 🏷️ 推奨ハッシュタグ")

        hashtags = generate_hashtags(product)

        st.markdown('<div class="hashtag-container">', unsafe_allow_html=True)
        hashtag_html = " ".join([f'<span class="hashtag">{tag}</span>' for tag in hashtags])
        st.markdown(hashtag_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # コピー用テキスト
        hashtag_text = " ".join(hashtags)
        st.text_area(
            "コピー用（全ハッシュタグ）",
            hashtag_text,
            height=80,
            key="hashtag_textarea"
        )

        st.info("""
        **ハッシュタグ使用のコツ：**
        - 商品タイトルと説明文の両方に入れる
        - 人気タグ（#日本代購）は必ず入れる
        - カテゴリ特化タグで絞り込みを狙う
        """)

    # === 利益シミュレーションタブ ===
    with ai_tab4:
        st.markdown("### 📊 推奨価格での利益シミュレーション")

        price_info = calculate_premium_price(
            product["price"], df, product["keyword"], 0.08
        )

        profit_info = calculate_final_profit(
            price_info["premium_price_twd"],
            exchange_rate,
            fee_rate,
            fixed_cost,
            cost_rate
        )

        # 現在価格 vs 推奨価格の比較
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 現在の価格で販売した場合")
            current_profit = calculate_final_profit(
                product["price"], exchange_rate, fee_rate, fixed_cost, cost_rate
            )
            st.metric("販売価格 (TWD)", f"NT${product['price']:,.0f}")
            st.metric("販売価格 (JPY)", f"¥{current_profit['price_jpy']:,.0f}")
            st.metric(
                "手残り利益",
                f"¥{current_profit['profit']:,.0f}",
                delta=None
            )

        with col2:
            st.markdown("#### 推奨価格で販売した場合")
            st.metric("販売価格 (TWD)", f"NT${price_info['premium_price_twd']:,.0f}")
            st.metric("販売価格 (JPY)", f"¥{profit_info['price_jpy']:,.0f}")
            profit_diff = profit_info['profit'] - current_profit['profit']
            st.metric(
                "手残り利益",
                f"¥{profit_info['profit']:,.0f}",
                delta=f"+¥{profit_diff:,.0f}"
            )

        # 詳細内訳
        st.markdown("#### 💴 利益計算の内訳（推奨価格ベース）")

        breakdown_df = pd.DataFrame({
            "項目": [
                "販売価格（円換算）",
                "手数料控除後",
                "推定原価",
                "固定コスト",
                "手残り利益"
            ],
            "金額": [
                f"¥{profit_info['price_jpy']:,.0f}",
                f"¥{profit_info['revenue_after_fee']:,.0f}",
                f"-¥{profit_info['estimated_cost']:,.0f}",
                f"-¥{fixed_cost:,.0f}",
                f"¥{profit_info['profit']:,.0f}"
            ]
        })

        st.table(breakdown_df)


def main():
    # ヘッダー
    st.markdown('<p class="main-header">🛒 Shopee台湾 リサーチダッシュボード</p>', unsafe_allow_html=True)

    # データ読み込み
    df = load_data()

    if df.empty:
        st.warning("データがありません。サイドバーの「データを更新」ボタンをクリックしてデータを取得してください。")

        st.sidebar.header("🔄 データ更新")
        data_mode_empty = st.sidebar.radio(
            "データ取得モード",
            options=["サンプルデータ（デモ用）", "API（ライブデータ）"],
            index=0,
            help="APIは台湾IPが必要な場合があります",
            key="data_mode_empty"
        )
        use_sample_empty = data_mode_empty == "サンプルデータ（デモ用）"

        if st.sidebar.button("🔄 データを取得開始", type="primary", use_container_width=True):
            with st.spinner("データを取得中..."):
                try:
                    run_scraper(use_sample=use_sample_empty)
                    load_data.clear()
                    st.sidebar.success("✅ データを取得しました！")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"❌ エラー: {e}")
        st.stop()

    # ===================
    # サイドバー: データ更新
    # ===================
    st.sidebar.header("🔄 データ更新")

    if os.path.exists(DATA_FILE):
        mod_time = os.path.getmtime(DATA_FILE)
        last_update = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
        st.sidebar.caption(f"最終更新: {last_update}")

    data_mode = st.sidebar.radio(
        "データ取得モード",
        options=["サンプルデータ（デモ用）", "API（ライブデータ）"],
        index=0,
        help="APIは台湾IPが必要な場合があります"
    )
    use_sample = data_mode == "サンプルデータ（デモ用）"

    if st.sidebar.button("🔄 データを更新", type="primary", use_container_width=True):
        with st.spinner("データを取得中..."):
            try:
                run_scraper(use_sample=use_sample)
                load_data.clear()
                st.sidebar.success("✅ データを更新しました！")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ エラー: {e}")

    st.sidebar.markdown("---")

    # ===================
    # サイドバー: 利益シミュレーター
    # ===================
    st.sidebar.header("🔧 設定")
    st.sidebar.subheader("💰 利益シミュレーター")

    exchange_rate = st.sidebar.slider(
        "為替レート (TWD→JPY)", min_value=3.0, max_value=7.0, value=4.8, step=0.1
    )
    fee_rate = st.sidebar.slider(
        "販売手数料率", min_value=0.0, max_value=0.30, value=0.10, step=0.01, format="%.0f%%"
    )
    fixed_cost = st.sidebar.slider(
        "固定コスト (円)", min_value=0, max_value=1000, value=200, step=50
    )
    cost_rate = st.sidebar.slider(
        "原価率", min_value=0.0, max_value=1.0, value=0.50, step=0.05, format="%.0f%%"
    )

    st.sidebar.markdown("---")

    # ===================
    # サイドバー: データフィルタ
    # ===================
    st.sidebar.subheader("🔍 データフィルタ")

    keywords = df["keyword"].unique().tolist()
    selected_keywords = st.sidebar.multiselect("ジャンル選択", options=keywords, default=keywords)
    min_profit = st.sidebar.number_input("最小利益 (円)", min_value=-1000, max_value=5000, value=0, step=100)
    min_sales = st.sidebar.number_input("最小販売数", min_value=0, max_value=10000, value=0, step=100)
    min_rating = st.sidebar.slider("最小評価", min_value=0.0, max_value=5.0, value=0.0, step=0.5)

    # データ処理
    df = recalculate_profit(df, exchange_rate, fee_rate / 100, fixed_cost, cost_rate / 100)

    filtered_df = df[
        (df["keyword"].isin(selected_keywords)) &
        (df["estimated_profit_sim"] >= min_profit) &
        (df["sales"] >= min_sales) &
        (df["shop_rating"] >= min_rating)
    ]

    # ===================
    # メトリクス表示
    # ===================
    st.subheader("📊 サマリー")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("総商品数", f"{len(filtered_df):,}")
    with col2:
        avg_profit = filtered_df["estimated_profit_sim"].mean() if not filtered_df.empty else 0
        st.metric("平均利益", f"¥{avg_profit:,.0f}")
    with col3:
        total_potential = (filtered_df["estimated_profit_sim"] * filtered_df["sales"]).sum() if not filtered_df.empty else 0
        st.metric("市場潜在利益", f"¥{total_potential:,.0f}")
    with col4:
        treasure_count = len(filtered_df[
            (filtered_df["estimated_profit_sim"] >= 500) &
            (filtered_df["sales"] >= 100) &
            (filtered_df["shop_rating"] >= 4.5)
        ])
        st.metric("お宝商品数", f"{treasure_count}")
    with col5:
        avg_sales = filtered_df["sales"].mean() if not filtered_df.empty else 0
        st.metric("平均販売数", f"{avg_sales:,.0f}")

    # ===================
    # メインコンテンツ（タブ形式）
    # ===================
    main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
        "📈 分析グラフ",
        "🏆 商品ランキング",
        "💎 お宝商品",
        "🤖 AI出品支援"
    ])

    # === 分析グラフタブ ===
    with main_tab1:
        st.subheader("📈 分析グラフ")
        chart_tab1, chart_tab2, chart_tab3 = st.tabs(["ジャンル別売上", "ジャンル別利益", "価格×売上分布"])

        with chart_tab1:
            if not filtered_df.empty:
                sales_by_keyword = filtered_df.groupby("keyword")["sales"].sum().sort_values(ascending=True)
                st.bar_chart(sales_by_keyword)

        with chart_tab2:
            if not filtered_df.empty:
                profit_by_keyword = filtered_df.groupby("keyword")["estimated_profit_sim"].mean().sort_values(ascending=True)
                st.bar_chart(profit_by_keyword)

        with chart_tab3:
            if not filtered_df.empty:
                chart_data = filtered_df[["price", "sales", "keyword"]].copy()
                st.scatter_chart(chart_data, x="price", y="sales", color="keyword")

    # === 商品ランキングタブ ===
    with main_tab2:
        st.subheader("🏆 商品ランキング")

        col_sort1, col_sort2 = st.columns(2)
        with col_sort1:
            sort_by = st.selectbox(
                "並び替え項目",
                options=[
                    ("利益（高い順）", "estimated_profit_sim", False),
                    ("販売数（多い順）", "sales", False),
                    ("価格（高い順）", "price", False),
                    ("評価（高い順）", "shop_rating", False),
                ],
                format_func=lambda x: x[0]
            )
        with col_sort2:
            top_n = st.selectbox("表示件数", options=[10, 15, 20, 30, 50], index=1)

        if not filtered_df.empty:
            sorted_df = filtered_df.sort_values(by=sort_by[1], ascending=sort_by[2]).head(top_n)

            display_df = sorted_df[[
                "keyword", "name", "price", "sales", "shop_rating",
                "price_jpy_sim", "estimated_profit_sim"
            ]].copy()
            display_df.columns = ["ジャンル", "商品名", "価格(TWD)", "販売数", "評価", "価格(円)", "利益(円)"]

            display_df["価格(TWD)"] = display_df["価格(TWD)"].apply(lambda x: f"NT${x:,.0f}")
            display_df["価格(円)"] = display_df["価格(円)"].apply(lambda x: f"¥{x:,.0f}")
            display_df["利益(円)"] = display_df["利益(円)"].apply(lambda x: f"¥{x:,.0f}")
            display_df["販売数"] = display_df["販売数"].apply(lambda x: f"{x:,}")

            st.dataframe(display_df, use_container_width=True, hide_index=True)

    # === お宝商品タブ ===
    with main_tab3:
        st.subheader("💎 お宝商品（高利益・高売上・高評価）")

        treasure_df = filtered_df[
            (filtered_df["estimated_profit_sim"] >= 500) &
            (filtered_df["sales"] >= 100) &
            (filtered_df["shop_rating"] >= 4.5)
        ].sort_values("estimated_profit_sim", ascending=False)

        if not treasure_df.empty:
            st.success(f"🎉 {len(treasure_df)}件のお宝商品が見つかりました！")

            treasure_display = treasure_df[[
                "keyword", "name", "price", "sales", "shop_rating", "estimated_profit_sim"
            ]].copy()
            treasure_display.columns = ["ジャンル", "商品名", "価格(TWD)", "販売数", "評価", "想定利益(円)"]

            treasure_display["価格(TWD)"] = treasure_display["価格(TWD)"].apply(lambda x: f"NT${x:,.0f}")
            treasure_display["想定利益(円)"] = treasure_display["想定利益(円)"].apply(lambda x: f"¥{x:,.0f}")
            treasure_display["販売数"] = treasure_display["販売数"].apply(lambda x: f"{x:,}")

            st.dataframe(treasure_display, use_container_width=True, hide_index=True)
        else:
            st.info("条件に合うお宝商品はありません。")

    # === AI出品支援タブ ===
    with main_tab4:
        st.subheader("🤖 AI出品支援")
        st.info("商品を選択して、AIによる価格分析・説明文生成・ハッシュタグ提案を受けられます。")

        if not filtered_df.empty:
            # 商品選択
            product_options = filtered_df.apply(
                lambda x: f"{x['name'][:50]}... (NT${x['price']:,.0f})",
                axis=1
            ).tolist()

            selected_idx = st.selectbox(
                "分析する商品を選択",
                options=range(len(product_options)),
                format_func=lambda x: product_options[x],
                key="product_selector"
            )

            selected_product = filtered_df.iloc[selected_idx].to_dict()

            # AI分析セクションを表示
            render_ai_analysis_section(
                selected_product, df, exchange_rate,
                fee_rate / 100, fixed_cost, cost_rate / 100
            )
        else:
            st.warning("分析可能な商品がありません。")

    # ===================
    # データエクスポート
    # ===================
    st.markdown("---")
    st.subheader("📥 データエクスポート")

    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        if not filtered_df.empty:
            csv = filtered_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📄 フィルタ済みデータをCSVでダウンロード",
                data=csv,
                file_name="filtered_products.csv",
                mime="text/csv",
            )

    with col_exp2:
        if not treasure_df.empty:
            csv_treasure = treasure_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="💎 お宝商品をCSVでダウンロード",
                data=csv_treasure,
                file_name="treasure_products.csv",
                mime="text/csv",
            )

    # フッター
    st.markdown("---")
    if os.path.exists(DATA_FILE):
        mod_time = os.path.getmtime(DATA_FILE)
        last_update = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
        footer_text = f"Shopee台湾リサーチツール | 最終更新: {last_update}"
    else:
        footer_text = "Shopee台湾リサーチツール"

    st.markdown(f'<div style="text-align: center; color: #888;">{footer_text}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
