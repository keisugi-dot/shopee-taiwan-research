"""Shopee Taiwan リサーチツール メインエントリーポイント"""

import os
import base64
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from scraper import ShopeeScraper
from config import SEARCH_KEYWORDS, OUTPUT_FILE

# 日本語フォント設定（macOS）
matplotlib.rcParams['font.family'] = ['Hiragino Sans', 'Arial Unicode MS', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False


def create_sales_chart(df: pd.DataFrame, output_file: str = "market_report.png") -> None:
    """ジャンル別の総販売数を棒グラフで可視化"""
    print("\n📊 グラフを作成中...")

    if "timestamp" in df.columns:
        latest_timestamp = df["timestamp"].max()
        df_latest = df[df["timestamp"] == latest_timestamp]
    else:
        df_latest = df

    genre_sales = df_latest.groupby("keyword")["sales"].sum().sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(12, 8))
    colors = plt.cm.viridis([i / len(genre_sales) for i in range(len(genre_sales))])
    bars = ax.barh(genre_sales.index, genre_sales.values, color=colors)

    for bar, value in zip(bars, genre_sales.values):
        ax.text(value + max(genre_sales.values) * 0.01, bar.get_y() + bar.get_height() / 2,
                f'{value:,.0f}', va='center', fontsize=10)

    ax.set_title("Shopee台湾 ジャンル別 総販売数比較\n(日本商品)", fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel("総販売数", fontsize=12)
    ax.set_ylabel("ジャンル（キーワード）", fontsize=12)
    ax.xaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"   ✅ グラフを {output_file} に保存しました")


def create_profit_chart(df: pd.DataFrame, output_file: str = "profit_report.png") -> None:
    """ジャンル別の平均想定利益を棒グラフで可視化"""
    if "estimated_profit_jpy" not in df.columns:
        return

    if "timestamp" in df.columns:
        latest_timestamp = df["timestamp"].max()
        df_latest = df[df["timestamp"] == latest_timestamp]
    else:
        df_latest = df

    genre_profit = df_latest.groupby("keyword")["estimated_profit_jpy"].mean().sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(12, 8))
    colors = ['#2ecc71' if v >= 0 else '#e74c3c' for v in genre_profit.values]
    bars = ax.barh(genre_profit.index, genre_profit.values, color=colors)

    for bar, value in zip(bars, genre_profit.values):
        offset = max(abs(genre_profit.values)) * 0.01
        x_pos = value + offset if value >= 0 else value - offset
        ha = 'left' if value >= 0 else 'right'
        ax.text(x_pos, bar.get_y() + bar.get_height() / 2,
                f'¥{value:,.0f}', va='center', ha=ha, fontsize=10)

    ax.set_title("Shopee台湾 ジャンル別 平均想定利益\n(日本商品)", fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel("平均想定利益（円）", fontsize=12)
    ax.set_ylabel("ジャンル（キーワード）", fontsize=12)
    ax.axvline(x=0, color='black', linewidth=0.5)
    ax.xaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'¥{int(x):,}'))

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"   ✅ 利益グラフを {output_file} に保存しました")


def show_profit_ranking(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """利益額ランキングを表示（上位N商品）"""
    print("\n" + "=" * 70)
    print("💰 【利益額ランキング TOP15】")
    print("=" * 70)

    if "timestamp" in df.columns:
        latest_timestamp = df["timestamp"].max()
        df_latest = df[df["timestamp"] == latest_timestamp].copy()
    else:
        df_latest = df.copy()

    # 利益順にソート
    profit_ranking = df_latest.nlargest(top_n, "estimated_profit_jpy")

    print(f"\n{'順位':<4} {'商品名':<42} {'ジャンル':<12} {'販売数':>8} {'価格(TWD)':>10} {'利益(円)':>10}")
    print("-" * 90)

    for i, row in enumerate(profit_ranking.itertuples(), 1):
        name = row.name[:38] + "..." if len(row.name) > 38 else row.name
        keyword = row.keyword.replace("日本 ", "")
        print(f"{i:<4} {name:<42} {keyword:<12} {row.sales:>8,} NT${row.price:>7,.0f} ¥{row.estimated_profit_jpy:>8,.0f}")

    return profit_ranking


def find_treasure_products(df: pd.DataFrame, min_profit: int = 500, min_sales: int = 100, min_rating: float = 4.5) -> pd.DataFrame:
    """お宝商品（優先仕入れ候補）を抽出"""
    print("\n" + "=" * 70)
    print("🏆 【お宝商品 - 優先仕入れ候補】")
    print("=" * 70)
    print(f"\n抽出条件:")
    print(f"  ✓ 想定利益 >= ¥{min_profit:,}")
    print(f"  ✓ 販売数 >= {min_sales:,}個")
    print(f"  ✓ ショップ評価 >= {min_rating}")

    if "timestamp" in df.columns:
        latest_timestamp = df["timestamp"].max()
        df_latest = df[df["timestamp"] == latest_timestamp].copy()
    else:
        df_latest = df.copy()

    # 3条件でフィルタリング
    treasure = df_latest[
        (df_latest["estimated_profit_jpy"] >= min_profit) &
        (df_latest["sales"] >= min_sales) &
        (df_latest["shop_rating"] >= min_rating)
    ].sort_values("estimated_profit_jpy", ascending=False)

    print(f"\n📦 該当商品: {len(treasure)}件\n")

    if len(treasure) > 0:
        print(f"{'順位':<4} {'商品名':<42} {'ジャンル':<10} {'販売数':>8} {'評価':>5} {'利益(円)':>10}")
        print("-" * 85)

        for i, row in enumerate(treasure.itertuples(), 1):
            name = row.name[:38] + "..." if len(row.name) > 38 else row.name
            keyword = row.keyword.replace("日本 ", "")
            print(f"{i:<4} {name:<42} {keyword:<10} {row.sales:>8,} ⭐{row.shop_rating:>3.1f} ¥{row.estimated_profit_jpy:>8,.0f}")
    else:
        print("   ⚠️ 条件を満たす商品が見つかりませんでした")

    return treasure


def create_html_report(df: pd.DataFrame, profit_ranking: pd.DataFrame, treasure_products: pd.DataFrame, output_file: str = "summary_report.html") -> None:
    """HTMLレポートを生成"""
    print("\n📄 HTMLレポートを作成中...")

    if "timestamp" in df.columns:
        latest_timestamp = df["timestamp"].max()
        df_latest = df[df["timestamp"] == latest_timestamp]
    else:
        df_latest = df
        latest_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 画像をBase64エンコード
    def encode_image(path):
        if os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        return ""

    market_img = encode_image("market_report.png")
    profit_img = encode_image("profit_report.png")

    # ジャンル別統計
    genre_stats = []
    for keyword in df_latest["keyword"].unique():
        genre_df = df_latest[df_latest["keyword"] == keyword]
        genre_stats.append({
            "ジャンル": keyword,
            "商品数": len(genre_df),
            "総販売数": genre_df["sales"].sum(),
            "平均価格": genre_df["price"].mean(),
            "平均利益": genre_df["estimated_profit_jpy"].mean() if "estimated_profit_jpy" in genre_df.columns else 0,
        })
    genre_stats_df = pd.DataFrame(genre_stats).sort_values("総販売数", ascending=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shopee台湾 リサーチレポート</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Hiragino Sans', 'Meiryo', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .header h1 {{
            color: #333;
            font-size: 2em;
            margin-bottom: 10px;
        }}
        .header .meta {{
            color: #666;
            font-size: 0.9em;
        }}
        .section {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .section h2 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .charts {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media (max-width: 900px) {{
            .charts {{ grid-template-columns: 1fr; }}
        }}
        .chart-box {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
        }}
        .chart-box img {{
            width: 100%;
            border-radius: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #667eea;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .highlight {{
            background: linear-gradient(90deg, #fff9c4, #fff);
        }}
        .profit-positive {{ color: #27ae60; font-weight: bold; }}
        .profit-negative {{ color: #e74c3c; font-weight: bold; }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .badge-gold {{ background: #ffd700; color: #333; }}
        .badge-silver {{ background: #c0c0c0; color: #333; }}
        .badge-bronze {{ background: #cd7f32; color: white; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-card .number {{
            font-size: 2em;
            font-weight: bold;
        }}
        .stat-card .label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .treasure-item {{
            background: linear-gradient(90deg, #fff9c4 0%, #ffffff 100%);
            border-left: 4px solid #ffd700;
        }}
        .footer {{
            text-align: center;
            color: white;
            padding: 20px;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛒 Shopee台湾 リサーチレポート</h1>
            <p class="meta">
                📅 取得日時: {latest_timestamp}<br>
                📦 分析商品数: {len(df_latest)}件 | 📁 累計データ: {len(df)}件
            </p>
        </div>

        <div class="section">
            <h2>📊 サマリー統計</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="number">{len(df_latest):,}</div>
                    <div class="label">分析商品数</div>
                </div>
                <div class="stat-card">
                    <div class="number">{df_latest["sales"].sum():,}</div>
                    <div class="label">総販売数</div>
                </div>
                <div class="stat-card">
                    <div class="number">NT${df_latest["price"].mean():,.0f}</div>
                    <div class="label">平均価格</div>
                </div>
                <div class="stat-card">
                    <div class="number">¥{df_latest["estimated_profit_jpy"].mean():,.0f}</div>
                    <div class="label">平均想定利益</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>📈 市場分析グラフ</h2>
            <div class="charts">
                <div class="chart-box">
                    <h3>総販売数比較</h3>
                    <img src="data:image/png;base64,{market_img}" alt="総販売数グラフ">
                </div>
                <div class="chart-box">
                    <h3>平均想定利益比較</h3>
                    <img src="data:image/png;base64,{profit_img}" alt="利益グラフ">
                </div>
            </div>
        </div>

        <div class="section">
            <h2>🏆 ジャンル別ランキング</h2>
            <table>
                <thead>
                    <tr>
                        <th>順位</th>
                        <th>ジャンル</th>
                        <th>商品数</th>
                        <th>総販売数</th>
                        <th>平均価格</th>
                        <th>平均想定利益</th>
                    </tr>
                </thead>
                <tbody>
"""

    for i, row in enumerate(genre_stats_df.itertuples(), 1):
        badge = '<span class="badge badge-gold">🥇</span>' if i == 1 else '<span class="badge badge-silver">🥈</span>' if i == 2 else '<span class="badge badge-bronze">🥉</span>' if i == 3 else f'{i}'
        profit_class = "profit-positive" if row.平均利益 > 0 else "profit-negative"
        html_content += f"""
                    <tr>
                        <td>{badge}</td>
                        <td>{row.ジャンル}</td>
                        <td>{row.商品数}</td>
                        <td>{row.総販売数:,}</td>
                        <td>NT${row.平均価格:,.0f}</td>
                        <td class="{profit_class}">¥{row.平均利益:,.0f}</td>
                    </tr>
"""

    html_content += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>💎 お宝商品 - 優先仕入れ候補</h2>
            <p style="color: #666; margin-bottom: 15px;">
                条件: 想定利益 ≥ ¥500 / 販売数 ≥ 100個 / 評価 ≥ 4.5
            </p>
"""

    if len(treasure_products) > 0:
        html_content += """
            <table>
                <thead>
                    <tr>
                        <th>順位</th>
                        <th>商品名</th>
                        <th>ジャンル</th>
                        <th>販売数</th>
                        <th>評価</th>
                        <th>価格(TWD)</th>
                        <th>想定利益</th>
                    </tr>
                </thead>
                <tbody>
"""
        for i, row in enumerate(treasure_products.itertuples(), 1):
            html_content += f"""
                    <tr class="treasure-item">
                        <td><span class="badge badge-gold">⭐{i}</span></td>
                        <td>{row.name[:50]}{'...' if len(row.name) > 50 else ''}</td>
                        <td>{row.keyword.replace('日本 ', '')}</td>
                        <td>{row.sales:,}</td>
                        <td>⭐{row.shop_rating}</td>
                        <td>NT${row.price:,.0f}</td>
                        <td class="profit-positive">¥{row.estimated_profit_jpy:,.0f}</td>
                    </tr>
"""
        html_content += """
                </tbody>
            </table>
"""
    else:
        html_content += '<p style="color: #e74c3c;">⚠️ 条件を満たす商品が見つかりませんでした</p>'

    html_content += """
        </div>

        <div class="section">
            <h2>💰 利益額ランキング TOP15</h2>
            <table>
                <thead>
                    <tr>
                        <th>順位</th>
                        <th>商品名</th>
                        <th>ジャンル</th>
                        <th>販売数</th>
                        <th>価格(TWD)</th>
                        <th>想定利益</th>
                    </tr>
                </thead>
                <tbody>
"""

    for i, row in enumerate(profit_ranking.itertuples(), 1):
        badge = '<span class="badge badge-gold">🥇</span>' if i == 1 else '<span class="badge badge-silver">🥈</span>' if i == 2 else '<span class="badge badge-bronze">🥉</span>' if i == 3 else f'{i}'
        html_content += f"""
                    <tr>
                        <td>{badge}</td>
                        <td>{row.name[:50]}{'...' if len(row.name) > 50 else ''}</td>
                        <td>{row.keyword.replace('日本 ', '')}</td>
                        <td>{row.sales:,}</td>
                        <td>NT${row.price:,.0f}</td>
                        <td class="profit-positive">¥{row.estimated_profit_jpy:,.0f}</td>
                    </tr>
"""

    html_content += f"""
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Generated by Shopee Taiwan Research Tool</p>
            <p>© 2026 - Powered by Claude Code</p>
        </div>
    </div>
</body>
</html>
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"   ✅ HTMLレポートを {output_file} に保存しました")


def analyze_results(df: pd.DataFrame) -> None:
    """取得データを分析してジャンル別の売れ行きを表示"""
    print("\n" + "=" * 60)
    print("📊 データ分析レポート")
    print("=" * 60)

    if df.empty:
        print("❌ 分析するデータがありません")
        return

    if "timestamp" in df.columns:
        latest_timestamp = df["timestamp"].max()
        df_analysis = df[df["timestamp"] == latest_timestamp]
        print(f"\n📅 分析対象: {latest_timestamp}")
    else:
        df_analysis = df

    print(f"📦 今回取得商品数: {len(df_analysis)}")
    print(f"📁 累計データ数: {len(df)}")

    print("\n" + "-" * 60)
    print("【ジャンル別 分析結果】")
    print("-" * 60)

    genre_stats = []

    for keyword in df_analysis["keyword"].unique():
        genre_df = df_analysis[df_analysis["keyword"] == keyword]

        stats = {
            "ジャンル": keyword,
            "商品数": len(genre_df),
            "平均価格": genre_df["price"].mean(),
            "総販売数": genre_df["sales"].sum(),
            "平均販売数": genre_df["sales"].mean(),
            "平均評価": genre_df["shop_rating"].mean(),
            "最高販売数": genre_df["sales"].max(),
        }

        if "estimated_profit_jpy" in genre_df.columns:
            stats["平均想定利益"] = genre_df["estimated_profit_jpy"].mean()

        genre_stats.append(stats)

        print(f"\n🏷️  {keyword}")
        print(f"   商品数:     {stats['商品数']}個")
        print(f"   平均価格:   NT${stats['平均価格']:,.0f}")
        print(f"   総販売数:   {stats['総販売数']:,}個")
        print(f"   平均販売数: {stats['平均販売数']:,.0f}個")
        print(f"   平均評価:   ⭐{stats['平均評価']:.1f}")
        if "平均想定利益" in stats:
            print(f"   平均想定利益: ¥{stats['平均想定利益']:,.0f}")

    stats_df = pd.DataFrame(genre_stats)

    print("\n" + "-" * 60)
    print("【🏆 売れ筋ジャンルランキング】")
    print("-" * 60)

    ranking = stats_df.sort_values("総販売数", ascending=False)

    for i, row in enumerate(ranking.itertuples(), 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        print(f"\n{medal} {row.ジャンル}")
        print(f"   総販売数: {row.総販売数:,}個 | 平均販売数: {row.平均販売数:,.0f}個")

    best_genre = ranking.iloc[0]

    print("\n" + "=" * 60)
    print("📈 【結論】")
    print("=" * 60)
    print(f"\n🎯 最も売れているジャンル: {best_genre['ジャンル']}")
    print(f"   - 総販売数: {best_genre['総販売数']:,}個")
    print(f"   - 平均販売数: {best_genre['平均販売数']:,.0f}個/商品")
    print(f"   - 平均価格: NT${best_genre['平均価格']:,.0f}")


def main():
    """メイン処理"""
    print("🚀 Shopee台湾リサーチツールを起動します\n")

    # 既存のCSVを削除（新規実行の場合）
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
        print(f"📝 既存の {OUTPUT_FILE} を削除しました（新規実行）\n")

    # スクレイピング実行
    scraper = ShopeeScraper()
    df = scraper.run(SEARCH_KEYWORDS)

    # データ分析
    if not df.empty:
        analyze_results(df)

        # グラフ作成
        create_sales_chart(df, "market_report.png")
        create_profit_chart(df, "profit_report.png")

        # 利益額ランキング表示
        profit_ranking = show_profit_ranking(df, top_n=15)

        # お宝商品抽出
        treasure_products = find_treasure_products(df, min_profit=500, min_sales=100, min_rating=4.5)

        # HTMLレポート作成
        create_html_report(df, profit_ranking, treasure_products, "summary_report.html")

    else:
        print("\n❌ データの取得に失敗しました")

    print("\n" + "=" * 60)
    print("✨ 処理完了")
    print("=" * 60)


if __name__ == "__main__":
    main()
