import requests
import json
import re
import xml.etree.ElementTree as ET
from flask import current_app

NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?hl=ko&gl=KR&ceid=KR:ko"

def search_naver_news(query, display=5):
    client_id = current_app.config.get('NAVER_SEARCH_CLIENT_ID', '')
    client_secret = current_app.config.get('NAVER_SEARCH_CLIENT_SECRET', '')
    if not client_id or not client_secret:
        return []
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {
        "query": query,
        "display": min(display, 10),
        "sort": "date",
    }
    try:
        res = requests.get(NAVER_NEWS_URL, headers=headers, params=params, timeout=10)
        if res.status_code != 200:
            return []
        data = res.json()
        items = data.get('items', [])
        results = []
        for item in items:
            title = re.sub(r'<[^>]+>', '', item.get('title', ''))
            description = re.sub(r'<[^>]+>', '', item.get('description', ''))
            results.append({
                "title": title,
                "description": description,
                "url": item.get('link', ''),
                "pubDate": item.get('pubDate', ''),
            })
        return results
    except Exception as e:
        return []

def search_google_news(query, display=5, language='ko'):
    try:
        hl = 'ko' if language == 'ko' else 'en'
        gl = 'KR' if language == 'ko' else 'US'
        url = f"https://news.google.com/rss/search?hl={hl}&gl={gl}&ceid={gl}:{hl}&q={requests.utils.quote(query)}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if res.status_code != 200:
            return []
        root = ET.fromstring(res.content)
        items = root.findall('.//item')
        results = []
        for item in items[:display]:
            title = (item.findtext('title', '') or '').strip()
            link = (item.findtext('link', '') or '').strip()
            desc = (item.findtext('description', '') or '').strip()
            pub_date = (item.findtext('pubDate', '') or '').strip()
            results.append({
                "title": re.sub(r'<[^>]+>', '', title),
                "description": re.sub(r'<[^>]+>', '', desc)[:200],
                "url": link,
                "pubDate": pub_date,
            })
        return results
    except Exception as e:
        return []

def search_news(query, display=5, language='ko'):
    results = search_naver_news(query, display)
    source = '네이버뉴스'
    if not results:
        results = search_google_news(query, display, language=language)
        source = '구글뉴스'
    return results, source

def build_news_query(title, description, town, village):
    keywords = []
    if title:
        keywords.append(title)
    if description:
        short_desc = description[:50]
        keywords.append(short_desc)
    if town:
        keywords.append(f"양평 {town} {village or ''}")
    else:
        keywords.append("양평군")
    base = " ".join(keywords)
    return base.strip()

def get_news_for_share(title, description, town, village):
    query = build_news_query(title, description, town, village)
    items, _ = search_news(query, display=5, language='ko')
    if items:
        summary = "; ".join([f"{i['title']}" for i in items[:3]])
        links = json.dumps([{"title": i['title'], "url": i['url']} for i in items], ensure_ascii=False)
        return summary, links
    return None, "[]"
