"""인증 Blueprint: 로그인 / 회원가입 / 로그아웃 / 소셜로그인 / 약관"""
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app
from models import db, User, PointHistory
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os, time

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/intro')
@auth_bp.route('/')
def intro():
    from models import NewsArticle
    selected_news = NewsArticle.query.filter(
        NewsArticle.is_selected == True,
        NewsArticle.world_admin_approved == True,
        NewsArticle.category.in_(['세계뉴스','환경뉴스','건강정보','복지정보','농업정보','관광소식'])
    ).order_by(NewsArticle.updated_at.desc()).limit(6).all()
    return render_template('intro.html', selected_news=selected_news)

@auth_bp.route('/presentation')
def presentation():
    return render_template('presentation.html')

@auth_bp.route('/terms')
def terms():
    return render_template('terms.html')

@auth_bp.route('/charter')
def charter():
    import markdown as md
    charter_path = os.path.join(current_app.root_path, 'charter.md')
    with open(charter_path, 'r', encoding='utf-8') as f:
        content = f.read()
    html = md.markdown(content, extensions=['fenced_code', 'tables'])
    return render_template('charter.html', content=html)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        verified_email = session.pop('email_verified_for_register', None)
        if not verified_email:
            return "<script>alert('이메일 인증을 먼저 완료해 주세요.'); location.href='/register';</script>"
        password = request.form['password']
        real_name = request.form['real_name']
        username = request.form['username']
        town = request.form['town']
        village = request.form['village']
        if User.query.filter_by(email=verified_email).first():
            session.pop('verify_email', None)
            return "<script>alert('이미 등록된 이메일입니다.'); location.href='/register';</script>"
        if User.query.filter_by(username=username).first():
            return "<script>alert('이미 있는 닉네임입니다.'); history.back();</script>"
        hashed_pw = generate_password_hash(password)
        now = datetime.now()
        new_user = User(
            username=username, password=hashed_pw,
            real_name=real_name, email=verified_email,
            email_verified=True,
            town=town, village=village,
            reg_town=town, reg_village=village,
            curr_town=town, curr_village=village,
            location_updated_at=now,
            points=1000
        )
        db.session.add(new_user)
        db.session.flush()
        new_user.last_payout = now
        history = PointHistory(user_id=new_user.id, change_type='signup', amount=1000, balance_after=1000, description='회원가입 지급')
        db.session.add(history)
        db.session.commit()
        from services.email_service import EmailService
        EmailService.send(verified_email, f"[양평마을] 가입을 환영합니다, {real_name}님",
            f"{real_name}님, 양평마을에 가입해 주셔서 감사합니다.\n\n지금 바로 다양한 서비스를 이용해 보세요.")
        return "<script>alert('가입 신청 완료! 로그인을 진행하세요.'); location.href='/intro';</script>"
    return render_template('register.html')

@auth_bp.route('/register/send-code', methods=['POST'])
def register_send_code():
    email = request.form.get('email', '').strip()
    if not email:
        return jsonify({'status':'error','msg':'이메일을 입력해 주세요.'})
    if User.query.filter_by(email=email).first():
        return jsonify({'status':'error','msg':'이미 등록된 이메일입니다.'})
    import secrets
    code = ''.join(secrets.choice('0123456789') for _ in range(6))
    session['verify_code'] = code
    session['verify_email'] = email
    session['verify_code_time'] = time.time()
    from services.email_service import EmailService
    EmailService.send(email, '[양평마을] 이메일 인증 코드', f'인증 코드: {code}\n\n회원가입 페이지에서 위 코드를 입력해 주세요.\n코드는 5분간 유효합니다.')
    return jsonify({'status':'success','msg':'인증 코드를 이메일로 발송했습니다.'})

@auth_bp.route('/register/verify-code', methods=['POST'])
def register_verify_code():
    code = request.form.get('code', '').strip()
    if not session.get('verify_code') or not session.get('verify_email'):
        return jsonify({'status':'error','msg':'인증 코드가 만료되었습니다.'})
    if time.time() - session.get('verify_code_time', 0) > 300:
        session.pop('verify_code', None); session.pop('verify_email', None); session.pop('verify_code_time', None)
        return jsonify({'status':'error','msg':'인증 코드가 만료되었습니다.'})
    if code != session.get('verify_code'):
        return jsonify({'status':'error','msg':'인증 코드가 일치하지 않습니다.'})
    session['email_verified_for_register'] = session['verify_email']
    session.pop('verify_code', None); session.pop('verify_code_time', None)
    return jsonify({'status':'success','msg':'이메일 인증 완료!'})

@auth_bp.route('/register/verify-email-button', methods=['POST'])
def register_verify_email_button():
    email = request.form.get('email', '').strip()
    if not email:
        return jsonify({'status':'error','msg':'이메일을 입력해 주세요.'})
    session['verify_email'] = email
    session['email_verified_for_legal'] = True
    session['email_verified_for_psycho'] = True
    session['email_verified_for_register'] = email
    from services.email_service import EmailService
    EmailService.send(email, '[양평마을] 이메일 인증 안내',
        f'이메일 주소({email})가 인증되었습니다.\n\n양평마을의 상담 게시판을 이용하실 수 있습니다.\n문의: yp@unocum.kr')
    return jsonify({'status':'success','msg':'이메일 인증 완료!', 'email': email})

def add_points(uid, amount, change_type, description, related_id=None):
    from models import User, PointHistory
    user = User.query.get(uid)
    if not user: return
    old_balance = user.points or 0
    user.points = old_balance + amount
    db.session.add(PointHistory(user_id=uid, change_type=change_type, amount=amount, balance_after=user.points, description=description, related_id=related_id))
    db.session.commit()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    default_next = request.referrer if request.referrer and request.referrer.startswith(request.host_url) and request.referrer != url_for('auth.login', _external=True) else None
    next_url = request.args.get('next') or request.form.get('next') or default_next
    if next_url and not next_url.startswith('/'):
        next_url = url_for('auth.intro')
    if request.method == 'POST':
        login_id = request.form['username']
        u = User.query.filter_by(username=login_id).first()
        if not u: u = User.query.filter_by(email=login_id).first()
        if u and check_password_hash(u.password, request.form['password']):
            session.update({'user_id': u.id, 'username': u.username, 'role': u.role})
            now = datetime.now()
            u.last_login = now
            lat = request.form.get('lat', type=float)
            lon = request.form.get('lon', type=float)
            if lat and lon:
                u.login_latitude = lat; u.login_longitude = lon
                from services.geocode import gps_to_town_village
                town, village = gps_to_town_village(lat, lon)
                if town: u.login_town = town; u.login_village = village or ''
            if u.last_payout:
                if (now - u.last_payout).days >= 30:
                    add_points(u.id, 1000, 'monthly', '30일 주기 물맑은머니 지급')
                    u.last_payout = now; db.session.commit()
            else:
                u.last_payout = now; db.session.commit()
            return redirect(next_url or url_for('user.profile', user_id=u.id))
        return "<script>alert('로그인 정보 오류'); history.back();</script>"
    return render_template('login.html', next=next_url)

@auth_bp.route('/logout')
def logout():
    uid = session.get('user_id')
    if uid:
        user = User.query.get(uid)
        if user:
            user.last_logout = datetime.now(); db.session.commit()
    session.clear()
    return redirect(url_for('auth.intro'))

@auth_bp.route('/oauth/login/<provider>')
def oauth_login(provider):
    if provider not in ('google','kakao','naver'):
        return "<script>alert('지원하지 않는 로그인 방식입니다.'); history.back();</script>"
    from services.oauth import oauth
    redirect_uri = url_for('auth.oauth_callback', provider=provider, _external=True)
    return oauth.create_client(provider).authorize_redirect(redirect_uri)

@auth_bp.route('/oauth/callback/<provider>')
def oauth_callback(provider):
    from services.oauth import oauth
    client = oauth.create_client(provider)
    token = client.authorize_access_token()
    if provider == 'google':
        userinfo = token.get('userinfo')
        if not userinfo:
            resp = client.get('https://www.googleapis.com/oauth2/v3/userinfo')
            userinfo = resp.json()
        email = userinfo.get('email',''); name = userinfo.get('name',''); sub = userinfo.get('sub','')
        if not email: return "<script>alert('이메일 정보를 가져올 수 없습니다.'); location.href='/login';</script>"
        u = User.query.filter_by(social_id=f'google_{sub}').first()
        if not u: u = User.query.filter_by(email=email).first()
        if not u:
            import random, string
            uname = name or email.split('@')[0]
            if User.query.filter_by(username=uname).first(): uname += ''.join(random.choices(string.digits, k=3))
            u = User(username=uname, email=email, real_name=name or uname, password=generate_password_hash(sub), email_verified=True)
            u.social_id = f'google_{sub}'; u.social_provider = 'google'; u.social_email = email
            u.points = 1000; now = datetime.now(); u.last_payout = now; u.location_updated_at = now
            db.session.add(u); db.session.flush()
            db.session.add(PointHistory(user_id=u.id, change_type='signup', amount=1000, balance_after=1000, description='소셜 회원가입 지급'))
            db.session.commit()
        session.update({'user_id': u.id, 'username': u.username, 'role': u.role})
        u.last_login = datetime.now(); db.session.commit()
        return redirect(url_for('user.profile', user_id=u.id))
    elif provider == 'kakao':
        userinfo = token.get('userinfo')
        if not userinfo:
            resp = client.get('https://kapi.kakao.com/v2/user/me')
            userinfo = resp.json()
        kakao_account = userinfo.get('kakao_account', {})
        email = kakao_account.get('email','')
        profile = kakao_account.get('profile', {})
        nickname = profile.get('nickname','')
        kid = str(userinfo.get('id',''))
        if not email: return "<script>alert('이메일 정보를 가져올 수 없습니다.'); location.href='/login';</script>"
        u = User.query.filter_by(social_id=f'kakao_{kid}').first()
        if not u: u = User.query.filter_by(email=email).first()
        if not u:
            import random, string
            uname = nickname or email.split('@')[0]
            if User.query.filter_by(username=uname).first(): uname += ''.join(random.choices(string.digits, k=3))
            u = User(username=uname, email=email, real_name=nickname or uname, password=generate_password_hash(kid), email_verified=True)
            u.social_id = f'kakao_{kid}'; u.social_provider = 'kakao'; u.social_email = email
            u.points = 1000; now = datetime.now(); u.last_payout = now; u.location_updated_at = now
            db.session.add(u); db.session.flush()
            db.session.add(PointHistory(user_id=u.id, change_type='signup', amount=1000, balance_after=1000, description='소셜 회원가입 지급'))
            db.session.commit()
        session.update({'user_id': u.id, 'username': u.username, 'role': u.role})
        u.last_login = datetime.now(); db.session.commit()
        return redirect(url_for('user.profile', user_id=u.id))
    elif provider == 'naver':
        userinfo = token.get('userinfo')
        if not userinfo:
            resp = client.get('https://openapi.naver.com/v1/nid/me')
            userinfo = resp.json().get('response', {})
        email = userinfo.get('email',''); name = userinfo.get('name','') or userinfo.get('nickname',''); nid = userinfo.get('id','')
        if not email: return "<script>alert('이메일 정보를 가져올 수 없습니다.'); location.href='/login';</script>"
        u = User.query.filter_by(social_id=f'naver_{nid}').first()
        if not u: u = User.query.filter_by(email=email).first()
        if not u:
            import random, string
            uname = name or email.split('@')[0]
            if User.query.filter_by(username=uname).first(): uname += ''.join(random.choices(string.digits, k=3))
            u = User(username=uname, email=email, real_name=name or uname, password=generate_password_hash(nid), email_verified=True)
            u.social_id = f'naver_{nid}'; u.social_provider = 'naver'; u.social_email = email
            u.points = 1000; now = datetime.now(); u.last_payout = now; u.location_updated_at = now
            db.session.add(u); db.session.flush()
            db.session.add(PointHistory(user_id=u.id, change_type='signup', amount=1000, balance_after=1000, description='소셜 회원가입 지급'))
            db.session.commit()
        session.update({'user_id': u.id, 'username': u.username, 'role': u.role})
        u.last_login = datetime.now(); db.session.commit()
        return redirect(url_for('user.profile', user_id=u.id))
    return "<script>alert('로그인 실패'); location.href='/login';</script>"
