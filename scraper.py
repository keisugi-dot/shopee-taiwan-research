"""Shopee Taiwan スクレイパー（API版）"""

import os
import random
import time
from datetime import datetime
import requests
import pandas as pd

from config import (
    SEARCH_KEYWORDS,
    PRODUCTS_PER_KEYWORD,
    OUTPUT_FILE,
    DELAYS,
    EXCHANGE_RATE,
    SALES_FEE_RATE,
    FIXED_COST_JPY,
    COST_RATE,
)
from sample_data import SAMPLE_PRODUCTS


class ShopeeScraper:
    """Shopee台湾のスクレイピングクラス（API使用）"""

    def __init__(self):
        self.session = requests.Session()
        self.all_products: list[dict] = []
        self._setup_session()

    def _setup_session(self) -> None:
        """セッションの設定"""
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://shopee.tw/",
            "X-Requested-With": "XMLHttpRequest",
            "X-Shopee-Language": "zh-Hant",
            "X-API-SOURCE": "pc",
            "If-None-Match-": "*",
            "Content-Type": "application/json",
        })

        # Cookie設定
        self.session.cookies.set("language", "zh-Hant", domain=".shopee.tw")
        self.session.cookies.set("SPC_F", self._generate_device_id(), domain=".shopee.tw")

    def _generate_device_id(self) -> str:
        """デバイスIDを生成"""
        import uuid
        return str(uuid.uuid4())

    def _random_delay(self, delay_type: str = "action") -> None:
        """ランダムな待機時間"""
        min_delay, max_delay = DELAYS.get(delay_type, (1, 2))
        time.sleep(random.uniform(min_delay, max_delay))

    def _calculate_profit(self, price_twd: float) -> dict:
        """利益を計算

        計算式:
        - 販売価格（円） = 販売価格（TWD） × 為替レート × (1 - 手数料率)
        - 仮の原価（円） = 販売価格（円） × 原価率
        - 想定利益（円） = 販売価格（円） - 仮の原価 - 固定コスト

        Args:
            price_twd: 販売価格（台湾ドル）

        Returns:
            dict: 利益関連の計算結果
        """
        # 販売価格（円）
        price_jpy = price_twd * EXCHANGE_RATE

        # 手数料控除後の売上（円）
        revenue_after_fee = price_jpy * (1 - SALES_FEE_RATE)

        # 仮の原価（販売価格の50%）
        estimated_cost = price_jpy * COST_RATE

        # 想定利益 = 売上 - 原価 - 固定コスト
        estimated_profit = revenue_after_fee - estimated_cost - FIXED_COST_JPY

        return {
            "price_jpy": round(price_jpy, 0),
            "estimated_cost_jpy": round(estimated_cost, 0),
            "estimated_profit_jpy": round(estimated_profit, 0),
        }

    def search_products(self, keyword: str) -> list[dict]:
        """キーワードで商品を検索（API使用）"""
        products = []

        print(f"\n🔍 検索中: {keyword}")

        # Shopee Search API
        api_url = "https://shopee.tw/api/v4/search/search_items"

        params = {
            "by": "relevancy",
            "keyword": keyword,
            "limit": PRODUCTS_PER_KEYWORD,
            "newest": 0,
            "order": "desc",
            "page_type": "search",
            "scenario": "PAGE_GLOBAL_SEARCH",
            "version": 2,
        }

        try:
            response = self.session.get(api_url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()

                items = data.get("items", [])
                if not items:
                    items = data.get("data", {}).get("items", [])

                print(f"   📦 API応答: {len(items)}個の商品")

                for item in items[:PRODUCTS_PER_KEYWORD]:
                    try:
                        item_basic = item.get("item_basic", item)

                        name = item_basic.get("name", "N/A")
                        price = item_basic.get("price", 0) / 100000
                        if price == 0:
                            price = item_basic.get("price_min", 0) / 100000

                        sales = item_basic.get("sold", 0)
                        if sales == 0:
                            sales = item_basic.get("historical_sold", 0)

                        shop_rating = item_basic.get("shop_rating", 0)
                        if shop_rating == 0:
                            shop_rating = item_basic.get("item_rating", {}).get("rating_star", 0)

                        # 利益計算
                        profit_info = self._calculate_profit(price)

                        if name and name != "N/A":
                            product = {
                                "keyword": keyword,
                                "name": name[:100],
                                "price": round(price, 0),
                                "sales": sales,
                                "shop_rating": round(shop_rating, 1),
                                **profit_info,
                            }
                            products.append(product)

                    except Exception:
                        continue

                print(f"   📊 {len(products)}個の商品データを取得")

            elif response.status_code == 403:
                print(f"   ⚠️ アクセス拒否（403）- 別の方法を試行中...")
                products = self._search_via_web(keyword)

            else:
                print(f"   ❌ APIエラー: {response.status_code}")
                products = self._search_via_web(keyword)

        except Exception as e:
            print(f"   ❌ エラー: {e}")
            products = self._search_via_web(keyword)

        return products

    def _search_via_web(self, keyword: str) -> list[dict]:
        """Web経由でのフォールバック検索"""
        products = []

        api_urls = [
            "https://shopee.tw/api/v4/search/search_items",
            "https://shopee.tw/api/v2/search_items/",
        ]

        for api_url in api_urls:
            try:
                params = {
                    "by": "relevancy",
                    "keyword": keyword,
                    "limit": PRODUCTS_PER_KEYWORD,
                    "newest": 0,
                    "order": "desc",
                }

                headers = {
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
                    "Accept": "application/json",
                    "Referer": "https://shopee.tw/",
                }

                response = self.session.get(api_url, params=params, headers=headers, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", data.get("data", {}).get("items", []))

                    if items:
                        print(f"   ✅ 代替API成功: {len(items)}個")
                        for item in items[:PRODUCTS_PER_KEYWORD]:
                            item_basic = item.get("item_basic", item)
                            price = item_basic.get("price", 0) / 100000
                            profit_info = self._calculate_profit(price)

                            product = {
                                "keyword": keyword,
                                "name": item_basic.get("name", "N/A")[:100],
                                "price": price,
                                "sales": item_basic.get("sold", item_basic.get("historical_sold", 0)),
                                "shop_rating": round(item_basic.get("shop_rating", 0), 1),
                                **profit_info,
                            }
                            products.append(product)
                        break

            except Exception:
                continue

        return products

    def run(self, keywords: list[str] | None = None, use_sample: bool = False) -> pd.DataFrame:
        """スクレイピングを実行

        Args:
            keywords: 検索キーワードリスト
            use_sample: True=サンプルデータ使用（デモ用）, False=API使用
        """
        if keywords is None:
            keywords = SEARCH_KEYWORDS

        # 現在のタイムスタンプ
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print("=" * 60)
        print("🛒 Shopee台湾 リサーチツール")
        print("=" * 60)
        print(f"   取得日時: {timestamp}")

        if use_sample:
            print("   モード: サンプルデータ（デモ用）")
            print("\n📦 サンプルデータを読み込み中...")

            for keyword in keywords:
                keyword_products = [p.copy() for p in SAMPLE_PRODUCTS if p["keyword"] == keyword]
                # 利益計算を追加
                for product in keyword_products[:PRODUCTS_PER_KEYWORD]:
                    profit_info = self._calculate_profit(product["price"])
                    product.update(profit_info)
                    product["timestamp"] = timestamp
                self.all_products.extend(keyword_products[:PRODUCTS_PER_KEYWORD])
                print(f"   ✅ {keyword}: {len(keyword_products[:PRODUCTS_PER_KEYWORD])}個")
        else:
            print("   モード: API（ライブデータ）")

            for i, keyword in enumerate(keywords):
                products = self.search_products(keyword)
                # タイムスタンプを追加
                for product in products:
                    product["timestamp"] = timestamp
                self.all_products.extend(products)

                if i < len(keywords) - 1:
                    print(f"\n   ⏳ 次の検索まで待機中...")
                    self._random_delay("between_keywords")

            # APIで取得できなかった場合、サンプルデータにフォールバック
            if not self.all_products:
                print("\n⚠️ APIからデータを取得できませんでした。")
                print("   地域制限の可能性があります（台湾IPが必要）")
                print("\n📦 サンプルデータを使用します...")

                for keyword in keywords:
                    keyword_products = [p.copy() for p in SAMPLE_PRODUCTS if p["keyword"] == keyword]
                    for product in keyword_products[:PRODUCTS_PER_KEYWORD]:
                        profit_info = self._calculate_profit(product["price"])
                        product.update(profit_info)
                        product["timestamp"] = timestamp
                    self.all_products.extend(keyword_products[:PRODUCTS_PER_KEYWORD])
                    print(f"   ✅ {keyword}: {len(keyword_products[:PRODUCTS_PER_KEYWORD])}個")

        # DataFrameに変換
        df = pd.DataFrame(self.all_products)

        if not df.empty:
            # 列の順序を整理
            columns_order = [
                "timestamp", "keyword", "name", "price", "sales", "shop_rating",
                "price_jpy", "estimated_cost_jpy", "estimated_profit_jpy"
            ]
            df = df[[col for col in columns_order if col in df.columns]]

            # 既存ファイルがあれば追記、なければ新規作成
            if os.path.exists(OUTPUT_FILE):
                existing_df = pd.read_csv(OUTPUT_FILE, encoding="utf-8-sig")
                df = pd.concat([existing_df, df], ignore_index=True)
                print(f"\n📝 既存データに追記しました")

            df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
            print(f"✅ 結果を {OUTPUT_FILE} に保存しました")
            print(f"   合計 {len(df)} 商品（累計）")

        return df


def main():
    """メイン処理"""
    scraper = ShopeeScraper()
    df = scraper.run()
    return df


if __name__ == "__main__":
    main()
