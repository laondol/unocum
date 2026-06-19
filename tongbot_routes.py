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
    popup = request.args.get('popup') == '1'
    if popup:
        return render_template('user_my_popup.html', user=user, bot=bot, drafts=drafts, schedules=schedules, stamps_count=stamps_count)
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

@tongbot_bp.route('/api/bot/tone', methods=['POST'])
def bot_tone():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    tone = request.json.get('tone', 'friendly')
    if tone not in ('friendly','respectful','strict'):
        return jsonify({"error": "올바른 말투를 선택하세요."})
    bot = _get_bot(uid)
    bot.tone = tone
    bot.updated_at = datetime.now()
    db.session.commit()
    return jsonify({"success": True, "tone": tone})

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
    talent = None
    if int(bot.chat_count or 0) % 10 == 0 and int(bot.chat_count or 0) > 0:
        talent = _discover_talent(bot, user)
    counselor = _detect_counselor_need(msg)
    counselor_msg = None
    if counselor == 'legal':
        counselor_msg = {'type':'legal','msg':'법률 고민이 있으신가요? 전문 노무사와 상담을 연결해 드릴까요? (50닢 소요)','url':'/legal/list'}
    elif counselor == 'psycho':
        counselor_msg = {'type':'psycho','msg':'마음이 힘드신가요? 심리상담사와 대화를 연결해 드릴까요? (30닢 소요)','url':'/psycho/list'}
    return jsonify({"reply": reply, "bot_name": bot.bot_name, "talent": talent, "mood": bot.mood, "level": bot.level, "counselor": counselor_msg})

MOODS = ['neutral','happy','excited','thoughtful','caring','playful']
MOOD_EMOJI = {'neutral':'😊','happy':'😄','excited':'🤩','thoughtful':'🤔','caring':'🥰','playful':'😜'}
LEVEL_NAMES = {1:'🥚 알',2:'🐣 새싹',3:'🌱 묘목',4:'🪴 나무',5:'🌸 꽃',6:'🌟 별',7:'👑 수호자'}

MOTHER_MOODS = {
    'warm': {'emoji':'💕', 'label':'따스한'},
    'proud': {'emoji':'🥲', 'label':'대견한'},
    'encourage': {'emoji':'💪', 'label':'응원하는'},
    'worried': {'emoji':'😌', 'label':'걱정되는'},
    'happy': {'emoji':'😊', 'label':'기쁜'},
    'blessing': {'emoji':'🙏', 'label':'축복하는'},
}

def _ai_reply(bot, user, user_msg):
    import random
    bot.chat_count = int(bot.chat_count or 0) + 1
    bot.exp = int(bot.exp or 0) + random.randint(5, 15)
    bot.intimacy = int(bot.intimacy or 0) + random.randint(1, 3)
    new_level = min(7, 1 + int(bot.exp or 0) // 100)
    if new_level > int(bot.level or 1):
        bot.level = new_level
    msg_lower = user_msg.lower()
    if any(w in msg_lower for w in ['힘들','지쳤','우울','슬프','속상','화나']):
        bot.mood = 'worried'
    elif any(w in msg_lower for w in ['감사','고마워','행복','좋아','기뻐']):
        bot.mood = 'happy'
    elif any(w in msg_lower for w in ['성공','해냈','이뤘','합격','완료','끝냈']):
        bot.mood = 'proud'
    elif any(w in msg_lower for w in ['도와줘','어떡','모르겠','가르쳐','알려줘']):
        bot.mood = 'encourage'
    else:
        bot.mood = random.choice(['warm','caring','blessing','encourage'])
    _m = MOTHER_MOODS.get(bot.mood, MOTHER_MOODS['warm'])
    mood_prefix = f"{_m['emoji']} ({_m['label']}) "
    if int(bot.chat_count or 0) > 0:
        bot.memory = (bot.memory or '')[-800:] + f'\n회원: {user_msg[:100]}'
    db.session.commit()
    lvl_name = LEVEL_NAMES.get(bot.level, '')
    _m = MOTHER_MOODS.get(bot.mood, MOTHER_MOODS['warm'])

    try:
        from config import Config
        import requests
        key = getattr(Config, 'GROQ_API_KEY', '')
        if not key:
            return f"{_m['emoji']} 안녕하세요! 저는 {bot.bot_name}입니다. {lvl_name} 단계예요."
        tone = bot.tone or 'friendly'
        tone_guide = {'friendly':'친근하고 편안한 말투로, 반말과 이모티콘을 자유롭게 사용하세요.',
                      'respectful':'존중하고 예의 바른 말투로, ~합니다/～요 체를 사용하세요.',
                      'strict':'엄격하고 간결한 말투로, 핵심만 전달하며 군더더기 없이 답변하세요.'}.get(tone, '')
        prompt = f"""당신은 '{bot.bot_name}'입니다. 회원 '{user.username}'님의 개인 AI 비서입니다.
말투: {tone_guide}
성장단계: {lvl_name} (Lv.{bot.level}) | 친밀도: {bot.intimacy}
2~3문장으로 간결하게 답변하세요.

회원: {user_msg}"""
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "max_tokens": 300},
            timeout=20)
        if r.status_code == 200:
            return f"{_m['emoji']} {r.json()['choices'][0]['message']['content']}"
    except:
        pass
    return f"{_m['emoji']} {user.username}님, 항상 응원하고 있어요. 무엇을 도와드릴까요?"

TALENT_KEYWORDS = {
    '글쓰기': ['글','쓰기','시','소설','일기','작문','이야기'],
    '그림': ['그림','사진','디자인','색','풍경','스케치'],
    '요리': ['요리','음식','레시피','맛집','베이킹','반찬'],
    '음악': ['노래','악기','음악','연주','기타','피아노'],
    '운동': ['운동','산책','달리기','등산','자전거','수영'],
    '기술': ['코딩','프로그램','컴퓨터','앱','개발','IT'],
    '상담': ['고민','상담','힘들','우울','조언','도움'],
    '봉사': ['봉사','나눔','돕다','기부','이웃','마을'],
}

COUNSELOR_KEYWORDS = {
    'legal': ['법','소송','계약','임금','해고','변호사','노무'],
    'psycho': ['우울','불안','스트레스','상담','마음','심리','외로움'],
}

def _discover_talent(bot, user):
    try:
        from config import Config
        import requests
        key = getattr(Config, 'GROQ_API_KEY', '')
        if not key:
            return _keyword_talent(bot)
        prompt = f"""다음 대화를 바탕으로 회원 '{user.username}'님의 숨은 재능이나 관심사를 발견하세요.
10단어 이내로 간결하게 답변하세요.

대화기록: {bot.memory or '없음'}"""
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "max_tokens": 50},
            timeout=15)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except:
        pass
    return _keyword_talent(bot)

def _keyword_talent(bot):
    memory = (bot.memory or '').lower()
    scores = {}
    for talent, kws in TALENT_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in memory)
        if score > 0:
            scores[talent] = score
    if scores:
        return max(scores, key=scores.get)
    return None

def _detect_counselor_need(user_msg):
    msg = user_msg.lower()
    for ctype, kws in COUNSELOR_KEYWORDS.items():
        if any(kw in msg for kw in kws):
            return ctype
    return None

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

@tongbot_bp.route('/admin/tongbot/monitor')
def admin_tongbot_monitor():
    if session.get('role') not in ('admin', 'leader'):
        return "권한 없음", 403
    bots = TongBot.query.order_by(TongBot.updated_at.desc()).limit(50).all()
    result = []
    for b in bots:
        u = User.query.get(b.user_id)
        result.append({
            "bot_name": b.bot_name, "user": u.username if u else '?',
            "level": b.level, "intimacy": b.intimacy, "chat_count": b.chat_count,
            "mood": b.mood, "tone": b.tone,
            "last_active": b.updated_at.strftime("%m/%d %H:%M") if b.updated_at else '',
            "memory_len": len(b.memory or ''),
        })
    return jsonify({"bots": result})

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
