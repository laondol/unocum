import random, string, re, requests, json
from sqlalchemy import or_
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, current_app
from models import db, User, TongBot, TongBotDraft, TongBotSchedule, ChatRoom, ChatMessage, Message, FriendCache, BotKnowledge, StoreInfo, ShareReport, SharedRoute
from datetime import datetime, timedelta, timezone
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
    from datetime import datetime, timedelta, timezone
    h = (datetime.now(timezone.utc) + timedelta(hours=9)).hour
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

    # 일정 의도 감지 → 일정 특화 AI로 처리
    schedule_info = None
    shopping_info = None

    # 쇼핑 의도 감지
    if any(kw in msg for kw in SHOPPING_TRIGGERS):
        keyword = msg
        for kw in ['가격','얼마','사고','구매','쇼핑','파는','싼','비싼','최저','추천']:
            keyword = keyword.replace(kw, '')
        keyword = keyword.strip()[:30]
        if len(keyword) >= 2:
            shop = _search_shopping(keyword)
            if shop:
                local = _find_nearby_stores(keyword, 2)
                parts = [f'🔍 "{keyword}" 검색 결과:\n']
                parts.append(f'💰 최저가: {shop["min_price"]:,}원 | 최고가: {shop["max_price"]:,}원')
                parts.append(f'🛒 온라인 쇼핑몰 {len(shop["items"])}건:')
                for item in shop['items'][:3]:
                    parts.append(f'  • {item["title"]} - {item["price"]:,}원 ({item["mall"]})\n    {item["link"]}')
                if local:
                    parts.append(f'\n🏪 근처 가게: {", ".join(local)}')
                else:
                    parts.append(f'\n🏪 근처 가게: 공유마당에서 확인하세요')
                parts.append(f'\n🔗 네이버 쇼핑: https://search.shopping.naver.com/search/all?query={keyword}')
                shopping_info = '\n'.join(parts)

    if _detect_schedule_intent(msg):
        try:
            sched_resp = bot_schedule_ai_internal(uid, msg, user, bot)
            if sched_resp.get('reply'):
                reply = sched_resp['reply']
            if sched_resp.get('action') == 'create' and sched_resp.get('schedule'):
                schedule_info = sched_resp['schedule']
        except Exception as e:
            current_app.logger.error(f'일정AI 오류: {e}')

    # 통벗 추천: 문맥에 맞는 기능 제안
    suggestions = None
    if not schedule_info and not shopping_info and not counselor:
        suggestions = _get_proactive_suggestions(user, msg)

    return jsonify({"reply": reply, "bot_name": bot.bot_name, "talent": talent, "mood": bot.mood, "level": bot.level, "counselor": counselor_msg, "schedule": schedule_info, "shopping": shopping_info, "suggestion": suggestions})

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

SCHEDULE_KEYWORDS = ['일정', '약속', '캘린더', '예약', '스케줄', '추가해', '등록해', '만들어줘', '생성해', '넣어줘', '기록해', '잡아줘', '저장해', '등록', '추가', '일정추가', '일정등록', '만나자', '보자', '가자', '갈까', '만날까']

def _detect_schedule_intent(msg):
    """일정 생성 의도 감지"""
    msg_lower = msg.lower()
    keyword_hit = any(kw in msg_lower for kw in SCHEDULE_KEYWORDS)
    # 시간 표현이 있으면 추가로 감지
    if not keyword_hit:
        has_time = bool(re.search(r'(\d{1,2}시|오전|오후|내일|모레|다음주|이번주|주말|오늘)', msg))
        has_action = bool(re.search(r'(만나|갈|볼|가자|보자|만날|약속|일정|예약)', msg))
        if has_time and has_action:
            return True
    return keyword_hit

KST = timezone(timedelta(hours=9))

def _parse_korean_datetime(msg, now):
    """한글 자연어 → datetime (KST)"""
    WEEKDAYS = {'월요일':0,'화요일':1,'수요일':2,'목요일':3,'금요일':4,'토요일':5,'일요일':6,
                '월':0,'화':1,'수':2,'목':3,'금':4,'토':5,'일':6}
    msg_clean = msg.replace(' ','')
    hour = None
    minute = 0
    ampm = None

    # 시간 추출
    tm = re.search(r'(오전|오후|아침|점심|저녁|밤)?\s*(\d{1,2})\s*시(\s*(\d{1,2})\s*분)?', msg)
    if tm:
        label = tm.group(1) or ''
        hour = int(tm.group(2))
        if tm.group(4):
            minute = int(tm.group(4))
        if '오후' in label or '저녁' in label or '밤' in label:
            if hour < 12:
                hour += 12
        elif '아침' in label or '점심' in label:
            ampm = 'pm' if '점심' in label else 'am'
            if ampm == 'pm' and hour < 12:
                hour += 12
        # "오전"은 그대로
    if hour is None:
        tm2 = re.search(r'(\d{1,2}):(\d{2})', msg)
        if tm2:
            hour = int(tm2.group(1))
            minute = int(tm2.group(2))

    # 날짜 계산
    target_date = now.date()
    if '오늘' in msg_clean:
        pass  # already now.date()
    elif '모레' in msg_clean:
        target_date += timedelta(days=2)
    elif '내일' in msg_clean:
        target_date += timedelta(days=1)
    elif '글피' in msg_clean:
        target_date += timedelta(days=3)
    elif any(w in msg_clean for w in WEEKDAYS):
        for wday_name, wday_num in WEEKDAYS.items():
            if wday_name in msg_clean:
                days_ahead = (wday_num - now.weekday()) % 7
                if '다음주' in msg_clean:
                    days_ahead += 7
                elif '다다음주' in msg_clean:
                    days_ahead += 14
                else:
                    if days_ahead == 0:
                        days_ahead = 7 if '다음' in msg_clean else 0
                target_date += timedelta(days=days_ahead or 7)
                break
    elif '다음주' in msg_clean:
        target_date += timedelta(days=7)
    elif '이번주' in msg_clean:
        pass

    # 절대 날짜: 6월 30일, 2026년 6월 30일, 6/30
    abs_full = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', msg)
    if abs_full:
        target_date = datetime(int(abs_full.group(1)), int(abs_full.group(2)), int(abs_full.group(3))).date()
    else:
        abs_md = re.search(r'(\d{1,2})월\s*(\d{1,2})일', msg)
        if abs_md:
            target_date = datetime(now.year, int(abs_md.group(1)), int(abs_md.group(2))).date()
        else:
            md = re.search(r'(\d{1,2})/(\d{1,2})', msg)
            if md:
                target_date = datetime(now.year, int(md.group(1)), int(md.group(2))).date()

    if hour is None:
        return None
    return datetime(target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=KST)

def _parse_schedule_from_text(msg, uid):
    """자연어에서 일정 정보 추출: title, event_date, location, memo"""
    result = {'title': '', 'event_date': None, 'location': '', 'memo': ''}
    now = datetime.now(KST)

    # 1) 한글 날짜/시간 파싱
    dt = _parse_korean_datetime(msg, now)
    if dt:
        result['event_date'] = dt

    # 2) 장소 추출
    loc = ''
    for pat in [r'(?:에서|에\s*가는|장소[는은]?\s*|위치[는은]?\s*|곳[은은]?\s*)\s*([\w가-힣\s]+?)(?=\s*(?:일정|약속|추가|등록|예약|\d{1,2}시|오전|오후|$))',
                r'([\w가-힣]+(?:에|에서|으로|로))\s*(?:일정|약속|추가|등록|예약|\d{1,2}시|오전|오후|$)']:
        m = re.search(pat, msg)
        if m:
            loc = m.group(1).strip()
            loc = re.sub(r'(에서|에|으로|로|장소[는은]?|위치[는은]?|곳[은은]?)\s*$', '', loc).strip()
            if len(loc) >= 2:
                break
    result['location'] = loc

    # 3) 제목 추출 (대상 + 내용을 짧게)
    title = msg
    words = title.split()
    cleaned = []
    for w in words:
        w_clean = re.sub(r'[~.!,?]+$', '', w)
        is_kw = any(kw in w_clean for kw in SCHEDULE_KEYWORDS)
        is_time = bool(re.match(r'^(오전|오후|아침|저녁|밤|내일|모레|오늘|글피|다음주|이번주|다다음주|월요일|화요일|수요일|목요일|금요일|토요일|일요일|월|화|수|목|금|토|일)$', w_clean)) or bool(re.match(r'^\d{1,2}시(\d{1,2}분)?$', w_clean)) or bool(re.match(r'^\d{1,2}:\d{2}$', w_clean)) or bool(re.match(r'^\d{1,2}월$|^\d{1,2}일$|^\d{4}년$', w_clean)) or bool(re.match(r'^\d{1,2}/\d{1,2}$', w_clean))
        if is_kw or is_time:
            continue
        if w_clean == loc or (loc and w_clean in loc.split()):
            continue
        # 조사 제거
        w_clean = re.sub(r'(을|를|이|가|은|는|의|과|와|으로|로|에서|에|께|한테)$', '', w_clean)
        if w_clean:
            cleaned.append(w_clean)
    title = ' '.join(cleaned).strip()
    if not title or len(title) < 2:
        title = '일정'
    result['title'] = title[:60]
    # 메모: 원본 메시지 저장 (출발/귀가시간은 저장 시 계산)
    result['memo'] = msg[:200]
    return result

def _geocode_location(loc_name):
    """장소명 → (lat,lng) 좌표"""
    if not loc_name:
        return None, None
    try:
        kakao_key = current_app.config.get('KAKAO_REST_API_KEY','')
        if not kakao_key:
            return None, None
        resp = requests.get('https://dapi.kakao.com/v2/local/search/keyword.json', params={
            'query': loc_name, 'size': 1
        }, headers={'Authorization': f'KakaoAK {kakao_key}'}, timeout=2)
        if resp.status_code == 200:
            docs = resp.json().get('documents', [])
            if docs:
                return float(docs[0].get('y',0)), float(docs[0].get('x',0))
    except:
        pass
    return None, None

def _resolve_location(location_name, uid):
    """카카오 키워드 검색으로 장소→좌표,주소,소요시간"""
    if not location_name:
        return None
    try:
        user = User.query.get(uid)
        kakao_key = current_app.config.get('KAKAO_REST_API_KEY', '')
        if not kakao_key:
            return None
        # 위치 기반으로 검색 (사용자 주소 근처)
        search_query = location_name
        if user and user.town:
            search_query = f'{user.town} {location_name}'
        resp = requests.get('https://dapi.kakao.com/v2/local/search/keyword.json', params={
            'query': search_query,
            'size': 1
        }, headers={'Authorization': f'KakaoAK {kakao_key}'}, timeout=3)
        if resp.status_code == 200:
            docs = resp.json().get('documents', [])
            if docs:
                p = docs[0]
                lat = float(p.get('y', 0))
                lng = float(p.get('x', 0))
                addr = p.get('road_address_name', '') or p.get('address_name', '')
                place_name = p.get('place_name', location_name)

                # 소요시간: 사용자 집 → 장소 (transit.py 사용)
                time_min = None
                dist_km = None
                if user and (user.curr_latitude or user.latitude):
                    from services.transit import haversine_km
                    home_lat = user.curr_latitude or user.latitude or 0
                    home_lng = user.curr_longitude or user.longitude or 0
                    if home_lat and home_lng:
                        dist_km = haversine_km(home_lat, home_lng, lat, lng)
                        time_min = round(dist_km * 15)

                return {'name': place_name, 'address': addr, 'latitude': lat, 'longitude': lng, 'travel_min': time_min, 'distance_km': round(dist_km, 1) if dist_km else None}
    except:
        pass
    return None

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
- 통벗: AI 개인비서. 기능: 대화(일반질문 직답·플랫폼안내), 말투 선택(친근/존중/엄격), 글쓰기 교정, 일정관리, 벗채팅, 재능발견"
통벗 기능:
- 대화: 일반적인 질문에는 직접 답변하고, 플랫폼 기능 질문에만 위 안내를 참고하세요.
- 📜 기록 버튼: 이전 대화 내용을 보여줍니다. 대화창 아래에 나타납니다.
- 글쓰기 탭: 글 작성 후 '교정부탁'을 누르면 AI가 맞춤법과 게시판을 추천해 줍니다.
- 일정/채팅: 각각 독립된 팝업창으로 열립니다. 프로필에서 버튼을 누르세요.

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
        prompt = f"""당신은 '{bot.bot_name}'입니다. '{user.username}'님의 개인 AI 도우미입니다.
말투: {tone_guide} | 성장: {lvl_name} Lv.{bot.level} | 친밀도: {bot.intimacy}

[대원칙]
1. 절대 거짓말 하지 않습니다. 모르면 모른다고 솔직히 말합니다.
2. 존재하지 않는 기능이나 URL을 절대 만들어내지 마세요.

[사고 방식]
답변하기 전에 다음 순서로 생각하세요:
1) 질문의 의도를 정확히 파악했는가?
2) 내가 아는 정보로 답할 수 있는가?
3) 모른다면 솔직히 모른다고 말한다.

[응답 원칙]
- 일반 질문에는 직접 답변하세요.
- 플랫폼 질문은 아래 [안내]의 정보만 사용하세요.
- 안내에 없는 기능은 "아직 그런 기능은 없습니다"라고 답하세요.
- 최종 답변만 2~3문장으로 출력하세요. 사고 과정은 출력하지 마세요.

[플랫폼 안내 - 플랫폼 기능 질문시에만 참고]
{PLATFORM_GUIDE}

[통벗 지식 공유]
다른 통벗들이 공유한 아래 지식이 있다면 참고하세요:
{_get_shared_knowledge(user_msg)}

회원: {user_msg}"""
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "max_tokens": 300},
            timeout=20)
        if r.status_code == 200:
            reply = r.json()['choices'][0]['message']['content']
            _save_knowledge(bot, user_msg, reply)
            return f"{_m['emoji']} {reply}"
    except:
        pass
    return f"{_m['emoji']} {user.username}님, 항상 응원하고 있어요. 무엇을 도와드릴까요?"

def _get_shared_knowledge(msg):
    try:
        words = msg.split()[:5]
        knowledge = BotKnowledge.query.order_by(BotKnowledge.useful_count.desc()).limit(30).all()
        matches = []
        for k in knowledge:
            if any(w in (k.topic or '') for w in words):
                matches.append(f"- {k.topic}: {k.content[:100]}")
        return '\n'.join(matches[:3]) if matches else '없음'
    except:
        return '없음'

def _save_knowledge(bot, user_msg, reply):
    try:
        if len(reply) > 30 and len(user_msg) > 10:
            words = user_msg.split()
            topic = ' '.join(words[:2]) if len(words) >= 2 else words[0]
            topic = topic[:50]
            k = BotKnowledge.query.filter_by(topic=topic).first()
            if k:
                k.useful_count = (k.useful_count or 0) + 1
            else:
                db.session.add(BotKnowledge(topic=topic, content=reply[:200], source_bot=bot.bot_name))
            db.session.commit()
    except:
        pass

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

@tongbot_bp.route('/api/bot/schedule/ai', methods=['POST'])
def bot_schedule_ai():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    msg = request.json.get('message', '').strip()
    if not msg:
        return jsonify({"error": "메시지를 입력하세요."})
    user = User.query.get(uid)
    bot = _get_bot(uid)
    return jsonify(bot_schedule_ai_internal(uid, msg, user, bot))

def _format_schedule_content(raw_text, bot_name, sched_context):
    """통벗이 일정 내용을 보기좋게 편집 + 필요시 코멘트 추가"""
    lines = []
    # 핵심 내용 정리
    key_points = []
    for part in raw_text.replace(',',' ').replace('.',' ').split():
        part = part.strip()
        if len(part) >= 2:
            key_points.append(part)

    # 깔끔한 내용으로 정리
    content = raw_text.strip()
    if len(content) > 10:
        content = '📋 ' + content

    # 관련 정보가 있으면 코멘트 추가
    comment = None
    lower = raw_text.lower()
    if any(kw in lower for kw in ['보험','계약','약관','청약']):
        comment = f'{{[{bot_name} 생각]}} 보험 관련 건은 꼼꼼히 비교하시고, 필요시 법률상담을 이용하세요.'
    elif any(kw in lower for kw in ['모임','약속','만남','식사']):
        comment = f'{{[{bot_name} 생각]}} 약속 전에 교통편 확인하시고, 늦으면 미리 연락하세요.'
    elif any(kw in lower for kw in ['병원','진료','건강','수술']):
        comment = f'{{[{bot_name} 생각]}} 진료 전 준비물(신분증, 보험증) 챙기세요.'
    elif any(kw in lower for kw in ['쇼핑','구매','장보기','마트','시장','옷','신발','가전','가구','선물']):
        stores = _find_nearby_stores(sched_context, 3)
        if stores:
            comment = f'{{[{bot_name} 생각]}} 근처 추천 가게: {", ".join(stores)}'
        else:
            comment = f'{{[{bot_name} 생각]}} 공유마당에 등록된 동네가게를 확인해 보세요.'

    result = content
    if comment:
        result += '\n\n' + comment
    return result

def _find_nearby_stores(context, limit=3):
    """근처 동네가게 찾기"""
    try:
        stores = StoreInfo.query.limit(limit).all()
        if stores:
            return [s.name for s in stores]
        reports = ShareReport.query.filter_by(status='approved').filter(ShareReport.title.isnot(None)).limit(limit).all()
        return [r.title for r in reports if r.title]
    except:
        return []

def _search_shopping(query):
    """네이버 쇼핑 검색 + 최저/최고가"""
    try:
        # 검색API 전용키 우선, 없으면 config 기본값
        ncid = os.getenv('NAVER_SEARCH_CLIENT_ID','') or 'Vi403Ckfdg8NGRPDfBin'
        ncsec = os.getenv('NAVER_SEARCH_CLIENT_SECRET','') or 'bepKiJZvWx'
        if not ncid:
            return None
        resp = requests.get('https://openapi.naver.com/v1/search/shop.json', params={
            'query': query, 'display': 5, 'sort': 'sim'
        }, headers={'X-Naver-Client-Id': ncid, 'X-Naver-Client-Secret': ncsec}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get('items', [])
            if items:
                prices = sorted([int(i.get('lprice',0)) for i in items if i.get('lprice')])
                return {
                    'items': [{
                        'title': i.get('title','').replace('<b>','').replace('</b>',''),
                        'price': int(i.get('lprice',0)),
                        'link': i.get('link',''),
                        'mall': i.get('mallName',''),
                        'image': i.get('image','')
                    } for i in items[:5]],
                    'min_price': min(prices) if prices else 0,
                    'max_price': max(prices) if prices else 0,
                    'count': len(items)
                }
    except:
        pass
    return None

SHOPPING_TRIGGERS = ['가격','얼마','사고','구매','쇼핑','파는','싼','비싼','최저가','최고가','가성비','추천','어디서','파나요','사나요']

def _get_proactive_suggestions(user, msg):
    """문맥 기반 추천 제안"""
    suggestions = []
    now = datetime.now(KST)
    h = now.hour
    has_home = bool(user.curr_latitude or user.latitude)

    # 시간대별 추천
    if 7 <= h <= 9:
        suggestions.append({'text': '오늘 일정 확인해 보세요', 'action': 'schedule'})
    if 17 <= h <= 20 and has_home:
        suggestions.append({'text': '귀가길 안내 받으실래요?', 'action': 'home'})
    if h >= 21:
        suggestions.append({'text': '내일 일정 미리 등록해 두세요', 'action': 'schedule'})

    # 대화 기반 추천
    if any(kw in msg for kw in ['뭐','어디','뭐하지','심심','할일']):
        suggestions.append({'text': '위치기반안내에서 주변 명소 확인', 'action': 'construction'})
    if any(kw in msg for kw in ['심심','할말','얘기','대화','외로']):
        suggestions.append({'text': '벗 채팅으로 이웃과 대화해 보세요', 'action': 'chat'})

    # 체크 안한 기능 추천 (랜덤 1개)
    all_tips = [
        {'text': '프로필에서 벗 신청하고 이웃과 소통하세요', 'action': 'friend'},
        {'text': '공유마당에 동네 소식 올려보세요', 'action': 'share'},
        {'text': '위치 보정하면 1닢 드려요!', 'action': 'location'},
        {'text': '통벗 말투를 바꿔보세요 (친근/존중/엄격)', 'action': 'tone'},
        {'text': '꿈꾸기에 마을 제안 올려보세요', 'action': 'dream'},
    ]
    import random
    suggestions.append(random.choice(all_tips))

    return suggestions[:3] if suggestions else None

def bot_schedule_ai_internal(uid, msg, user, bot=None):
    now = datetime.now(KST)
    today_str = now.strftime('%Y-%m-%d %H:%M')
    weekday = ['월','화','수','목','금','토','일'][now.weekday()]

    # 기존 일정 + 벗 목록
    scheds = TongBotSchedule.query.filter_by(user_id=uid).order_by(TongBotSchedule.event_date.asc()).limit(20).all()
    sched_list = []
    for s in scheds:
        evt = s.event_date
        if evt:
            s_str = f"#{s.id} {evt.strftime('%m/%d %H:%M')}"
            if s.end_date:
                s_str += f"~{s.end_date.strftime('%H:%M')}"
            s_str += f" {s.title}"
            if s.location:
                s_str += f" @{s.location}"
            sched_list.append(s_str)

    home_addr = f"{user.town or ''} {user.village or ''}".strip()
    if hasattr(user, 'curr_address') and user.curr_address:
        home_addr = user.curr_address

    system_prompt = f"""당신은 일정관리 AI입니다. 사용자의 메시지를 분석하여 아래 JSON 형식 중 하나로만 응답하세요. 다른 말은 절대 하지 마세요.

현재: {today_str} ({weekday}요일)
사용자 기본주소: {home_addr}
내 벗: (기능 준비 중)
기존 일정:
{chr(10).join(sched_list) if sched_list else '(없음)'}

[응답 형식 - 하나만 선택]
1. 일정 생성: {{"action":"create","title":"짧은제목","event_date":"2026-06-27T15:00","location":"장소명","description":"설명"}}
2. 일정 조회: {{"action":"query","period":"today|tomorrow|week|all"}}
3. 일정 삭제: {{"action":"delete","id":일정번호}}
4. 일정 변경: {{"action":"update","id":일정번호,"changes":{{"title":"새제목","description":"메모내용"}}}}
     ※ id 대신 keyword로 제목 검색 가능: {{"action":"update","keyword":"양지애","changes":{{"description":"메모내용"}}}}
5. 빈시간 찾기: {{"action":"find_free","date":"2026-06-27","duration_min":60}}
6. 공통 빈시간: {{"action":"find_common","date":"2026-06-27","friend_names":["벗이름1","벗이름2"],"duration_min":60}}
7. 일반 대화: {{"action":"chat","reply":"친절한답변"}}

[규칙]
- event_date는 반드시 ISO형식(YYYY-MM-DDTHH:MM)으로
- title은 30자 이내로 간결하게
- 날짜가 언급되지 않으면 오늘 기준으로
- "내일"은 {now.date() + timedelta(days=1)} 기준
- 시간이 언급되지 않으면 오전 9시로
- id는 기존 일정의 #번호를 참고
- find_free 시 duration_min 기본값 60"""

    try:
        groq_key = current_app.config.get('GROQ_API_KEY', os.getenv('GROQ_API_KEY', ''))
        if not groq_key:
            return {"reply": "AI 서비스가 현재 이용 불가능합니다.", "action": "chat"}

        resp = requests.post('https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {groq_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'llama-3.1-8b-instant',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': msg}
                ],
                'temperature': 0.1,
                'max_tokens': 300
            }, timeout=10)
        ai_text = resp.json()['choices'][0]['message']['content'].strip()
        # JSON 응답만 추출
        json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', ai_text, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{.*\}', ai_text, re.DOTALL)
        if not json_match:
            return {"reply": ai_text[:200], "action": "chat"}

        action_data = json.loads(json_match.group())
    except:
        return {"reply": "죄송합니다. 일정을 이해하지 못했어요. 다시 말씀해 주세요.", "action": "chat"}

    action = action_data.get('action', 'chat')

    if action == 'create':
        try:
            evt_str = action_data.get('event_date', '')
            evt = datetime.fromisoformat(evt_str) if evt_str else None
            if not evt:
                return {"reply": "날짜/시간을 알 수 없습니다.", "action": "chat"}
            s = TongBotSchedule(
                user_id=uid,
                title=action_data.get('title', '일정'),
                description=action_data.get('description', ''),
                content=action_data.get('content', ''),
                event_date=evt,
                location=action_data.get('location', ''),
                memo='AI 생성'
            )
            db.session.add(s)
            db.session.commit()
            dt_str = evt.strftime('%m/%d %H:%M')
            fb = [f"📅 오늘 일정에 등록되었습니다!"]
            fb.append(f"제목: {s.title}")
            fb.append(f"시간: {dt_str}")
            if s.location:
                fb.append(f"장소: {s.location}")
            user_home = User.query.get(uid)
            if s.location and user_home:
                loc_lat, loc_lng = _geocode_location(s.location)
                home_lat = user_home.curr_latitude or user_home.latitude
                home_lng = user_home.curr_longitude or user_home.longitude
                if loc_lat and home_lat:
                    from services.transit import haversine_km
                    d = haversine_km(home_lat, home_lng, loc_lat, loc_lng)
                    travel_min = round(d * 15)
                    dep_time = evt - timedelta(minutes=travel_min + 15)
                    ret_time = evt + timedelta(hours=1, minutes=travel_min)
                    fb.append(f"출발시간: {dep_time.strftime('%H:%M')} (이동 약{travel_min}분)")
                    fb.append(f"귀가가능시간: {ret_time.strftime('%H:%M')}")
                else:
                    fb.append("기본장소에서 하시는 모임이 아니신데 장소가 정확하지 않아서 출발시간과 귀가시간을 특정하기 어렵습니다.")
                    fb.append("상세주소를 알려주시면 출발시간과 귀가시간을 알려 드리겠습니다.")
            reply = '\n'.join(fb)
            return {"reply": reply, "action": "create", "schedule": {"id": s.id, "title": s.title, "date": dt_str}}
        except Exception as e:
            return {"reply": f"일정 저장 실패: {e}", "action": "chat"}

    elif action == 'query':
        period = action_data.get('period', 'all')
        scheds = TongBotSchedule.query.filter_by(user_id=uid).order_by(TongBotSchedule.event_date.asc())
        if period == 'today':
            scheds = scheds.filter(TongBotSchedule.event_date >= now.strftime('%Y-%m-%d')).filter(TongBotSchedule.event_date < (now + timedelta(days=1)).strftime('%Y-%m-%d'))
        elif period == 'tomorrow':
            tm = now + timedelta(days=1)
            scheds = scheds.filter(TongBotSchedule.event_date >= tm.strftime('%Y-%m-%d')).filter(TongBotSchedule.event_date < (tm + timedelta(days=1)).strftime('%Y-%m-%d'))
        elif period == 'week':
            scheds = scheds.filter(TongBotSchedule.event_date >= now.strftime('%Y-%m-%d')).filter(TongBotSchedule.event_date < (now + timedelta(days=7)).strftime('%Y-%m-%d'))
        result = scheds.limit(15).all()
        if not result:
            return {"reply": "해당 기간에 등록된 일정이 없습니다.", "action": "query"}
        lines = [f"📅 {period} 일정 ({len(result)}건):"]
        for s in result:
            evt = s.event_date
            line = f"  {evt.strftime('%m/%d %H:%M')} {s.title}"
            if s.location:
                line += f" @{s.location}"
            lines.append(line)
        return {"reply": '\n'.join(lines), "action": "query"}

    elif action == 'delete':
        sid = action_data.get('id')
        s = TongBotSchedule.query.filter_by(id=sid, user_id=uid).first()
        if not s:
            return {"reply": f"#{sid} 일정을 찾을 수 없습니다.", "action": "chat"}
        title = s.title
        db.session.delete(s)
        db.session.commit()
        return {"reply": f"🗑️ '{title}' 일정을 삭제했습니다.", "action": "delete"}

    elif action == 'update':
        sid = action_data.get('id')
        s = None
        if sid:
            s = TongBotSchedule.query.filter_by(id=sid, user_id=uid).first()
        # id 없으면 제목 키워드로 검색
        if not s:
            keyword = action_data.get('keyword', '')
            if not keyword:
                # changes의 title에서 키워드 추출 시도
                ch_title = action_data.get('changes', {}).get('title', '')
                for word in (msg + ' ' + ch_title).split():
                    if len(word) >= 2:
                        found = TongBotSchedule.query.filter(
                            TongBotSchedule.user_id == uid,
                            TongBotSchedule.title.ilike(f'%{word}%')
                        ).order_by(TongBotSchedule.event_date.desc()).first()
                        if found:
                            s = found
                            break
        if not s:
            return {"reply": f"관련 일정을 찾을 수 없습니다.", "action": "chat"}
        changes = action_data.get('changes', {})
        updated = []
        if 'title' in changes:
            s.title = changes['title']; updated.append('제목')
        if 'event_date' in changes:
            s.event_date = datetime.fromisoformat(changes['event_date']); updated.append('시간')
        if 'location' in changes:
            s.location = changes['location']; updated.append('장소')
        if 'description' in changes:
            raw = changes['description']
            bot_name = bot.bot_name if bot else '통벗'
            s.description = raw
            s.content = _format_schedule_content(raw, bot_name, s.title)
            updated.append('내용')
        if 'content' in changes:
            s.content = changes['content']
            if '내용' not in updated: updated.append('내용')
        db.session.commit()
        return {"reply": f"✏️ {s.title} 일정이 수정됨 ({', '.join(updated)})", "action": "update"}

    elif action == 'find_free':
        date_str = action_data.get('date', now.strftime('%Y-%m-%d'))
        duration = int(action_data.get('duration_min', 60))
        day_scheds = TongBotSchedule.query.filter_by(user_id=uid).filter(
            TongBotSchedule.event_date >= f'{date_str} 00:00',
            TongBotSchedule.event_date <= f'{date_str} 23:59'
        ).order_by(TongBotSchedule.event_date.asc()).all()
        busy = [(9*60, 9*60)]
        for s in day_scheds:
            evt = s.event_date
            if evt:
                start_min = evt.hour * 60 + evt.minute
                end_min = start_min + 60
                if s.end_date:
                    end_min = s.end_date.hour * 60 + s.end_date.minute
                busy.append((start_min, end_min))
        busy.append((21*60, 21*60))
        busy.sort()
        free_slots = []
        for i in range(len(busy) - 1):
            gap = busy[i+1][0] - busy[i][1]
            if gap >= duration:
                start_h = busy[i][1] // 60
                start_m = busy[i][1] % 60
                end_h = busy[i+1][0] // 60
                end_m = busy[i+1][0] % 60
                free_slots.append(f"{start_h:02d}:{start_m:02d}~{end_h:02d}:{end_m:02d}")
        if free_slots:
            return {"reply": f"🕐 {date_str} 빈 시간 ({duration}분 이상):\n" + '\n'.join(f"  {s}" for s in free_slots[:5]), "action": "find_free"}
        else:
            return {"reply": f"😔 {date_str}에 {duration}분 이상 빈 시간이 없습니다.", "action": "find_free"}

    elif action == 'find_common':
        date_str = action_data.get('date', now.strftime('%Y-%m-%d'))
        duration = int(action_data.get('duration_min', 60))
        friend_names = action_data.get('friend_names', [])
        if not friend_names:
            return {"reply": "어떤 벗과 일정을 조율할까요?", "action": "chat"}
        friend_users = User.query.filter(User.username.in_(friend_names)).all()
        if not friend_users:
            return {"reply": "해당 벗을 찾을 수 없습니다.", "action": "chat"}
        friend_ids = [f.id for f in friend_users]
        all_busy = [(9*60, 9*60)]
        for fid in friend_ids:
            f_scheds = TongBotSchedule.query.filter_by(user_id=fid).filter(
                TongBotSchedule.event_date >= f'{date_str} 00:00',
                TongBotSchedule.event_date <= f'{date_str} 23:59'
            ).all()
            for s in f_scheds:
                sm = s.event_date.hour * 60 + s.event_date.minute
                em = sm + 60
                if s.end_date:
                    em = s.end_date.hour * 60 + s.end_date.minute
                all_busy.append((sm, em))
        all_busy.append((21*60, 21*60))
        all_busy.sort()
        free_slots = []
        for i in range(len(all_busy)-1):
            gap = all_busy[i+1][0] - all_busy[i][1]
            if gap >= duration:
                sh = all_busy[i][1] // 60; sm = all_busy[i][1] % 60
                eh = all_busy[i+1][0] // 60; em = all_busy[i+1][0] % 60
                free_slots.append(f"{sh:02d}:{sm:02d}~{eh:02d}:{em:02d}")
        fnames = ', '.join(friend_names[:3])
        if free_slots:
            return {"reply": f"🤝 {fnames} 공통 빈시간 ({date_str}, {duration}분 이상):\n" + '\n'.join(f"  ✅ {s}" for s in free_slots[:5]), "action": "find_common"}
        else:
            return {"reply": f"😔 {date_str}에 {fnames} 모두 가능한 시간이 없습니다.", "action": "find_common"}

    else:
        return {"reply": action_data.get('reply', '무엇을 도와드릴까요?'), "action": "chat"}

@tongbot_bp.route('/api/bot/schedule/calc-time', methods=['POST'])
def bot_schedule_calc_time():
    """장소명→출발/귀가시간 계산 (도보/자전거/대중교통)"""
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"로그인"}),401
    data = request.get_json()
    loc = data.get('location','').strip()
    event_time = data.get('event_time','')
    if not loc: return jsonify({})
    user = User.query.get(uid)
    home_lat = user.curr_latitude or user.latitude or 0
    home_lng = user.curr_longitude or user.longitude or 0
    if not home_lat:
        return jsonify({"error": "기본주소가 설정되지 않았습니다. 회원정보에서 이웃인증을 해주세요."})
    try:
        loc_lat, loc_lng = _geocode_location(loc)
        if not loc_lat:
            # 좌표 못찾으면 양평군 기준으로 대략 계산
            return jsonify({"error": f"'{loc}'의 위치를 찾을 수 없습니다.", "walk":{"dep":"","ret":""}})
        from services.transit import haversine_km
        d = haversine_km(home_lat, home_lng, loc_lat, loc_lng)
        if d < 0.05: d = 0.5  # 너무 가까우면 최소 500m로
        parts = event_time.split(':')
        h = int(parts[0]) if parts and parts[0] else 9
        m = int(parts[1]) if len(parts)>1 and parts[1] else 0
        et = datetime.now(KST).replace(hour=h, minute=m, second=0, microsecond=0)
        # 막차 정보
        last_transit = ""
        try:
            if user.curr_town and user.curr_village:
                from services.transit import suggest_optimal_departure
                sug = suggest_optimal_departure(home_lat, home_lng, user.curr_town, user.curr_village)
                if sug and sug.get('last_transit_from_station'):
                    last_transit = f"막차 {sug['last_transit_from_station']} ({sug.get('direction','')})"
        except: pass
        return jsonify({
            "walk": {"min": round(d*15), "dep": (et - timedelta(minutes=round(d*15)+15)).strftime('%H:%M')},
            "bike": {"min": round(d*5), "dep": (et - timedelta(minutes=round(d*5)+10)).strftime('%H:%M')},
            "transit": {"min": round(d*5+15), "dep": (et - timedelta(minutes=round(d*5)+25)).strftime('%H:%M'), "ret": (et + timedelta(hours=1, minutes=round(d*5)+15)).strftime('%H:%M'), "last_transit": last_transit},
            "distance_km": round(d,1)
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@tongbot_bp.route('/api/bot/schedule', methods=['GET', 'POST'])
def bot_schedule():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    if request.method == 'GET':
        user = User.query.get(uid)
        home_lat = user.curr_latitude or user.latitude
        home_lng = user.curr_longitude or user.longitude
        schedules = TongBotSchedule.query.filter_by(user_id=uid).order_by(TongBotSchedule.event_date.asc()).limit(30).all()
        result_list = []
        for s in schedules:
            item = {
                "id": s.id, "title": s.title, "description": s.description,
                "content": s.content or s.description or '',
                "memo": s.memo, "location": s.location,
                "event_date": s.event_date.strftime("%Y-%m-%d %H:%M") if s.event_date else "",
                "end_date": s.end_date.strftime("%Y-%m-%d %H:%M") if s.end_date else "",
                "departure_location": s.departure_location or '',
                "return_location": s.return_location or '',
                "departure_time": s.departure_time.strftime('%H:%M') if s.departure_time else '',
                "return_time": s.return_time.strftime('%H:%M') if s.return_time else '',
                "invited": s.invited_user_ids, "color": "gray"
            }
            # 컬러 판정 (이동/귀가는 info, 위치 있는 일반일정은 blue, 종일은 red)
            is_move = '이동' in s.title or '귀가' in s.title
            evt = s.event_date
            if evt:
                has_time = evt.hour != 0 or evt.minute != 0
                is_allday = not has_time and (not s.end_date or (s.end_date.hour == 23 and s.end_date.minute == 59))
                if is_move:
                    item["color"] = "info"
                elif is_allday:
                    item["color"] = "red"
                elif s.location and not is_move:
                    item["color"] = "blue"
                else:
                    item["color"] = "gray"
            result_list.append(item)
        return jsonify({"schedules": result_list})
    data = request.json
    end_date = None
    if data.get('end_date'):
        try: end_date = datetime.fromisoformat(data['end_date'])
        except: pass
    s = TongBotSchedule(user_id=uid, title=data.get('title',''), description=data.get('description',''),
        event_date=datetime.fromisoformat(data.get('event_date','')),
        end_date=end_date,
        location=data.get('location',''),
        memo=data.get('memo',''),
        invited_user_ids=data.get('invited',''),
        departure_location=data.get('departure_location',''),
        return_location=data.get('return_location',''))
    if data.get('departure_time'):
        s.departure_time = datetime.fromisoformat(data['departure_time']) if data['departure_time'] else None
    if data.get('return_time'):
        s.return_time = datetime.fromisoformat(data['return_time']) if data['return_time'] else None
    db.session.add(s)
    db.session.flush()

    # Auto-create 이동/귀가 if location is set and not home
    location = data.get('location','')
    auto_created = []
    if location:
        user = User.query.get(uid)
        home_addr = f"{user.town or ''} {user.village or ''}".strip()
        if user.curr_address: home_addr = user.curr_address
        home_lat = user.curr_latitude
        home_lng = user.curr_longitude
        evt_start = datetime.fromisoformat(data.get('event_date',''))
        if user.temp_address and user.temp_latitude and user.temp_longitude and user.temp_start_date and user.temp_end_date:
            if user.temp_start_date <= evt_start <= user.temp_end_date:
                home_addr = f"[임시] {user.temp_address}"
                home_lat = user.temp_latitude
                home_lng = user.temp_longitude
        naver_id = current_app.config.get('NAVER_CLIENT_ID', os.getenv('NAVER_CLIENT_ID', ''))
        naver_secret = current_app.config.get('NAVER_CLIENT_SECRET', os.getenv('NAVER_CLIENT_SECRET', ''))
        from services.directions import plan_segment, format_itinerary

        loc_lat, loc_lng = _geocode_location(location)
        if loc_lat and loc_lng and home_lat and home_lng:
            from services.transit import haversine_km
            d = haversine_km(home_lat, home_lng, loc_lat, loc_lng)
            if d > 1.0:
                evt_end = end_date or (evt_start + timedelta(hours=1))
                stime = evt_start.strftime("%H:%M")

                # 이동: event_date=도착시간(약속-5분), departure_time=출발시간(역산)
                arr_dt = evt_start - timedelta(minutes=5)
                plan_to = plan_segment(home_addr, home_lat, home_lng, location, loc_lat, loc_lng, arr_dt.strftime("%H:%M"),
                    home_town=user.town or '', home_village=user.village or '',
                    naver_id=naver_id, naver_secret=naver_secret)
                plan_to.update({"from_lat":home_lat,"from_lng":home_lng,"to_lat":loc_lat,"to_lng":loc_lng})
                dep_dt = arr_dt - timedelta(minutes=plan_to['total_min'])
                move = TongBotSchedule(user_id=uid, title=f"{data.get('title','')} 이동",
                    description=format_itinerary(plan_to),
                    content=json.dumps(plan_to, ensure_ascii=False),
                    event_date=arr_dt, departure_time=dep_dt, location=location,
                    memo=f"이동 {plan_to['total_min']}분", departure_location=home_addr, return_location=location)
                db.session.add(move)
                db.session.flush()
                auto_created.append({"id":move.id,"title":move.title,"type":"move","arrival":arr_dt.strftime("%H:%M"),"departure":dep_dt.strftime("%H:%M")})

                # 귀가: 같은 날 기존 귀가 삭제 후 마지막 위치 기준으로 새로 생성
                evt_date_start = evt_start.replace(hour=0, minute=0, second=0)
                evt_date_end = evt_start.replace(hour=23, minute=59, second=59)
                existing_returns = TongBotSchedule.query.filter(
                    TongBotSchedule.user_id == uid,
                    TongBotSchedule.title == "집으로 이동",
                    TongBotSchedule.event_date >= evt_date_start,
                    TongBotSchedule.event_date <= evt_date_end,
                    TongBotSchedule.id != s.id
                ).all()
                for er in existing_returns:
                    db.session.delete(er)

                # 귀가: event_date=출발시간, return_time=도착시간
                target_arrival = "22:00"
                plan_home = plan_segment(location, loc_lat, loc_lng, home_addr, home_lat, home_lng, target_arrival,
                    home_town=user.town or '', home_village=user.village or '',
                    naver_id=naver_id, naver_secret=naver_secret)
                plan_home.update({"from_lat":loc_lat,"from_lng":loc_lng,"to_lat":home_lat,"to_lng":home_lng})
                ret_dep = datetime.strptime(f"2026-07-11 {plan_home['departure']}", "%Y-%m-%d %H:%M")
                if ret_dep < evt_end:
                    ret_dep = evt_end + timedelta(minutes=5)
                ret_arr = ret_dep + timedelta(minutes=plan_home['total_min'])
                home_return = TongBotSchedule(user_id=uid, title="집으로 이동",
                    description=format_itinerary(plan_home),
                    content=json.dumps(plan_home, ensure_ascii=False),
                    event_date=ret_dep, return_time=ret_arr, location=home_addr,
                    memo=f"귀가 {plan_home['total_min']}분", departure_location=location, return_location=home_addr)
                db.session.add(home_return)
                db.session.flush()
                auto_created.append({"id":home_return.id,"title":"집으로 이동","type":"return","departure":ret_dep.strftime("%H:%M"),"arrival":ret_arr.strftime("%H:%M")})

    db.session.commit()
    return jsonify({"success": True, "id": s.id, "auto_created": auto_created})

@tongbot_bp.route('/api/bot/schedule/update', methods=['POST'])
def bot_schedule_update():
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"로그인"}),401
    data = request.get_json()
    s = TongBotSchedule.query.get(data.get('id'))
    if not s or s.user_id != uid: return jsonify({"error":"권한없음"}),403
    if data.get('title'): s.title = data['title']
    if data.get('location'): s.location = data['location']
    if data.get('description'): s.description = data['description']
    if data.get('memo'): s.memo = data['memo']
    if data.get('departure_location') is not None: s.departure_location = data['departure_location']
    if data.get('return_location') is not None: s.return_location = data['return_location']
    if data.get('event_date'):
        try: s.event_date = datetime.fromisoformat(data['event_date'])
        except: pass
    if data.get('end_date'):
        try: s.end_date = datetime.fromisoformat(data['end_date'])
        except: pass
    db.session.commit()
    return jsonify({"success": True})

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
    return render_template('schedule2.html')
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
    from services.security import validate_upload, secure_save
    ok, msg = validate_upload(f)
    if not ok:
        return jsonify({"error": msg})
    try:
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'tongbot')
        os.makedirs(upload_dir, exist_ok=True)
        url = secure_save(f, upload_dir)
        return jsonify({"url": url, "filename": os.path.basename(url)})
    except Exception as e:
        return jsonify({"error": str(e)})

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

@tongbot_bp.route('/api/bot/trip/plan', methods=['POST'])
def bot_trip_plan():
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"로그인 필요"}), 401
    msg = request.json.get('message','').strip()
    if not msg: return jsonify({"error":"메시지를 입력하세요."})
    user = User.query.get(uid)
    if not user: return jsonify({"error":"사용자 없음"}), 404

    def _hm_to_min(t):
        p=t.split(':'); return int(p[0])*60+int(p[1]) if len(p)>1 else int(p[0])

    home_addr = f"{user.town or ''} {user.village or ''}".strip()
    if user.curr_address: home_addr = user.curr_address
    home_lat = user.curr_latitude
    home_lng = user.curr_longitude

    office_addr = user.office_address or ''
    office_lat = user.office_latitude
    office_lng = user.office_longitude
    work_start = user.work_start_time or '09:00'

    groq_key = current_app.config.get('GROQ_API_KEY', os.getenv('GROQ_API_KEY',''))
    if not groq_key: return jsonify({"error":"AI 서비스 불가"})

    # Step 1: Parse date first
    KST = timedelta(hours=9)
    today = datetime.now(KST)
    date_prompt = f"""Extract the date from this Korean text as YYYY-MM-DD format. If "오늘" → {today.strftime('%Y-%m-%d')}. If "내일" → {(today+timedelta(days=1)).strftime('%Y-%m-%d')}. If month/day given like "7월11일" → 2026-07-11.
Output ONLY the date in YYYY-MM-DD format, nothing else.
Text: {msg}"""
    try:
        dr = requests.post('https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization':f'Bearer {groq_key}','Content-Type':'application/json'},
            json={'model':'llama-3.1-8b-instant','messages':[{'role':'user','content':date_prompt}],'temperature':0,'max_tokens':20}, timeout=10)
        event_date_str = dr.json()['choices'][0]['message']['content'].strip()
        import re as _re
        dm = _re.search(r'\d{4}-\d{2}-\d{2}', event_date_str)
        if dm: event_date_str = dm.group()
        else: event_date_str = today.strftime('%Y-%m-%d')
    except:
        event_date_str = today.strftime('%Y-%m-%d')

    # Step 2: Parse itinerary stops
    system_prompt = f"""Parse the user's Korean itinerary into a JSON array of stops with format:
[{{"title":"리얼리스트 미팅","name":"리얼리스트","time":"10:00","location":"양평읍 리얼리스트","type":"meeting"}}]

Rules:
- "title" is schedule title including activity (미팅, 방문, 모임 etc.)
- "name" is short place name for 이동 schedule naming
- "time" is arrival time in HH:MM format. 오전10시→10:00, 오후2시→14:00, 저녁7시→19:00
- "location" is full location for geocoding (include town/area prefix like 양평읍, 옥천, 용문)
- "type" is always "meeting"
- Output ONLY JSON array, no explanation
- Include ALL stops mentioned"""
    try:
        resp = requests.post('https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization':f'Bearer {groq_key}','Content-Type':'application/json'},
            json={'model':'llama-3.1-8b-instant','messages':[
                {'role':'system','content':system_prompt},
                {'role':'user','content':msg}
            ],'temperature':0.1,'max_tokens':1000}, timeout=15)
        ai_text = resp.json()['choices'][0]['message']['content'].strip()
        import re, json as _json
        json_match = re.search(r'\[.*\]', ai_text, re.DOTALL)
        if not json_match: return jsonify({"error":"일정을 파싱하지 못했습니다","ai_raw":ai_text})
        stops = _json.loads(json_match.group())
    except Exception as e:
        return jsonify({"error":f"AI 파싱 오류: {str(e)}"})

    if not stops: return jsonify({"error":"일정이 없습니다."})

    # Check temp accommodation for this date
    try:
        evt_date = datetime.strptime(event_date_str, '%Y-%m-%d')
        if user.temp_address and user.temp_latitude and user.temp_longitude and user.temp_start_date and user.temp_end_date:
            if user.temp_start_date <= evt_date <= user.temp_end_date:
                home_addr = f"[임시] {user.temp_address}"
                home_lat = user.temp_latitude
                home_lng = user.temp_longitude
    except:
        pass

    from services.directions import plan_segment, format_itinerary, haversine_km
    import json as _json
    naver_id = current_app.config.get('NAVER_CLIENT_ID', os.getenv('NAVER_CLIENT_ID', ''))
    naver_secret = current_app.config.get('NAVER_CLIENT_SECRET', os.getenv('NAVER_CLIENT_SECRET', ''))

    entries = []
    first_stop = stops[0]
    last_stop = stops[-1]

    # Step 3: Create meeting schedules
    for s in stops:
        stime = s.get('time','12:00')
        stitle = s.get('title','') or s.get('name','')
        sname = s.get('name','') or stitle
        sloc = s.get('location','') or sname
        evt_dt = datetime.strptime(f"{event_date_str} {stime}", "%Y-%m-%d %H:%M")
        evt = TongBotSchedule(user_id=uid, title=stitle,
            event_date=evt_dt, location=sloc, memo="")
        db.session.add(evt)
        db.session.flush()
        entries.append({"id":evt.id,"title":stitle,"date":event_date_str,"time":stime,"location":sloc,"type":"meeting"})

    # Step 4: Check if first stop is at office → can we go from office?
    need_home_start = False
    origin_label = f"회사({office_addr})"
    origin_lat = office_lat
    origin_lng = office_lng

    if office_addr and office_lat:
        fs_loc = first_stop.get('location','') or first_stop.get('name','')
        loc_lat, loc_lng = _geocode_location(fs_loc)
        if loc_lat and office_lat:
            d = haversine_km(office_lat, office_lng, loc_lat, loc_lng)
            if d > 1.0:
                ws = _hm_to_min(work_start)
                arr = _hm_to_min(first_stop.get('time','10:00'))
                avail_min = arr - ws
                travel_need = round(d / 20 * 60) + 25
                if travel_need > avail_min:
                    need_home_start = True

    if need_home_start or not office_addr or not office_lat:
        origin_label = f"집({home_addr})"
        origin_lat = home_lat
        origin_lng = home_lng

    # Step 5: Create 이동 schedules between consecutive stops
    prev_lat = origin_lat
    prev_lng = origin_lng
    prev_name = origin_label

    for i, stop in enumerate(stops):
        sname = stop.get('name','')
        sloc = stop.get('location','') or sname
        stime = stop.get('time','12:00')
        loc_lat, loc_lng = _geocode_location(sloc)
        if not loc_lat:
            loc_lat = prev_lat or home_lat
            loc_lng = prev_lng or home_lng

        if prev_lat and loc_lat:
            plan = plan_segment(prev_name, prev_lat, prev_lng, sname, loc_lat, loc_lng, stime,
                              home_town=user.town or '', home_village=user.village or '',
                              naver_id=naver_id, naver_secret=naver_secret)
            plan.update({"from_lat":prev_lat,"from_lng":prev_lng,"to_lat":loc_lat,"to_lng":loc_lng})
            memo = format_itinerary(plan)
            arr_dt = datetime.strptime(f"{event_date_str} {stime}", "%Y-%m-%d %H:%M")
            dep_dt = datetime.strptime(f"{event_date_str} {plan['departure']}", "%Y-%m-%d %H:%M")
            move_title = f"{sname} 이동"
            plan_json = _json.dumps(plan, ensure_ascii=False)
            mov = TongBotSchedule(user_id=uid, title=move_title, description=memo,
                content=plan_json, event_date=arr_dt, departure_time=dep_dt, location=sloc,
                memo=f"이동 {plan['total_min']}분 | {plan['distance_km']}km",
                departure_location=prev_name, return_location=sloc)
            db.session.add(mov)
            db.session.flush()
            entries.append({"id":mov.id,"title":move_title,"date":event_date_str,
                "time":stime,"departure_time":plan['departure'],"arrival":stime,"total_min":plan['total_min'],
                "memo":memo,"type":"move"})

        prev_lat = loc_lat
        prev_lng = loc_lng
        prev_name = sname

    # Step 6: 귀가
    if home_lat:
        ret_time = "20:00"
        if last_stop.get('time'):
            ret_min = _hm_to_min(last_stop['time']) + 120
            if ret_min < 24*60:
                ret_time = f"{ret_min//60:02d}:{ret_min%60:02d}"
        plan_home = plan_segment(prev_name, prev_lat, prev_lng, f"집({home_addr})", home_lat, home_lng, ret_time,
                               home_town=user.town or '', home_village=user.village or '',
                               naver_id=naver_id, naver_secret=naver_secret)
        plan_home.update({"from_lat":prev_lat,"from_lng":prev_lng,"to_lat":home_lat,"to_lng":home_lng})
        memo_home = f"🏠 귀가\n{format_itinerary(plan_home)}"
        dep_dt = datetime.strptime(f"{event_date_str} {plan_home['departure']}", "%Y-%m-%d %H:%M")
        plan_json = _json.dumps(plan_home, ensure_ascii=False)
        sh = TongBotSchedule(user_id=uid, title="집으로 이동", description=memo_home,
            content=plan_json, event_date=dep_dt, location=home_addr,
            memo=f"귀가 {plan_home['total_min']}분 | {plan_home['distance_km']}km",
            departure_location=prev_name, return_location=home_addr)
        db.session.add(sh)
        db.session.flush()
        entries.append({"id":sh.id,"title":"집으로 이동","date":event_date_str,
            "time":plan_home['departure'],"arrival":plan_home['arrival'],
            "total_min":plan_home['total_min'],"memo":memo_home,"type":"return"})

    db.session.commit()

    return jsonify({"status":"success","entries":entries,"date":event_date_str,
        "parsed_stops":stops,"origin":origin_label,"need_home_start":need_home_start})

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

@tongbot_bp.route('/api/bot/route/<int:schedule_id>')
def bot_route_detail(schedule_id):
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"로그인 필요"}), 401
    s = TongBotSchedule.query.get_or_404(schedule_id)
    if s.user_id != uid: return jsonify({"error":"권한 없음"}), 403
    route_data = None
    if s.content:
        try: route_data = json.loads(s.content)
        except: route_data = None
    evt = s.event_date.strftime("%Y-%m-%d %H:%M") if s.event_date else ""
    return jsonify({"schedule":{"id":s.id,"title":s.title,"event_date":evt,
        "location":s.location,"departure_location":s.departure_location,
        "return_location":s.return_location},"route":route_data})

@tongbot_bp.route('/api/bot/route/<int:schedule_id>/save', methods=['POST'])
def bot_route_save(schedule_id):
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"로그인 필요"}), 401
    s = TongBotSchedule.query.get_or_404(schedule_id)
    if s.user_id != uid: return jsonify({"error":"권한 없음"}), 403
    data = request.get_json() or {}
    steps = data.get('steps',[])
    route_data = {"steps":steps,"total_min":data.get('total_min',0),"distance_km":data.get('distance_km',0),
                  "departure":data.get('departure',''),"arrival":data.get('arrival','')}
    s.content = json.dumps(route_data, ensure_ascii=False)
    if data.get('title'): s.title = data['title']
    if data.get('departure_location'): s.departure_location = data['departure_location']
    if data.get('return_location'): s.return_location = data['return_location']
    db.session.commit()
    return jsonify({"success":True,"route":route_data})

@tongbot_bp.route('/api/bot/route/<int:schedule_id>/share', methods=['POST'])
def bot_route_share(schedule_id):
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"로그인 필요"}), 401
    s = TongBotSchedule.query.get_or_404(schedule_id)
    if s.user_id != uid: return jsonify({"error":"권한 없음"}), 403
    if not s.content: return jsonify({"error":"경로 데이터 없음"})
    try: route_data = json.loads(s.content)
    except: return jsonify({"error":"경로 파싱 실패"})
    sr = SharedRoute(from_name=s.departure_location or '', to_name=s.return_location or s.location or '',
                     from_lat=0, from_lng=0, to_lat=0, to_lng=0,
                     steps=s.content, total_min=route_data.get('total_min'), distance_km=route_data.get('distance_km'),
                     creator_id=uid, source_schedule_id=schedule_id)
    db.session.add(sr)
    db.session.commit()
    return jsonify({"success":True,"shared_id":sr.id})

@tongbot_bp.route('/api/bot/route/shared')
def bot_route_shared_list():
    kw = request.args.get('q','').strip()
    q = SharedRoute.query
    if kw:
        q = q.filter(or_(SharedRoute.from_name.ilike(f'%{kw}%'), SharedRoute.to_name.ilike(f'%{kw}%')))
    routes = q.order_by(SharedRoute.updated_at.desc()).limit(50).all()
    return jsonify({"routes":[{
        "id":r.id,"from_name":r.from_name,"to_name":r.to_name,
        "total_min":r.total_min,"distance_km":r.distance_km,
        "creator_id":r.creator_id
    } for r in routes]})
