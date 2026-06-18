import requests
import json
import re
import xml.etree.ElementTree as ET
from flask import current_app
from datetime import datetime, timedelta

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

def get_local_share_context(title, description, town, village, exclude_id=0):
    """같은 리(읍/면)의 다른 회원 공유마당 내용을 중심으로 지역 소식 생성"""
    if not town:
        return "특별한 내용이 없습니다.", "[]", []
    from models import ShareReport
    cutoff = datetime.now() - timedelta(days=30)
    nearby = ShareReport.query.filter(
        ShareReport.town == town,
        ShareReport.status == 'approved',
        ShareReport.id != exclude_id,
        ShareReport.created_at >= cutoff
    ).order_by(ShareReport.created_at.desc()).limit(10).all()
    if not nearby:
        return "특별한 내용이 없습니다.", "[]", []
    # 최대 3개 이미지 선정
    with_image = [s for s in nearby if s.image_path][:3]
    # AI 요약 생성
    context_lines = []
    for s in nearby[:5]:
        loc = f"{s.town} {s.village or ''}" if s.town else '위치미상'
        context_lines.append(f"- [{loc}] {s.title or '제목없음'}: {s.description or ''}")
    ai_text = "; ".join(context_lines)
    try:
        from openai import OpenAI
        key = current_app.config.get("GROQ_API_KEY", "")
        client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
        sys_p = "당신은 양평군 지역 공유 콘텐츠 큐레이터입니다. 아래 이웃주민들이 공유한 내용을 분석하여 2~3줄로 요약하세요. 같은 지역의 다양한 소식을 자연스럽게 연결하세요. 내용이 충분하지 않으면 '특별한 내용이 없습니다.'라고만 출력하세요."
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":sys_p},{"role":"user","content":f"양평군 {town} {village or ''} 지역 최근 공유 내용:\n{ai_text[:2000]}"}],
            timeout=30
        )
        summary = resp.choices[0].message.content.strip()
    except:
        summary = f"양평군 {town} {village or ''} 지역에 최근 공유된 소식입니다."
    ids_json = json.dumps([s.id for s in with_image], ensure_ascii=False)
    return summary, ids_json, [s.id for s in with_image]
