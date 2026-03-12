import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from html_generator import create_report

# .envファイルから環境変数を読み込む
load_dotenv()

# TMDB API設定
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
PRIME_VIDEO_PROVIDER_ID = 9 # Amazon Prime Video JP

def fetch_tmdb_data(endpoint, params=None):
    """
    TMDB APIにリクエストを送信し、データを取得するヘルパー関数
    """
    if not TMDB_API_KEY or TMDB_API_KEY == "your_api_key_here":
         print("エラー: TMDB_API_KEYが設定されていません。.envファイルを確認してください。")
         return None

    if params is None:
        params = {}
    
    params["api_key"] = TMDB_API_KEY
    params["language"] = "ja-JP"
    params["region"] = "JP"
    
    url = f"{TMDB_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"APIリクエストエラー: {e}")
        return None

def get_new_releases():
    """最近追加されたPrime Video作品を取得"""
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"新着作品を取得しています...")
    params = {
        "with_watch_providers": PRIME_VIDEO_PROVIDER_ID,
        "watch_region": "JP",
        "sort_by": "primary_release_date.desc",
        "primary_release_date.lte": today,
        "vote_count.gte": 5,
        "page": 1
    }
    return fetch_tmdb_data("/discover/movie", params)

def get_popular_releases():
    """現在Prime Videoで人気の作品を取得"""
    print(f"人気作品を取得しています...")
    params = {
        "with_watch_providers": PRIME_VIDEO_PROVIDER_ID,
        "watch_region": "JP",
        "sort_by": "popularity.desc",
        "page": 1
    }
    return fetch_tmdb_data("/discover/movie", params)
    
def get_anime_releases():
    """Prime Videoのアニメ（直近人気）を取得"""
    print(f"アニメ作品を取得しています...")
    # 16 is TMDB ID for Animation
    params = {
        "with_watch_providers": PRIME_VIDEO_PROVIDER_ID,
        "watch_region": "JP",
        "with_genres": "16", 
        "sort_by": "popularity.desc",
        "page": 1
    }
    # アニメはTV番組(discover/tv)と映画(discover/movie)両方ありますが
    # まずは映画(劇場版アニメ等)で取得します。
    return fetch_tmdb_data("/discover/movie", params)
    
def get_family_safe_releases():
    """PG12/R15除外（G指定のみ）のファミリー向け作品を取得"""
    print(f"ファミリー向け(全年齢対象)作品を取得しています...")
    # certification_country=JP and certification.lte=G excludes PG12, R15+, etc.
    params = {
        "with_watch_providers": PRIME_VIDEO_PROVIDER_ID,
        "watch_region": "JP",
        "certification_country": "JP",
        "certification.lte": "G",
        "sort_by": "popularity.desc",
        "page": 1
    }
    return fetch_tmdb_data("/discover/movie", params)

def check_prime_video_updates():
    """
    Prime Videoチェッカーのメイン処理
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] Prime Videoのデータ確認を開始します...")
    
    if not TMDB_API_KEY or TMDB_API_KEY == "your_api_key_here":
         print("終了します: APIキーの設定が必要です。")
         return
         
    new_data = get_new_releases()
    popular_data = get_popular_releases()
    anime_data = get_anime_releases()
    family_safe_data = get_family_safe_releases()

    # HTMLレポートを生成
    if any([new_data, popular_data, anime_data, family_safe_data]):
        output_file = create_report(new_data, popular_data, anime_data, family_safe_data)
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(output_file)}")

    print(f"[{now}] 処理が完了しました。次回まで待機します。")

if __name__ == "__main__":
    check_prime_video_updates()
