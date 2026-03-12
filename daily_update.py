#!/usr/bin/env python3
"""
Prime Video 日次更新パイプライン
================================
1. TMDBから全ジャンルデータを取得
2. メタデータ（年齢制限・ランキング）を付与
3. 日付つきJSONとしてdeployフォルダに保存
4. manifest.jsonを更新（利用可能な日付リスト）
5. Netlify APIで自動デプロイ

使い方:
  python3 daily_update.py                    # ローカル実行（デプロイなし）
  python3 daily_update.py --deploy           # ローカル実行 + Netlifyデプロイ
  NETLIFY_TOKEN=xxx NETLIFY_SITE_ID=xxx python3 daily_update.py --deploy  # CI用
"""

import os
import sys
import time
import json
import glob
import requests
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# === 設定 ===
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
PRIME_VIDEO_PROVIDER_ID = 9
ANIME_GENRE_ID = 16
API_DELAY = 0.5  # 1秒に2回（安全かつ高速）

DEPLOY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "netlify_deploy")
DATA_DIR = os.path.join(DEPLOY_DIR, "data")

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
    all_items = []
    for page in range(1, max_pages + 1):
        print(f"  [{item_type}] {genre_name} p{page}", end="", flush=True)
        params = {
            "api_key": TMDB_API_KEY, "language": "ja-JP", "region": "JP",
            "with_watch_providers": PRIME_VIDEO_PROVIDER_ID, "watch_region": "JP",
            "with_genres": str(genre_id), "sort_by": "popularity.desc", "page": page
        }
        try:
            r = requests.get(f"{TMDB_BASE_URL}{endpoint}", params=params)
            r.raise_for_status()
            data = r.json()
            results = data.get("results", [])
            for item in results:
                all_items.append({
                    "id": item.get("id"), "type": item_type,
                    "title": item.get("title") or item.get("name") or "不明",
                    "release_date": item.get("release_date") or item.get("first_air_date") or "",
                    "poster_path": item.get("poster_path"),
                    "vote_average": item.get("vote_average", 0),
                    "vote_count": item.get("vote_count", 0),
                    "popularity": item.get("popularity", 0),
                    "genre_ids": item.get("genre_ids", []),
                    "adult": item.get("adult", False)
                })
            print(f" ({len(results)})")
            if page >= data.get("total_pages", max_pages) or page >= 500:
                break
        except requests.exceptions.RequestException as e:
            print(f" ERROR: {e}")
            break
        time.sleep(API_DELAY)
    return all_items


def fetch_certification_ids(endpoint, cert_level):
    all_ids = set()
    page = 1
    while True:
        params = {
            "api_key": TMDB_API_KEY, "language": "ja-JP", "region": "JP",
            "with_watch_providers": PRIME_VIDEO_PROVIDER_ID, "watch_region": "JP",
            "certification_country": "JP", "certification": cert_level, "page": page
        }
        try:
            r = requests.get(f"{TMDB_BASE_URL}{endpoint}", params=params)
            r.raise_for_status()
            data = r.json()
            for item in data.get("results", []):
                all_ids.add(item.get("id"))
            if page >= data.get("total_pages", page):
                break
            page += 1
            time.sleep(API_DELAY)
        except:
            break
    return all_ids


def step1_fetch_all():
    """全ジャンルのデータを取得"""
    print("\n=== STEP 1: 全ジャンルデータ取得 ===")
    all_data = []
    for gid, gname in MOVIE_GENRES.items():
        all_data.extend(fetch_pages("/discover/movie", "movie", gid, gname))
        time.sleep(1)
    for gid, gname in TV_GENRES.items():
        all_data.extend(fetch_pages("/discover/tv", "tv", gid, gname))
        time.sleep(1)

    unique = {f"{i['type']}_{i['id']}": i for i in all_data}.values()
    data = sorted(unique, key=lambda x: x["popularity"], reverse=True)
    print(f"取得完了: {len(all_data)}件 → 重複除去後 {len(data)}件")
    return list(data)


def step2_add_metadata(data):
    """年齢制限・ランキング・新作タグの付与"""
    print("\n=== STEP 2: メタデータ付与 ===")
    print("年齢制限の逆引き中...")
    certs = {}
    for ep, typ in [("/discover/movie", "movie"), ("/discover/tv", "tv")]:
        for cert in ["PG12", "R15+", "R18+"]:
            ids = fetch_certification_ids(ep, cert)
            certs[f"{typ}_{cert}"] = ids
            print(f"  {typ} {cert}: {len(ids)}件")

    thirty = datetime.now() - timedelta(days=30)
    ninety = datetime.now() - timedelta(days=90)
    anime_rank = 1

    for i, item in enumerate(data):
        item["rank_overall"] = i + 1
        if ANIME_GENRE_ID in item.get("genre_ids", []):
            item["rank_anime"] = anime_rank
            anime_rank += 1
        else:
            item["rank_anime"] = None

        cert = "G"
        t, iid = item["type"], item["id"]
        if iid in certs.get(f"{t}_R18+", set()) or item.get("adult"):
            cert = "R18+"
        elif iid in certs.get(f"{t}_R15+", set()):
            cert = "R15+"
        elif iid in certs.get(f"{t}_PG12", set()):
            cert = "PG12"
        item["certification"] = cert

        item["release_status"] = "OLD"
        rd = item.get("release_date", "")
        if rd and len(rd) >= 10:
            try:
                d = datetime.strptime(rd[:10], "%Y-%m-%d")
                if d >= thirty:
                    item["release_status"] = "NEW"
                elif d >= ninety:
                    item["release_status"] = "SEMI_NEW"
            except ValueError:
                pass

    print(f"メタデータ付与完了。アニメ1位: {[x['title'] for x in data if x.get('rank_anime')==1]}")
    return data


def step3_save_and_manifest(data, today_str):
    """日付つきJSONを保存し、manifest.jsonを更新"""
    print("\n=== STEP 3: 保存 & マニフェスト更新 ===")
    os.makedirs(DATA_DIR, exist_ok=True)

    # 日付つきJSONを保存
    daily_file = os.path.join(DATA_DIR, f"{today_str}.json")
    with open(daily_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"保存: {daily_file} ({os.path.getsize(daily_file) / 1024 / 1024:.1f}MB)")

    # 最新版もルートに置く（初回アクセス用）
    latest_file = os.path.join(DEPLOY_DIR, "prime_video_ultimate.json")
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    # manifest.json を生成（利用可能な全日付）
    existing_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")), reverse=True)
    dates = [os.path.basename(f).replace(".json", "") for f in existing_files]
    manifest = {"latest": today_str, "dates": dates, "total_items": len(data)}
    manifest_file = os.path.join(DEPLOY_DIR, "manifest.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"manifest.json 更新: {len(dates)}日分のデータ")


def step4_deploy():
    """Netlify APIで自動デプロイ"""
    print("\n=== STEP 4: Netlifyデプロイ ===")
    token = os.environ.get("NETLIFY_TOKEN", "")
    site_id = os.environ.get("NETLIFY_SITE_ID", "")
    if not token or not site_id:
        print("NETLIFY_TOKEN / NETLIFY_SITE_ID が未設定。デプロイをスキップします。")
        return False

    # netlify_deploy フォルダ内のファイルを収集
    files_to_deploy = {}
    for root, dirs, files in os.walk(DEPLOY_DIR):
        for fname in files:
            full_path = os.path.join(root, fname)
            rel_path = "/" + os.path.relpath(full_path, DEPLOY_DIR)
            with open(full_path, "rb") as f:
                sha1 = hashlib.sha1(f.read()).hexdigest()
            files_to_deploy[rel_path] = sha1

    # Step 1: デプロイの作成（ファイルハッシュを送信）
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(
        f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
        headers=headers, json={"files": files_to_deploy}
    )
    resp.raise_for_status()
    deploy = resp.json()
    deploy_id = deploy["id"]
    required = deploy.get("required", [])
    print(f"デプロイID: {deploy_id} / アップロード必要ファイル数: {len(required)}")

    # Step 2: 必要なファイルだけアップロード
    sha_to_path = {}
    for root, dirs, files in os.walk(DEPLOY_DIR):
        for fname in files:
            full_path = os.path.join(root, fname)
            rel_path = "/" + os.path.relpath(full_path, DEPLOY_DIR)
            with open(full_path, "rb") as f:
                content = f.read()
            sha1 = hashlib.sha1(content).hexdigest()
            sha_to_path[sha1] = (full_path, rel_path)

    for sha in required:
        if sha in sha_to_path:
            full_path, rel_path = sha_to_path[sha]
            with open(full_path, "rb") as f:
                content = f.read()
            upload_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/octet-stream"
            }
            upload_resp = requests.put(
                f"https://api.netlify.com/api/v1/deploys/{deploy_id}/files{rel_path}",
                headers=upload_headers, data=content
            )
            upload_resp.raise_for_status()
            print(f"  アップロード: {rel_path} ({len(content)/1024:.0f}KB)")

    print(f"デプロイ完了！ https://eclectic-mermaid-0e1ebd.netlify.app")
    return True


def main():
    if not TMDB_API_KEY:
        print("エラー: TMDB_API_KEY が設定されていません。")
        sys.exit(1)

    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"===== Prime Video 日次更新 ({today_str}) =====")

    data = step1_fetch_all()
    data = step2_add_metadata(data)
    step3_save_and_manifest(data, today_str)

    # index.html もコピー
    src_html = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.html")
    dst_html = os.path.join(DEPLOY_DIR, "index.html")
    if os.path.exists(src_html):
        import shutil
        shutil.copy2(src_html, dst_html)

    if "--deploy" in sys.argv:
        step4_deploy()
    else:
        print("\n※ --deploy フラグなし。Netlifyへのデプロイはスキップしました。")

    print(f"\n===== 完了 ({today_str}) =====")


if __name__ == "__main__":
    main()
