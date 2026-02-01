"""Shopee台湾リサーチ ダッシュボード"""

import os
from datetime import datetime
import pandas as pd
import streamlit as st

from scraper import ShopeeScraper
from config import SEARCH_KEYWORDS

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# ページ設定
st.set_page_config(
    page_title="Shopee Taiwan Research",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# モダンなCSS
st.markdown("""
<style>
    /* フォント */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* メインヘッダー */
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }

    .sub-header {
        font-size: 0.95rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }

    /* カード */
    .metric-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.5rem;
        transition: all 0.2s ease;
    }

    .metric-card:hover {
        border-color: #d1d5db;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    .metric-label {
        font-size: 0.75rem;
        font-weight: 500;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }

    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #1a1a2e;
    }

    /* セクション */
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a2e;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #f3f4f6;
    }

    /* AI分析カード */
    .ai-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #2d2d44 100%);
        border-radius: 16px;
        padding: 2rem;
        color: white;
        margin: 1rem 0;
    }

    .ai-card h3 {
        color: white;
        font-weight: 600;
        margin-bottom: 1rem;
    }

    /* 価格表示 */
    .price-highlight {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        margin: 0.5rem 0;
    }

    .price-highlight .label {
        font-size: 0.75rem;
        color: #166534;
        font-weight: 500;
    }

    .price-highlight .value {
        font-size: 1.5rem;
        color: #166534;
        font-weight: 700;
    }

    /* テキストエリア */
    .description-area {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.5rem;
        font-size: 0.9rem;
        line-height: 1.8;
    }

    /* タグ */
    .tag {
        display: inline-block;
        background: #1a1a2e;
        color: white;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        margin: 0.2rem;
        font-size: 0.8rem;
        font-weight: 500;
    }

    /* サイドバー */
    [data-testid="stSidebar"] {
        background: #fafafa;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
    }

    /* ボタン */
    .stButton > button {
        background: #1a1a2e;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        background: #2d2d44;
        box-shadow: 0 4px 12px rgba(26,26,46,0.3);
    }

    /* データフレーム */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }

    /* タブ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #f3f4f6;
        border-radius: 10px;
        padding: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* メトリクス */
    [data-testid="metric-container"] {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1rem;
    }

    /* 非表示 */
    #MainMenu, footer, header {
        visibility: hidden;
    }

    .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "research_results.csv"


@st.cache_data
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    return pd.DataFrame()


def run_scraper(use_sample: bool = False):
    scraper = ShopeeScraper()
    scraper.run(keywords=SEARCH_KEYWORDS, use_sample=use_sample)


def recalculate_profit(df, exchange_rate, fee_rate, fixed_cost, cost_rate):
    df = df.copy()
    df["price_jpy"] = df["price"] * exchange_rate
    df["revenue"] = df["price_jpy"] * (1 - fee_rate)
    df["cost"] = df["price_jpy"] * cost_rate
    df["profit"] = df["revenue"] - df["cost"] - fixed_cost
    return df


def get_api_key():
    try:
        if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
            return st.secrets['ANTHROPIC_API_KEY']
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


def calculate_premium_price(price, df, keyword, rate=0.08):
    same = df[df["keyword"] == keyword]
    min_p = same["price"].min() if not same.empty else price
    avg_p = same["price"].mean() if not same.empty else price
    return {"min": min_p, "avg": avg_p, "premium": min_p * (1 + rate)}


def is_food(name, keyword):
    foods = ["零食", "泡麵", "調味料", "咖啡", "食品", "餅乾", "糖果"]
    return any(f in keyword or f in name for f in foods)


def generate_description(product):
    name, keyword, price = product["name"], product["keyword"], product["price"]
    is_f = is_food(name, keyword)

    features = {
        "日本 零食": ("日本人氣零食", "獨特風味", "精緻包裝"),
        "日本 泡麵": ("日本國民美食", "濃郁湯頭", "道地風味"),
        "日本 調味料": ("專業主廚愛用", "提升料理層次", "天然食材"),
        "日本 咖啡": ("嚴選咖啡豆", "香醇順口", "職人烘焙"),
        "日本 生活用品": ("日本製造", "設計精美", "品質保證"),
        "日本 美容": ("日本熱銷", "溫和配方", "適合亞洲肌膚"),
    }.get(keyword, ("日本品質", "人氣商品", "值得信賴"))

    return f"""【商品特點】

・{features[0]}
・{features[1]}
・{features[2]}
・100% 日本原裝進口

【產品規格】

商品名稱：{name[:50]}
售價：NT${price:,.0f}
產地：日本

【為什麼選擇我們】

✓ 日本通路代購 — 正規店舖購入
✓ 空運直送 — 新鮮直達
✓ 包裝嚴實 — 完整保護
✓ 快速出貨 — 3-5天內寄出
{"✓ 最新效期 — 保證新鮮" if is_f else "✓ 正品保證"}

有問題歡迎詢問！"""


def generate_hashtags(keyword):
    base = ["#日本代購", "#日本直送", "#空運直送", "#日本正品"]
    category = {
        "日本 零食": ["#日本零食", "#進口零食", "#日本伴手禮"],
        "日本 泡麵": ["#日本泡麵", "#日本拉麵", "#日本美食"],
        "日本 調味料": ["#日本調味料", "#料理必備", "#日本廚房"],
        "日本 咖啡": ["#日本咖啡", "#咖啡控", "#辦公室必備"],
        "日本 生活用品": ["#日本生活", "#日本雜貨", "#質感生活"],
        "日本 美容": ["#日本美妝", "#日本保養", "#日本藥妝"],
    }.get(keyword, ["#日本商品"])
    return base + category


def main():
    # ヘッダー
    st.markdown('<p class="main-header">Shopee Taiwan Research</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">台湾市場リサーチ & AI出品支援ツール</p>', unsafe_allow_html=True)

    df = load_data()

    if df.empty:
        st.info("データがありません。サイドバーからデータを取得してください。")
        with st.sidebar:
            st.markdown("### Data")
            mode = st.radio("Mode", ["Sample", "API"], horizontal=True)
            if st.button("Fetch Data", use_container_width=True):
                with st.spinner("Loading..."):
                    run_scraper(use_sample=(mode == "Sample"))
                    load_data.clear()
                    st.rerun()
        st.stop()

    # サイドバー
    with st.sidebar:
        st.markdown("### Data")
        if os.path.exists(DATA_FILE):
            t = datetime.fromtimestamp(os.path.getmtime(DATA_FILE))
            st.caption(f"Updated: {t.strftime('%Y-%m-%d %H:%M')}")

        mode = st.radio("Mode", ["Sample", "API"], horizontal=True, label_visibility="collapsed")
        if st.button("Refresh", use_container_width=True):
            with st.spinner("Loading..."):
                run_scraper(use_sample=(mode == "Sample"))
                load_data.clear()
                st.rerun()

        st.markdown("---")
        st.markdown("### Settings")

        ex_rate = st.slider("Exchange Rate", 3.0, 7.0, 4.8, 0.1)
        fee = st.slider("Fee Rate", 0.0, 0.3, 0.1, 0.01, format="%.0f%%")
        fixed = st.slider("Fixed Cost (JPY)", 0, 1000, 200, 50)
        cost_r = st.slider("Cost Rate", 0.0, 1.0, 0.5, 0.05, format="%.0f%%")

        st.markdown("---")
        st.markdown("### Filter")

        kws = df["keyword"].unique().tolist()
        sel_kw = st.multiselect("Category", kws, kws)
        min_profit = st.number_input("Min Profit (JPY)", -1000, 5000, 0, 100)
        min_sales = st.number_input("Min Sales", 0, 10000, 0, 100)

    # データ処理
    df = recalculate_profit(df, ex_rate, fee, fixed, cost_r)
    fdf = df[(df["keyword"].isin(sel_kw)) & (df["profit"] >= min_profit) & (df["sales"] >= min_sales)]

    # メトリクス
    cols = st.columns(4)
    metrics = [
        ("Products", f"{len(fdf):,}"),
        ("Avg Profit", f"¥{fdf['profit'].mean():,.0f}" if not fdf.empty else "¥0"),
        ("Avg Sales", f"{fdf['sales'].mean():,.0f}" if not fdf.empty else "0"),
        ("Treasure", f"{len(fdf[(fdf['profit']>=500)&(fdf['sales']>=100)]):,}"),
    ]
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)

    # メインタブ
    tab1, tab2, tab3 = st.tabs(["Analytics", "Rankings", "AI Assistant"])

    with tab1:
        st.markdown('<p class="section-title">Category Analysis</p>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if not fdf.empty:
                sales_data = fdf.groupby("keyword")["sales"].sum().sort_values()
                st.bar_chart(sales_data, color="#1a1a2e")
        with c2:
            if not fdf.empty:
                profit_data = fdf.groupby("keyword")["profit"].mean().sort_values()
                st.bar_chart(profit_data, color="#059669")

    with tab2:
        st.markdown('<p class="section-title">Product Rankings</p>', unsafe_allow_html=True)

        c1, c2 = st.columns([2, 1])
        with c1:
            sort_opt = st.selectbox(
                "Sort by",
                [("Profit", "profit"), ("Sales", "sales"), ("Price", "price")],
                format_func=lambda x: x[0],
                label_visibility="collapsed"
            )
        with c2:
            n = st.selectbox("Show", [10, 20, 50], label_visibility="collapsed")

        if not fdf.empty:
            show_df = fdf.sort_values(sort_opt[1], ascending=False).head(n)
            display = show_df[["keyword", "name", "price", "sales", "profit"]].copy()
            display.columns = ["Category", "Product", "Price (TWD)", "Sales", "Profit (JPY)"]
            display["Price (TWD)"] = display["Price (TWD)"].apply(lambda x: f"NT${x:,.0f}")
            display["Profit (JPY)"] = display["Profit (JPY)"].apply(lambda x: f"¥{x:,.0f}")
            display["Sales"] = display["Sales"].apply(lambda x: f"{x:,}")
            st.dataframe(display, use_container_width=True, hide_index=True)

    with tab3:
        st.markdown('<p class="section-title">AI Listing Assistant</p>', unsafe_allow_html=True)

        if fdf.empty:
            st.warning("No products available")
        else:
            options = fdf.apply(lambda x: f"{x['name'][:40]}... (NT${x['price']:,.0f})", axis=1).tolist()
            idx = st.selectbox("Select Product", range(len(options)), format_func=lambda x: options[x])
            product = fdf.iloc[idx].to_dict()

            st.markdown("---")

            # 価格分析
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Pricing Analysis**")
                prem_rate = st.slider("Premium Rate", 0.05, 0.15, 0.08, 0.01, format="%.0f%%")
                prices = calculate_premium_price(product["price"], df, product["keyword"], prem_rate)

                st.markdown(f"""
                <div class="price-highlight">
                    <div class="label">RECOMMENDED PRICE</div>
                    <div class="value">NT${prices['premium']:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

                m1, m2 = st.columns(2)
                m1.metric("Min Price", f"NT${prices['min']:,.0f}")
                m2.metric("Avg Price", f"NT${prices['avg']:,.0f}")

            with col2:
                st.markdown("**Profit Simulation**")

                curr = product["price"] * ex_rate * (1-fee) - product["price"] * ex_rate * cost_r - fixed
                prem = prices['premium'] * ex_rate * (1-fee) - prices['premium'] * ex_rate * cost_r - fixed

                m1, m2 = st.columns(2)
                m1.metric("Current", f"¥{curr:,.0f}")
                m2.metric("Premium", f"¥{prem:,.0f}", delta=f"+¥{prem-curr:,.0f}")

            st.markdown("---")

            # 説明文とハッシュタグ
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("**Product Description (Traditional Chinese)**")
                desc = generate_description(product)
                st.text_area("", desc, height=350, label_visibility="collapsed")
                st.download_button(
                    "Download",
                    desc,
                    f"description_{datetime.now().strftime('%Y%m%d')}.txt",
                    use_container_width=True
                )

            with col2:
                st.markdown("**Hashtags**")
                tags = generate_hashtags(product["keyword"])
                for tag in tags:
                    st.markdown(f'<span class="tag">{tag}</span>', unsafe_allow_html=True)
                st.text_area("Copy", " ".join(tags), height=100, label_visibility="collapsed")

    # フッター
    st.markdown("---")
    st.markdown(
        '<p style="text-align:center;color:#9ca3af;font-size:0.8rem;">Shopee Taiwan Research Tool</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
