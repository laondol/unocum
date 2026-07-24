import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, PointHistory, Message

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register/send-code', methods=['POST'])
def register_send_code():
    email = request.form.get('email', '').strip()
    if not email:
        return jsonify({'status':'error','msg':'이메일을 입력해 주세요.'})
    # 회원가입용 이메일 체크
    purpose = request.form.get('purpose', 'register')
    if purpose == 'register' and User.query.filter_by(email=email).first():
        return jsonify({'status':'error','msg':'이미 등록된 이메일입니다.'})
    import secrets, time
    code = ''.join(secrets.choice('0123456789') for _ in range(6))
    session['verify_code'] = code
    session['verify_email'] = email
    session['verify_code_time'] = time.time()
    session['verify_purpose'] = purpose
    from services.email_service import EmailService
    EmailService.send(email, '[양평마을] 이메일 인증 코드', f'인증 코드: {code}\n\n5분간 유효합니다.')
    return jsonify({'status':'success','msg':'인증 코드를 이메일로 발송했습니다.'})

@auth_bp.route('/register/verify-code', methods=['POST'])
def register_verify_code():
    code = request.form.get('code', '').strip()
    import time
    if not session.get('verify_code') or not session.get('verify_email'):
        return jsonify({'status':'error','msg':'인증 코드가 만료되었습니다. 다시 발송해 주세요.'})
    if time.time() - session.get('verify_code_time', 0) > 300:
        session.pop('verify_code', None)
        session.pop('verify_email', None)
        session.pop('verify_code_time', None)
        return jsonify({'status':'error','msg':'인증 코드가 만료되었습니다. 다시 발송해 주세요.'})
    if code != session.get('verify_code'):
        return jsonify({'status':'error','msg':'인증 코드가 일치하지 않습니다.'})
    session['email_verified_for_register'] = session['verify_email']
    session.pop('verify_code', None)
    session.pop('verify_code_time', None)
    return jsonify({'status':'success','msg':'이메일 인증 완료!'})

@auth_bp.route('/register/verify-email-button', methods=['POST'])
def register_verify_email_button():
    email = request.form.get('email', '').strip()
    if not email:
        return jsonify({'status':'error','msg':'이메일을 입력해 주세요.'})
    redirect_url = request.form.get('redirect', '/legal/list')
    import secrets
    from models import TempEmailVerify
    token = secrets.token_urlsafe(32)
    existing = TempEmailVerify.query.filter_by(email=email, is_verified=False).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
    record = TempEmailVerify(email=email, token=token, redirect=redirect_url)
    db.session.add(record)
    db.session.commit()
    verify_url = url_for('register_verify_email_confirm', token=token, _external=True)
    from services.email_service import EmailService
    EmailService.send(email, '[양평마을] 이메일 인증을 완료해 주세요',
        f'아래 링크를 클릭하면 이메일 인증이 완료됩니다.\n\n{verify_url}\n\n이 링크는 30분간 유효합니다.\n문의: yp@unocum.kr')
    return jsonify({'status':'success','msg':'인증 링크를 이메일로 발송했습니다. 메일함을 확인해 주세요.'})

@auth_bp.route('/register/verify-email/<token>')
def register_verify_email_confirm(token):
    from models import TempEmailVerify
    record = TempEmailVerify.query.filter_by(token=token, is_verified=False).first()
    if not record:
        return "<script>alert('만료되었거나 유효하지 않은 링크입니다.'); location.href='/legal/list';</script>"
    if record.created_at and datetime.now() - record.created_at > timedelta(minutes=30):
        db.session.delete(record)
        db.session.commit()
        return "<script>alert('인증 링크가 만료되었습니다. 다시 인증해 주세요.'); location.href='/legal/list';</script>"
    record.is_verified = True
    db.session.commit()
    session['verify_email'] = record.email
    session['email_verified_for_legal'] = True
    session['email_verified_for_psycho'] = True
    session['email_verified_for_register'] = record.email
    target = record.redirect or '/legal/list'
    db.session.delete(record)
    db.session.commit()
    return f"<script>alert('이메일 인증이 완료되었습니다.'); location.href='{target}';</script>"

@auth_bp.route('/reset-password')
def reset_password():
    return _serve_spa()

@auth_bp.route('/reset-password/send', methods=['POST'])
def reset_password_send():
    data = request.get_json()
    email = data.get('email','').strip()
    if not email:
        return jsonify({"status":"error","msg":"이메일을 입력하세요."})
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"status":"error","msg":"등록되지 않은 이메일입니다."})
    import secrets, time
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expiry = datetime.now() + timedelta(hours=1)
    db.session.commit()
    reset_url = url_for('reset_password_confirm', token=token, _external=True)
    from services.email_service import EmailService
    sent = EmailService.send(email, '[양평마을] 비밀번호 재설정',
        f'비밀번호 재설정 링크:\n{reset_url}\n\n1시간 내에 사용해 주세요.')
    if sent:
        return jsonify({"status":"success","msg":"재설정 링크를 이메일로 발송했습니다."})
    else:
        return jsonify({"status":"success","msg":"로컬모드: 메일발송 실패","debug_url":reset_url})

@auth_bp.route('/reset-password/<token>')
def reset_password_confirm(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.now():
        return "<script>alert('만료된 링크입니다.'); location.href='/reset-password';</script>"
    return _serve_spa()

@auth_bp.route('/reset-password/confirm', methods=['POST'])
def reset_password_confirm_post():
    data = request.get_json()
    token = data.get('token','')
    password = data.get('password','')
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.now():
        return jsonify({"status":"error","msg":"만료된 링크입니다."})
    user.password = generate_password_hash(password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.session.commit()
    return jsonify({"status":"success","msg":"비밀번호가 변경되었습니다. 로그인해 주세요."})

def _serve_spa():
    react_index = os.path.join(current_app.root_path, 'frontend', 'dist', 'index.html')
    if os.path.exists(react_index):
        return send_file(react_index)
    return render_template('intro.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return _serve_spa()
    if request.method == 'POST':
        verified_email = session.pop('email_verified_for_register', None)
        if not verified_email:
            return "<script>alert('이메일 인증을 먼저 완료해 주세요.'); location.href='/register';</script>"
        password = request.form['password']
        real_name = request.form['real_name']
        username = request.form.get('username','').strip()
        # username이 비었으면 이메일 앞부분으로 자동 생성
        if not username and verified_email:
            username = verified_email.split('@')[0][:20]
        # GPS 기반 위치
        lat = request.form.get('lat', type=float)
        lon = request.form.get('lon', type=float)
        town = ''
        village = ''
        neighbor = False
        if lat and lon:
            from services.geocode import gps_to_town_village, is_in_yangpyeong
            if is_in_yangpyeong(lat, lon):
                t, v = gps_to_town_village(lat, lon)
                town = t or ''
                village = v or ''
                neighbor = True
        # town/village 없는 경우 form에서 가져오기
        if not town:
            town = request.form.get('town', '')
        if not village:
            village = request.form.get('village', '')
        
        if User.query.filter_by(email=verified_email).first():
            session.pop('verify_email', None)
            return "<script>alert('이미 등록된 이메일입니다.'); location.href='/register';</script>"
        hashed_pw = generate_password_hash(password)
        now = datetime.now()
        new_user = User(
            username=username, password=hashed_pw,
            real_name=real_name, email=verified_email,
            email_verified=True,
            town=town, village=village,
            reg_town=town, reg_village=village,
            curr_town=town, curr_village=village,
            is_neighbor=neighbor,
            location_updated_at=now,
            points=1000
        )
        # 프로필 이미지 저장
        profile_img = request.files.get('profile_img')
        if profile_img and profile_img.filename:
            from services.security import validate_upload, secure_save
            ok, msg = validate_upload(profile_img, max_mb=5)
            if ok:
                profile_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles')
                os.makedirs(profile_dir, exist_ok=True)
                try:
                    path = secure_save(profile_img, profile_dir, max_mb=5)
                    new_user.profile_image = path
                except Exception:
                    pass
        db.session.add(new_user)
        db.session.flush()
        new_user.last_payout = now
        history = PointHistory(
            user_id=new_user.id, change_type='signup', amount=1000,
            balance_after=1000, description='회원가입 지급'
        )
        db.session.add(history)
        db.session.commit()
        
        # === 기본 벗 자동 추가: 함사양(관리자) + 같은 마을의 마을지기 ===
        try:
            from models import Friend
            # 1) 모든 관리자(함사양)를 기본 벗으로 추가
            admins = User.query.filter(User.role == 'admin').all()
            for admin_user in admins:
                if admin_user.id != new_user.id:
                    existing = Friend.query.filter(
                        ((Friend.requester_id == new_user.id) & (Friend.receiver_id == admin_user.id)) |
                        ((Friend.requester_id == admin_user.id) & (Friend.receiver_id == new_user.id))
                    ).first()
                    if not existing:
                        f = Friend(requester_id=admin_user.id, receiver_id=new_user.id, status='accepted')
                        db.session.add(f)
            # 2) 같은 읍/면 + 리의 마을지기를 기본 벗으로 추가
            if town and village:
                leaders = User.query.filter(User.role == 'leader', User.town == town, User.village == village).all()
                for leader_user in leaders:
                    if leader_user.id != new_user.id:
                        existing = Friend.query.filter(
                            ((Friend.requester_id == new_user.id) & (Friend.receiver_id == leader_user.id)) |
                            ((Friend.requester_id == leader_user.id) & (Friend.receiver_id == new_user.id))
                        ).first()
                        if not existing:
                            f = Friend(requester_id=leader_user.id, receiver_id=new_user.id, status='accepted')
                            db.session.add(f)
            db.session.commit()
        except Exception as e:
            print(f'[WARN] auto-friend error: {e}')
        
        from services.email_service import EmailService
        EmailService.send(verified_email, f"[양평마을] 가입을 환영합니다, {real_name}님",
            f"{real_name}님, 양평마을에 가입해 주셔서 감사합니다.\n\n지금 바로 다양한 서비스를 이용해 보세요.\n- 게시글 작성 및 공유\n- 법률/심리 상담\n- 경사로 설치 신청\n- 이웃과 소통\n\nhttps://test.unocum.kr")
        
        return "<script>alert('가입 신청 완료! 로그인을 진행하세요.'); location.href='/intro';</script>"
    return _serve_spa()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    default_next = request.referrer if request.referrer and request.referrer.startswith(request.host_url) and request.referrer != url_for('auth.login', _external=True) else None
    next_url = request.args.get('next') or request.form.get('next') or default_next
    if next_url and not next_url.startswith('/'):
        next_url = url_for('page.intro')
    if request.method == 'POST':
        login_id = request.form['username']
        u = User.query.filter_by(email=login_id).first()
        if u and check_password_hash(u.password, request.form['password']):
            session.update({'user_id': u.id, 'username': u.username, 'role': u.role, 'email': u.email or '', 'real_name': u.real_name or '', 'managed_pages': u.managed_pages or ''})
            now = datetime.now()
            u.last_login = now
            # 로그인 위치 기록 (GPS from form)
            lat = request.form.get('lat', type=float)
            lon = request.form.get('lon', type=float)
            if lat and lon:
                u.login_latitude = lat
                u.login_longitude = lon
                from services.geocode import gps_to_town_village
                town, village = gps_to_town_village(lat, lon)
                if town:
                    u.login_town = town
                    u.login_village = village or ''
            # 30일 주기 닢 지급 (가입일 기준, 가입 시 1000P만 지급)
            now = datetime.now()
            if u.last_payout:
                if (now - u.last_payout).days >= 30:
                    add_points(u.id, 1000, 'monthly', '30일 주기 물맑은머니 지급')
                    if 'village' in (u.managed_pages or ''):
                        add_points(u.id, 10000, 'village_monthly', '마을지기 활동지원금')
                    u.last_payout = now
                    db.session.commit()
            else:
                u.last_payout = now
                db.session.commit()
            return redirect(next_url or url_for('user.user_profile', user_id=u.id))
        return jsonify({"status":"error","msg":"로그인 정보가 올바르지 않습니다."}), 401
    return _serve_spa()

@auth_bp.route('/logout')
def logout():
    uid = session.get('user_id')
    if uid:
        user = User.query.get(uid)
        if user:
            user.last_logout = datetime.now()
            db.session.commit()
    session.clear()
    return redirect(url_for('page.intro'))

# --- [OAuth2 소셜 로그인] Google / Kakao / Naver ---
@auth_bp.route('/oauth/login/<provider>')
def oauth_login(provider):
    if provider not in ('google', 'kakao', 'naver'):
        return "<script>alert('지원하지 않는 로그인 방식입니다.'); history.back();</script>"
    redirect_uri = url_for('oauth_callback', provider=provider, _external=True)
    return oauth.create_client(provider).authorize_redirect(redirect_uri)

@auth_bp.route('/oauth/callback/<provider>')
def oauth_callback(provider):
    if provider not in ('google', 'kakao', 'naver'):
        return "<script>alert('지원하지 않는 로그인 방식입니다.'); history.back();</script>"
    try:
        token = oauth.create_client(provider).authorize_access_token()
    except Exception as e:
        return f"<script>alert('OAuth 인증 실패: {str(e)}'); history.back();</script>"
    userinfo = oauth.create_client(provider).userinfo(token=token)
    if not userinfo:
        return "<script>alert('사용자 정보를 가져올 수 없습니다.'); history.back();</script>"

    if provider == 'google':
        social_id = userinfo.get('sub')
        email = userinfo.get('email', '')
        name = userinfo.get('name', email.split('@')[0] if email else 'google_user')
    elif provider == 'kakao':
        kakao_account = userinfo.get('kakao_account', {})
        social_id = str(userinfo.get('id'))
        email = kakao_account.get('email', '')
        profile = kakao_account.get('profile', {})
        name = profile.get('nickname', email.split('@')[0] if email else 'kakao_user')
    elif provider == 'naver':
        response = userinfo.get('response', {})
        social_id = response.get('id')
        email = response.get('email', '')
        name = response.get('name', response.get('nickname', email.split('@')[0] if email else 'naver_user'))
    else:
        social_id = None

    if not social_id:
        return "<script>alert('고유 식별자를 받지 못했습니다.'); history.back();</script>"

    if not email:
        return "<script>alert('SNS 계정에 이메일이 연동되어 있지 않습니다. ' + ('카카오' if provider == 'kakao' else '네이버' if provider == 'naver' else 'Google') + ' 설정에서 이메일 제공을 활성화해 주세요.'); history.back();</script>"

    uid = provider + '_' + str(social_id)
    user = User.query.filter_by(social_id=uid).first()

    if not user:
        existing_email_user = None
        if email:
            existing_email_user = User.query.filter_by(email=email).first()
        if existing_email_user:
            existing_email_user.social_id = uid
            existing_email_user.social_provider = provider
            existing_email_user.social_email = email
            existing_email_user.email_verified = True
            db.session.commit()
            user = existing_email_user
        else:
            base_username = name.replace(' ', '_')[:30]
            username = base_username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            hashed_pw = generate_password_hash(os.urandom(16).hex())
            now = datetime.now()
            user = User(
                username=username,
                password=hashed_pw,
                real_name=name,
                email=email,
                email_verified=True,
                social_id=uid,
                social_provider=provider,
                social_email=email,
                town='양평읍',
                village='양근리',
                reg_town='양평읍', reg_village='양근리',
                curr_town='양평읍', curr_village='양근리',
                location_updated_at=now,
                points=1000
            )
            db.session.add(user)
            db.session.flush()
            user.last_payout = now
            ph = PointHistory(user_id=user.id, change_type='signup', amount=1000,
                             balance_after=1000, description='SNS 회원가입 지급')
            db.session.add(ph)
            db.session.commit()

    session.update({'user_id': user.id, 'username': user.username, 'role': user.role, 'email': user.email or '', 'real_name': user.real_name or ''})
    now = datetime.now()
    user.last_login = now
    if user.last_payout and (now - user.last_payout).days >= 30:
        add_points(user.id, 1000, 'monthly', '30일 주기 물맑은머니 지급')
        if 'village' in (user.managed_pages or ''):
            add_points(user.id, 10000, 'village_monthly', '마을지기 활동지원금')
        user.last_payout = now
    elif not user.last_payout:
        user.last_payout = now
    db.session.commit()
    next_url = request.args.get('next') or url_for('news.world_news')
    if not next_url.startswith('/'):
        next_url = url_for('news.world_news')
    return redirect(next_url)

# --- [이메일 인증] ---
@auth_bp.route('/verify-email/send', methods=['POST'])
def verify_email_send():
    uid = session.get('user_id')
    if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
    user = User.query.get(uid)
    if not user or not user.email:
        return jsonify({'status':'error','msg':'등록된 이메일이 없습니다.'}), 400
    if user.email_verified:
        return jsonify({'status':'error','msg':'이미 인증된 이메일입니다.'}), 400
    import secrets
    token = secrets.token_urlsafe(32)
    user.email_verification_token = token
    user.email_verification_sent_at = datetime.now()
    db.session.commit()
    verify_url = url_for('verify_email_confirm', token=token, _external=True)
    EmailService.send(
        user.email,
        '[양평마을] 이메일 인증을 완료해 주세요',
        f'{user.real_name or user.username}님,\n\n아래 링크를 클릭하면 이메일 인증이 완료됩니다:\n\n{verify_url}\n\n인증 후 게시글 작성, 투표 등 모든 기능을 이용하실 수 있습니다.\n\n감사합니다.\n함께사는양평 드림'
    )
    return jsonify({'status':'success','msg':'인증 이메일을 발송했습니다. 메일함을 확인해 주세요.'})

@auth_bp.route('/verify-email/<token>')
def verify_email_confirm(token):
    user = User.query.filter_by(email_verification_token=token).first()
    if not user:
        return "<script>alert('유효하지 않거나 만료된 인증 링크입니다.'); location.href='/intro';</script>"
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_sent_at = None
    db.session.commit()
    return "<script>alert('✅ 이메일 인증이 완료되었습니다. 이제 모든 기능을 이용하실 수 있습니다.'); location.href='/main';</script>"

# --- [주소 수정] ---
@auth_bp.route('/user/update-address', methods=['POST'])
def user_update_address():
    uid = session.get('user_id')
    if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
    user = User.query.get(uid)
    if not user: return jsonify({'status':'error','msg':'사용자 없음'}), 404
    town = request.form.get('town', '').strip()
    village = request.form.get('village', '').strip()
    if not town:
        return jsonify({'status':'error','msg':'읍/면을 선택해주세요.'})
    if town != '관외' and village:
        pass  # 리까지 입력
    user.town = town
    user.village = village
    user.curr_town = town
    user.curr_village = village
    db.session.commit()

@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    login_id = data.get('username', '')
    u = User.query.filter_by(email=login_id).first()
    if u and check_password_hash(u.password, data.get('password', '')):
        session.update({'user_id': u.id, 'username': u.username, 'role': u.role, 'email': u.email or '', 'real_name': u.real_name or '', 'managed_pages': u.managed_pages or ''})
        u.last_login = datetime.now()
        db.session.commit()
        return jsonify({'status': 'success', 'user': {'id': u.id, 'username': u.username, 'role': u.role, 'email': u.email, 'real_name': u.real_name, 'managed_pages': u.managed_pages, 'points': u.points, 'town': u.town, 'village': u.village}})
    return jsonify({'status': 'error', 'msg': '로그인 정보가 올바르지 않습니다.'}), 401

@auth_bp.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.form
    verified_email = session.pop('email_verified_for_register', None)
    if not verified_email:
        return jsonify({'status': 'error', 'msg': '이메일 인증을 먼저 완료해 주세요.'}), 400
    password = data.get('password', '')
    real_name = data.get('real_name', '')
    username = data.get('username', '').strip()
    if not username and verified_email:
        username = verified_email.split('@')[0][:20]
    lat = data.get('lat', type=float)
    lon = data.get('lon', type=float)
    town = data.get('town', '')
    village = data.get('village', '')
    neighbor = False
    if lat and lon:
        from services.geocode import gps_to_town_village, is_in_yangpyeong
        if is_in_yangpyeong(lat, lon):
            t, v = gps_to_town_village(lat, lon)
            town = t or town
            village = v or village
            neighbor = True
    if User.query.filter_by(email=verified_email).first():
        session.pop('verify_email', None)
        return jsonify({'status': 'error', 'msg': '이미 등록된 이메일입니다.'}), 400
    hashed_pw = generate_password_hash(password)
    now = datetime.now()
    new_user = User(username=username, password=hashed_pw, real_name=real_name, email=verified_email, email_verified=True, town=town, village=village, reg_town=town, reg_village=village, curr_town=town, curr_village=village, is_neighbor=neighbor, location_updated_at=now, points=1000)
    profile_img = request.files.get('profile_img')
    if profile_img and profile_img.filename:
        import os
        from services.security import validate_upload, secure_save
        ok, msg = validate_upload(profile_img, max_mb=5)
        if ok:
            profile_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles')
            os.makedirs(profile_dir, exist_ok=True)
            try:
                path = secure_save(profile_img, profile_dir, max_mb=5)
                new_user.profile_image = path
            except Exception:
                pass
    db.session.add(new_user)
    db.session.flush()
    new_user.last_payout = now
    history = PointHistory(user_id=new_user.id, change_type='signup', amount=1000, balance_after=1000, description='회원가입 지급')
    db.session.add(history)
    db.session.commit()
    return jsonify({'status': 'success', 'msg': '가입 완료! 로그인해 주세요.'})

@auth_bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    uid = session.get('user_id')
    if uid:
        user = User.query.get(uid)
        if user:
            user.last_logout = datetime.now()
            db.session.commit()
    session.clear()
    return jsonify({'status': 'success'})
