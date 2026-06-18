import requests, re, json, random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from flask import current_app

_cache = {}
_CACHE_TTL = timedelta(minutes=30)

SOURCES = [
    {"name": "YPN뉴스", "url": "https://www.ypnews.co.kr/", "type": "ypnews"},
    {"name": "양평시민의소리", "url": "https://www.ypsori.com/", "type": "ypsori"},
    {"name": "양평백운신문", "url": "http://www.ypnews.kr/", "type": "ypnewskr"},
]

def _scrape_ypnews():
    try:
        r = requests.get("https://www.ypnews.co.kr/", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        for a in soup.select("a[href*='/news/']")[:30]:
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            full_url = href if href.startswith("http") else f"https://www.ypnews.co.kr{href}"
            articles.append({"title": title, "url": full_url, "source": "YPN뉴스"})
        return articles
    except:
        return []

def _scrape_ypsori():
    try:
        r = requests.get("https://www.ypsori.com/", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        for a in soup.select("a[href*='/news/']")[:30]:
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            full_url = href if href.startswith("http") else f"https://www.ypsori.com{href}"
            articles.append({"title": title, "url": full_url, "source": "양평시민의소리"})
        return articles
    except:
        return []

def _scrape_ypnewskr():
    try:
        r = requests.get("http://www.ypnews.kr/", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        articles = []
        for a in soup.select("a[href*='/news/']")[:30]:
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            full_url = href if href.startswith("http") else f"http://www.ypnews.kr{href}"
            articles.append({"title": title, "url": full_url, "source": "양평백운신문"})
        return articles
    except:
        return []

def get_local_news(town=None, village=None):
    global _cache
    now = datetime.now()
    # refresh cache if expired
    if "articles" not in _cache or now - _cache.get("ts", now) > _CACHE_TTL:
        all_articles = []
        all_articles.extend(_scrape_ypnews())
        all_articles.extend(_scrape_ypsori())
        all_articles.extend(_scrape_ypnewskr())
        seen = set()
        unique = []
        for a in all_articles:
            if a["url"] not in seen:
                seen.add(a["url"])
                unique.append(a)
        _cache["articles"] = unique
        _cache["ts"] = now
    articles = _cache["articles"]
    if not town:
        return articles[:10]
    # score: same village +3, same town +2, 양평 match +1
    scored = []
    for a in articles:
        score = 0
        t = a["title"]
        if village and village in t:
            score += 3
        elif town and town in t:
            score += 2
        elif "양평" in t:
            score += 1
        if score > 0:
            scored.append((-score, a))
    scored.sort(key=lambda x: x[0])
    return [a for _, a in scored[:10]] or articles[:5]

def get_quick_links(town=None, village=None):
    links = [
        {"name": "YPN뉴스", "url": f"https://www.ypnews.co.kr/?s={town or '양평'}"},
        {"name": "양평시민의소리", "url": f"https://www.ypsori.com/?s={town or '양평'}"},
        {"name": "양평백운신문", "url": f"http://www.ypnews.kr/?s={town or '양평'}"},
        {"name": "양평농협", "url": "https://yp.nonghyup.com/user/indexSub.do?codyMenuSeq=6180662&siteId=yp"},
        {"name": "인스타그램", "url": "https://www.instagram.com/explore/tags/양평/"},
    ]
    return links

def get_nearby_heritage(lat, lng, max_km=5):
    import xml.etree.ElementTree as ET
    from math import radians, sin, cos, sqrt, atan2
    def _dist(lat1, lng1, lat2, lng2):
        R = 6371
        dlat = radians(lat2 - lat1)
        dlng = radians(lng2 - lng1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
        return R * 2 * atan2(sqrt(a), sqrt(1-a))
    try:
        r = requests.get("https://www.cha.go.kr/cha/SearchKindOpenapiList.do?pageUnit=1000&ccbaCtcd=31", timeout=15)
        root = ET.fromstring(r.content)
        items = root.findall(".//item")
        nearby = []
        for item in items:
            try:
                ilat = float(item.findtext("latitude", "0") or "0")
                ilng = float(item.findtext("longitude", "0") or "0")
                if ilat == 0 or ilng == 0:
                    continue
                d = _dist(lat, lng, ilat, ilng)
                if d <= max_km:
                    name = item.findtext("ccbaMnm1", "")
                    ctype = item.findtext("ccmaName", "")
                    city = item.findtext("ccsiName", "")
                    nearby.append({"name": name, "type": ctype, "city": city, "lat": round(ilat, 6), "lng": round(ilng, 6), "dist": round(d, 1)})
            except: pass
        nearby.sort(key=lambda x: x["dist"])
        return nearby[:10]
    except:
        return []
