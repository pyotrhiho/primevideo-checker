import os
from datetime import datetime

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prime Video Checker - Report</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --accent: #0ea5e9;
            --danger: #ef4444;
            --new: #10b981;
            --anime: #ec4899;
            --safe: #8b5cf6;
            --star: #fbbf24;
        }}
        body {{
            font-family: 'Inter', 'Segoe UI', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 2rem;
        }}
        h1 {{
            text-align: center;
            font-weight: 800;
            margin-bottom: 0.5rem;
            color: var(--accent);
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .section-title {{
            font-size: 1.5rem;
            margin-top: 3rem;
            margin-bottom: 1rem;
            border-bottom: 2px solid var(--card-bg);
            padding-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .badge {{
            font-size: 0.8rem;
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            font-weight: bold;
        }}
        .bg-new {{ background-color: var(--new); color: white; }}
        .bg-popular {{ background-color: var(--accent); color: white; }}
        .bg-anime {{ background-color: var(--anime); color: white; }}
        .bg-safe {{ background-color: var(--safe); color: white; }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1.5rem;
        }}
        .card {{
            background-color: var(--card-bg);
            border-radius: 12px;
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
            display: block;
            position: relative;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.3);
        }}
        .thumbnail {{
            width: 100%;
            height: 300px;
            background-color: #334155;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-sub);
            position: relative;
        }}
        .thumbnail img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .info {{
            padding: 1rem;
        }}
        .title {{
            font-weight: bold;
            font-size: 1.1rem;
            margin: 0 0 0.5rem 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .meta {{
            font-size: 0.85rem;
            color: var(--text-sub);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .rating {{
            display: flex;
            align-items: center;
            gap: 0.2rem;
            color: var(--star);
            font-weight: bold;
        }}
        .rating-count {{
            color: var(--text-sub);
            font-size: 0.75rem;
            font-weight: normal;
        }}
        .note {{
            text-align: center;
            color: var(--text-sub);
            margin-bottom: 2rem;
            font-size: 0.9rem;
        }}
        .tmdb-attribution {{
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-sub);
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid var(--card-bg);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Prime Video Scanner Report</h1>
        <p class="note">Generated at: {timestamp}</p>

        <h2 class="section-title">
            <span class="badge bg-new">NEW</span>
            最近追加された作品
        </h2>
        <div class="grid">
            {new_items_html}
        </div>

        <h2 class="section-title">
            <span class="badge bg-popular">HOT</span>
            現在人気の作品
        </h2>
        <div class="grid">
            {popular_items_html}
        </div>

        <h2 class="section-title">
            <span class="badge bg-anime">ANIME</span>
            人気のアニメ作品
        </h2>
        <div class="grid">
            {anime_items_html}
        </div>

        <h2 class="section-title">
            <span class="badge bg-safe">SAFE</span>
            全年齢対象(PG12・R15除外)の映画
        </h2>
        <div class="grid">
            {family_safe_items_html}
        </div>
        
        <div class="tmdb-attribution">
            This product uses the TMDB API but is not endorsed or certified by TMDB.
        </div>
    </div>
</body>
</html>
"""

def generate_card_html(item):
    title = item.get("title", "タイトル不明")
    if not title:
        title = item.get("name", "タイトル不明")
        
    release_date = item.get("release_date", "")
    if not release_date:
        release_date = item.get("first_air_date", "")
        
    year = release_date.split("-")[0] if release_date else "----"
    
    poster_path = item.get("poster_path")
    image_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
    
    rating = item.get("vote_average", 0)
    vote_count = item.get("vote_count", 0)
    
    # 検索用リンク (Amazon Prime Videoで検索)
    search_query = title.replace(" ", "+")
    link_url = f"https://www.amazon.co.jp/s?k={search_query}&i=instant-video"

    image_html = f'<img src="{image_url}" alt="{title}">' if image_url else '画像なし'
    
    return f"""
    <a href="{link_url}" target="_blank" class="card">
        <div class="thumbnail">
            {image_html}
        </div>
        <div class="info">
            <h3 class="title" title="{title}">{title}</h3>
            <div class="meta">
                <span>{year}</span>
                <span class="rating">★ {rating:.1f} <span class="rating-count">({vote_count})</span></span>
            </div>
        </div>
    </a>
    """

def create_report(new_data, popular_data, anime_data, family_safe_data, output_file="prime_video_report.html"):
    new_items_html = ""
    if new_data and "results" in new_data:
        for item in new_data["results"][:12]:
            new_items_html += generate_card_html(item)
            
    popular_items_html = ""
    if popular_data and "results" in popular_data:
        for item in popular_data["results"][:12]:
            popular_items_html += generate_card_html(item)
            
    anime_items_html = ""
    if anime_data and "results" in anime_data:
        for item in anime_data["results"][:12]:
            anime_items_html += generate_card_html(item)

    family_safe_items_html = ""
    if family_safe_data and "results" in family_safe_data:
        for item in family_safe_data["results"][:12]:
            family_safe_items_html += generate_card_html(item)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    final_html = HTML_TEMPLATE.format(
        timestamp=now,
        new_items_html=new_items_html,
        popular_items_html=popular_items_html,
        anime_items_html=anime_items_html,
        family_safe_items_html=family_safe_items_html
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    print(f"HTMLレポートを生成しました: {output_file}")
    return output_file
