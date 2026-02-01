"""Shopee Taiwan スクレイピング設定"""

# Base URL
BASE_URL = "https://shopee.tw"

# 検索キーワードリスト（食品ジャンルを細分化）
SEARCH_KEYWORDS = [
    "日本 零食",      # お菓子
    "日本 泡麵",      # カップ麺
    "日本 調味料",    # 調味料
    "日本 咖啡",      # コーヒー
    "日本 生活用品",  # 生活用品
    "日本 美容",      # 美容
]

# 利益計算用の設定
EXCHANGE_RATE = 4.8        # 1 TWD = 4.8 JPY
SALES_FEE_RATE = 0.10      # 販売手数料 10%
FIXED_COST_JPY = 200       # 固定コスト（送料・梱包）200円
COST_RATE = 0.50           # 仮の原価率（販売価格の50%）

# 各キーワードで取得する商品数
PRODUCTS_PER_KEYWORD = 30

# 出力ファイル
OUTPUT_FILE = "research_results.csv"

# ブラウザ設定（台湾ユーザーとして）
BROWSER_CONFIG = {
    "locale": "zh-TW",
    "timezone_id": "Asia/Taipei",
    "geolocation": {"latitude": 25.0330, "longitude": 121.5654},  # 台北
    "permissions": ["geolocation"],
}

# リクエストヘッダー（台湾ユーザー）
HEADERS = {
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# 待機時間設定（秒）
DELAYS = {
    "page_load": (3, 5),      # ページ読み込み後の待機
    "scroll": (0.5, 1.5),     # スクロール間の待機
    "between_keywords": (5, 10),  # キーワード間の待機
    "action": (0.3, 0.8),     # アクション間の待機
}

# タイムアウト（ミリ秒）
TIMEOUT = 60000
