import os
import time
import requests
import json
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
PRIME_VIDEO_PROVIDER_ID = 9 # Amazon Prime Video JP
ANIME_GENRE_ID = "16" # Animation

def fetch_pages(endpoint, item_type, max_pages=50):
    """アニメジャンル限定で、さらに深く(50ページ=1000件)データを取得する"""
    all_items = []
    
    for page in range(1, max_pages + 1):
        print(f"アニメ集中取得中: {item_type} - ページ {page}/{max_pages} ...", end="", flush=True)
        params = {
            "api_key": TMDB_API_KEY,
            "language": "ja-JP",
            "region": "JP",
            "with_watch_providers": PRIME_VIDEO_PROVIDER_ID,
            "watch_region": "JP",
            "with_genres": ANIME_GENRE_ID, # アニメに限定
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
            
            # APIが用意している最終ページに到達したら早めに抜ける
            if page >= data.get("total_pages", max_pages):
                print(" -> 最後のページに到達しました。")
                break
                
        except requests.exceptions.RequestException as e:
            print(f" ERROR: {e}")
            break
            
        time.sleep(1) # 1秒待機
        
    return all_items

def main():
    if not TMDB_API_KEY or TMDB_API_KEY == "your_api_key_here":
         print("エラー: APIキーが設定されていません。")
         return
         
    print("=== アニメ特化: 大量データ取得テストを開始します ===")
    
    # アニメ映画を最大50ページ (約1000件)
    anime_movies = fetch_pages("/discover/movie", "movie", max_pages=50)
    
    # アニメTV番組を最大50ページ (約1000件)
    anime_tv_shows = fetch_pages("/discover/tv", "tv", max_pages=50)
    
    # 既存の prime_video_all.json をあれば読み込む（データをどんどん継ぎ足して巨大な図鑑にするため）
    existing_data = []
    output_file = "prime_video_all.json"
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                print(f"既存のデータベース ({len(existing_data)}件) を読み込みました。")
        except:
            print("既存DBの読み込みに失敗したため、新規に上書きします。")

    # 全データを統合
    all_data = existing_data + anime_movies + anime_tv_shows
    
    # 重複排除 (同じIDなら弾く)
    unique_data = {f"{item['type']}_{item['id']}": item for item in all_data}.values()
    final_list = list(unique_data)
    
    # 人気順(popularity)で改めて全体をソート
    final_list.sort(key=lambda x: x["popularity"], reverse=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
        
    print("===========================================")
    print(f"取得完了: アニメデータを追加し、合計 {len(final_list)} 件の最新データベースが完成しました！")

if __name__ == "__main__":
    main()
