import random, string
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, current_app
from models import db, User, TongBot, TongBotDraft, TongBotSchedule
from datetime import datetime
import os, uuid

tongbot_bp = Blueprint('tongbot', __name__)

def _get_bot(user_id):
    bot = TongBot.query.filter_by(user_id=user_id).first()
    if not bot:
        uid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        bid = f"A-{uid}"
        while TongBot.query.filter_by(bot_id=bid).first():
            uid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            bid = f"A-{uid}"
        bot = TongBot(user_id=user_id, bot_id=bid, bot_name=bid)
        db.session.add(bot)
        db.session.commit()
    return bot

@tongbot_bp.route('/user/my')
def my_page():
    if not session.get('user_id'):
        return redirect(url_for('login', next='/user/my'))
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('login'))
    bot = _get_bot(user.id)
    drafts = TongBotDraft.query.filter_by(user_id=user.id).order_by(TongBotDraft.updated_at.desc()).limit(20).all()
    schedules = TongBotSchedule.query.filter_by(user_id=user.id).order_by(TongBotSchedule.event_date.desc()).limit(10).all()
    stamps_count = 0
    try:
        from models import HeritageStamp
        stamps_count = HeritageStamp.query.filter_by(user_id=user.id).count()
    except: pass
    return render_template('user_my.html', user=user, bot=bot, drafts=drafts, schedules=schedules, stamps_count=stamps_count)

@tongbot_bp.route('/api/bot/rename', methods=['POST'])
def bot_rename():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    new_name = request.json.get('name', '').strip()
    if not new_name or len(new_name) < 2 or len(new_name) > 20:
        return jsonify({"error": "이름은 2~20자로 입력해 주세요."})
    if not new_name.replace('_','').replace('-','').isalnum() and not any(c.isalpha() for c in new_name):
        return jsonify({"error": "한글/영문/숫자/-/_ 만 사용 가능합니다."})
    existing = TongBot.query.filter_by(bot_name=new_name).first()
    if existing and existing.user_id != uid:
        return jsonify({"error": "이미 다른 회원이 사용 중인 이름입니다."})
    bot = _get_bot(uid)
    bot.bot_name = new_name
    bot.updated_at = datetime.now()
    db.session.commit()
    return jsonify({"success": True, "name": new_name})

@tongbot_bp.route('/api/bot/chat', methods=['POST'])
def bot_chat():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    msg = request.json.get('message', '').strip()
    if not msg:
        return jsonify({"error": "메시지를 입력하세요."})
    bot = _get_bot(uid)
    user = User.query.get(uid)
    reply = _ai_reply(bot, user, msg)
    return jsonify({"reply": reply, "bot_name": bot.bot_name})

def _ai_reply(bot, user, user_msg):
    try:
        from config import Config
        import requests
        key = getattr(Config, 'GROQ_API_KEY', '')
        if not key:
            return f"안녕하세요, {user.username}님! 저는 {bot.bot_name}입니다. 어떤 도움이 필요하신가요?"
        prompt = f"""당신은 '{bot.bot_name}'이라는 이름의 AI 도우미입니다. 회원 이름은 '{user.username}'입니다.
당신은 함께사는양평 커뮤니티에서 활동을 돕는 개인 비서입니다.
친근하고 따뜻한 말투로 답변하세요. 답변은 2~3문장으로 간결하게.

회원 메시지: {user_msg}"""
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "max_tokens": 300},
            timeout=20)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"{user.username}님, 지금은 응답하기 어렵네요. 잠시 후 다시 시도해 주세요."
    except:
        return f"{user.username}님, 무엇을 도와드릴까요?"

@tongbot_bp.route('/api/bot/draft', methods=['GET', 'POST'])
def bot_draft():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    if request.method == 'GET':
        draft_id = request.args.get('id', type=int)
        if draft_id:
            draft = TongBotDraft.query.get(draft_id)
            if draft and draft.user_id == uid:
                return jsonify({"id": draft.id, "title": draft.title, "content": draft.content, "category": draft.category, "status": draft.status, "bot_review": draft.bot_review, "bot_suggestion": draft.bot_suggestion})
            return jsonify({"error": "찾을 수 없습니다."}), 404
        drafts = TongBotDraft.query.filter_by(user_id=uid).order_by(TongBotDraft.updated_at.desc()).limit(20).all()
        return jsonify({"drafts": [{"id": d.id, "title": d.title, "category": d.category, "status": d.status, "content": d.content, "updated_at": d.updated_at.strftime("%m/%d %H:%M") if d.updated_at else ""} for d in drafts]})
    data = request.json
    draft_id = data.get('id')
    if draft_id:
        draft = TongBotDraft.query.get(draft_id)
        if not draft or draft.user_id != uid:
            return jsonify({"error": "권한이 없습니다."}), 403
        draft.title = data.get('title', draft.title)
        draft.content = data.get('content', draft.content)
        draft.category = data.get('category', draft.category)
        draft.status = data.get('status', draft.status)
        draft.updated_at = datetime.now()
    else:
        draft = TongBotDraft(user_id=uid, title=data.get('title',''), content=data.get('content',''), category=data.get('category',''), status='draft')
        db.session.add(draft)
    db.session.commit()
    return jsonify({"success": True, "id": draft.id})

@tongbot_bp.route('/api/bot/review/<int:draft_id>', methods=['POST'])
def bot_review(draft_id):
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    draft = TongBotDraft.query.get_or_404(draft_id)
    if draft.user_id != uid:
        return jsonify({"error": "권한이 없습니다."}), 403
    try:
        from config import Config
        import requests
        key = getattr(Config, 'GROQ_API_KEY', '')
        prompt = f"""당신은 교정 도우미입니다. 회원이 작성한 글을 검토하고 다음을 제안하세요:
1. 맞춤법/문법 교정
2. 어디에 게시하면 좋을지 (공유마당/꿈꾸기/소식/법률상담/심리상담 중 선택)
3. 개선된 버전의 글

원본 제목: {draft.title}
원본 내용: {draft.content}
카테고리: {draft.category or '미정'}

응답 형식:
[게시추천]: (공유마당/꿈꾸기/소식/법률상담/심리상담 중 하나)
[교정본]:
(교정된 글 전체)"""
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "max_tokens": 800},
            timeout=30)
        review = ""
        suggestion = ""
        if r.status_code == 200:
            review = r.json()["choices"][0]["message"]["content"]
            for line in review.split('\n'):
                if '[게시추천]' in line:
                    suggestion = line.split(']')[1].strip() if ']' in line else line.replace('[게시추천]','').strip()
                    break
        draft.bot_review = review
        draft.bot_suggestion = suggestion
        draft.status = 'reviewed'
        draft.updated_at = datetime.now()
        db.session.commit()
        return jsonify({"success": True, "review": review, "suggestion": suggestion})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@tongbot_bp.route('/api/bot/schedule', methods=['GET', 'POST'])
def bot_schedule():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    if request.method == 'GET':
        schedules = TongBotSchedule.query.filter_by(user_id=uid).order_by(TongBotSchedule.event_date.asc()).limit(30).all()
        return jsonify({"schedules": [{"id": s.id, "title": s.title, "description": s.description, "event_date": s.event_date.strftime("%Y-%m-%d %H:%M") if s.event_date else "", "invited": s.invited_user_ids} for s in schedules]})
    data = request.json
    s = TongBotSchedule(user_id=uid, title=data.get('title',''), description=data.get('description',''), event_date=datetime.fromisoformat(data.get('event_date','')), invited_user_ids=data.get('invited',''))
    db.session.add(s)
    db.session.commit()
    return jsonify({"success": True, "id": s.id})

@tongbot_bp.route('/api/bot/upload', methods=['POST'])
def bot_upload():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    f = request.files.get('file')
    if not f:
        return jsonify({"error": "파일이 없습니다."})
    ext = os.path.splitext(f.filename)[1].lower()
    if request.form.get('type') == 'image' and ext not in ('.jpg','.jpeg','.png','.gif','.webp'):
        return jsonify({"error": "지원하지 않는 이미지 형식입니다."})
    fname = f"{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'tongbot')
    os.makedirs(upload_dir, exist_ok=True)
    f.save(os.path.join(upload_dir, fname))
    url = f"/static/uploads/tongbot/{fname}"
    return jsonify({"url": url, "filename": fname})
