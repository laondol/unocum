import json, re
from datetime import datetime
from openai import OpenAI

GROQ_MODEL = "llama-3.3-70b-versatile"

def _groq_text(system, user, format_json=False, timeout=120):
    try:
        from flask import current_app
        key = current_app.config.get("GROQ_API_KEY", "")
        client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
        kwargs = {"model": GROQ_MODEL, "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ], "timeout": timeout}
        if format_json:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content
        return json.loads(content) if format_json else content
    except Exception as e:
        print(f"[NewsService] Groq 오류: {e}")
        return {} if format_json else None

def ai_search_news(news_type='world', trending_context=''):
    trending_note = ""
    if trending_context:
        trending_note = f"\n참고: 최근 회원들이 많이 추천한 인기 카테고리는 '{trending_context}'입니다. 이 주제들을 우선 고려하되, 항상 실제 존재하는 최신 뉴스만 제안하세요."
    if news_type == 'kr_yp':
        system = "당신은 경기 양평군민을 위한 국내 뉴스 큐레이터입니다. 반드시 실제 존재하는 최근 대한민국 뉴스 주제만 제안하세요. 절대 가짜를 만들지 마세요."
        prompt = f"""오늘 기준 실제 뉴스에서 찾을 수 있는, 경기 양평군민이 꼭 알아야 할 국내 뉴스 주제 10가지를 제안해 주세요.
각 항목은 네이버 뉴스 검색에 사용할 검색어로도 활용되므로 구체적인 키워드를 포함하세요.
{trending_note}
다음 JSON 배열 형식으로 출력하세요:
{{"news": [{{"title": "뉴스 검색용 구체적 키워드 (예: '정부 청년 일자리 지원 정책 2025', '경기도 농업인 재해보험 확대')", "summary": "한국어 3줄 요약", "reason": "양평군민에게 왜 중요한지", "category": "대한민국뉴스/양평소식/정책정보/지역소식 중 하나"}}]}}
중요: 절대 가짜 정보를 만들지 마세요. title은 네이버 뉴스 검색에 사용할 검색어이므로 실제 키워드여야 합니다."""
    else:
        system = "You are a world news curator for Yangpyeong County residents in South Korea. Select ONLY real, recent international news that practically affects their daily lives (food prices, farming, tourism, small business, climate, health). NEVER make up fake news."
        prompt = f"""Suggest 10 WORLD NEWS topics (international, non-Korean) that Yangpyeong residents should know about. 
Each topic must be an actual searchable English keyword.
{trending_note}
Output in JSON array format:
{{"news": [{{"title": "English search keyword for news lookup (e.g. 'FAO global food price index 2026', 'international coffee arabica price trend')", "summary": "한국어 3줄 요약 (Korean)", "reason": "양평군민 생활/자영업/농업/관광/물가와 연결되는 이유를 한국어로 구체적으로 (Korean)", "category": "세계뉴스/환경뉴스/건강정보/복지정보/농업정보/관광소식 중 하나"}}]}}
CRITICAL: NEVER make up fake news or fake URLs. title must be a real English search keyword that will find actual international articles on Google News. summary and reason in Korean."""
    result = _groq_text(system, prompt, format_json=True)
    if not result:
        return []
    try:
        return result.get("news", [])
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
    return _groq_text(system, prompt, format_json=True)

def ai_summarize_url(text):
    system = "당신은 기사 요약 전문가입니다. 한국어로 답변하세요. '본문바로가기','블로그','카테고리','검색','메뉴','이웃추가','공유하기','URL복사','신고하기','폰트크기' 등 블로그 UI/네비게이션 텍스트는 전부 무시하고, 오직 기사의 핵심 본문 내용만 요약하세요."
    prompt = f"""다음 웹페이지 내용 중 기사 본문만 골라 분석하여 양평군민에게 유용한 정보인지 판단하고 아래 JSON으로 출력하세요:
{{
  "title": "실제 기사 제목 (사이트명/블로그명 말고)",
  "summary": "핵심 내용 한국어 3줄 요약 (블로그 UI/버튼/메뉴 등은 완전히 제외하고 순수 기사 내용만)",
  "category": "분야 (대한민국뉴스/양평소식/정책정보/지역소식/세계뉴스/환경뉴스/건강정보/복지정보/농업정보/관광소식 중 하나)",
  "is_useful": true/false
}}
내용: {text[:3000]}"""
    return _groq_text(system, prompt, format_json=True)

def clean_cjk_text(title, summary='', content=''):
    """한자/일본어를 한국어로 변환. 불가피하면 괄호에 한국어 발음 추가."""
    texts = []
    if title: texts.append(f"제목: {title}")
    if summary: texts.append(f"요약: {summary}")
    if content: texts.append(f"본문: {content}")
    if not texts:
        return title, summary, content
    combined = '\n\n'.join(texts)
    system = "당신은 한국어 전문 편집자입니다. 다음 원칙을 따라 텍스트를 수정하세요:\n1. 모든 한자(중국 한자)는 한국어로 바꾸세요. (예: 幸福→행복, 大統領→대통령)\n2. 모든 일본어는 한국어로 바꾸세요.\n3. 불가피하게 한자/일본어를 써야 한다면, 바로 뒤 괄호에 한국어 발음을 추가하세요. (예: 東京(도쿄))\n4. 결과는 자연스러운 한국어로만 작성하세요.\n5. JSON 형식으로만 출력하세요."
    prompt = f"""다음 텍스트에서 한자와 일본어를 위 원칙대로 처리해 주세요:

{combined}

JSON 형식:
{{"title": "수정된 제목", "summary": "수정된 요약", "content": "수정된 본문"}}"""
    result = _groq_text(system, prompt, format_json=True)
    if not result:
        return title, summary, content
    return (
        result.get('title', title),
        result.get('summary', summary),
        result.get('content', content)
    )