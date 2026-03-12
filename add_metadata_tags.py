import os
import time
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
PRIME_VIDEO_PROVIDER_ID = 9 # Amazon Prime Video JP
ANIME_GENRE_ID = 16

def fetch_certification_ids(endpoint, cert_level):
    """特定の年齢制限（PG12, R15+等）を持つ作品のIDリストを取得する"""
    print(f"[{endpoint}] {cert_level}指定の作品を逆引き検索中...")
    all_ids = set()
    page = 1
    
    while True:
        params = {
            "api_key": TMDB_API_KEY,
            "language": "ja-JP",
            "region": "JP",
            "with_watch_providers": PRIME_VIDEO_PROVIDER_ID,
            "watch_region": "JP",
            "certification_country": "JP",
            "certification": cert_level,
            "page": page
        }
        
        url = f"{TMDB_BASE_URL}{endpoint}"
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            for r in data.get("results", []):
                all_ids.add(r.get("id"))
                
            total_pages = data.get("total_pages", page)
            if page >= total_pages:
                break
                
            page += 1
            time.sleep(0.5) # API制限回避
            
        except requests.exceptions.RequestException as e:
            print(f" ERROR: {e}")
            break
            
    print(f" -> {len(all_ids)}件 のIDを抽出しました。")
    return all_ids

def main():
    db_file = "prime_video_ultimate.json"
    if not os.path.exists(db_file):
        print(f"エラー: {db_file} が見つかりません。")
        return

    print("=== 巨大変換スクリプト（メタデータ付与）開始 ===")
    
    with open(db_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"データベース読み込み完了: {len(data)}件")

    # --- 1. 年齢制限の逆引き抽出 ---
    pg12_movie_ids = fetch_certification_ids("/discover/movie", "PG12")
    r15_movie_ids = fetch_certification_ids("/discover/movie", "R15+")
    r18_movie_ids = fetch_certification_ids("/discover/movie", "R18+")
    
    pg12_tv_ids = fetch_certification_ids("/discover/tv", "PG12")
    r15_tv_ids = fetch_certification_ids("/discover/tv", "R15+")
    r18_tv_ids = fetch_certification_ids("/discover/tv", "R18+")
    
    # --- 2. メタデータの計算と付与 ---
    thirty_days_ago = datetime.now() - timedelta(days=30)
    ninety_days_ago = datetime.now() - timedelta(days=90)
    
    # 全体を人気順で再ソート（念のため）
    data.sort(key=lambda x: x.get("popularity", 0), reverse=True)
    
    # アニメの人気順ランキング用カウンター
    anime_counter = 1
    
    print("各作品にタグとランキングを付与しています...")
    for i, item in enumerate(data):
        item_id = item["id"]
        item_type = item["type"]
        
        # 全体ランキング
        item["rank_overall"] = i + 1
        
        # アニメランキング
        if ANIME_GENRE_ID in item.get("genre_ids", []):
            item["rank_anime"] = anime_counter
            anime_counter += 1
        else:
            item["rank_anime"] = None
            
        # 年齢制限判定
        cert = "G" # デフォルトは全年齢
        if item_type == "movie":
            if item_id in r18_movie_ids or item.get("adult") == True: cert = "R18+"
            elif item_id in r15_movie_ids: cert = "R15+"
            elif item_id in pg12_movie_ids: cert = "PG12"
        elif item_type == "tv":
            if item_id in r18_tv_ids or item.get("adult") == True: cert = "R18+"
            elif item_id in r15_tv_ids: cert = "R15+"
            elif item_id in pg12_tv_ids: cert = "PG12"
            
        item["certification"] = cert
        
        # 新作判定 (リリース日が30日以内ならNEW、90日以内ならSEMI-NEW)
        item["release_status"] = "OLD"
        rel_date_str = item.get("release_date")
        if rel_date_str:
            try:
                # 'YYYY-MM-DD' を判定
                # 時々 'YYYY' だけの場合があるのでパースに失敗したら無視
                if len(rel_date_str) >= 10:
                    rel_date = datetime.strptime(rel_date_str[:10], "%Y-%m-%d")
                    if rel_date >= thirty_days_ago:
                        item["release_status"] = "NEW"
                    elif rel_date >= ninety_days_ago:
                        item["release_status"] = "SEMI_NEW"
            except ValueError:
                pass
                
    # --- 3. 保存 ---
    with open(db_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"メタデータ付与完了！上書き保存しました。")
    print(f"1位のアニメ: {[x['title'] for x in data if x.get('rank_anime') == 1]}")
    print("==============================================")

if __name__ == "__main__":
    main()
