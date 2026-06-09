import requests
import json
from datetime import datetime, timedelta
from models import db, Post, User

# 1. 1차 심사 AI 호출 (EXAONE 3.5)
def call_ai_judge(title, content, is_comment=False):
    url = "http://localhost:11434/api/generate"
    role = "댓글 방역 지킴이" if is_comment else "공동체 자치 지킴이"
    system_prompt = f"""당신은 '함께사는양평' {role}입니다. 반드시 한국어로 JSON 형식으로만 대답하세요.
    양식: {{"score": 숫자(-50~50), "category": "8대사회권분야", "summary": "3줄요약", "reason": "이유", "improvement_tip": "제안 보완을 위해 주민에게 제시할 대안 1가지"}}"""
    
    full_text = f"제목: {title}\n본문: {content}" if not is_comment else content
    try:
        res = requests.post(url, json={
            "model": "exaone3.5", "prompt": f"{system_prompt}\n분석대상: {full_text}",
            "stream": False, "format": "json"
        }, timeout=60)
        data = json.loads(res.json()['response'])
        data['score'] = max(-50, min(50, int(data.get('score', 0))))
        return data
    except Exception as e:
        print(f"AI 심사 에러: {e}")
        return {"score": 0, "category": "일반", "summary": "분석 일시 지연", "reason": "지연", "improvement_tip": "내용을 구체화 해보세요."}

# 2. 관리자-AI 토론 호출
def call_ai_debate(post, admin_opinion, suggested_score):
    url = "http://localhost:11434/api/generate"
    debate_prompt = f"""당신은 자치 지킴이 AI입니다. 관리자가 '{admin_opinion}'의 논리로 점수를 {suggested_score}점으로 조정을 요청했습니다.
    검토 후 정중한 답변과 최종 점수를 합의하여 JSON {{"ai_reply": "답변", "final_ai_score": 점수}}로 출력하세요. 점수 범위는 -50~50입니다."""
    try:
        res = requests.post(url, json={"model": "exaone3.5", "prompt": debate_prompt, "stream": False, "format": "json"}, timeout=120)
        result = json.loads(res.json()['response'])
        result['final_ai_score'] = max(-50, min(50, int(result.get('final_ai_score', suggested_score))))
        return result
    except:
        return {"ai_reply": "토론 지연 발생", "final_ai_score": post.ai_score}

# 3. 비동기 멀티스레드 심사 파이프라인 (0.1초 즉시 저장용)
def background_ai_judge(app, post_id):
    with app.app_context():
        post = Post.query.get(post_id)
        if not post: return

        print(f"[BG AI] {post.title} analysis started...")
        ai_res = call_ai_judge(post.title, post.content)
        
        post.ai_score = ai_res.get('score', 0)
        post.total_score = post.ai_score + post.admin_score + post.leader_score + post.member_score
        post.ai_category = ai_res.get('category', '일반제안')
        post.ai_summary = ai_res.get('summary', '요약 완료')
        post.ai_reason = ai_res.get('reason', '분석 완료')
        post.ai_improvement_tip = ai_res.get('improvement_tip', '보안 계획을 보완해 보세요.')
        
        if post.total_score <= -50:
            user = User.query.get(post.user_id)
            if user:
                user.points -= 100
                post.deadline = datetime.now() + timedelta(days=30)
                
        db.session.commit()
        print(f"[BG AI] {post.title} analysis complete, DB updated.")