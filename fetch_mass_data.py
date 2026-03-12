import os
import time
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
PRIME_VIDEO_PROVIDER_ID = 9 # Amazon Prime Video JP

def fetch_pages(endpoint, item_type, max_pages=25):
    """複数ページのデータを取得する"""
    all_items = []
    
    for page in range(1, max_pages + 1):
        print(f"取得中: {item_type} - ページ {page}/{max_pages} ...", end="", flush=True)
        params = {
            "api_key": TMDB_API_KEY,
            "language": "ja-JP",
            "region": "JP",
            "with_watch_providers": PRIME_VIDEO_PROVIDER_ID,
            "watch_region": "JP",
            "sort_by": "popularity.desc", # 人気順で取得
            "page": page
        }
        
        url = f"{TMDB_BASE_URL}{endpoint}"
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            for r in results:
                # 映画とTVで共通のフォーマットにするため少し加工する
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
            
        except requests.exceptions.RequestException as e:
            print(f" ERROR: {e}")
            break # エラーが出たらループを抜ける
            
        # 【重要】APIの利用制限を考慮して1秒待機する（ユーザーが実際に体験する負荷テスト）
        time.sleep(1)
        
    return all_items

def main():
    if not TMDB_API_KEY or TMDB_API_KEY == "your_api_key_here":
         print("エラー: APIキーが設定されていません。")
         return
         
    print("=== 大量データ取得テストを開始します ===")
    print("注意: 1秒に1回の制限を設けているため、約50秒かかります。")
    
    # 映画を25ページ (約500件)
    movies = fetch_pages("/discover/movie", "movie", max_pages=25)
    
    # TV番組を25ページ (約500件)
    tv_shows = fetch_pages("/discover/tv", "tv", max_pages=25)
    
    # 重複排除 (同じIDなら弾く) - 基本は被らないが念の為
    all_data = movies + tv_shows
    unique_data = {f"{item['type']}_{item['id']}": item for item in all_data}.values()
    final_list = list(unique_data)
    
    # 人気順(popularity)で改めて全体をソート
    final_list.sort(key=lambda x: x["popularity"], reverse=True)
    
    output_file = "prime_video_all.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
        
    print("===========================================")
    print(f"取得完了: 合計 {len(final_list)} 件のデータを保存しました！")
    print(f"ファイル: {output_file}")
    
    # HTMLアプリを開くための準備完了メッセージ
    print("\n次は「app.html」をブラウザで開いて、このJSONデータを高速で表示・絞り込みするテストをします。")

if __name__ == "__main__":
    main()
