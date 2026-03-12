import os
import time
import requests
import json
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
PRIME_VIDEO_PROVIDER_ID = 9 # Amazon Prime Video JP

# TMDBの主要なジャンルIDリスト
MOVIE_GENRES = {
    28: "アクション", 12: "アドベンチャー", 16: "アニメーション", 35: "コメディ",
    80: "犯罪", 99: "ドキュメンタリー", 18: "ドラマ", 10751: "ファミリー",
    14: "ファンタジー", 36: "歴史", 27: "ホラー", 10402: "音楽",
    9648: "謎", 10749: "ロマンス", 878: "SF", 10770: "TV映画",
    53: "スリラー", 10752: "戦争", 37: "西部劇"
}

TV_GENRES = {
    10759: "アクション・アドベンチャー", 16: "アニメーション", 35: "コメディ",
    80: "犯罪", 99: "ドキュメンタリー", 18: "ドラマ", 10751: "ファミリー",
    10762: "キッズ", 9648: "謎", 10763: "ニュース", 10764: "リアリティ",
    10765: "SF・ファンタジー", 10766: "ソープオペラ", 10767: "トーク",
    10768: "戦争・政治", 37: "西部劇"
}

def fetch_pages(endpoint, item_type, genre_id, genre_name, max_pages=500):
    """指定されたジャンルの全データをTMDB制限(最大500ページ)まで取得する"""
    all_items = []
    
    # TMDB API limits the max offset (page * size) to 10,000 items (500 pages)
    # Beyond page 500, the API returns an error.
    for page in range(1, max_pages + 1):
        print(f"[{item_type}] {genre_name} - Page {page} ...", end="", flush=True)
        params = {
            "api_key": TMDB_API_KEY,
            "language": "ja-JP",
            "region": "JP",
            "with_watch_providers": PRIME_VIDEO_PROVIDER_ID,
            "watch_region": "JP",
            "with_genres": str(genre_id),
            "sort_by": "popularity.desc",
            "page": page
        }
        
        url = f"{TMDB_BASE_URL}{endpoint}"
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            for r in results:
                item = {
                    "id": r.get("id"),
                    "type": item_type,
                    "title": r.get("title") or r.get("name") or "不明",
                    "release_date": r.get("release_date") or r.get("first_air_date") or "",
                    "poster_path": r.get("poster_path"),
                    "vote_average": r.get("vote_average", 0),
                    "vote_count": r.get("vote_count", 0),
                    "popularity": r.get("popularity", 0),
                    "genre_ids": r.get("genre_ids", []),
                    "adult": r.get("adult", False)
                }
                all_items.append(item)
                
            print(f" OK ({len(results)}件)")
            
            # APIが返す「このジャンルの全ページ数」に到達したら終了
            total_pages = data.get("total_pages", max_pages)
            if page >= total_pages or page >= 500:
                print(f" -> 完了 ({page}ページ)。次のジャンルへ。")
                break
                
        except requests.exceptions.RequestException as e:
            print(f" ERROR: {e}")
            break
            
        time.sleep(1) # TMDB Rate Limit (50/sec max, but playing it safe at 1/sec for stability)
        
    return all_items

def main():
    if not TMDB_API_KEY or TMDB_API_KEY == "your_api_key_here":
         print("エラー: APIキーが設定されていません。")
         return
         
    print("==================================================")
    print(" 限界テスト: 全ジャンル網羅スクレイピング開始")
    print(" ※各APIコールで1秒待機するため、非常に時間がかかります。")
    print(" ※TMDBの上限仕様により、1つの条件につき最大1万件(500ページ)が取得限界です。")
    print("==================================================")
    
    all_data = []

    # 1. 映画の全ジャンルを取得
    print("\n--- 映画データの取得開始 ---")
    for genre_id, genre_name in MOVIE_GENRES.items():
        items = fetch_pages("/discover/movie", "movie", genre_id, genre_name)
        all_data.extend(items)
        time.sleep(2) # ジャンル間の休憩

    # 2. TV番組の全ジャンルを取得
    print("\n--- TV番組データの取得開始 ---")
    for genre_id, genre_name in TV_GENRES.items():
        items = fetch_pages("/discover/tv", "tv", genre_id, genre_name)
        all_data.extend(items)
        time.sleep(2) # ジャンル間の休憩

    # 重複排除 (1つの作品が複数のジャンルに属している場合があるため)
    unique_data = {f"{item['type']}_{item['id']}": item for item in all_data}.values()
    final_list = list(unique_data)
    
    # 全体を人気順でソート
    final_list.sort(key=lambda x: x["popularity"], reverse=True)
    
    output_file = "prime_video_ultimate.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
        
    print("==================================================")
    print(f"総取得件数(重複前): {len(all_data)} 件")
    print(f"最終保存件数(重複解除後): {len(final_list)} 件")
    print(f"巨大データベースを保存しました: {output_file}")
    print("==================================================")

if __name__ == "__main__":
    main()
