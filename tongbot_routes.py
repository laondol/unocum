import random, string
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, current_app
from models import db, User, TongBot, TongBotDraft, TongBotSchedule, ChatRoom, ChatMessage, Message, FriendCache
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
    active_tab = request.args.get('tab', 'chat')
    room_id = request.args.get('room', type=int)
    action = request.args.get('action', '')
    if room_id and action:
        _handle_chat_action(user.id, room_id, action)
        active_tab = 'friendchat'
    greeting = _greeting(user)
    import json
    chat_rooms = ChatRoom.query.filter(ChatRoom.is_active==True, ChatRoom.participants.contains(str(user.id))).order_by(ChatRoom.created_at.desc()).limit(10).all()
    tpl = 'user_my_popup.html' if popup else 'user_my.html'
    return render_template(tpl, user=user, bot=bot, drafts=drafts, schedules=schedules, stamps_count=stamps_count, greeting=greeting, chat_rooms=chat_rooms, json=json, active_tab=active_tab)

@tongbot_bp.route('/chat')
def chat_page():
    if not session.get('user_id'):
        return redirect(url_for('login', next='/chat'))
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('login'))
    bot = _get_bot(user.id)
    room_id = request.args.get('room', type=int)
    action = request.args.get('action', '')
    if room_id and action:
        _handle_chat_action(user.id, room_id, action)
    import json
    chat_rooms = ChatRoom.query.filter(ChatRoom.is_active==True, ChatRoom.participants.contains(str(user.id))).order_by(ChatRoom.created_at.desc()).limit(10).all()
    open_room = room_id if room_id else 0
    return render_template('chat.html', user=user, bot=bot, chat_rooms=chat_rooms, json=json, open_room=open_room)

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

def _time_greeting(user):
    h = datetime.now().hour
    if h < 6: return "깊은 밤"
    if h < 9: return "상쾌한 아침"
    if h < 12: return "활기찬 오전"
    if h < 14: return "점심"
    if h < 17: return "따스한 오후"
    if h < 20: return "저녁"
    return "조용한 밤"

def _weather_hint(user):
    m = datetime.now().month
    if m in (3,4,5): return "봄꽃이 피는 계절"
    if m in (6,7,8): return "여름 더위"
    if m in (9,10,11): return "가을 바람"
    return "겨울 추위"

def _greeting(user):
    import random
    t = _time_greeting(user)
    w = _weather_hint(user)
    loc = f"{user.curr_town or '양평'}"
    greetings = [
        f"{t}이에요, {user.username}님! {w} 속에서도 건강 챙기세요.",
        f"{t}입니다! 오늘 {loc}은 어떠신가요?",
        f"좋은 {t}이에요! {w}에 딱 맞는 하루 보내세요.",
    ]
    return random.choice(greetings)

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
    bot.memory = (bot.memory or '')[-800:] + f'\n통벗: {reply[:150]}'
    db.session.commit()
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

@tongbot_bp.route('/api/bot/history')
def bot_history():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    bot = _get_bot(uid)
    lines = (bot.memory or '').strip().split('\n')
    history = []
    for line in lines[-50:]:
        line = line.strip()
        if line.startswith('회원:'):
            history.append({"role": "user", "text": line[3:].strip()})
        elif line.startswith('통벗:'):
            history.append({"role": "bot", "text": line[3:].strip()})
    return jsonify({"history": history, "total": bot.chat_count or 0})

MOODS = ['neutral','happy','excited','thoughtful','caring','playful']
MOOD_EMOJI = {'neutral':'😊','happy':'😄','excited':'🤩','thoughtful':'🤔','caring':'🥰','playful':'😜'}
LEVEL_NAMES = {1:'🥚 알',2:'🐣 새싹',3:'🌱 묘목',4:'🪴 나무',5:'🌸 꽃',6:'🌟 별',7:'👑 수호자'}

PLATFORM_GUIDE = """[함께사는양평 플랫폼 안내 - 회원 질문에 반드시 이 정보를 우선 참고하세요]

주요 메뉴:
- 소식: 대한민국과양평(/kr-yp-news), 세계와양평(/world-news) - 마을/세계 뉴스 제공
- 공유마당(/share): 주민들이 가게·풍경·나눔 정보를 사진과 함께 공유
- 꿈꾸기(/main): 마을에 바라는 제안 작성, 투표로 실현
- 위치기반안내(/construction): 국가유산·풍경·동네가게·집으로(귀가길안내)·교통·알림
- 법률상담(/legal/list): 노무사 이훈의 무료 법률상담
- 심리상담소(/psycho/list): 전문 심리상담 예약

회원활동:
- 벗 신청: 다른 회원 프로필(/user/번호)에서 '벗 신청' 버튼 클릭
- 닢(포인트): 활동하면 쌓이고, 닢 충전(/mypage/points/charge)으로 구매 가능
- 이웃인증: 프로필에서 GPS로 현재 위치 확인 후 '이웃인증' 버튼
- 통벗: AI 개인비서, 말투 선택(친근/존중/엄격), 글쓰기 교정 도움

자주 묻는 질문:
- 벗은 어디서 만드나요? → 다른 회원님 프로필에 방문하여 '벗 신청' 버튼을 누르세요. 프로필은 /user/회원번호 에서 확인할 수 있습니다.
- 글은 어디에 쓰나요? → 꿈꾸기, 공유마당, 소식 탭에서 작성 가능합니다. 통벗의 글쓰기 탭에서도 작성 후 교정받을 수 있어요.
- 위치기반안내는 뭔가요? → 현재 위치 주변 국가유산, 동네가게, 집 가는 길 막차시간을 알려줍니다."""

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
        prompt = f"""{PLATFORM_GUIDE}

당신은 '{bot.bot_name}'입니다. 회원 '{user.username}'님의 개인 AI 비서입니다.
말투: {tone_guide}
성장단계: {lvl_name} (Lv.{bot.level}) | 친밀도: {bot.intimacy}
회원이 플랫폼 기능에 대해 물으면 위 [플랫폼 안내]를 참고하여 구체적인 사용법을 알려주세요.
일반적인 조언보다 플랫폼 내 해결 방법을 우선 안내하세요.
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

def _handle_chat_action(uid, room_id, action):
    room = ChatRoom.query.get(room_id)
    if not room: return
    import json
    status_map = json.loads(room.status_map or '{}')
    user = User.query.get(uid)
    bot = _get_bot(uid)
    if action == 'join':
        status_map[str(uid)] = 'joined'
        db.session.add(ChatMessage(room_id=room_id, user_id=None, username='✅',
            message=f'{user.username}님이 입장했습니다.', is_bot=True))
    elif action == 'decline':
        status_map[str(uid)] = 'declined'
    elif action == 'monitor':
        status_map[str(uid)] = 'monitoring'
        db.session.add(ChatMessage(room_id=room_id, user_id=None, username=bot.bot_name,
            message=f'{user.username}님이 모니터링 모드로 참여했습니다.', is_bot=True))
    room.status_map = json.dumps(status_map)
    db.session.commit()

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

@tongbot_bp.route('/api/bot/schedule/delete', methods=['POST'])
def bot_schedule_delete():
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"로그인"}),401
    data = request.get_json()
    s = TongBotSchedule.query.get(data.get('id'))
    if not s or s.user_id != uid: return jsonify({"error":"권한없음"}),403
    db.session.delete(s)
    db.session.commit()
    return jsonify({"success":True})

@tongbot_bp.route('/schedule')
def schedule_popup():
    if not session.get('user_id'):
        return redirect(url_for('login', next='/schedule'))
    user = User.query.get(session['user_id'])
    bot = _get_bot(user.id)
    # 약속 수락/거절 처리
    accept_uid = request.args.get('accept', type=int)
    decline_uid = request.args.get('decline', type=int)
    event_date = request.args.get('date','')
    title = request.args.get('title','약속')
    msg = ''
    if accept_uid and event_date:
        s = TongBotSchedule(user_id=user.id, title=f'{title} (수락)', event_date=datetime.fromisoformat(event_date))
        db.session.add(s)
        db.session.commit()
        msg = '약속이 일정에 등록되었습니다!'
    if decline_uid:
        msg = '약속을 거절했습니다.'
    return render_template('schedule_popup.html', user=user, bot=bot, msg=msg)

@tongbot_bp.route('/api/bot/schedule/common', methods=['POST'])
def schedule_common():
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"로그인"}),401
    data = request.get_json()
    date = data.get('date','')
    duration = data.get('duration',60)
    friend_ids = data.get('friend_ids',[])
    if not date: return jsonify({"slots":[]})
    all_ids = [uid] + friend_ids
    all_busy = {}
    import json
    for fid in all_ids:
        schedules = TongBotSchedule.query.filter_by(user_id=fid).all()
        busy_times = []
        for s in schedules:
            if s.event_date and str(s.event_date)[:10] == date:
                t = str(s.event_date)[11:16]
                busy_times.append(t)
        all_busy[fid] = set(busy_times)
    # Find common free slots
    slots = []
    for h in range(6, 23):
        for m in range(0, 60, 30):
            time = f"{h:02d}:{m:02d}"
            if any(time in busy for busy in all_busy.values()):
                continue
            # Count consecutive free minutes
            free_min = 0
            tm = h*60 + m
            while tm < 23*60:
                ct = f"{tm//60:02d}:{tm%60:02d}"
                if any(ct in busy for busy in all_busy.values()):
                    break
                free_min += 30
                tm += 30
                if free_min >= duration:
                    break
            if free_min >= duration:
                slots.append({"time":time,"free_min":free_min})
    return jsonify({"slots":slots,"friend_count":len(all_ids),"date":date})

@tongbot_bp.route('/api/bot/schedule/invite', methods=['POST'])
def schedule_invite():
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"로그인"}),401
    data = request.get_json()
    title = data.get('title','약속')
    date = data.get('date','')
    time = data.get('time','')
    duration = data.get('duration',60)
    friend_ids = data.get('friend_ids',[])
    if not date or not time: return jsonify({"error":"날짜/시간 필요"})
    sender = User.query.get(uid)
    event_date = f"{date} {time}:00"
    for fid in friend_ids:
        msg = f'<div style="text-align:center;padding:10px;"><strong>📅 약속 제안: {title}</strong><br><small>{sender.username}님의 제안</small><br>🕐 {date} {time} ({duration}분)<hr style="margin:5px 0;"><a href="https://test.unocum.kr/schedule?accept={uid}&date={event_date}&title={title}" style="display:inline-block;padding:6px 12px;background:#198754;color:#fff;border-radius:6px;text-decoration:none;margin:2px;">✅ 수락</a> <a href="https://test.unocum.kr/schedule?decline={uid}" style="display:inline-block;padding:6px 12px;background:#dc3545;color:#fff;border-radius:6px;text-decoration:none;margin:2px;">❌ 거절</a></div>'
        db.session.add(Message(sender_id=uid, sender_name=sender.username, receiver_id=fid,
            subject=f'📅 약속 제안: {title}', content=msg, sender_role='member'))
    db.session.commit()
    return jsonify({"success":True,"msg":f"{len(friend_ids)}명에게 약속 제안을 보냈습니다!"})

@tongbot_bp.route('/api/bot/schedule/plan', methods=['POST'])
def schedule_plan():
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"로그인"}),401
    data = request.get_json()
    date = data.get('date','')
    items = data.get('items',[])
    user = User.query.get(uid)
    from_loc = data.get('from','') or f"{user.town or ''} {user.village or ''}".strip() or '양평'
    to_loc = data.get('to','') or from_loc
    from services.transit import haversine_km, geocode_address, estimate_transit_time_rough
    from config import Config
    s = geocode_address(from_loc, Config.KAKAO_REST_API_KEY) if from_loc else None
    start_coords = (s['lat'], s['lng']) if s else (37.49, 127.49)
    e = geocode_address(to_loc, Config.KAKAO_REST_API_KEY) if to_loc else None
    end_coords = (e['lat'], e['lng']) if e else start_coords
    plan = []
    prev_coords = start_coords
    for item in items:
        g = geocode_address(item.get('loc',''), Config.KAKAO_REST_API_KEY) if item.get('loc') else None
        coords = (g['lat'], g['lng']) if g else None
        travel = estimate_transit_time_rough(prev_coords[0], prev_coords[1], coords[0] if coords else prev_coords[0], coords[1] if coords else prev_coords[1])
        if item.get('time'):
            arr_min = int(item['time'].split(':')[0])*60 + int(item['time'].split(':')[1])
        else:
            arr_min = 540
        dep_prev = arr_min - travel
        dep_str = f"{dep_prev//60:02d}:{dep_prev%60:02d}"
        end_min = arr_min + item.get('dur',60)
        end_str = f"{end_min//60:02d}:{end_min%60:02d}"
        plan.append({'title':item['title'],'arrive':item.get('time','--:--'),'dur':item.get('dur',60),'travel_min':travel,'leave_when':end_str,'depart_prev':dep_str})
        prev_coords = coords if coords else prev_coords
    last_end = end_min if items else 540
    travel_home = estimate_transit_time_rough(prev_coords[0], prev_coords[1], end_coords[0], end_coords[1])
    arrive_home = f"{(last_end+travel_home)//60:02d}:{(last_end+travel_home)%60:02d}"
    first_leave = plan[0]['depart_prev'] if plan else '09:00'
    return jsonify({'date':date,'from':from_loc,'to':to_loc,'leave_time':first_leave,'plan':plan,'arrive_home':arrive_home})

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

# ─── 벗 채팅 ───

@tongbot_bp.route('/api/chat/friends')
def chat_friends():
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"로그인"}),401
    import json
    cache = FriendCache.query.get(uid)
    if cache:
        friend_ids = json.loads(cache.friend_ids or '[]')
    else:
        from models import Friend
        f1 = Friend.query.filter_by(requester_id=uid, status='accepted').all()
        f2 = Friend.query.filter_by(receiver_id=uid, status='accepted').all()
        friend_ids = list(set([f.receiver_id for f in f1] + [f.requester_id for f in f2]))
        db.session.add(FriendCache(user_id=uid, friend_ids=json.dumps(friend_ids)))
        db.session.commit()
    users = User.query.filter(User.id.in_(friend_ids)).all() if friend_ids else []
    return jsonify({"friends":[{"id":u.id,"username":u.username,"name":u.real_name or u.username,"town":u.town or "","village":u.village or ""} for u in users]})

def _rebuild_friend_cache(uid):
    from models import Friend
    import json
    f1 = Friend.query.filter_by(requester_id=uid, status='accepted').all()
    f2 = Friend.query.filter_by(receiver_id=uid, status='accepted').all()
    friend_ids = set()
    for f in f1: friend_ids.add(f.receiver_id)
    for f in f2: friend_ids.add(f.requester_id)
    cache = FriendCache.query.get(uid)
    if cache:
        cache.friend_ids = json.dumps(list(friend_ids))
        cache.updated_at = datetime.now()
    else:
        db.session.add(FriendCache(user_id=uid, friend_ids=json.dumps(list(friend_ids))))
    db.session.commit()

@tongbot_bp.route('/api/chat/rooms', methods=['GET','POST'])
def chat_rooms():
    uid = session.get('user_id')
    if not uid: return jsonify({"error": "로그인"}), 401
    if request.method == 'POST':
        data = request.json
        name = data.get('name','채팅방')
        friends = data.get('friends',[])
        schedule = data.get('schedule')
        if not friends: return jsonify({"error":"벗을 선택하세요"})
        import json, datetime as _dt
        pids = [uid] + friends
        status_map = {str(uid): 'joined'}
        for f in friends: status_map[str(f)] = 'invited'
        room = ChatRoom(name=name, creator_id=uid, participants=json.dumps(pids),
                       status_map=json.dumps(status_map),
                       expires_at=datetime.now() + _dt.timedelta(hours=2))
        db.session.add(room)
        db.session.flush()
        # 일정 연결
        if schedule and schedule.get('title') and schedule.get('event_date'):
            try:
                s = TongBotSchedule(user_id=uid, title=schedule['title'],
                    description=schedule.get('description',''),
                    event_date=datetime.fromisoformat(schedule['event_date']),
                    invited_user_ids=json.dumps(friends))
                db.session.add(s)
            except: pass
        # 초대 쪽지 발송
        creator = User.query.get(uid)
        invite_msg = f'<div style="text-align:center;padding:10px;"><strong>💬 채팅 초대: {name}</strong><br><small>{creator.username}님이 초대했습니다</small><hr style="margin:5px 0;"><a href="https://test.unocum.kr/chat?room={room.id}&action=join" style="display:inline-block;padding:6px 12px;background:#198754;color:#fff;border-radius:6px;text-decoration:none;margin:2px;">✅ 입장</a> <a href="https://test.unocum.kr/chat?room={room.id}&action=decline" style="display:inline-block;padding:6px 12px;background:#dc3545;color:#fff;border-radius:6px;text-decoration:none;margin:2px;">❌ 거절</a> <a href="https://test.unocum.kr/chat?room={room.id}&action=monitor" style="display:inline-block;padding:6px 12px;background:#6c757d;color:#fff;border-radius:6px;text-decoration:none;margin:2px;">👁️ 모니터링</a></div>'
        for fid in friends:
            db.session.add(Message(sender_id=uid, sender_name=creator.username, receiver_id=fid,
                subject=f'💬 채팅 초대: {name}', content=invite_msg, sender_role='member'))
        # 통벗 입장
        bot = _get_bot(uid)
        db.session.add(ChatMessage(room_id=room.id, user_id=None, username=bot.bot_name,
            message=f"채팅방이 개설되었습니다! {len(friends)}명의 벗을 초대했습니다. 💕", is_bot=True))
        db.session.commit()
        return jsonify({"id": room.id, "name": name})
    import json
    # 만료된 방 정리
    ChatRoom.query.filter(ChatRoom.is_active==True, ChatRoom.expires_at < datetime.now()).update({"is_active":False}, synchronize_session=False)
    db.session.commit()
    rooms = ChatRoom.query.filter(ChatRoom.is_active==True, ChatRoom.participants.contains(str(uid))).order_by(ChatRoom.created_at.desc()).limit(20).all()
    result = []
    for r in rooms:
        pids = json.loads(r.participants or '[]')
        names = []
        for pid in pids:
            u = User.query.get(pid)
            names.append(u.username if u else str(pid))
        result.append({"id": r.id, "name": r.name, "participants": names, "created": r.created_at.strftime("%H:%M") if r.created_at else ''})
    return jsonify({"rooms": result})

@tongbot_bp.route('/api/chat/messages/<int:room_id>', methods=['GET','POST'])
def chat_messages(room_id):
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"로그인"}),401
    import json
    room = ChatRoom.query.get_or_404(room_id)
    pids = json.loads(room.participants or '[]')
    if uid not in pids: return jsonify({"error":"권한없음"}),403
    if request.method == 'POST':
        msg = request.json.get('message','').strip()
        if not msg: return jsonify({"error":"내용입력"})
        # 비방 감지
        bad_words = ['바보','멍청','죽어','꺼져','XX','시발','병신']
        is_bad = any(w in msg for w in bad_words)
        db.session.add(ChatMessage(room_id=room_id, user_id=uid, username=session.get('username',''), message=msg))
        if is_bad:
            bot = _get_bot(uid)
            db.session.add(ChatMessage(room_id=room_id, user_id=None, username=bot.bot_name,
                message=f"⚠️ 부적절한 표현이 감지되었습니다. 서로 존중하는 대화를 부탁드려요.", is_bot=True))
        db.session.commit()
        # 통벗 조율 (5회마다)
        count = ChatMessage.query.filter_by(room_id=room_id, is_bot=False).count()
        if count % 5 == 0:
            _moderate_chat(room_id)
        return jsonify({"ok":True})
    msgs = ChatMessage.query.filter_by(room_id=room_id).order_by(ChatMessage.created_at.desc()).limit(50).all()
    msgs.reverse()
    return jsonify({"messages":[{"id":m.id,"username":m.username,"message":m.message,"is_bot":m.is_bot,"time":m.created_at.strftime("%H:%M") if m.created_at else ""} for m in msgs]})

def _moderate_chat(room_id):
    bot = _get_bot(session.get('user_id'))
    msgs = ChatMessage.query.filter_by(room_id=room_id, is_bot=False).order_by(ChatMessage.created_at.desc()).limit(10).all()
    if not msgs: return
    recent = ' | '.join([f"{m.username}:{m.message[:30]}" for m in msgs])
    try:
        from config import Config
        import requests
        key = getattr(Config, 'GROQ_API_KEY', '')
        if not key: return
        prompt = f"""당신은 채팅 중재자입니다. 다음 대화를 보고 분위기를 판단하세요.
긍정적이면 칭찬, 부정적이면 부드럽게 조율하는 한 문장을 쓰세요.
대화: {recent}"""
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"}, json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":prompt}],"max_tokens":100}, timeout=15)
        if r.status_code == 200:
            reply = r.json()["choices"][0]["message"]["content"]
            db.session.add(ChatMessage(room_id=room_id, user_id=None, username=bot.bot_name, message=f"💬 {reply}", is_bot=True))
            db.session.commit()
    except: pass

@tongbot_bp.route('/api/chat/invite/<int:room_id>', methods=['POST'])
def chat_invite(room_id):
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"로그인"}),401
    import json
    room = ChatRoom.query.get_or_404(room_id)
    pids = json.loads(room.participants or '[]')
    if uid not in pids: return jsonify({"error":"권한없음"}),403
    friend_id = request.json.get('friend_id')
    if not friend_id or friend_id in pids: return jsonify({"error":"불가"})
    pids.append(int(friend_id))
    room.participants = json.dumps(pids)
    db.session.commit()
    return jsonify({"ok":True})

@tongbot_bp.route('/api/chat/warn/<int:room_id>', methods=['POST'])
def chat_warn(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    bot = _get_bot(room.creator_id)
    db.session.add(ChatMessage(room_id=room_id, user_id=None, username='⏰',
        message=f"⚠️ 채팅방이 10분 후에 종료됩니다. 중요한 내용은 미리 저장해 주세요!", is_bot=True))
    db.session.commit()
    return jsonify({"ok":True})

@tongbot_bp.route('/api/chat/close/<int:room_id>', methods=['POST'])
def chat_close(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    room.is_active = False
    bot = _get_bot(room.creator_id)
    db.session.add(ChatMessage(room_id=room_id, user_id=None, username='⏰',
        message=f"🛑 2시간이 지나 채팅방이 종료되었습니다. 다음에 또 만나요! 💕", is_bot=True))
    db.session.commit()
    return jsonify({"ok":True})
