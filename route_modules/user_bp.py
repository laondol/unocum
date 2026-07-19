from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app
from datetime import datetime
from models import db, User, Message, Friend, ShareReport, Post, PointHistory, VillageWish, LegalPost, PsychoPost, ChatMessage, LegalAppointment, TongBot, TongBotDraft
from werkzeug.security import generate_password_hash, check_password_hash
from route_modules.common import has_page_access
from services.security import save_village_file
from services.transit import haversine_km, geocode_address
from services.geocode import gps_to_town_village

user_bp = Blueprint('user', __name__)

@user_bp.route('/user/<int:user_id>')
def user_profile(user_id):
    if not session.get('username'):
        return redirect(url_for('auth.login', next=request.path))
    user = User.query.get_or_404(user_id)
    raw_history = PointHistory.query.filter_by(user_id=user.id).order_by(PointHistory.created_at.desc()).limit(50).all()
    running = user.points
    for h in raw_history:
        h.balance_after = running
        running -= h.amount
    point_history = raw_history
    
    uid = session['user_id']
    # 받은 쪽지 (관리자/리더 우선 정렬)
    if user.id == uid:
        messages = Message.query.filter_by(receiver_id=user.id).order_by(
            db.case(
                (Message.sender_role == 'admin', 0),
                (Message.sender_role == 'leader', 1),
                else_=2
            ),
            Message.created_at.desc()
        ).all()
    elif session.get('role') in ('admin','leader'):
        messages = []
    else:
        messages = Message.query.filter(
            ((Message.sender_id==uid) & (Message.receiver_id==user.id)) |
            ((Message.sender_id==user.id) & (Message.receiver_id==uid))
        ).order_by(Message.created_at.desc()).all()
    
    is_friend = False
    if session.get('user_id') and session['user_id'] != user.id:
        f = Friend.query.filter(
            ((Friend.requester_id==session['user_id']) & (Friend.receiver_id==user.id) & (Friend.status=='accepted')) |
            ((Friend.requester_id==user.id) & (Friend.receiver_id==session['user_id']) & (Friend.status=='accepted'))
        ).first()
        is_friend = bool(f)
    
    is_own = (session.get('user_id') == user.id)
    is_admin = session.get('role') == 'leader'
    bot_name = ''
    # 회원의 모든 게시글 통합
    posts = []
    # 꿈꾸기
    user_posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).all()
    for p in user_posts:
        posts.append({'title': p.title, 'date': p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else '', 'type': '꿈꾸기', 'url': f'/post/{p.id}', 'id': p.id})
    # 공유마당
    user_shares = ShareReport.query.filter_by(user_id=user.id).order_by(ShareReport.created_at.desc()).all()
    for s in user_shares:
        posts.append({'title': s.title, 'date': s.created_at.strftime('%Y-%m-%d %H:%M') if s.created_at else '', 'type': '공유', 'url': f'/share/detail/{s.id}', 'id': s.id})
    # 마을에 바란다
    user_wishes = VillageWish.query.filter_by(user_id=user.id).order_by(VillageWish.created_at.desc()).all()
    for w in user_wishes:
        posts.append({'title': w.content[:50], 'date': w.created_at.strftime('%Y-%m-%d %H:%M') if w.created_at else '', 'type': '바람', 'url': f'/village/my-wishes', 'id': w.id})
    # 법률/심리 상담
    legal_posts = LegalPost.query.filter_by(user_id=user.id).order_by(LegalPost.created_at.desc()).all() if hasattr(LegalPost, 'user_id') else []
    for l in legal_posts:
        posts.append({'title': l.title, 'date': l.created_at.strftime('%Y-%m-%d %H:%M') if l.created_at else '', 'type': '법률', 'url': f'/legal/post/{l.id}', 'id': l.id})
    # 상담 예약
    appointments = LegalAppointment.query.filter_by(user_id=user.id).order_by(LegalAppointment.date.desc()).limit(10).all()
    appt_list = []
    for a in appointments:
        appt_list.append({
            'title': a.content or '상담예약',
            'date': a.date.isoformat() if a.date else '',
            'time_slot': a.time_slot,
            'location': a.location or '',
            'status': a.status,
            'url': f'/legal/schedule',
            'edit_url': f'/legal/appointment/{a.id}/edit',
            'id': a.id
        })
    # 통벗 초안
    drafts = TongBotDraft.query.filter_by(user_id=user.id).order_by(TongBotDraft.updated_at.desc()).all()
    for d in drafts:
        posts.append({'title': d.title or '초안', 'date': d.updated_at.strftime('%Y-%m-%d %H:%M') if d.updated_at else '', 'type': '통벗', 'url': f'/user/my?popup=1', 'id': d.id})
    # 정렬
    posts.sort(key=lambda x: x['date'], reverse=True)
    curr_location = ''
    # 통벗 정보
    bot = TongBot.query.filter_by(user_id=user.id).first()
    bot_memory = (bot.memory or '')[-500:] if bot else ''
    bot_drafts = TongBotDraft.query.filter_by(user_id=user.id).order_by(TongBotDraft.updated_at.desc()).limit(5).all()
    if is_own or is_admin:
        if user.curr_address:
            curr_location = user.curr_address
        if not curr_location and user.curr_latitude and user.curr_longitude:
            from services.transit import reverse_geocode
            from config import Config
            geo = reverse_geocode(user.curr_latitude, user.curr_longitude,
                kakao_key=Config.KAKAO_REST_API_KEY,
                naver_id=Config.NAVER_CLIENT_ID or Config.NAVER_SEARCH_CLIENT_ID,
                naver_secret=Config.NAVER_CLIENT_SECRET or Config.NAVER_SEARCH_CLIENT_SECRET)
            if geo and geo.get('address'):
                curr_location = geo['address']
    if not curr_location:
        curr_location = f"{user.curr_town or ''} {user.curr_village or ''}".strip() or '위치 없음'
    if is_own:
        bot = TongBot.query.filter_by(user_id=uid).first()
        if not bot:
            import random, string as _s
            uid_str = ''.join(random.choices(_s.ascii_uppercase + _s.digits, k=4))
            bid = f"A-{uid_str}"
            while TongBot.query.filter_by(bot_id=bid).first():
                uid_str = ''.join(random.choices(_s.ascii_uppercase + _s.digits, k=4))
                bid = f"A-{uid_str}"
            bot = TongBot(user_id=uid, bot_id=bid, bot_name=bid)
            db.session.add(bot)
            db.session.commit()
        bot_name = bot.bot_name
    bot_message = ''
    if is_own and bot_name:
        try:
            h = (datetime.now() + timedelta(hours=9)).hour
            time_ctx = '아침' if h < 12 else ('오후' if h < 18 else '저녁')
            import random
            tips = ['오늘 양평 날씨에 맞는 옷차림을 추천해 드릴까요?',
                '잠시 스트레칭 어떠세요? 건강이 최고예요!',
                '오늘 하루 감사한 일 세 가지만 떠올려 보세요.',
                '좋아하는 음악 한 곡 들으면서 잠시 쉬어 가세요.',
                '오늘 양평의 맛집 정보가 궁금하신가요?']
            try:
                from config import Config
                import requests
                key = getattr(Config, 'GROQ_API_KEY', '')
                if key:
                    prompt = f'회원 {user.username}님에게 {time_ctx}에 어울리는 따뜻한 한마디를 20자 내외로 해주세요.'
                    r = requests.post('https://api.groq.com/openai/v1/chat/completions',
                        headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},
                        json={'model':'llama-3.1-8b-instant','messages':[{'role':'user','content':prompt}],'max_tokens':60},
                        timeout=5)
                    if r.status_code == 200:
                        bot_message = r.json()['choices'][0]['message']['content'].strip()
            except: pass
            if not bot_message:
                bot_message = random.choice(tips)
        except:
            bot_message = '오늘도 행복한 하루 되세요! 💕'
    # 게시글 모음 (위에서 이미 통합됨)
    posts.sort(key=lambda x: x["date"], reverse=True)
    posts = posts[:15]
    # 공유한 사진
    share_images = []
    img_shares = ShareReport.query.filter(ShareReport.user_id == user.id, ShareReport.image_path.isnot(None), ShareReport.image_path != '').order_by(ShareReport.created_at.desc()).limit(12).all()
    for s in img_shares:
        if hasattr(s, 'image_path') and s.image_path:
            share_images.append({'path': s.image_path, 'title': s.title, 'url': f'/share/detail/{s.id}'})
    
    recent_friends = []
    if is_own:
        f1 = Friend.query.filter_by(requester_id=uid, status='accepted').all()
        f2 = Friend.query.filter_by(receiver_id=uid, status='accepted').all()
        friend_ids = set()
        for f in f1: friend_ids.add(f.receiver_id)
        for f in f2: friend_ids.add(f.requester_id)
        if friend_ids:
            recent = []
            for fid in friend_ids:
                last_msg = ChatMessage.query.filter(ChatMessage.user_id==fid).order_by(ChatMessage.created_at.desc()).first()
                recent.append({"id":fid, "last":last_msg.created_at if last_msg else None})
            recent.sort(key=lambda x: x["last"] or datetime.min, reverse=True)
            for r in recent:
                u = User.query.get(r["id"])
                if u:
                    recent_friends.append({"id":u.id,"username":u.username,"name":u.real_name or u.username,"town":u.town or "","village":u.village or ""})
    
    return render_template('user_profile.html', 
        profile_user=user, 
        point_history=point_history, 
        messages=messages,
        is_own=is_own,
        is_admin=is_admin,
        is_friend=is_friend,
        bot_name=bot_name,
        posts=posts,
        share_images=share_images,
        appointments=appt_list,
        bot_memory=bot_memory,
        bot_drafts=bot_drafts,
        curr_location=curr_location,
        recent_friends=recent_friends,
        bot_message=bot_message
    )

@user_bp.route('/user/location/refresh', methods=['POST'])
def user_location_refresh():
    if not session.get('username'):
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    user = User.query.get(session['user_id'])
    data = request.get_json() or {}
    lat = float(data.get('lat', 0))
    lon = float(data.get('lon', 0))
    if not lat or not lon:
        return jsonify({"status": "error", "msg": "GPS 위치가 필요합니다."}), 400
    # GPS 보정 오프셋 적용
    lat += (user.curr_offset_lat or 0)
    lon += (user.curr_offset_lng or 0)
    town, village = gps_to_town_village(lat, lon)
    user.curr_latitude = lat
    user.curr_longitude = lon
    if town:
        user.curr_town = town
        user.curr_village = village or ''
    user.location_updated_at = datetime.now()
    db.session.commit()
    return jsonify({
        "status": "success",
        "lat": lat, "lon": lon,
        "town": user.curr_town or '',
        "village": user.curr_village or ''
    })

@user_bp.route('/user/location/share/toggle', methods=['POST'])
def user_location_share_toggle():
    if not session.get('username'):
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    user = User.query.get(session['user_id'])
    data = request.get_json() or {}
    val = data.get('value', 'off')
    if val not in ('friends', 'off'):
        return jsonify({"status": "error", "msg": "잘못된 값입니다."}), 400
    user.location_share = (val == 'friends')
    db.session.commit()
    return jsonify({"status": "success", "value": val})

@user_bp.route('/user/village/notify/toggle', methods=['POST'])
def user_village_notify_toggle():
    if not session.get('username'):
        return jsonify({"status":"error","msg":"로그인 필요"}), 401
    user = User.query.get(session['user_id'])
    val = request.get_json().get('value', True)
    user.village_notify = val
    db.session.commit()
    return jsonify({"status":"success"})

@user_bp.route('/user/location/correct', methods=['POST'])
def user_location_correct():
    if not session.get('username'):
        return jsonify({"status":"error","msg":"로그인 필요"}), 401
    user = User.query.get(session['user_id'])
    if request.is_json:
        data = request.get_json()
        manual_loc = data.get('manual_loc','').strip()
        gps_lat = data.get('gps_lat', type=float) or 0
        gps_lng = data.get('gps_lng', type=float) or 0
    else:
        manual_loc = request.form.get('manual_loc','').strip()
        gps_lat = float(request.form.get('gps_lat', 0) or 0)
        gps_lng = float(request.form.get('gps_lng', 0) or 0)
    if not manual_loc:
        return jsonify({"status":"error","msg":"위치를 입력하세요"})
    from services.transit import geocode_address, haversine_km
    from config import Config
    geo = geocode_address(manual_loc, Config.KAKAO_REST_API_KEY)
    if geo and geo.get('lat'):
        dist = haversine_km(gps_lat, gps_lng, geo['lat'], geo['lng']) if gps_lat else 0
        if gps_lat and dist <= 1.0:
            user.curr_offset_lat = (user.curr_offset_lat or 0) + (geo['lat'] - gps_lat)
            user.curr_offset_lng = (user.curr_offset_lng or 0) + (geo['lng'] - gps_lng)
            learn_msg = f" (GPS 오차 {dist:.2f}km 학습됨)"
        else:
            learn_msg = ""
        user.curr_latitude = geo['lat']
        user.curr_longitude = geo['lng']
    user.curr_address = manual_loc[:200]
    user.address = manual_loc[:200]
    user.location_updated_at = datetime.now()
    already_got = PointHistory.query.filter_by(user_id=user.id, change_type='location_correct').first()
    if not already_got:
        user.points = (user.points or 0) + 1
        db.session.add(PointHistory(user_id=user.id, change_type='location_correct', amount=1, description=f'위치 보정: {manual_loc}'))
    db.session.commit()
    if request.is_json:
        if not already_got:
            return jsonify({"status":"success","msg":f"'{manual_loc}'(으)로 보정되었습니다. 1닢 지급!{learn_msg}"})
        else:
            return jsonify({"status":"success","msg":f"'{manual_loc}'(으)로 보정되었습니다."})
    back = request.args.get('back','')
    if back == 'construction':
        return redirect('/construction?tab=home')
    return redirect('/user/' + str(user.id))
def _cleanup_expired_posts():
    now = datetime.now()
    expired = Post.query.filter(Post.total_score <= -50, Post.deadline != None, Post.deadline < now).all()
    for p in expired:
        db.session.delete(p)
    if expired:
        db.session.commit()
        print(f'[CLEANUP] {len(expired)} expired post(s) deleted')

# ========== 닢 시스템 ==========
def add_points(user_id, amount, change_type, description, related_id=None):
    """닢 적립/차감 + 내역 기록"""
    user = User.query.get(user_id)
    if not user: return
    user.points += amount
    balance = user.points
    history = PointHistory(
        user_id=user_id,
        change_type=change_type,
        amount=amount,
        balance_after=balance,
        description=description,
        related_id=related_id
    )
    db.session.add(history)
    db.session.commit()
    return balance

def check_email_verified(user_id):
    user = User.query.get(user_id)
    return user and user.email_verified

