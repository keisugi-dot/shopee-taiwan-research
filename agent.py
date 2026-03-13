"""Shopee Taiwan リサーチ AIエージェント

Claude Opus 4.6 を使ったインタラクティブな市場調査エージェント。
スクレイピング・分析・レポート生成を自然言語で操作できます。
"""

import json
import os
from datetime import datetime

import anthropic
import pandas as pd

from config import SEARCH_KEYWORDS, OUTPUT_FILE
from scraper import ShopeeScraper
from main import (
    analyze_results,
    create_sales_chart,
    create_profit_chart,
    show_profit_ranking,
    find_treasure_products,
    create_html_report,
)

client = anthropic.Anthropic()
MODEL = "claude-opus-4-6"

# ────────────────────────────────────────────────────────────────────────────
# ツール定義
# ────────────────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "search_products",
        "description": (
            "Shopee台湾で商品を検索・スクレイピングします。"
            "指定したキーワードで商品データ（価格・販売数・評価・想定利益）を取得します。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "検索キーワードのリスト。省略するとデフォルト設定を使用。",
                },
                "use_sample": {
                    "type": "boolean",
                    "description": "True でサンプルデータを使用（デモ用）。デフォルト False。",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_summary",
        "description": (
            "現在読み込まれているデータのサマリーを返します。"
            "商品数・ジャンル別統計・総販売数などを確認できます。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "analyze_market",
        "description": (
            "ジャンル別の市場分析を実行します。"
            "売れ筋ランキング・平均価格・販売数・想定利益などを分析します。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "find_best_products",
        "description": (
            "利益・販売数・評価の条件でお宝商品（優先仕入れ候補）を抽出します。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "min_profit": {
                    "type": "number",
                    "description": "最低想定利益（円）。デフォルト 500。",
                },
                "min_sales": {
                    "type": "number",
                    "description": "最低販売数。デフォルト 100。",
                },
                "min_rating": {
                    "type": "number",
                    "description": "最低ショップ評価。デフォルト 4.5。",
                },
                "top_n": {
                    "type": "integer",
                    "description": "表示する上位件数。デフォルト 10。",
                },
            },
            "required": [],
        },
    },
    {
        "name": "generate_report",
        "description": (
            "市場分析グラフと HTMLレポートを生成・保存します。"
            "summary_report.html, market_report.png, profit_report.png が作成されます。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ────────────────────────────────────────────────────────────────────────────
# ツール実行
# ────────────────────────────────────────────────────────────────────────────

def _load_df() -> pd.DataFrame:
    """保存済みCSVがあれば読み込む。なければ空のDataFrameを返す。"""
    if os.path.exists(OUTPUT_FILE):
        return pd.read_csv(OUTPUT_FILE, encoding="utf-8-sig")
    return pd.DataFrame()


def tool_search_products(keywords: list[str] | None = None, use_sample: bool = False) -> str:
    if keywords is None:
        keywords = SEARCH_KEYWORDS

    # 既存CSVを削除して新規取得
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    scraper = ShopeeScraper()
    df = scraper.run(keywords=keywords, use_sample=use_sample)

    if df.empty:
        return "商品データの取得に失敗しました。"

    return (
        f"✅ 取得完了\n"
        f"  キーワード: {', '.join(keywords)}\n"
        f"  取得商品数: {len(df)} 件\n"
        f"  ジャンル数: {df['keyword'].nunique()} ジャンル\n"
        f"  平均価格: NT${df['price'].mean():,.0f}\n"
        f"  平均想定利益: ¥{df['estimated_profit_jpy'].mean():,.0f}"
    )


def tool_get_summary() -> str:
    df = _load_df()
    if df.empty:
        return "データがありません。まず search_products を実行してください。"

    if "timestamp" in df.columns:
        latest = df["timestamp"].max()
        df_latest = df[df["timestamp"] == latest]
    else:
        df_latest = df
        latest = "不明"

    lines = [
        f"📊 データサマリー",
        f"  取得日時: {latest}",
        f"  総商品数: {len(df_latest):,} 件",
        f"  ジャンル数: {df_latest['keyword'].nunique()} ジャンル",
        f"  総販売数: {df_latest['sales'].sum():,}",
        f"  平均価格: NT${df_latest['price'].mean():,.0f}",
    ]

    if "estimated_profit_jpy" in df_latest.columns:
        lines.append(f"  平均想定利益: ¥{df_latest['estimated_profit_jpy'].mean():,.0f}")

    lines.append("\nジャンル別商品数:")
    for kw, cnt in df_latest.groupby("keyword").size().items():
        lines.append(f"  {kw}: {cnt} 件")

    return "\n".join(lines)


def tool_analyze_market() -> str:
    df = _load_df()
    if df.empty:
        return "データがありません。まず search_products を実行してください。"

    if "timestamp" in df.columns:
        latest = df["timestamp"].max()
        df_latest = df[df["timestamp"] == latest]
    else:
        df_latest = df

    genre_stats = []
    for kw in df_latest["keyword"].unique():
        g = df_latest[df_latest["keyword"] == kw]
        stat = {
            "ジャンル": kw,
            "商品数": len(g),
            "総販売数": int(g["sales"].sum()),
            "平均価格_TWD": round(g["price"].mean(), 0),
            "平均販売数": round(g["sales"].mean(), 0),
            "平均評価": round(g["shop_rating"].mean(), 2),
        }
        if "estimated_profit_jpy" in g.columns:
            stat["平均想定利益_JPY"] = round(g["estimated_profit_jpy"].mean(), 0)
        genre_stats.append(stat)

    ranked = sorted(genre_stats, key=lambda x: x["総販売数"], reverse=True)

    lines = ["📈 ジャンル別 市場分析レポート", "=" * 50]
    for i, s in enumerate(ranked, 1):
        medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i}."
        lines.append(f"\n{medal} {s['ジャンル']}")
        lines.append(f"   商品数: {s['商品数']} | 総販売数: {s['総販売数']:,}")
        lines.append(f"   平均価格: NT${s['平均価格_TWD']:,.0f} | 平均販売数: {s['平均販売数']:,.0f}")
        lines.append(f"   平均評価: ⭐{s['平均評価']}")
        if "平均想定利益_JPY" in s:
            lines.append(f"   平均想定利益: ¥{s['平均想定利益_JPY']:,.0f}")

    return "\n".join(lines)


def tool_find_best_products(
    min_profit: float = 500,
    min_sales: float = 100,
    min_rating: float = 4.5,
    top_n: int = 10,
) -> str:
    df = _load_df()
    if df.empty:
        return "データがありません。まず search_products を実行してください。"

    if "timestamp" in df.columns:
        latest = df["timestamp"].max()
        df_latest = df[df["timestamp"] == latest].copy()
    else:
        df_latest = df.copy()

    if "estimated_profit_jpy" not in df_latest.columns:
        return "利益データがありません。"

    treasure = df_latest[
        (df_latest["estimated_profit_jpy"] >= min_profit)
        & (df_latest["sales"] >= min_sales)
        & (df_latest["shop_rating"] >= min_rating)
    ].sort_values("estimated_profit_jpy", ascending=False).head(top_n)

    if treasure.empty:
        return (
            f"条件を満たす商品が見つかりませんでした。\n"
            f"条件: 利益≥¥{min_profit:,} / 販売数≥{min_sales:,} / 評価≥{min_rating}"
        )

    lines = [
        f"💎 お宝商品 TOP{len(treasure)}",
        f"条件: 利益≥¥{min_profit:,} / 販売数≥{min_sales:,} / 評価≥{min_rating}",
        "=" * 60,
    ]
    for i, row in enumerate(treasure.itertuples(), 1):
        name = row.name[:45] + "..." if len(row.name) > 45 else row.name
        genre = row.keyword.replace("日本 ", "")
        lines.append(
            f"{i:>2}. {name}\n"
            f"    ジャンル: {genre} | 販売数: {row.sales:,} | 評価: ⭐{row.shop_rating}\n"
            f"    価格: NT${row.price:,.0f} | 想定利益: ¥{row.estimated_profit_jpy:,.0f}"
        )
    return "\n".join(lines)


def tool_generate_report() -> str:
    df = _load_df()
    if df.empty:
        return "データがありません。まず search_products を実行してください。"

    create_sales_chart(df, "market_report.png")
    create_profit_chart(df, "profit_report.png")
    profit_ranking = show_profit_ranking(df, top_n=15)
    treasure = find_treasure_products(df, min_profit=500, min_sales=100, min_rating=4.5)
    create_html_report(df, profit_ranking, treasure, "summary_report.html")

    return (
        "✅ レポート生成完了\n"
        "  📊 market_report.png  - ジャンル別販売数グラフ\n"
        "  💰 profit_report.png  - ジャンル別利益グラフ\n"
        "  📄 summary_report.html - 総合HTMLレポート"
    )


def execute_tool(name: str, tool_input: dict) -> str:
    """ツール名とinputを受け取って実行し、結果文字列を返す。"""
    try:
        if name == "search_products":
            return tool_search_products(
                keywords=tool_input.get("keywords"),
                use_sample=tool_input.get("use_sample", False),
            )
        elif name == "get_summary":
            return tool_get_summary()
        elif name == "analyze_market":
            return tool_analyze_market()
        elif name == "find_best_products":
            return tool_find_best_products(
                min_profit=tool_input.get("min_profit", 500),
                min_sales=tool_input.get("min_sales", 100),
                min_rating=tool_input.get("min_rating", 4.5),
                top_n=tool_input.get("top_n", 10),
            )
        elif name == "generate_report":
            return tool_generate_report()
        else:
            return f"未知のツール: {name}"
    except Exception as e:
        return f"ツール実行エラー ({name}): {e}"


# ────────────────────────────────────────────────────────────────────────────
# エージェントループ
# ────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """あなたはShopee台湾の日本商品リサーチを専門とするAIアシスタントです。

提供されたツールを使って、ユーザーの市場調査をサポートしてください。

## できること
- Shopee台湾で日本商品を検索・スクレイピング
- ジャンル別の市場分析（売れ筋・価格・利益）
- お宝商品（高利益・高評価・高販売数）の抽出
- 市場分析グラフとHTMLレポートの生成

## 回答スタイル
- 日本語で明確に回答する
- データに基づいた具体的なインサイトを提供する
- ビジネス判断に役立つ観点でコメントする
"""

def run_agent(user_message: str, conversation_history: list[dict]) -> str:
    """ユーザーメッセージを受け取り、エージェントループを実行して最終回答を返す。"""

    conversation_history.append({"role": "user", "content": user_message})

    print("\n🤖 ", end="", flush=True)

    while True:
        # ストリーミングで回答を取得
        with client.messages.stream(
            model=MODEL,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversation_history,
        ) as stream:
            full_response = stream.get_final_message()

        # アシスタントのメッセージを履歴に追加
        conversation_history.append({
            "role": "assistant",
            "content": full_response.content,
        })

        # テキストブロックを表示
        for block in full_response.content:
            if block.type == "text":
                print(block.text, flush=True)

        # ツール使用がなければ終了
        tool_use_blocks = [b for b in full_response.content if b.type == "tool_use"]
        if not tool_use_blocks:
            break

        # ツールを実行して結果を収集
        tool_results = []
        for tool_block in tool_use_blocks:
            print(f"\n  🔧 {tool_block.name} を実行中...", flush=True)
            result = execute_tool(tool_block.name, tool_block.input)
            print(f"  ✅ 完了\n", flush=True)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": result,
            })

        # ツール結果を履歴に追加して次のループへ
        conversation_history.append({"role": "user", "content": tool_results})
        print("\n🤖 ", end="", flush=True)

    # 最後のテキスト回答を返す
    last_text = ""
    for block in full_response.content:
        if block.type == "text":
            last_text = block.text
    return last_text


# ────────────────────────────────────────────────────────────────────────────
# CLI インターフェース
# ────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("🛒 Shopee台湾 リサーチ AIエージェント")
    print("   Powered by Claude Opus 4.6")
    print("=" * 60)
    print("終了するには 'quit' または 'exit' を入力してください。\n")

    conversation_history: list[dict] = []

    while True:
        try:
            user_input = input("あなた: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 エージェントを終了します。")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "終了"):
            print("👋 エージェントを終了します。")
            break

        run_agent(user_input, conversation_history)
        print()


if __name__ == "__main__":
    main()
