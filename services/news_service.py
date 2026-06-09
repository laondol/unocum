import requests, json, re
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "exaone3.5"

def _call_ollama(prompt, system="", format_json=False):
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    if system:
        payload["system"] = system
    if format_json:
        payload["format"] = "json"
    try:
        res = requests.post(OLLAMA_URL, json=payload, timeout=120)
        return res.json().get("response", "")
    except Exception as e:
        print(f"[NewsService] Ollama 오류: {e}")
        return None

def ai_search_news():
    system = "당신은 경기도 여주·양평군민을 위한 세계뉴스 큐레이터입니다."
    prompt = """오늘 기준으로 경기도 여주·양평 지역 주민들에게 도움이 될 만한 세계 뉴스 10가지를 추천해 주세요.
각 뉴스는 다음 JSON 배열 형식으로 출력하세요:
{"news": [{"title": "뉴스제목", "summary": "한국어 3줄 요약", "reason": "양평군민에게 왜 중요한지", "category": "분야(환경/경제/복지/농업/관광/기술/건강/문화)", "url": "해당 뉴스의 원본 기사 URL (https://...)"}]}
반드시 실제 존재하는 기사 URL을 기입하세요. 뉴스는 반드시 실제 최근 세계에서 일어난 이슈여야 하며, 양평군민의 생활, 농업, 관광, 소상공인, 환경, 복지와 관련성이 높은 것을 선별하세요."""
    result = _call_ollama(prompt, system, format_json=True)
    if not result:
        return []
    try:
        data = json.loads(result)
        return data.get("news", [])
    except:
        return []

def ai_translate_and_format(title, content, source_lang="en"):
    system = f"당신은 전문 번역가입니다. {source_lang}를 한국어(경기 양평 방언 포함)로 자연스럽게 번역하고, 기사 형식으로 정리해 주세요."
    prompt = f"""다음 기사를 한국어로 번역하고, 아래 JSON 형식으로 출력하세요:
{{
  "title": "번역된 제목",
  "summary": "3줄 요약",
  "content": "본문 내용 (HTML <p>태그로 감싼 문단들)"
}}
원본 제목: {title}
원본 내용: {content[:3000]}"""
    result = _call_ollama(prompt, system, format_json=True)
    if not result:
        return None
    try:
        return json.loads(result)
    except:
        return None

def ai_summarize_url(text):
    system = "당신은 기사 요약 전문가입니다. 한국어로 답변하세요."
    prompt = f"""다음 웹페이지 내용을 분석하여 양평군민에게 유용한 정보인지 판단하고 아래 JSON으로 출력하세요:
{{
  "title": "추출한 제목",
  "summary": "한국어 3줄 요약",
  "category": "분야",
  "is_useful": true/false
}}
내용: {text[:4000]}"""
    result = _call_ollama(prompt, system, format_json=True)
    if not result:
        return None
    try:
        return json.loads(result)
    except:
        return None
