from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app, send_file
from datetime import datetime
from models import db, User, Message, Friend, ShareReport, Post, PointHistory, VillageWish, LegalPost, PsychoPost, ChatMessage, LegalAppointment, TongBot, TongBotDraft
from werkzeug.security import generate_password_hash, check_password_hash
from route_modules.common import has_page_access
from services.security import save_village_file
from services.transit import haversine_km, geocode_address
from services.geocode import gps_to_town_village

user_bp = Blueprint('user', __name__)

def _serve_spa():
    import os
    from flask import current_app, send_file
    path = os.path.join(current_app.root_path, 'frontend', 'dist', 'index.html')
    if os.path.exists(path):
        return send_file(path)
    from flask import render_template
    return render_template('intro.html')

@user_bp.route('/api/user/<int:user_id>/profile')
def api_user_profile(user_id):
    if not session.get('username'):
        return jsonify({'error': 'login'}), 401
    user = User.query.get_or_404(user_id)
    uid = session['user_id']
    is_own = (uid == user.id)
    is_admin = session.get('role') in ('admin', 'leader')

    is_friend = False
    if uid != user.id:
        f = Friend.query.filter(
            ((Friend.requester_id==uid) & (Friend.receiver_id==user.id) & (Friend.status=='accepted')) |
            ((Friend.requester_id==user.id) & (Friend.receiver_id==uid) & (Friend.status=='accepted'))
        ).first()
        is_friend = bool(f)

    p_is_village = 'village' in (user.managed_pages or '') or ((user.managed_pages or '')[:3] == 'vi_')

    raw_history = PointHistory.query.filter_by(user_id=user.id).order_by(PointHistory.created_at.desc()).limit(50).all()
    running = user.points
    for h in raw_history:
        h.balance_after = running
        running -= h.amount

    if user.id == uid:
        messages = Message.query.filter_by(receiver_id=user.id).order_by(
            db.case((Message.sender_role == 'admin', 0), (Message.sender_role == 'leader', 1), else_=2),
            Message.created_at.desc()
        ).all()
    elif is_admin:
        messages = []
    else:
        messages = Message.query.filter(
            ((Message.sender_id==uid) & (Message.receiver_id==user.id)) |
            ((Message.sender_id==user.id) & (Message.receiver_id==uid))
        ).order_by(Message.created_at.desc()).all()

    posts = []
    for p in Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).all():
        posts.append({'title': p.title, 'date': p.created_at.isoformat() if p.created_at else '', 'type': '꿈꾸기', 'url': f'/post/{p.id}'})
    for s in ShareReport.query.filter_by(user_id=user.id).order_by(ShareReport.created_at.desc()).all():
        posts.append({'title': s.title, 'date': s.created_at.isoformat() if s.created_at else '', 'type': '공유', 'url': f'/share/detail/{s.id}'})
    for w in VillageWish.query.filter_by(user_id=user.id).order_by(VillageWish.created_at.desc()).all():
        posts.append({'title': (w.content or '')[:50], 'date': w.created_at.isoformat() if w.created_at else '', 'type': '바람', 'url': '/village/my-wishes'})
    if hasattr(LegalPost, 'user_id'):
        for l in LegalPost.query.filter_by(user_id=user.id).order_by(LegalPost.created_at.desc()).all():
            posts.append({'title': l.title, 'date': l.created_at.isoformat() if l.created_at else '', 'type': '법률', 'url': f'/legal/post/{l.id}'})
    posts.sort(key=lambda x: x['date'], reverse=True)

    appointments = []
    for a in LegalAppointment.query.filter_by(user_id=user.id).order_by(LegalAppointment.date.desc()).limit(10).all():
        appointments.append({
            'title': a.content or '상담예약', 'date': a.date.isoformat() if a.date else '',
            'time_slot': a.time_slot, 'location': a.location or '',
            'status': a.status, 'edit_url': f'/legal/appointment/{a.id}/edit', 'id': a.id
        })

    drafts = TongBotDraft.query.filter_by(user_id=user.id).order_by(TongBotDraft.updated_at.desc()).all()
    bot = TongBot.query.filter_by(user_id=user.id).first()
    bot_memory = (bot.memory or '')[-500:] if bot else ''

    curr_location = ''
    if is_own or is_admin:
        if user.curr_address:
            curr_location = user.curr_address
        if not curr_location and user.curr_latitude and user.curr_longitude:
            from config import Config
            from services.transit import reverse_geocode
            geo = reverse_geocode(user.curr_latitude, user.curr_longitude,
                kakao_key=Config.KAKAO_REST_API_KEY,
                naver_id=Config.NAVER_CLIENT_ID or Config.NAVER_SEARCH_CLIENT_ID,
                naver_secret=Config.NAVER_CLIENT_SECRET or Config.NAVER_SEARCH_CLIENT_SECRET)
            if geo and geo.get('address'):
                curr_location = geo['address']
    if not curr_location:
        curr_location = f"{user.curr_town or ''} {user.curr_village or ''}".strip() or '위치 없음'

    share_images = []
    for s in ShareReport.query.filter(ShareReport.user_id == user.id, ShareReport.image_path.isnot(None), ShareReport.image_path != '').order_by(ShareReport.created_at.desc()).limit(12).all():
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
                recent.append({"id":fid, "last":last_msg.created_at.isoformat() if last_msg else None})
            recent.sort(key=lambda x: x["last"] or '', reverse=True)
            for r in recent:
                u = User.query.get(r["id"])
                if u:
                    recent_friends.append({"id":u.id,"username":u.username,"name":u.real_name or u.username,"town":u.town or "","village":u.village or ""})

    return jsonify({
        'profile_user': {
            'id': user.id, 'username': user.username, 'real_name': user.real_name,
            'town': user.town, 'village': user.village, 'social_provider': user.social_provider,
            'points': user.points, 'role': user.role, 'managed_pages': user.managed_pages,
            'is_neighbor': user.is_neighbor, 'location_share': user.location_share,
            'village_notify': user.village_notify != False,
            'curr_address': user.curr_address,
        },
        'is_own': is_own, 'is_admin': is_admin, 'is_friend': is_friend,
        'p_is_village': p_is_village,
        'point_history': [{
            'id': h.id, 'change_type': h.change_type, 'amount': h.amount,
            'balance_after': h.balance_after, 'description': h.description,
            'created_at': h.created_at.isoformat() if h.created_at else None
        } for h in raw_history],
        'messages': [{
            'id': m.id, 'subject': m.subject, 'content': m.content,
            'sender_role': m.sender_role, 'is_read': m.is_read,
            'created_at': m.created_at.isoformat() if m.created_at else None
        } for m in messages],
        'posts': posts[:15],
        'appointments': appointments,
        'drafts': [{'id': d.id, 'title': d.title, 'category': d.category, 'status': d.status,
            'updated_at': d.updated_at.isoformat() if d.updated_at else None} for d in drafts],
        'bot_memory': bot_memory,
        'curr_location': curr_location,
        'share_images': share_images,
        'recent_friends': recent_friends,
        'profile_initial': (user.real_name or user.username)[0] if (user.real_name or user.username) else '?',
    })


@user_bp.route('/user/<int:user_id>')
def user_profile(user_id):
    if not session.get('username'):
        return redirect(url_for('auth.login', next=request.path))
    return _serve_spa()


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


@user_bp.route('/user/edit-profile')
def user_edit_profile():
    if not session.get('username'):
        return redirect(url_for('auth.login', next=request.path))
    return _serve_spa()


@user_bp.route('/api/user/edit-profile', methods=['GET'])
def api_user_edit_profile_get():
    if not session.get('username'):
        return jsonify({'error': 'login'}), 401
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'user not found'}), 404
    return jsonify({
        'id': user.id,
        'real_name': user.real_name or '',
        'email': user.email or '',
        'phone': user.phone or '',
        'home_address': user.curr_address or '',
        'office_address': user.office_address or '',
    })


@user_bp.route('/api/user/edit-profile', methods=['POST'])
def api_user_edit_profile_post():
    if not session.get('username'):
        return jsonify({'status': 'error', 'msg': '로그인이 필요합니다.'}), 401
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'status': 'error', 'msg': '사용자를 찾을 수 없습니다.'}), 404
    real_name = (request.form.get('real_name', '') or '').strip()
    email = (request.form.get('email', '') or '').strip()
    phone = (request.form.get('phone', '') or '').strip()
    home_address = (request.form.get('home_address', '') or '').strip()
    office_address = (request.form.get('office_address', '') or '').strip()
    if not email:
        return jsonify({'status': 'error', 'msg': '이메일은 필수입니다.'})
    existing = User.query.filter(User.email == email, User.id != user.id).first()
    if existing:
        return jsonify({'status': 'error', 'msg': '이미 사용 중인 이메일입니다.'})
    user.real_name = real_name[:50] if real_name else None
    user.email = email[:100]
    user.phone = phone[:20] if phone else None
    if home_address != (user.curr_address or ''):
        user.curr_address = home_address[:200] if home_address else None
        if home_address:
            try:
                from config import Config
                geo = geocode_address(home_address, Config.KAKAO_REST_API_KEY)
                if geo and geo.get('lat'):
                    user.curr_latitude = geo['lat']
                    user.curr_longitude = geo['lng']
            except Exception:
                pass
    if office_address != (user.office_address or ''):
        user.office_address = office_address[:200] if office_address else None
        if office_address:
            try:
                from config import Config
                geo = geocode_address(office_address, Config.KAKAO_REST_API_KEY)
                if geo and geo.get('lat'):
                    user.office_latitude = geo['lat']
                    user.office_longitude = geo['lng']
            except Exception:
                pass
    db.session.commit()
    return jsonify({'status': 'success', 'msg': '회원정보가 저장되었습니다.', 'redirect': f'/user/{user.id}'})


@user_bp.route('/api/user/change-password/send-code', methods=['POST'])
def api_user_change_password_send_code():
    if not session.get('username'):
        return jsonify({'status': 'error', 'msg': '로그인이 필요합니다.'}), 401
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'status': 'error', 'msg': '사용자를 찾을 수 없습니다.'}), 404
    if not user.email:
        return jsonify({'status': 'error', 'msg': '이메일이 등록되어 있지 않습니다.'})
    import secrets, time
    code = ''.join(secrets.choice('0123456789') for _ in range(6))
    session['pw_change_code'] = code
    session['pw_change_code_time'] = time.time()
    from services.email_service import EmailService
    EmailService.send(user.email, '[양평마을] 비밀번호 변경 인증코드', f'인증코드: {code}\n\n5분간 유효합니다.')
    return jsonify({'status': 'success', 'msg': f'{user.email}로 인증코드를 발송했습니다.'})


@user_bp.route('/api/user/change-password/verify', methods=['POST'])
def api_user_change_password_verify():
    if not session.get('username'):
        return jsonify({'status': 'error', 'msg': '로그인이 필요합니다.'}), 401
    import time
    code = ''
    new_pw = ''
    if request.is_json:
        data = request.get_json()
        code = (data.get('code', '') or '').strip()
        new_pw = data.get('password', '') or ''
    else:
        code = (request.form.get('code', '') or '').strip()
        new_pw = request.form.get('password', '') or ''
    if not session.get('pw_change_code'):
        return jsonify({'status': 'error', 'msg': '인증코드가 만료되었습니다. 다시 발송해 주세요.'})
    if time.time() - session.get('pw_change_code_time', 0) > 300:
        session.pop('pw_change_code', None)
        session.pop('pw_change_code_time', None)
        return jsonify({'status': 'error', 'msg': '인증코드가 만료되었습니다. 다시 발송해 주세요.'})
    if code != session.get('pw_change_code'):
        return jsonify({'status': 'error', 'msg': '인증코드가 일치하지 않습니다.'})
    if not new_pw or len(new_pw) < 4:
        return jsonify({'status': 'error', 'msg': '비밀번호는 4자 이상이어야 합니다.'})
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'status': 'error', 'msg': '사용자를 찾을 수 없습니다.'}), 404
    user.password = generate_password_hash(new_pw)
    db.session.commit()
    session.pop('pw_change_code', None)
    session.pop('pw_change_code_time', None)
    return jsonify({'status': 'success', 'msg': '비밀번호가 변경되었습니다.'})

