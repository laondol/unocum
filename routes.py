from flask import render_template, request, redirect, url_for, jsonify, session, current_app
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from urllib.parse import quote
import json, base64, os, threading, requests

from models import db, User, Post, Comment, NewsArticle, NewsComment, NewsRecommendation, NewsVote, PointHistory, ShareReport, Message, ShareComment, ConstructionNotice, VillageAlert, HeritageStamp, TongBot, TongBotDraft, TongBotSchedule, ChatRoom, ChatMessage, VillageCache, LegalPost, LegalAppointment, LawyerSchedule, GoogleCalendarConfig, PsychoPost, PsychoAppointment, PsychoDoctorSchedule, PsychoGoogleCalendarConfig, RampApplication, Friend, FriendGroup, PostVote, StoreInfo
from services.oauth import oauth
from services.security import save_village_file
from services.ai_service import call_ai_judge, call_ai_debate, background_ai_judge, moderate_image, background_process_share
from services.email_service import EmailService
from services.construction import sync_construction_notices, sync_traffic_incidents, sync_congestion_info
from services.news_service import ai_search_news, ai_translate_and_format, ai_summarize_url
from services.geocode import haversine, gps_to_town_village, get_nearby_reports, is_in_yangpyeong, YANGPYEONG_BOUNDS, YANGPYEONG_VILLAGES

# --- [공개 경로] 인트로 및 대시보드 ---
def register_routes(app):
    
    @app.route('/')
    @app.route('/intro')
    def intro():
        selected_news = NewsArticle.query.filter(NewsArticle.is_selected == True, NewsArticle.world_admin_approved == True, NewsArticle.category.in_(['세계뉴스', '환경뉴스', '건강정보', '복지정보', '농업정보', '관광소식'])).order_by(NewsArticle.updated_at.desc()).limit(6).all()
        return render_template('intro.html', selected_news=selected_news)

    @app.route('/presentation')
    def presentation():
        return render_template('presentation.html')

    @app.route('/terms')
    def terms():
        return render_template('terms.html')

    @app.route('/charter')
    def charter():
        import markdown as md
        charter_path = os.path.join(current_app.root_path, 'charter.md')
        with open(charter_path, 'r', encoding='utf-8') as f:
            content = f.read()
        html = md.markdown(content, extensions=['fenced_code', 'tables'])
        return render_template('charter.html', content=html)

    @app.route('/main')
    def index():
        now = datetime.now()
        _cleanup_expired_posts()
        posts = Post.query.filter(Post.total_score > -50, ((Post.created_at <= now - timedelta(hours=48)) | (Post.is_forced_approved == True))).order_by(Post.created_at.desc()).all()
        return render_template('index.html', posts=posts)

    @app.route('/all-proposals')
    def all_proposals():
        now = datetime.now()
        user_id = session.get('user_id')
        _cleanup_expired_posts()
        
        all_posts = Post.query.order_by(Post.created_at.desc()).all()
        posts = []
        for p in all_posts:
            # AI 검토전 (ai_score==0): 작성자만 볼 수 있음
            if p.ai_score == 0 and p.created_at and p.created_at > now - timedelta(hours=48):
                if p.user_id == user_id: posts.append(p)
                continue
            # 점수 -50 이하: 본인만 볼 수 있음
            if p.total_score <= -50:
                if p.user_id == user_id: posts.append(p)
                continue
            # 관리자 강제 승인: 모두에게 공개
            if p.is_forced_approved:
                posts.append(p)
                continue
            # 점수 0 초과(양성): 모두에게 공개
            if p.total_score > 0:
                posts.append(p)
                continue
            # 48시간 경과: 모두에게 공개
            if p.created_at and p.created_at <= now - timedelta(hours=48):
                posts.append(p)
                continue
            # 본인 글: 심사 중에도 본인에게 공개
            if p.user_id == user_id:
                posts.append(p)
                continue
        return render_template('all_proposals.html', posts=posts, now=now, timedelta=timedelta)

    # --- [회원가입] 이웃 가입 및 선택적 주민 인증 수집 ---
    @app.route('/api/reverse-geocode')
    def reverse_geocode():
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        if not lat or not lon:
            return jsonify({"status": "error", "msg": "위도/경도 필요"})
        from services.geocode import gps_to_town_village, is_in_yangpyeong
        if not is_in_yangpyeong(lat, lon):
            return jsonify({"status": "outside", "msg": "관외 지역"})
        town, village = gps_to_town_village(lat, lon)
        return jsonify({"status": "success", "town": town or '', "village": village or ''})

    @app.route('/register/send-code', methods=['POST'])
    def register_send_code():
        email = request.form.get('email', '').strip()
        if not email:
            return jsonify({'status':'error','msg':'이메일을 입력해 주세요.'})
        if User.query.filter_by(email=email).first():
            return jsonify({'status':'error','msg':'이미 등록된 이메일입니다.'})
        import secrets, time
        code = ''.join(secrets.choice('0123456789') for _ in range(6))
        session['verify_code'] = code
        session['verify_email'] = email
        session['verify_code_time'] = time.time()
        from services.email_service import EmailService
        EmailService.send(email, '[양평마을] 이메일 인증 코드',
            f'인증 코드: {code}\n\n회원가입 페이지에서 위 코드를 입력해 주세요.\n코드는 5분간 유효합니다.')
        return jsonify({'status':'success','msg':'인증 코드를 이메일로 발송했습니다.'})

    @app.route('/register/verify-code', methods=['POST'])
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

    @app.route('/register', methods=['GET', 'POST'])
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
            history = PointHistory(
                user_id=new_user.id, change_type='signup', amount=1000,
                balance_after=1000, description='회원가입 지급'
            )
            db.session.add(history)
            db.session.commit()
            
            from services.email_service import EmailService
            EmailService.send(verified_email, f"[양평마을] 가입을 환영합니다, {real_name}님",
                f"{real_name}님, 양평마을에 가입해 주셔서 감사합니다.\n\n지금 바로 다양한 서비스를 이용해 보세요.\n- 게시글 작성 및 공유\n- 법률/심리 상담\n- 경사로 설치 신청\n- 이웃과 소통\n\nhttps://test.unocum.kr")
            
            return "<script>alert('가입 신청 완료! 로그인을 진행하세요.'); location.href='/intro';</script>"
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        default_next = request.referrer if request.referrer and request.referrer.startswith(request.host_url) and request.referrer != url_for('login', _external=True) else None
        next_url = request.args.get('next') or request.form.get('next') or default_next
        if next_url and not next_url.startswith('/'):
            next_url = url_for('intro')
        if request.method == 'POST':
            login_id = request.form['username']
            u = User.query.filter_by(username=login_id).first()
            if not u:
                u = User.query.filter_by(email=login_id).first()
            if u and check_password_hash(u.password, request.form['password']):
                session.update({'user_id': u.id, 'username': u.username, 'role': u.role})
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
                        u.last_payout = now
                        db.session.commit()
                else:
                    u.last_payout = now
                    db.session.commit()
                return redirect(next_url or url_for('user_profile', user_id=u.id))
            return "<script>alert('로그인 정보 오류'); history.back();</script>"
        return render_template('login.html', next=next_url)

    @app.route('/logout')
    def logout():
        uid = session.get('user_id')
        if uid:
            user = User.query.get(uid)
            if user:
                user.last_logout = datetime.now()
                db.session.commit()
        session.clear()
        return redirect(url_for('intro'))

    # --- [OAuth2 소셜 로그인] Google / Kakao / Naver ---
    @app.route('/oauth/login/<provider>')
    def oauth_login(provider):
        if provider not in ('google', 'kakao', 'naver'):
            return "<script>alert('지원하지 않는 로그인 방식입니다.'); history.back();</script>"
        redirect_uri = url_for('oauth_callback', provider=provider, _external=True)
        return oauth.create_client(provider).authorize_redirect(redirect_uri)

    @app.route('/oauth/callback/<provider>')
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

        session.update({'user_id': user.id, 'username': user.username, 'role': user.role})
        now = datetime.now()
        user.last_login = now
        if user.last_payout and (now - user.last_payout).days >= 30:
            add_points(user.id, 1000, 'monthly', '30일 주기 물맑은머니 지급')
            user.last_payout = now
        elif not user.last_payout:
            user.last_payout = now
        db.session.commit()
        next_url = request.args.get('next') or url_for('world_news')
        if not next_url.startswith('/'):
            next_url = url_for('world_news')
        return redirect(next_url)

    # --- [이메일 인증] ---
    @app.route('/verify-email/send', methods=['POST'])
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

    @app.route('/verify-email/<token>')
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
    @app.route('/user/update-address', methods=['POST'])
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
        return jsonify({'status':'success','msg':'주소가 수정되었습니다.'})

    # --- [이웃주민 위치인증] ---
    @app.route('/neighbor/verify', methods=['POST'])
    def neighbor_verify():
        uid = session.get('user_id')
        if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
        user = User.query.get(uid)
        if not user: return jsonify({'status':'error','msg':'사용자 없음'}), 404
        if user.is_neighbor:
            return jsonify({'status':'error','msg':'이미 이웃주민 인증되었습니다.'})
        lat = request.form.get('lat', type=float)
        lon = request.form.get('lon', type=float)
        if not lat or not lon:
            return jsonify({'status':'error','msg':'위치 정보가 필요합니다.'})
        from services.geocode import gps_to_town_village, is_in_yangpyeong
        if not is_in_yangpyeong(lat, lon):
            return jsonify({'status':'error','msg':'현재 위치가 양평군 관외입니다. 양평군 내에서 인증해 주세요.'})
        town, village = gps_to_town_village(lat, lon)
        if not town:
            return jsonify({'status':'error','msg':'위치를 확인할 수 없습니다.'})
        user.is_neighbor = True
        user.town = town
        user.village = village or ''
        user.reg_town = town
        user.reg_village = village or ''
        user.curr_latitude = lat
        user.curr_longitude = lon
        user.curr_town = town
        user.curr_village = village or ''
        # Kakao 역지오코딩으로 상세주소 조회 → 기본주소로 저장
        try:
            import requests as req_lib
            kakao_key = current_app.config.get('KAKAO_REST_API_KEY','')
            if kakao_key:
                r = req_lib.get('https://dapi.kakao.com/v2/local/geo/coord2address.json', params={
                    'x': lon, 'y': lat
                }, headers={'Authorization': f'KakaoAK {kakao_key}'}, timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    docs = data.get('documents', [])
                    if docs:
                        road = docs[0].get('road_address') or {}
                        addr = docs[0].get('address') or {}
                        full_addr = road.get('address_name','') or addr.get('address_name','')
                        building = road.get('building_name','')
                        if building:
                            full_addr += f' ({building})'
                        if full_addr:
                            user.address = full_addr[:200]
                            user.curr_address = full_addr[:200]
        except:
            pass
        user.location_updated_at = datetime.now()
        db.session.commit()
        return jsonify({'status':'success','msg':'이웃주민 인증 완료!', 'town': town, 'village': village or ''})

    # --- [초고속 제안 제출] 0.1초 즉시 등록 및 백그라운드 AI 스레드 작동 ---
    @app.route('/submit', methods=['POST'])
    def submit():
        user_id = session.get('user_id')
        if not user_id: return jsonify({"status": "fail", "msg": "로그인이 필요합니다."})
        user = User.query.get(user_id)
        if not user:
            session.clear()
            return jsonify({"status": "fail", "msg": "세션 불일치. 다시 로그인해 주세요."})

        title = request.form.get('title')
        content = request.form.get('content')
        file_url = None

        # 🏡 [보안 패치]: 참고 자료 업로드 시에도 주민의 주소지 폴더에 격리 저장
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                if ext in ('mp4', 'avi', 'mov', 'mkv', 'webm'):
                    fname = f"video_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                    target_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"{user.town}_{user.village}")
                    if not os.path.exists(target_dir): os.makedirs(target_dir)
                    file.save(os.path.join(target_dir, fname))
                    file_url = f"/static/uploads/{user.town}_{user.village}/{fname}"
                else:
                    file_url = save_village_file(file, app.config['UPLOAD_FOLDER'], user.town, user.village)

        # 그림판 드로잉 저장
        drawing = request.form.get('drawing_data')
        if drawing and len(drawing) > 2000:
            data = base64.b64decode(drawing.split(",")[1])
            fname = f"draw_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            target_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"{user.town}_{user.village}")
            if not os.path.exists(target_dir): os.makedirs(target_dir)
            with open(os.path.join(target_dir, fname), "wb") as f: f.write(data)
            file_url = f"/static/uploads/{user.town}_{user.village}/{fname}"

        # 1차 즉시 임시 저장 (대기 시간 완전히 소멸)
        new_post = Post(
            user_id=user.id, author_name=user.username, title=title, content=content,
            ai_score=0, total_score=0, category="분석중",
            ai_summary="🌳 AI 지킴이가 제안서를 정독하고 있습니다...",
            ai_reason="지킴이 AI 분석 대기 중...",
            ai_improvement_tip="AI 대안 분석 중...",
            file_path=file_url, updated_at=datetime.now()
        )
        db.session.add(new_post)
        db.session.flush()

        # 게시글 작성 시 100닢 차감 (즉시 적용)
        user.points -= 100
        user.points = max(0, user.points)
        new_post.penalty_applied = True
        new_post.deadline = datetime.now() + timedelta(days=30)
        db.session.commit()

        # 백그라운드 AI 처리 스레드 기동
        threading.Thread(target=background_ai_judge, args=(current_app._get_current_object(), new_post.id)).start()
        return jsonify({"status": "success"})

    @app.route('/post/<int:post_id>')
    def view(post_id):
        post = Post.query.get_or_404(post_id)
        uid = session.get('user_id')
        role = session.get('role')
        is_owner = (post.user_id == uid)
        # AI 검토전: 작성자와 관리자만 접근
        if post.ai_score == 0 and post.created_at and post.created_at > datetime.now() - timedelta(hours=48):
            if not is_owner and role not in ('admin', 'leader'):
                return "검토전입니다. AI 분석 완료 후 공개됩니다.", 403
        # 낙제(-50점 이하): 작성자와 관리자만 접근
        if post.total_score <= -50:
            if not is_owner and role not in ('admin', 'leader'):
                return "접근 권한이 없습니다. 낙제(-50점 이하) 게시물은 작성자만 볼 수 있습니다.", 403
        comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.asc()).all()
        return render_template('view.html', post=post, comments=comments)

    # --- [주민 전용] 제안 보완 수정 및 48시간 리셋 ---
    @app.route('/post/edit/<int:post_id>', methods=['GET', 'POST'])
    def edit_post(post_id):
        if 'user_id' not in session: return "로그인 필요", 403
        post = Post.query.get_or_404(post_id)
        if post.user_id != session['user_id'] and session.get('role') != 'admin':
            return "권한 없음", 403

        if request.method == 'POST':
            post.title = request.form['title']
            post.content = request.form['content']
            post.updated_at = datetime.now()
            post.is_forced_approved = False 
            
            # 파일 업로드 처리
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename != '':
                    file_url = save_village_file(file, app.config['UPLOAD_FOLDER'], post.author_name, post.user.town if post.user else 'unknown')
                    post.file_path = file_url
            
            # 그림판 드로잉 저장
            drawing = request.form.get('drawing_data')
            if drawing and len(drawing) > 2000:
                data = base64.b64decode(drawing.split(",")[1])
                fname = f"draw_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                target_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"{post.author_name}_{post.user.town if post.user else 'unknown'}")
                if not os.path.exists(target_dir): os.makedirs(target_dir)
                with open(os.path.join(target_dir, fname), "wb") as f: f.write(data)
                post.file_path = f"/static/uploads/{post.author_name}_{post.user.town if post.user else 'unknown'}/{fname}"
            
            ai_res = call_ai_judge(post.title, post.content)
            post.ai_score = ai_res.get('score', 0)
            post.total_score = post.ai_score + post.admin_score + post.leader_score + post.member_score
            post.ai_summary = ai_res.get('summary')
            post.ai_reason = ai_res.get('reason')
            post.ai_improvement_tip = ai_res.get('improvement_tip')
            
            db.session.commit()
            return redirect(url_for('all_proposals'))
        return render_template('edit_post.html', post=post)

    # --- [지킴이 전용] 제안 관제 및 숙의 토론 ---
    @app.route('/admin')
    def admin():
        if session.get('role') not in ['admin', 'leader']: return "권한 없음", 403
        posts = Post.query.order_by(Post.created_at.desc()).all()
        return render_template('admin.html', posts=posts)

    @app.route('/admin/post/<int:post_id>')
    def admin_post_view(post_id):
        if session.get('role') not in ['admin', 'leader']: return "권한 부족", 403
        post = Post.query.get_or_404(post_id)
        import json as _json
        debate_logs = _json.loads(post.ai_debate_log) if post.ai_debate_log else []
        return render_template('admin_view.html', post=post, debate_logs=debate_logs)

    @app.route('/admin/update_scores/<int:post_id>', methods=['POST'])
    def update_scores(post_id):
        if session.get('role') not in ['admin', 'leader']: return "권한 부족", 403
        post = Post.query.get_or_404(post_id)
        role = session.get('role')
        if role == 'admin':
            post.admin_score = int(request.form.get('admin_score', 0))
        elif role == 'leader':
            post.leader_score = int(request.form.get('leader_score', 0))
        post.is_forced_approved = 'force_approve' in request.form
        post.total_score = post.ai_score + post.admin_score + post.leader_score + post.member_score
        # 관리자와 책임자가 모두 점수를 주면 자동 공개 (-50점 이하는 제외)
        if post.admin_score != 0 and post.leader_score != 0 and post.total_score > -50:
            post.is_forced_approved = True
        db.session.commit()
        return redirect(url_for('admin_post_view', post_id=post.id))

    @app.route('/admin/debate/<int:post_id>', methods=['POST'])
    def admin_debate(post_id):
        if session.get('role') not in ['admin', 'leader']: return jsonify({"status": "error", "msg": "권한 부족"}), 403
        post = Post.query.get_or_404(post_id)
        admin_opinion = request.form.get('admin_opinion')
        if not admin_opinion:
            return jsonify({"status": "error", "msg": "의견을 입력하세요"}), 400
        suggested_score = int(request.form.get('suggested_score', post.ai_score))
        try:
            res = call_ai_debate(post, admin_opinion, suggested_score)
        except Exception as e:
            return jsonify({"status": "error", "msg": f"AI 응답 오류: {e}"}), 500
        logs = json.loads(post.ai_debate_log) if post.ai_debate_log else []
        logs.append({"time": datetime.now().strftime('%H:%M'), "admin": admin_opinion, "ai": res.get('ai_reply', 'AI 분석 오류')})
        post.ai_debate_log = json.dumps(logs, ensure_ascii=False)
        post.ai_score = res.get('final_ai_score', post.ai_score)
        post.total_score = post.ai_score + post.admin_score + post.leader_score + post.member_score
        db.session.commit()
        return jsonify({"status": "success"})

    # --- [지킴이 전용] 이웃 관리 및 고지서 즉시 영구 파기 ---
    @app.route('/admin/users')
    def admin_users():
        if session.get('role') not in ['admin', 'leader']: return "권한 부족", 403
        users = User.query.order_by(User.id.desc()).all()
        return render_template('admin_users.html', users=users)

    @app.route('/admin/users/verify/<int:user_id>/<string:action>')
    def verify_user(user_id, action):
        if session.get('role') not in ['admin', 'leader']: return "권한 부족", 403
        user = User.query.get_or_404(user_id)
        
        if action == 'approve':
            user.is_verified_resident = True
            user.points += 500
            print(f"[{user.real_name}] 이웃 인증 승인 완료. 500닢 가점.")
        elif action == 'reject':
            user.is_verified_resident = False
            user.verified_method = 'none'
            print(f"[{user.real_name}] 주민 인증 반려.")
            
        # 🛡️ 고지서 이미지 즉시 파기 (개인정보 방역 수칙 준수)
        if user.bill_image_path:
            file_abs_path = os.path.join(app.config['UPLOAD_FOLDER'], 'bills', os.path.basename(user.bill_image_path))
            try:
                if os.path.exists(file_abs_path):
                    os.remove(file_abs_path)
                    print(f"🔥 주민 보안 자치 규약에 따라 {user.real_name}님의 고지서 사진 파일을 완전 파기했습니다.")
            except Exception as e:
                print(f"파일 삭제 에러: {e}")
            user.bill_image_path = None
            
        db.session.commit()
        return redirect(url_for('admin_users'))

    @app.route('/comment/<int:post_id>', methods=['POST'])
    def add_comment(post_id):
        content = request.form.get('content')
        ai_res = call_ai_judge("", content, is_comment=True)
        new_cm = Comment(post_id=post_id, author=session.get('username', '이웃'), content=content, total_score=ai_res.get('score', 0))
        db.session.add(new_cm)
        db.session.commit()
        return redirect(url_for('view', post_id=post_id))

    # ============================================================
    # [관리자 전용] AI 뉴스 큐레이션 시스템
    # ============================================================
    @app.route('/admin/news')
    def admin_news():
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        page = request.args.get('page', 1, type=int)
        tab = request.args.get('tab', 'all')
        query = NewsArticle.query
        if tab == 'all':
            query = query.filter(or_(NewsArticle.is_ai_generated == False, NewsArticle.is_selected == True))
        elif tab == 'world':
            query = query.filter(NewsArticle.category.in_(['세계뉴스', '환경뉴스', '건강정보', '복지정보', '농업정보', '관광소식']))
        elif tab == 'kr_yp':
            query = query.filter(NewsArticle.category.in_(['대한민국뉴스', '양평소식', '정책정보', '지역소식']))
        news_list = query.order_by(NewsArticle.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
        return render_template('admin_news.html', news_list=news_list, tab=tab)

    @app.route('/admin/news/ai-suggest', methods=['POST'])
    def admin_news_ai_suggest():
        if session.get('role') not in ['admin', 'leader']:
            return jsonify({"status": "error", "msg": "권한 없음"}), 403
        tab = request.form.get('tab', 'world')
        # 회원들이 많이 추천한 인기 카테고리/키워드 수집
        trending_context = ''
        try:
            top_cats = db.session.query(NewsArticle.category, db.func.count(NewsVote.id)).join(NewsVote, NewsVote.news_id == NewsArticle.id).filter(NewsVote.vote == 'like').group_by(NewsArticle.category).order_by(db.func.count(NewsVote.id).desc()).limit(3).all()
            if top_cats:
                cats = [c[0] for c in top_cats if c[0]]
                trending_context = ', '.join(cats)
        except:
            pass
        suggestions = ai_search_news(news_type=tab, trending_context=trending_context)
        if not suggestions:
            return jsonify({"status": "error", "msg": "AI 주제 제안 실패. Groq 서버를 확인하세요."})
        from services.naver_news import search_news
        count = 0
        for item in suggestions:
            title = item.get('title', '')
            if not title:
                continue
            search_lang = 'en' if tab == 'world' else 'ko'
            news_results, news_source = search_news(title, display=1, language=search_lang)
            if news_results:
                real = news_results[0]
                category = item.get('category', '세계뉴스')
                if tab == 'kr_yp' and category not in ['대한민국뉴스', '양평소식', '정책정보', '지역소식']:
                    category = '대한민국뉴스'
                elif tab == 'world' and category not in ['세계뉴스', '환경뉴스', '건강정보', '복지정보', '농업정보', '관광소식']:
                    category = '세계뉴스'
                ai_reason = item.get('reason', '')
                # 세계뉴스는 영문→한글 번역
                raw_title = real.get('title', title)
                raw_desc = real.get('description', '')
                if tab == 'world' and raw_title:
                    try:
                        from services.news_service import _groq_text
                        trans = _groq_text(
                            "Translate English news to natural Korean. Output JSON only.",
                            f"Translate to Korean:\nEN title: {raw_title[:200]}\nEN description: {raw_desc[:500]}\n\nJSON: {{\"title\": \"번역된 제목\", \"description\": \"번역된 내용\"}}",
                            format_json=True
                        )
                        if trans:
                            raw_title = trans.get('title', raw_title) or raw_title
                            raw_desc = trans.get('description', raw_desc) or raw_desc
                    except:
                        pass
                article = NewsArticle(
                    title=raw_title,
                    summary=(raw_desc or '')[:200],
                    content=f"<p>{(raw_desc or '')[:1000]}</p>",
                    category=category,
                    source_url=real.get('url', ''),
                    is_ai_generated=False,
                    is_selected=True,
                    ai_reason=ai_reason,
                    created_by=session.get('user_id'),
                    source_name=news_source
                )
                # 한자/일본어 정리
                try:
                    from services.news_service import clean_cjk_text
                    cleaned_title, cleaned_summary, cleaned_content = clean_cjk_text(article.title, article.summary, article.content)
                    article.title = cleaned_title or article.title
                    article.summary = cleaned_summary or article.summary
                    article.content = cleaned_content or article.content
                except:
                    pass
                # AI 승인 자동 True
                if tab == 'world':
                    article.world_ai_approved = True
                elif tab == 'kr_yp':
                    article.kr_yp_ai_approved = True
                db.session.add(article)
                count += 1
        db.session.commit()
        return jsonify({"status": "success", "count": count, "msg": f"✅ 실제 뉴스 {count}개를 가져왔습니다{' (영문→한글 번역 완료)' if tab == 'world' else ''}."})

    @app.route('/admin/news/toggle/<int:news_id>')
    def admin_news_toggle(news_id):
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        article = NewsArticle.query.get_or_404(news_id)
        article.is_selected = not article.is_selected
        article.updated_at = datetime.now()
        db.session.commit()
        return redirect(url_for('admin_news'))

    @app.route('/admin/news/approve/<int:news_id>/<string:tab>/<string:approver>')
    def admin_news_approve(news_id, tab, approver):
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        article = NewsArticle.query.get_or_404(news_id)
        if tab == 'world':
            if approver == 'ai':
                article.world_ai_approved = not article.world_ai_approved
            elif approver == 'admin':
                article.world_admin_approved = not article.world_admin_approved
        elif tab == 'kr_yp':
            if approver == 'ai':
                article.kr_yp_ai_approved = not article.kr_yp_ai_approved
            elif approver == 'admin':
                article.kr_yp_admin_approved = not article.kr_yp_admin_approved
        article.updated_at = datetime.now()
        db.session.commit()
        return redirect(url_for('admin_news', tab=tab))

    @app.route('/admin/news/delete/<int:news_id>')
    def admin_news_delete(news_id):
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        article = NewsArticle.query.get_or_404(news_id)
        if article.image_path:
            img_path = os.path.join(current_app.root_path, article.image_path.lstrip('/'))
            try:
                if os.path.exists(img_path): os.remove(img_path)
            except: pass
        db.session.delete(article)
        db.session.commit()
        return redirect(url_for('admin_news'))

    @app.route('/admin/news/create', methods=['GET', 'POST'])
    def admin_news_create():
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            if not title:
                return "<script>alert('제목을 입력하세요.'); history.back();</script>"
            img_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    img_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'news')
                    if not os.path.exists(img_dir): os.makedirs(img_dir)
                    fname = f"news_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                    file.save(os.path.join(img_dir, fname))
                    img_path = f"/static/uploads/news/{fname}"
            article = NewsArticle(
                title=title,
                summary=request.form.get('summary', ''),
                content=request.form.get('content', ''),
                source_url=request.form.get('source_url', ''),
                source_name=request.form.get('source_name', ''),
                image_path=img_path,
                category=request.form.get('category', '세계뉴스'),
                ai_reason=request.form.get('ai_reason', ''),
                is_selected='is_selected' in request.form,
                created_by=session.get('user_id')
            )
            try:
                ai_res = call_ai_judge(title, request.form.get('content', '')[:500])
                article.ai_score = ai_res.get('score', 0)
            except:
                article.ai_score = 0
            # 한자/일본어 정리
            try:
                from services.news_service import clean_cjk_text
                cleaned_title, cleaned_summary, cleaned_content = clean_cjk_text(article.title, article.summary, article.content)
                article.title = cleaned_title or article.title
                article.summary = cleaned_summary or article.summary
                article.content = cleaned_content or article.content
            except:
                pass
            db.session.add(article)
            db.session.commit()
            return redirect(url_for('admin_news'))
        return render_template('admin_news_create.html', article=None)

    @app.route('/admin/news/edit/<int:news_id>', methods=['GET', 'POST'])
    def admin_news_edit(news_id):
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        article = NewsArticle.query.get_or_404(news_id)
        translated = ''
        if request.args.get('translate') == '1' and article.source_url:
            try:
                import requests as req
                r = req.get(article.source_url, headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
                text = r.text[:3000]
                key = current_app.config.get('GROQ_API_KEY','')
                if key:
                    prompt = f"다음 내용을 한국어로 번역하세요. 원문 그대로 상세히 번역하세요.\n\n{text}"
                    rr = req.post("https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                        json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":prompt}],"max_tokens":1500},
                        timeout=30)
                    if rr.status_code == 200:
                        translated = rr.json()["choices"][0]["message"]["content"]
            except: pass
        if request.method == 'POST':
            article.title = request.form.get('title', '').strip()
            article.summary = request.form.get('summary', '')
            article.content = request.form.get('content', '')
            article.source_url = request.form.get('source_url', '')
            article.source_name = request.form.get('source_name', '')
            article.category = request.form.get('category', '세계뉴스')
            article.ai_reason = request.form.get('ai_reason', '')
            article.is_selected = 'is_selected' in request.form
            article.updated_at = datetime.now()
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    img_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'news')
                    if not os.path.exists(img_dir): os.makedirs(img_dir)
                    fname = f"news_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                    file.save(os.path.join(img_dir, fname))
                    article.image_path = f"/static/uploads/news/{fname}"
            try:
                ai_res = call_ai_judge(article.title, article.content[:500])
                article.ai_score = ai_res.get('score', 0)
            except:
                article.ai_score = 0
            # 한자/일본어 정리
            try:
                from services.news_service import clean_cjk_text
                cleaned_title, cleaned_summary, cleaned_content = clean_cjk_text(article.title, article.summary, article.content)
                article.title = cleaned_title or article.title
                article.summary = cleaned_summary or article.summary
                article.content = cleaned_content or article.content
            except:
                pass
            db.session.commit()
            return redirect(url_for('admin_news'))
        return render_template('admin_news_create.html', article=article, translated=translated)

    @app.route('/admin/news/clean-cjk', methods=['POST'])
    def admin_news_clean_cjk():
        if session.get('role') not in ['admin', 'leader']:
            return jsonify({"status": "error", "msg": "권한 없음"}), 403
        from services.news_service import clean_cjk_text
        tab = request.form.get('tab', 'all')
        query = NewsArticle.query
        if tab == 'world':
            query = query.filter(NewsArticle.category.in_(['세계뉴스', '환경뉴스', '건강정보', '복지정보', '농업정보', '관광소식']))
        elif tab == 'kr_yp':
            query = query.filter(NewsArticle.category.in_(['대한민국뉴스', '양평소식', '정책정보', '지역소식']))
        articles = query.all()
        count = 0
        for a in articles:
            try:
                cleaned_title, cleaned_summary, cleaned_content = clean_cjk_text(a.title, a.summary, a.content)
                if cleaned_title and cleaned_title != a.title:
                    a.title = cleaned_title
                if cleaned_summary and cleaned_summary != a.summary:
                    a.summary = cleaned_summary
                if cleaned_content and cleaned_content != a.content:
                    a.content = cleaned_content
                a.updated_at = datetime.now()
                count += 1
            except:
                pass
        db.session.commit()
        return jsonify({"status": "success", "count": count, "msg": f"✅ 뉴스 {count}개 한자/일본어 정리 완료"})

    @app.route('/admin/news/import-url', methods=['POST'])
    def admin_news_import_url():
        if session.get('role') not in ['admin', 'leader']:
            return jsonify({"status": "error", "msg": "권한 없음"}), 403
        url = request.form.get('url', '').strip()
        tab = request.form.get('tab', 'world')
        if not url:
            return jsonify({"status": "error", "msg": "URL을 입력하세요."})
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'utf-8'
            text = resp.text
        except Exception as e:
            return jsonify({"status": "error", "msg": f"페이지를 가져올 수 없습니다: {str(e)}"})
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(text, 'html.parser')
            # 제거할 태그
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript', 'form', 'button']): tag.decompose()
            # 제거할 클래스/아이디 패턴 (UI/광고/네비게이션)
            for pattern in ['gnb', 'lnb', 'menu', 'navi', 'sidebar', 'footer', 'header', 'banner', 'ad ', 'wrap_', 'search', 'comment', 'reply', 'btn_', 'link_']:
                for el in soup.find_all(class_=lambda c: c and pattern in str(c).lower()):
                    el.decompose()
                for el in soup.find_all(id=lambda i: i and pattern in str(i).lower()):
                    el.decompose()
            # 본문 영역 우선 추출 시도
            main_area = soup.find('article') or soup.find('main') or soup.find('[role="main"]')
            raw_text = main_area.get_text(separator='\n', strip=True) if main_area else soup.get_text(separator='\n', strip=True)
            # 한 줄에 2글자 미만 or 특정 UI 키워드 줄 제거
            ui_keywords = ['본문 바로가기', '카테고리 이동', 'MY메뉴', '검색', '공유하기', 'URL복사', '신고하기',
                           '메뉴 열기', '메뉴 닫기', '이웃추가', '폰트 크기', '폰트크기', '블로그', '카페',
                           '메일', '뉴스', '지도', '로그인', 'MY', '메뉴', '펼쳐보기', '더보기']
            lines = [l for l in raw_text.split('\n')
                     if len(l.strip()) >= 3
                     and not any(kw in l for kw in ui_keywords)]
            body_text = '\n'.join(lines)[:3000]
        except:
            body_text = text[:2000]
        result = ai_summarize_url(body_text[:3000])
        if not result:
            result = {"title": "URL에서 가져온 기사", "summary": "AI 요약 실패", "category": "세계뉴스", "is_useful": True}
        # URL을 가져온 탭에 맞게 카테고리 지정
        category = result.get('category', '세계뉴스')
        if tab == 'kr_yp' and category not in ['대한민국뉴스', '양평소식', '정책정보', '지역소식']:
            category = '대한민국뉴스'
        article = NewsArticle(
            title=result.get('title', '가져온 기사'),
            summary=result.get('summary', ''),
            content=f"<p>{body_text[:2000].replace(chr(10), '</p><p>')}</p>",
            source_url=url,
            category=category,
            is_selected=True,
            is_ai_generated=True,
            created_by=session.get('user_id')
        )
        # 한자/일본어 정리
        try:
            from services.news_service import clean_cjk_text
            cleaned_title, cleaned_summary, cleaned_content = clean_cjk_text(article.title, article.summary, article.content)
            article.title = cleaned_title or article.title
            article.summary = cleaned_summary or article.summary
            article.content = cleaned_content or article.content
        except:
            pass
        # AI 승인 자동 True
        if tab == 'world':
            article.world_ai_approved = True
        elif tab == 'kr_yp':
            article.kr_yp_ai_approved = True
        db.session.add(article)
        db.session.commit()
        return jsonify({"status": "success", "news_id": article.id})

    @app.route('/news/like/<int:news_id>', methods=['POST'])
    def news_like(news_id):
        if not session.get('username'):
            return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
        uid = session['user_id']
        article = NewsArticle.query.get_or_404(news_id)
        existing = NewsVote.query.filter_by(user_id=uid, news_id=news_id).first()
        if existing:
            if existing.vote == 'like':
                return jsonify({"status": "success", "msg": "이미 추천했습니다.", "likes": article.like_count, "dislikes": article.dislike_count})
            existing.vote = 'like'
            article.like_count += 1
            article.dislike_count = max(0, article.dislike_count - 1)
            add_points(uid, 5, 'like', '뉴스 좋아요', news_id)
        else:
            db.session.add(NewsVote(user_id=uid, news_id=news_id, vote='like'))
            article.like_count += 1
            add_points(uid, 5, 'like', '뉴스 좋아요', news_id)
        db.session.commit()
        return jsonify({"status": "success", "likes": article.like_count, "dislikes": article.dislike_count})

    @app.route('/news/dislike/<int:news_id>', methods=['POST'])
    def news_dislike(news_id):
        if not session.get('username'):
            return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
        uid = session['user_id']
        article = NewsArticle.query.get_or_404(news_id)
        existing = NewsVote.query.filter_by(user_id=uid, news_id=news_id).first()
        if existing:
            if existing.vote == 'dislike':
                return jsonify({"status": "success", "msg": "이미 싫어요했습니다.", "likes": article.like_count, "dislikes": article.dislike_count})
            existing.vote = 'dislike'
            article.dislike_count += 1
            article.like_count = max(0, article.like_count - 1)
        else:
            db.session.add(NewsVote(user_id=uid, news_id=news_id, vote='dislike'))
            article.dislike_count += 1
        db.session.commit()
        return jsonify({"status": "success", "likes": article.like_count, "dislikes": article.dislike_count})

    @app.route('/news/<int:news_id>')
    def news_detail(news_id):
        article = NewsArticle.query.get_or_404(news_id)
        comments = NewsComment.query.filter_by(news_id=news_id).order_by(NewsComment.created_at.asc()).all()
        return render_template('news_detail.html', article=article, comments=comments)

    @app.route('/news/comment', methods=['POST'])
    def news_comment():
        if not session.get('username'):
            return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
        news_id = request.form.get('news_id', type=int)
        content = request.form.get('content', '').strip()
        parent_id = request.form.get('parent_id', type=int)
        
        if not news_id or not content:
            return jsonify({"status": "error", "msg": "내용을 입력하세요."})
        
        # AI 검토
        ai_res = call_ai_judge("", content, is_comment=True)
        is_hidden = ai_res.get('score', 0) <= -50
        
        comment = NewsComment(
            news_id=news_id,
            user_id=session.get('user_id'),
            author_name=session.get('username'),
            content=content,
            parent_id=parent_id if parent_id else None,
            ai_score=ai_res.get('score', 0),
            is_hidden=is_hidden
        )
        db.session.add(comment)
        add_points(session['user_id'], 10, 'comment', '뉴스 댓글 작성', news_id)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "ai_score": ai_res.get('score', 0),
            "is_hidden": is_hidden
        })

    @app.route('/news/<int:news_id>/comments')
    def news_comments_fragment(news_id):
        comments = NewsComment.query.filter_by(news_id=news_id).order_by(NewsComment.created_at.asc()).all()
        return render_template('news_comment_item.html', comments=comments)

    @app.route('/api/news/content/<int:news_id>')
    def api_news_content(news_id):
        a = NewsArticle.query.get_or_404(news_id)
        return jsonify({
            'title': a.title,
            'content': a.content or '본문 내용이 없습니다.',
            'category': a.category,
            'summary': a.summary or ''
        })

    def _get_news_with_recs(news_list):
        """각 뉴스에 승인된 추천링크 로드"""
        for a in news_list.items:
            a.recs = NewsRecommendation.query.filter_by(news_id=a.id, is_approved=True).order_by(NewsRecommendation.created_at.desc()).limit(3).all()
        return news_list

    @app.route('/world-news')
    def world_news():
        page = request.args.get('page', 1, type=int)
        news_list = NewsArticle.query.filter(NewsArticle.is_selected == True, NewsArticle.world_admin_approved == True, NewsArticle.category.in_(['세계뉴스', '환경뉴스', '건강정보', '복지정보', '농업정보', '관광소식'])).order_by(NewsArticle.like_count.desc(), NewsArticle.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
        return render_template('world_news.html', news_list=_get_news_with_recs(news_list), title="세계 뉴스")

    @app.route('/yp-news')
    def yp_news():
        page = request.args.get('page', 1, type=int)
        news_list = NewsArticle.query.filter(NewsArticle.is_selected == True, db.or_(NewsArticle.world_admin_approved == True, NewsArticle.kr_yp_admin_approved == True)).order_by(NewsArticle.like_count.desc(), NewsArticle.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
        return render_template('yp_news.html', news_list=_get_news_with_recs(news_list), title="양평 소식")

    @app.route('/kr-yp-news')
    def kr_yp_news():
        page = request.args.get('page', 1, type=int)
        news_list = NewsArticle.query.filter(
            NewsArticle.is_selected == True,
            NewsArticle.kr_yp_admin_approved == True,
            NewsArticle.category.in_(['대한민국뉴스', '양평소식', '정책정보', '지역소식'])
        ).order_by(NewsArticle.like_count.desc(), NewsArticle.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
        return render_template('kr_yp_news.html', news_list=_get_news_with_recs(news_list), title="대한민국과양평")

    @app.route('/news/<int:news_id>/recommend', methods=['POST'])
    def news_recommend(news_id):
        if not session.get('username'):
            return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
        article = NewsArticle.query.get_or_404(news_id)
        title = request.form.get('title', '').strip()
        url = request.form.get('url', '').strip()
        description = request.form.get('description', '').strip()
        if not title or not url:
            return jsonify({"status": "error", "msg": "제목과 URL을 입력하세요."})
        rec = NewsRecommendation(
            news_id=news_id,
            user_id=session.get('user_id'),
            author_name=session.get('username'),
            title=title,
            url=url,
            description=description
        )
        db.session.add(rec)
        db.session.commit()
        return jsonify({"status": "success", "msg": "추천링크가 접수되었습니다. 관리자 승인 후 게시됩니다."})

    @app.route('/news/<int:news_id>/recommendations')
    def news_recommendations_fragment(news_id):
        recs = NewsRecommendation.query.filter_by(news_id=news_id, is_approved=True).order_by(NewsRecommendation.created_at.desc()).all()
        return render_template('news_recommendation_item.html', recommendations=recs)

    @app.route('/admin/news/recommendations')
    def admin_news_recommendations():
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        page = request.args.get('page', 1, type=int)
        recs = NewsRecommendation.query.filter_by(is_approved=False).order_by(NewsRecommendation.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
        return render_template('admin_news_recommendations.html', recs=recs)

    @app.route('/admin/news/recommendation/approve/<int:rec_id>')
    def admin_news_recommendation_approve(rec_id):
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        rec = NewsRecommendation.query.get_or_404(rec_id)
        rec.is_approved = True
        rec.approved_by = session.get('user_id')
        rec.approved_at = datetime.now()
        db.session.commit()
        return redirect(url_for('admin_news_recommendations'))

    @app.route('/admin/news/recommendation/reject/<int:rec_id>')
    def admin_news_recommendation_reject(rec_id):
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        rec = NewsRecommendation.query.get_or_404(rec_id)
        db.session.delete(rec)
        db.session.commit()
        return redirect(url_for('admin_news_recommendations'))

    # ========== 낙제 게시물 30일 자동 삭제 ==========
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

    @app.route('/mypage/points')
    def mypage_points():
        if not session.get('username'):
            return redirect(url_for('login', next=request.path))
        user = User.query.get(session['user_id'])
        raw_history = PointHistory.query.filter_by(user_id=user.id).order_by(PointHistory.created_at.desc()).limit(100).all()
        # 잔액을 실제 user.points 기준으로 재계산 (내역 불일치 방지)
        running = user.points
        for h in raw_history:
            h.balance_after = running
            running -= h.amount
        return render_template('mypage_points.html', user=user, history=raw_history)

    @app.route('/admin/users/points/<int:user_id>', methods=['GET', 'POST'])
    def admin_user_points(user_id):
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        user = User.query.get_or_404(user_id)
        if request.method == 'POST':
            amount = int(request.form.get('amount', 0))
            change_type = request.form.get('change_type', 'admin_adjust')
            description = request.form.get('description', '관리자 조정')
            add_points(user.id, amount, change_type, description)
            return redirect(url_for('admin_user_points', user_id=user.id))
        history = PointHistory.query.filter_by(user_id=user.id).order_by(PointHistory.created_at.desc()).all()
        return render_template('admin_user_points.html', user=user, history=history)

    @app.route('/mypage/points/charge')
    def points_charge():
        if not session.get('username'):
            return redirect(url_for('login', next='/mypage/points/charge'))
        user = User.query.get(session['user_id'])
        history = PointHistory.query.filter_by(user_id=user.id).order_by(PointHistory.created_at.desc()).limit(20).all()
        portone_store = current_app.config.get('PORTONE_STORE_ID', 'store-12345678')
        portone_channel = current_app.config.get('PORTONE_CHANNEL_KEY', 'channel-key-12345678')
        return render_template('points_charge.html', user=user, point_history=history,
            portone_store_id=portone_store, portone_channel=portone_channel)

    @app.route('/api/payment/prepare', methods=['POST'])
    def payment_prepare():
        if not session.get('username'):
            return jsonify({"error": "로그인이 필요합니다."}), 401
        data = request.get_json()
        nip = data.get('nip', 0)
        if nip < 1000:
            return jsonify({"error": "최소 1,000닢부터 충전 가능합니다."})
        payment_id = f"nip_{session['user_id']}_{int(datetime.now().timestamp())}"
        return jsonify({"payment_id": payment_id, "nip": nip})

    @app.route('/api/payment/verify', methods=['POST'])
    def payment_verify():
        if not session.get('username'):
            return jsonify({"error": "로그인이 필요합니다."}), 401
        data = request.get_json()
        nip = data.get('nip', 0)
        uid = session['user_id']
        user = User.query.get(uid)
        if not user:
            return jsonify({"error": "사용자를 찾을 수 없습니다."})
        user.points = (user.points or 0) + nip
        db.session.add(PointHistory(
            user_id=uid, change_type='charge', amount=nip,
            description=f'닢 충전 ({nip}닢)', balance_after=user.points
        ))
        db.session.commit()
        return jsonify({"success": True, "nip": nip, "balance": user.points})

    def check_paid_transition():
        """유료전환 체크: 총 회원 1만명 초과 시"""
        total_users = User.query.count()
        if total_users > 10000:
            # 무료회원 중 미전환자에게 알림 등 처리 가능
            pass
        return total_users > 10000

    @app.route('/search')
    def search():
        q = request.args.get('q', '').strip()
        results = {'posts': [], 'shares': [], 'news': []}
        if q:
            results['posts'] = Post.query.filter(
                db.or_(Post.title.ilike(f'%{q}%'), Post.content.ilike(f'%{q}%'))
            ).order_by(Post.created_at.desc()).limit(20).all()
            results['shares'] = ShareReport.query.filter(
                db.or_(ShareReport.title.ilike(f'%{q}%'), ShareReport.description.ilike(f'%{q}%'))
            ).order_by(ShareReport.created_at.desc()).limit(20).all()
            results['news'] = NewsArticle.query.filter(
                db.or_(NewsArticle.title.ilike(f'%{q}%'), NewsArticle.summary.ilike(f'%{q}%')),
                db.or_(NewsArticle.world_admin_approved == True, NewsArticle.kr_yp_admin_approved == True)
            ).order_by(NewsArticle.created_at.desc()).limit(20).all()
        return render_template('search.html', q=q, results=results)

    @app.route('/api/rag/search')
    def rag_search_api():
        q = request.args.get('q', '').strip()
        if not q:
            return jsonify({'hits': []})
        from services.rag import search
        hits = search(q, top_k=10)
        return jsonify({'hits': hits})

    # --- [회원 프로필 & 쪽지] ---

    @app.route('/post/like/<int:post_id>', methods=['POST'])
    def post_like(post_id):
        uid = session.get('user_id')
        if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
        existing = PostVote.query.filter_by(post_id=post_id, user_id=uid).first()
        if existing:
            return jsonify({'status':'error','msg':'이미 투표했습니다'}), 400
        post = Post.query.get_or_404(post_id)
        v = PostVote(post_id=post_id, user_id=uid, vote_type='like')
        db.session.add(v)
        post.like_count = (post.like_count or 0) + 1
        like_count = post.like_count
        dislike_count = post.dislike_count or 0
        total_voters = like_count + dislike_count
        if total_voters <= 30:
            post.member_score = like_count - dislike_count
        else:
            post.member_score = round((like_count - dislike_count) * 30 / total_voters)
        post.member_score = max(-30, min(30, post.member_score))
        post.total_score = post.ai_score + post.admin_score + post.leader_score + post.member_score
        voter = User.query.get(uid)
        voter_history = PointHistory(user_id=uid, change_type='like', amount=-5, balance_after=voter.points - 5, description='좋아요 투표', related_id=post_id)
        db.session.add(voter_history)
        voter.points -= 5
        if post.user_id and post.user_id != uid:
            author = User.query.get(post.user_id)
            author_history = PointHistory(user_id=post.user_id, change_type='like_reward', amount=1, balance_after=author.points + 1, description='좋아요 받음', related_id=post_id)
            db.session.add(author_history)
            author.points += 1
        status_changed = False
        if post.status == '제안' and post.total_score >= 80:
            post.status = '현실화'
            status_changed = True
            admin_user = User.query.filter(User.role == 'admin').first()
            if admin_user and post.user_id and post.user_id != admin_user.id:
                msg = Message(
                    sender_id=admin_user.id,
                    sender_name=admin_user.username,
                    sender_role='admin',
                    receiver_id=post.user_id,
                    subject='🎉 현실화 축하드립니다',
                    content='회의에 참석 하실 수 있으실까요 가능한 날짜와 시간을 알려 주세요. 직접 방문하거나 구글미트로 회의 하실 수 있습니다. 혹시 문의 사항이 있으시면 010-2438-7953으로 오전 10시 ~ 오후 6시 월 금요일 사이에 연락 주세요.'
                )
                db.session.add(msg)
        db.session.commit()
        return jsonify({'status':'success', 'likes':post.like_count, 'dislikes':post.dislike_count, 'total_score':post.total_score, 'status_changed':status_changed, 'new_status':post.status})

    @app.route('/post/dislike/<int:post_id>', methods=['POST'])
    def post_dislike(post_id):
        uid = session.get('user_id')
        if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
        existing = PostVote.query.filter_by(post_id=post_id, user_id=uid).first()
        if existing:
            return jsonify({'status':'error','msg':'이미 투표했습니다'}), 400
        post = Post.query.get_or_404(post_id)
        v = PostVote(post_id=post_id, user_id=uid, vote_type='dislike')
        db.session.add(v)
        post.dislike_count = (post.dislike_count or 0) + 1
        like_count = post.like_count or 0
        dislike_count = post.dislike_count
        total_voters = like_count + dislike_count
        if total_voters <= 30:
            post.member_score = like_count - dislike_count
        else:
            post.member_score = round((like_count - dislike_count) * 30 / total_voters)
        post.member_score = max(-30, min(30, post.member_score))
        post.total_score = post.ai_score + post.admin_score + post.leader_score + post.member_score
        voter = User.query.get(uid)
        voter_history = PointHistory(user_id=uid, change_type='dislike', amount=-5, balance_after=voter.points - 5, description='나빠요 투표', related_id=post_id)
        db.session.add(voter_history)
        voter.points -= 5
        if post.user_id and post.user_id != uid:
            author = User.query.get(post.user_id)
            author_history = PointHistory(user_id=post.user_id, change_type='dislike_penalty', amount=-1, balance_after=author.points - 1, description='나빠요 받음', related_id=post_id)
            db.session.add(author_history)
            author.points -= 1
        db.session.commit()
        return jsonify({'status':'success', 'likes':post.like_count, 'dislikes':post.dislike_count, 'total_score':post.total_score})

    @app.route('/user/<int:user_id>')
    def user_profile(user_id):
        if not session.get('username'):
            return redirect(url_for('login', next=request.path))
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
        bot_name = ''
        posts = []
        curr_location = ''
        yp_towns = {'양평읍','강상면','강하면','양서면','옥천면','서종면','단월면','청운면','양동면','지평면','용문면','개군면'}
        if user.curr_address:
            curr_location = user.curr_address
        elif user.curr_town and user.curr_town in yp_towns:
            curr_location = f"{user.curr_town} {user.curr_village or ''}"
        elif user.curr_latitude and user.curr_longitude:
            from services.transit import reverse_geocode
            from config import Config
            geo = reverse_geocode(user.curr_latitude, user.curr_longitude,
                kakao_key=Config.KAKAO_REST_API_KEY,
                naver_id=Config.NAVER_SEARCH_CLIENT_ID,
                naver_secret=Config.NAVER_SEARCH_CLIENT_SECRET)
            if geo and geo.get('address'):
                curr_location = geo['address']
            else:
                curr_location = f"{user.curr_latitude:.4f}, {user.curr_longitude:.4f}"
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
        # 게시글 모음
        from models import Post, ShareReport
        own_posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).limit(10).all()
        for p in own_posts:
            posts.append({"type": "제안", "title": p.title, "url": f"/post/{p.id}", "date": p.created_at.strftime("%m/%d") if p.created_at else ""})
        own_shares = ShareReport.query.filter_by(user_id=user.id).order_by(ShareReport.created_at.desc()).limit(10).all()
        for s in own_shares:
            posts.append({"type": "공유", "title": s.title or "제목없음", "url": f"/share/detail/{s.id}", "date": s.created_at.strftime("%m/%d") if s.created_at else ""})
        posts.sort(key=lambda x: x["date"], reverse=True)
        posts = posts[:15]
        
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
            is_friend=is_friend,
            bot_name=bot_name,
            posts=posts,
            curr_location=curr_location,
            recent_friends=recent_friends,
            bot_message=bot_message
        )

    @app.route('/user/location/refresh', methods=['POST'])
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

    @app.route('/user/location/share/toggle', methods=['POST'])
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

    @app.route('/user/village/notify/toggle', methods=['POST'])
    def user_village_notify_toggle():
        if not session.get('username'):
            return jsonify({"status":"error","msg":"로그인 필요"}), 401
        user = User.query.get(session['user_id'])
        val = request.get_json().get('value', True)
        user.village_notify = val
        db.session.commit()
        return jsonify({"status":"success"})

    @app.route('/user/location/correct', methods=['POST'])
    def user_location_correct():
        if not session.get('username'):
            return jsonify({"status":"error","msg":"로그인 필요"}), 401
        user = User.query.get(session['user_id'])
        # JSON 또는 폼 POST 모두 지원
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
        # 상세주소 지오코딩
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
        user.address = manual_loc[:200]  # 기본주소도 함께 갱신
        user.location_updated_at = datetime.now()
        user.points = (user.points or 0) + 1
        db.session.add(PointHistory(user_id=user.id, change_type='location_correct', amount=1, description=f'위치 보정: {manual_loc}'))
        db.session.commit()
        if request.is_json:
            return jsonify({"status":"success","msg":f"'{manual_loc}'(으)로 보정되었습니다. 1닢 지급!{learn_msg}"})
        back = request.args.get('back','')
        if back == 'construction':
            return redirect('/construction?tab=home')
        return redirect('/user/' + str(user.id))

    @app.route('/message/inbox')
    def message_inbox():
        if not session.get('username'):
            return redirect(url_for('login', next='/message/inbox'))
        uid = session['user_id']
        tab = request.args.get('tab', 'received')
        received = Message.query.filter_by(receiver_id=uid).order_by(Message.created_at.desc()).all()
        sent_msgs = Message.query.filter_by(sender_id=uid).order_by(Message.created_at.desc()).all()
        for m in sent_msgs:
            u = User.query.get(m.receiver_id)
            m.receiver_name = u.real_name or u.username if u else '알수없음'
        return render_template('message_inbox.html', received=received, sent=sent_msgs, tab=tab)

    @app.route('/message/send/<int:receiver_id>', methods=['GET', 'POST'])
    def send_message(receiver_id):
        if not session.get('username'):
            return redirect(url_for('login', next=request.path))
        receiver = User.query.get_or_404(receiver_id)
        if request.method == 'POST':
            subject = request.form.get('subject', '').strip()
            content = request.form.get('content', '').strip()
            if not subject or not content:
                return "<script>alert('제목과 내용을 입력하세요.'); history.back();</script>"
            msg = Message(
                sender_id=session['user_id'],
                sender_name=session['username'],
                sender_role=session.get('role', 'user'),
                receiver_id=receiver.id,
                subject=subject,
                content=content
            )
            db.session.add(msg)
            db.session.commit()
            return redirect(url_for('user_profile', user_id=receiver.id))
        return render_template('send_message.html', receiver=receiver)

    @app.route('/message/read/<int:msg_id>', methods=['GET', 'POST'])
    def read_message(msg_id):
        if not session.get('username'):
            return redirect(url_for('login', next=request.path))
        msg = Message.query.get_or_404(msg_id)
        if msg.receiver_id != session['user_id'] and session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        msg.is_read = True
        db.session.commit()
        if request.method == 'POST':
            return jsonify({'status':'success'})
        return redirect(url_for('message_inbox'))

    def is_mobile(user_agent):
        """모바일 기기 판별"""
        mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'phone']
        ua = user_agent.lower()
        return any(kw in ua for kw in mobile_keywords)

    def ai_classify_village_report(title, description, image_path=None, town=None, village=None):
        """AI로 제보 분류 및 리단위 특정"""
        try:
            from services.ai_service import call_ai_judge
            location_info = f"GPS: ({town or '없음'}, {village or '없음'})" if not (town or village) else f"주소: {town} {village}"
            prompt = f"""양평군 마을 제보를 분석해주세요.
제목: {title}
내용: {description}
사용자 위치: {location_info}

다음을 JSON으로 반환:
{{
  "category": "도로/환경/안전/시설/기타 중 하나",
  "summary": "3줄 요약",
  "confidence": 0.0~1.0,
  "village_guess": "예상 리 이름 (주소/GPS 기반 추정)"
}}"""
            result = call_ai_judge("", prompt)
            import json
            data = json.loads(result.get('response', '{}'))
            return data
        except:
            return {"category": "기타", "summary": "AI 분류 대기 중", "confidence": 0.5, "village_guess": ""}

    def ai_classify_share_report(title, description, latitude, longitude, image_path=None, drawing_path=None):
        """AI로 공유 내용 분류 및 지역 뉴스 검색"""
        try:
            from services.ai_service import call_ai_judge
            location_info = f"위도: {latitude}, 경도: {longitude}" if latitude and longitude else "위치 미제공"
            prompt = f"""양평군 공유 내용을 분석해주세요.
제목: {title or '제목 없음'}
내용: {description or '내용 없음'}
위치: {location_info}
이미지: {'있음' if image_path else '없음'}
그리기: {'있음' if drawing_path else '없음'}

다음을 JSON으로 반환:
{{
  "category": "사건/풍경/장소/맛집/기타 중 하나",
  "summary": "3줄 요약",
  "confidence": 0.0~1.0,
  "region_news": "해당 위치(반경 5km) 관련 뉴스 요약 (없으면 '관련 뉴스 없음')",
  "news_links": "[{{\"title\": \"기사제목\", \"url\": \"링크\"}}] 형태 JSON 문자열",
  "danger_alert": true/false (위험/긴급 상황 판단 시 true)
}}"""
            result = call_ai_judge("", prompt)
            import json
            data = json.loads(result.get('response', '{}'))
            return data
        except:
            return {"category": "기타", "summary": "AI 분류 대기 중", "confidence": 0.5, "region_news": "관련 뉴스 없음", "news_links": "[]", "danger_alert": False}

    # --- [공유하기 시스템] ---
    @app.route('/share-report', methods=['GET', 'POST'])
    def share_report():
        user = User.query.get(session.get('user_id')) if session.get('username') else None
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            latitude = request.form.get('latitude', type=float)
            longitude = request.form.get('longitude', type=float)
            
            if not latitude or not longitude:
                return jsonify({"status": "error", "msg": "위치 수집이 필요합니다. 새로고침 후 위치 허용해주세요."}), 400
            
            image_path = None
            for field in ['image', 'camera_image']:
                if field in request.files:
                    file = request.files[field]
                    if file and file.filename:
                        img_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'share_reports')
                        if not os.path.exists(img_dir): os.makedirs(img_dir)
                        fname = f"share_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                        file.save(os.path.join(img_dir, fname))
                        image_path = f"/static/uploads/share_reports/{fname}"
                        break
            
            drawing_path = None
            drawing = request.form.get('drawing_data')
            if drawing and len(drawing) > 2000:
                data = base64.b64decode(drawing.split(",")[1])
                fname = f"draw_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                target_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'share_reports')
                if not os.path.exists(target_dir): os.makedirs(target_dir)
                with open(os.path.join(target_dir, fname), "wb") as f: f.write(data)
                drawing_path = f"/static/uploads/share_reports/{fname}"
            
            video_path = None
            if 'video' in request.files:
                file = request.files['video']
                if file and file.filename and '.' in file.filename:
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    if ext in ('mp4', 'avi', 'mov', 'mkv', 'webm'):
                        img_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'share_reports')
                        fname = f"video_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                        file.save(os.path.join(img_dir, fname))
                        video_path = f"/static/uploads/share_reports/{fname}"
            
            from services.geocode import gps_to_town_village
            resolved_town, resolved_village = gps_to_town_village(latitude, longitude)
            share_town = resolved_town or (user.town if user else '')
            share_village = resolved_village or (user.village if user else '')
            share_address = f"경기도 양평군 {share_town} {share_village}".strip()

            report = ShareReport(
                user_id=user.id if user else 0,
                author_name=user.username if user else '익명',
                title=title or '공유',
                description=description,
                image_path=image_path,
                drawing_path=drawing_path,
                video_path=video_path,
                latitude=latitude,
                longitude=longitude,
                town=share_town,
                village=share_village,
                address=share_address,
                ai_category='분석중',
                ai_summary='',
                ai_confidence=0.5,
                ai_region_news='',
                ai_news_links='[]',
                ai_danger_alert=False
            )
            if video_path:
                report.status = 'pending_review'
                report.moderation_result = 'video'
                report.moderation_reason = '동영상은 승인 후 공개됩니다'
            else:
                report.status = 'approved'
                _resolve_canonical_store_name(report)
                # 실시간 이미지 검사
                if image_path:
                    try:
                        from services.ai_service import moderate_image
                        abs_path = os.path.join(current_app.root_path, image_path.lstrip('/'))
                        flagged, reason, cat = moderate_image(abs_path)
                        if flagged:
                            report.status = 'pending_person' if cat == 'person' else 'flagged'
                            report.moderation_result = cat
                            report.moderation_reason = reason
                    except:
                        pass
            db.session.add(report)
            db.session.commit()

            app_obj = current_app._get_current_object()
            uid = user.id if user else 0
            threading.Thread(target=background_process_share,
                args=(app_obj, report.id, title, description, latitude, longitude, image_path, drawing_path, uid)).start()

            return jsonify({"status": "success", "msg": "공유가 접수되었습니다.", "report_id": report.id})
        return render_template('share_report.html', user=user)

    @app.route('/admin/share-reports')
    def admin_share_reports():
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        reports = ShareReport.query.order_by(ShareReport.created_at.desc()).all()
        
        # 위험 알림 별도 표시
        danger_reports = [r for r in reports if r.ai_danger_alert]
        
        return render_template('admin_share_reports.html', 
            reports=reports, 
            danger_reports=danger_reports)

    @app.route('/admin/ramp-applications')
    def admin_ramp_applications():
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        apps = RampApplication.query.order_by(RampApplication.created_at.desc()).all()
        return render_template('admin_ramp_applications.html', apps=apps)

    @app.route('/admin/message/send', methods=['GET', 'POST'])
    def admin_message_send():
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        if request.method == 'POST':
            send_type = request.form.get('send_type', 'all')
            subject = request.form.get('subject', '').strip()
            content = request.form.get('content', '').strip()
            if not content:
                return jsonify({'status':'error', 'msg':'내용을 입력하세요.'})
            recipients = []
            if send_type == 'all':
                recipients = User.query.filter(User.role.notin_(['admin', 'leader'])).all()
            elif send_type == 'individual':
                receiver_id = request.form.get('receiver_id', type=int)
                if receiver_id:
                    user = User.query.get(receiver_id)
                    if user:
                        recipients = [user]
            elif send_type == 'town':
                town = request.form.get('town', '')
                if town:
                    recipients = User.query.filter(
                        db.or_(User.reg_town == town, User.curr_town == town),
                        User.role.notin_(['admin', 'leader'])
                    ).all()
            elif send_type == 'village':
                town = request.form.get('town', '')
                village = request.form.get('village', '')
                if town and village:
                    recipients = User.query.filter(
                        db.or_(
                            db.and_(User.reg_town == town, User.reg_village == village),
                            db.and_(User.curr_town == town, User.curr_village == village)
                        ),
                        User.role.notin_(['admin', 'leader'])
                    ).all()
            elif send_type == 'group':
                group_id = request.form.get('group_id', type=int)
                if group_id:
                    members = Friend.query.filter_by(group_id=group_id, status='accepted').all()
                    recipient_ids = set()
                    for m in members:
                        if m.user_id != session['user_id']:
                            recipient_ids.add(m.user_id)
                        if m.friend_id != session['user_id']:
                            recipient_ids.add(m.friend_id)
                    recipients = User.query.filter(User.id.in_(recipient_ids)).all()
            if not recipients:
                return jsonify({'status':'error', 'msg':'발송 대상을 찾을 수 없습니다.'})
            sender = User.query.get(session['user_id'])
            total_cost = len(recipients) * 10
            if sender.points < total_cost:
                return jsonify({'status':'error', 'msg':f'닢이 부족합니다. (필요: {total_cost}닢, 보유: {sender.points}닢)'})
            sender.points -= total_cost
            ph = PointHistory(user_id=sender.id, change_type='message', amount=-total_cost, balance_after=sender.points, description=f'관리자 대량 쪽지 발송 ({len(recipients)}명)')
            db.session.add(ph)
            for user in recipients:
                msg = Message(
                    sender_id=sender.id,
                    sender_name=sender.username,
                    sender_role=sender.role or 'admin',
                    receiver_id=user.id,
                    subject=subject or '(제목 없음)',
                    content=content
                )
                db.session.add(msg)
            db.session.commit()
            return jsonify({'status':'success', 'msg':f'{len(recipients)}명에게 쪽지를 발송했습니다. ({total_cost}닢 차감)'})
        towns = list(YANGPYEONG_BOUNDS.keys())
        villages = YANGPYEONG_VILLAGES
        groups = FriendGroup.query.filter_by(user_id=session['user_id']).all()
        users = User.query.order_by(User.real_name, User.username).all()
        return render_template('admin_message.html', towns=towns, villages=villages, groups=groups, users=users)

    @app.route('/leader/share-reports')
    def leader_share_reports():
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        user = User.query.get(session['user_id'])
        reports = ShareReport.query.filter_by(town=user.town, village=user.village).order_by(ShareReport.created_at.desc()).all()
        return render_template('leader_share_reports.html', reports=reports, town=user.town, village=user.village)

    # --- [공개] 공유 페이지 ---
    @app.route('/share')
    def share():
        """공개 공유 페이지 - 사건/풍경/장소 모두 표시"""
        town = request.args.get('town', '')
        village = request.args.get('village', '')
        category = request.args.get('category', '')
        role = session.get('role', '')
        uid = session.get('user_id')
        
        if uid:
            query = ShareReport.query.filter(
                db.or_(ShareReport.status == 'approved', ShareReport.user_id == uid)
            )
        else:
            query = ShareReport.query.filter_by(status='approved')
        if town:
            query = query.filter_by(town=town)
        if village:
            query = query.filter_by(village=village)
        if category:
            query = query.filter_by(ai_category=category)
        
        reports = query.order_by(ShareReport.created_at.desc()).limit(50).all()
        
        towns = db.session.query(ShareReport.town).filter_by(status='approved').distinct().all()
        towns = [t[0] for t in towns if t[0]]
        
        villages = []
        if town:
            villages = db.session.query(ShareReport.village).filter_by(status='approved', town=town).distinct().all()
            villages = [v[0] for v in villages if v[0]]
        
        categories = ['사건', '풍경', '장소', '맛집', '기타']
        
        return render_template('share.html', 
            reports=reports, 
            towns=towns, 
            villages=villages,
            categories=categories,
            selected_town=town,
            selected_village=village,
            selected_category=category
        )

    @app.route('/share/map')
    def share_map():
        category = request.args.get('category', '')
        role = session.get('role', '')
        if role in ('admin', 'leader'):
            query = ShareReport.query
        else:
            query = ShareReport.query.filter_by(status='approved')
        if category:
            query = query.filter_by(ai_category=category)
        reports = query.order_by(ShareReport.created_at.desc()).all()
        import json
        reports_json = []
        for r in reports:
            reports_json.append({
                "id": r.id,
                "title": r.title or "",
                "category": r.ai_category or "",
                "town": r.town or "", "village": r.village or "",
                "lat": r.latitude, "lon": r.longitude,
                "image": r.image_path or r.drawing_path or "",
                "summary": (r.ai_summary or r.description or "")[:80]
            })
        categories = ['사건', '풍경', '장소', '맛집', '기타']
        return render_template('share_map.html',
            reports=reports,
            reports_json=json.dumps(reports_json, ensure_ascii=False),
            categories=categories,
            selected_category=category
        )

    @app.route('/share/nearby')
    def share_nearby():
        """내 주변 공유 (JSON)"""
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        max_km = request.args.get('max_km', 20, type=int)
        if not lat or not lon:
            return jsonify({"status": "error", "msg": "위치가 필요합니다."}), 400
        reports = ShareReport.query.filter_by(status='approved').all()
        nearby = get_nearby_reports(reports, lat, lon, max_count=12, max_km=max_km)
        items = []
        for r, dist in nearby:
            items.append({
                "id": r.id,
                "title": r.title or "제목 없음",
                "category": r.ai_category,
                "town": r.town, "village": r.village,
                "lat": r.latitude, "lon": r.longitude,
                "image": r.image_path or r.drawing_path or "",
                "summary": (r.ai_summary or r.description or "")[:100],
                "distance": dist,
                "like_count": r.like_count,
                "dislike_count": r.dislike_count
            })
        return jsonify({"status": "success", "items": items})

    @app.route('/share-report/toggle/<int:report_id>/<string:action>', methods=['GET', 'POST'])
    def share_report_toggle(report_id, action):
        if session.get('role') not in ['admin', 'leader']:
            return jsonify({"status":"error","msg":"권한 없음"}), 403
        report = ShareReport.query.get_or_404(report_id)
        if action == 'approve':
            report.status = 'approved'
            _resolve_canonical_store_name(report)
            report.updated_at = datetime.now()
        elif action == 'reject':
            report.status = 'rejected'
            report.updated_at = datetime.now()
            # AI 학습: rejected 이미지는 AI가 다시 참고하도록 기록
            report.moderation_reason = (report.moderation_reason or '') + ' | 관리자 반려'
        db.session.commit()
        if request.method == 'POST':
            return jsonify({"status":"success","action":action})
        return redirect(request.referrer or url_for('admin_share_reports'))

    @app.route('/share-report/like/<int:report_id>', methods=['POST'])
    def share_report_like(report_id):
        if not session.get('username'):
            return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
        report = ShareReport.query.get_or_404(report_id)
        if report.status != 'approved':
            return jsonify({"status": "error", "msg": "승인된 공유만 평가 가능합니다."}), 403
        report.like_count += 1
        db.session.commit()
        return jsonify({"status": "success", "likes": report.like_count, "dislikes": report.dislike_count})

    @app.route('/share-report/dislike/<int:report_id>', methods=['POST'])
    def share_report_dislike(report_id):
        if not session.get('username'):
            return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
        report = ShareReport.query.get_or_404(report_id)
        if report.status != 'approved':
            return jsonify({"status": "error", "msg": "승인된 공유만 평가 가능합니다."}), 403
        report.dislike_count += 1
        db.session.commit()
        return jsonify({"status": "success", "likes": report.like_count, "dislikes": report.dislike_count})

    @app.route('/share-report/delete/<int:report_id>', methods=['POST'])
    def share_report_delete(report_id):
        if not session.get('username'):
            return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
        report = ShareReport.query.get_or_404(report_id)
        # 공유자 본인만 삭제 가능
        if report.user_id != session.get('user_id') and session.get('role') not in ['admin', 'leader']:
            return jsonify({"status": "error", "msg": "자신의 공유만 삭제할 수 있습니다."}), 403
        db.session.delete(report)
        db.session.commit()
        return jsonify({"status": "success", "msg": "공유가 삭제되었습니다."})

    @app.route('/share-report/accept-person/<int:report_id>')
    def share_accept_person(report_id):
        uid = session.get('user_id')
        if not uid:
            return "<script>alert('로그인이 필요합니다.'); location.href='/login';</script>"
        report = ShareReport.query.get_or_404(report_id)
        if report.user_id != uid:
            return "<script>alert('본인의 공유만 동의할 수 있습니다.'); location.href='/main';</script>"
        if report.status != 'pending_person':
            return "<script>alert('현재 상태에서 동의할 수 없습니다.'); location.href='/main';</script>"
        report.moderation_result = 'person_accepted'
        report.status = 'approved'
        _resolve_canonical_store_name(report)
        report.moderation_reason = (report.moderation_reason or '') + ' | 회원 책임 동의함'
        db.session.commit()
        return "<script>alert('✅ 책임 동의가 완료되었습니다. 공유글이 게시되었습니다.'); location.href='/share/detail/"+str(report_id)+"';</script>"

    @app.route('/share-report/mosaic/<int:report_id>', methods=['POST'])
    def share_mosaic(report_id):
        uid = session.get('user_id')
        if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
        report = ShareReport.query.get_or_404(report_id)
        role = session.get('role', '')
        if report.user_id != uid and role not in ('admin', 'leader'):
            return jsonify({'status':'error','msg':'권한 없음'}), 403
        from services.ai_service import mosaic_image_faces
        img_path = None
        for attr in ['image_path', 'drawing_path']:
            p = getattr(report, attr, None)
            if p:
                abs_p = os.path.join(current_app.root_path, '..', p.lstrip('/')).replace('/', os.sep)
                if os.path.exists(abs_p):
                    img_path = abs_p
                    break
        if not img_path:
            return jsonify({'status':'error','msg':'모자이크 처리할 이미지가 없습니다.'})
        result = mosaic_image_faces(img_path)
        if result is None:
            return jsonify({'status':'error','msg':'얼굴을 감지할 수 없거나 처리에 실패했습니다.'})
        rel = os.path.relpath(result, os.path.join(current_app.root_path, '..')).replace(os.sep, '/')
        report.image_path = '/' + rel
        report.moderation_result = 'mosaic_applied'
        report.moderation_reason = (report.moderation_reason or '') + ' | AI 모자이크 처리됨'
        report.status = 'pending'
        db.session.commit()
        return jsonify({'status':'success','msg':'AI 모자이크 처리 완료, 재검토 대기 중입니다.'})

    # --- [공유 댓글] ---
    @app.route('/share/detail/<int:report_id>')
    def share_detail(report_id):
        report = ShareReport.query.get_or_404(report_id)
        role = session.get('role', '')
        uid = session.get('user_id')
        if report.status != 'approved' and role not in ('admin', 'leader') and report.user_id != uid:
            return "승인된 공유만 볼 수 있습니다.", 403
        comments = ShareComment.query.filter_by(share_id=report_id, parent_id=None).order_by(ShareComment.created_at.asc()).all()
        # 위치 기반 가까운 공유 (정렬: 내글→같은리→같은면→같은군)
        nearby_shares = []
        if report.latitude and report.longitude and report.town:
            from services.geocode import haversine
            all_approved = ShareReport.query.filter(
                ShareReport.status == 'approved',
                ShareReport.id != report_id,
                ShareReport.latitude.isnot(None),
                ShareReport.longitude.isnot(None),
                ShareReport.town.isnot(None)
            ).all()
            scored = []
            cat_order = {'사건': 0, '풍경': 1, '맛집': 2, '장소': 3, '기타': 4}
            for s in all_approved:
                try:
                    d = haversine(report.latitude, report.longitude, s.latitude, s.longitude)
                    if d > 20:
                        continue
                    same_village = s.town == report.town and s.village and s.village == report.village
                    same_town = s.town == report.town
                    me_first = (s.user_id == uid)
                    if me_first:
                        priority = 0
                    elif same_village:
                        priority = 1
                    elif same_town:
                        priority = 2
                    else:
                        priority = 3
                    cat_pri = cat_order.get(s.ai_category, 4)
                    scored.append((priority, cat_pri, d, s))
                except:
                    pass
            scored.sort(key=lambda x: (x[0], x[1], x[2]))
            nearby_shares = [(s, round(d, 1)) for p, cp, d, s in scored[:10]]
        # 지역 소식 (외부 사이트 스크래핑)
        local_news = []
        local_links = []
        try:
            from services.local_sources import get_local_news, get_quick_links
            local_news = get_local_news(town=report.town, village=report.village)
            local_links = get_quick_links(town=report.town, village=report.village)
        except:
            pass
        # 주변 건축/공사 정보
        nearby_construction = []
        if report.latitude and report.longitude:
            from services.geocode import haversine
            notices = ConstructionNotice.query.filter_by(is_active=True).all()
            for n in notices:
                if n.latitude and n.longitude:
                    if haversine(report.latitude, report.longitude, n.latitude, n.longitude) < 10:
                        nearby_construction.append(n)
        return render_template('share_detail.html', report=report, comments=comments, nearby_shares=nearby_shares, local_news=local_news, local_links=local_links, nearby_construction=nearby_construction)

    @app.route('/share/comment/<int:report_id>', methods=['POST'])
    def share_add_comment(report_id):
        if not session.get('username'):
            return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
        content = request.form.get('content', '').strip()
        parent_id = request.form.get('parent_id', type=int)
        if not content:
            return jsonify({"status": "error", "msg": "내용을 입력하세요."}), 400
        report = ShareReport.query.get_or_404(report_id)
        if report.status != 'approved':
            return jsonify({"status": "error", "msg": "승인된 공유만 댓글을 달 수 있습니다."}), 403
        user = User.query.get(session['user_id'])
        comment = ShareComment(
            share_id=report_id,
            user_id=user.id,
            author=user.username,
            content=content,
            parent_id=parent_id
        )
        db.session.add(comment)
        db.session.commit()
        return jsonify({"status": "success", "msg": "댓글이 등록되었습니다."})

    @app.route('/share/comment/delete/<int:comment_id>', methods=['POST'])
    def share_delete_comment(comment_id):
        if not session.get('username'):
            return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
        comment = ShareComment.query.get_or_404(comment_id)
        if comment.user_id != session.get('user_id') and session.get('role') not in ['admin', 'leader']:
            return jsonify({"status": "error", "msg": "삭제 권한이 없습니다."}), 403
        ShareComment.query.filter_by(parent_id=comment_id).delete()
        db.session.delete(comment)
        db.session.commit()
        return jsonify({"status": "success", "msg": "삭제되었습니다."})

    # --- [외부링크 중계] ---
    @app.route('/go')
    def go():
        url = request.args.get('url', '')
        title = request.args.get('title', '외부페이지')
        if not url:
            return "URL이 필요합니다.", 400
        from urllib.parse import quote
        back = request.args.get('back', request.headers.get('Referer', '/construction'))
        return render_template('go.html', url=url, title=title, back=back)

    # --- [소식 번역] ---
    @app.route('/api/news/translate')
    def news_translate():
        url = request.args.get('url','')
        title = request.args.get('title','')
        if not url:
            return "<p>URL이 필요합니다.</p>"
        try:
            import requests as req
            r = req.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
            text = r.text[:3000]
            key = current_app.config.get('GROQ_API_KEY','')
            if key:
                prompt = f"다음 웹페이지 내용을 한국어로 5문장 이내로 요약 번역하세요.\n\n제목: {title}\n내용: {text}"
                rr = req.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                    json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":prompt}],"max_tokens":500},
                    timeout=20)
                if rr.status_code == 200:
                    result = rr.json()["choices"][0]["message"]["content"]
                    return f"<div style='padding:20px;font-size:0.9rem;line-height:1.8;'><h5>🌐 번역 요약</h5><a href='{url}' target='_blank' style='font-size:0.8rem;'>원문보기</a><hr>{result.replace(chr(10),'<br>')}</div>"
            return f"<p>번역을 불러올 수 없습니다. <a href='{url}' target='_blank'>원문보기</a></p>"
        except Exception as e:
            return f"<p>오류: {str(e)[:100]}</p>"
    @app.route('/construction')
    @app.route('/construction')
    def construction():
        notices = ConstructionNotice.query.filter_by(is_active=True).order_by(ConstructionNotice.created_at.desc()).all()
        alerts = VillageAlert.query.filter_by(is_active=True).order_by(VillageAlert.created_at.desc()).limit(20).all()
        from config import Config
        dg_key = getattr(Config, 'DATA_GO_KR_API_KEY', '')
        gg_key = getattr(Config, 'GG_TRAFFIC_API_KEY', '')
        return render_template('construction.html', notices=notices, alerts=alerts, api_key_configured=bool(dg_key), traffic_key_configured=bool(gg_key))

    @app.route('/construction/heritage')
    def construction_heritage():
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        if not lat or not lng:
            return jsonify([])
        from services.local_sources import get_nearby_heritage
        from services.transit import haversine_km
        items = get_nearby_heritage(lat, lng, max_km=5)
        uid = session.get('user_id')
        home_lat = home_lng = None
        home_label = ''
        stamped_names = set()
        if uid:
            user = User.query.get(uid)
            if user and user.curr_town and user.curr_village:
                from services.transit import lookup_village_coords
                hc = lookup_village_coords(user.curr_town, user.curr_village)
                if hc:
                    home_lat, home_lng = hc
            stamps = HeritageStamp.query.filter_by(user_id=uid).all()
            stamped_names = {s.heritage_name for s in stamps}
        for h in items:
            h['stamped'] = h['name'] in stamped_names
            if home_lat and home_lng:
                d_home = round(haversine_km(h['lat'], h['lng'], home_lat, home_lng), 1)
                h['dist_from_home'] = d_home
                h['near_home'] = d_home <= 5
            else:
                h['near_home'] = False
        return jsonify(items)

    @app.route('/construction/heritage/stamp', methods=['POST'])
    def heritage_stamp():
        uid = session.get('user_id')
        if not uid:
            return jsonify({"error": "로그인이 필요합니다."}), 401
        data = request.get_json()
        name = data.get('name', '').strip()
        lat = data.get('lat', type=float)
        lng = data.get('lng', type=float)
        gps_lat = data.get('gps_lat', type=float)
        gps_lng = data.get('gps_lng', type=float)
        if not name or not lat or not lng:
            return jsonify({"success": False, "error": "정보가 부족합니다."})
        from services.transit import haversine_km
        if gps_lat and gps_lng:
            dist = haversine_km(gps_lat, gps_lng, lat, lng)
            if dist > 0.2:
                return jsonify({"success": False, "error": f"현장에서만 찍을 수 있어요! 약 {round(dist*1000)}m 떨어져 있습니다. 가까이 가서 다시 시도해 주세요.", "distance_m": round(dist*1000)})
        existing = HeritageStamp.query.filter_by(user_id=uid, heritage_name=name).first()
        if existing:
            return jsonify({"success": False, "error": "이미 방문 완료한 국가유산입니다."})
        stamp = HeritageStamp(user_id=uid, heritage_name=name, heritage_lat=lat, heritage_lng=lng)
        db.session.add(stamp)
        db.session.commit()
        return jsonify({"success": True, "message": "⭐ 스탬프가 찍혔습니다!"})

    @app.route('/construction/transit')
    def construction_transit():
        from_lat = request.args.get('from_lat', type=float)
        from_lng = request.args.get('from_lng', type=float)
        if not from_lat or not from_lng:
            return jsonify({"error": "출발 위치가 필요합니다."}), 400
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "로그인이 필요합니다."}), 401
        from models import User
        user = User.query.get(user_id)
        if not user or (not user.village and not user.curr_village):
            return jsonify({"error": "등록된 주소가 없습니다. 마이페이지에서 설정해 주세요."}), 400
        home_town = user.town or user.curr_town or ''
        home_village = user.village or user.curr_village or ''
        # 보정된 위치가 있으면 그걸 집 주소로
        if user.curr_address and user.curr_latitude and user.curr_longitude:
            to_address = user.curr_address
            dest = {"lat": user.curr_latitude, "lng": user.curr_longitude, "address": to_address}
        else:
            to_address = f"경기 양평군 {home_town} {home_village}".strip()
            dest = None
        from config import Config
        kakao_key = Config.KAKAO_REST_API_KEY
        naver_id = Config.NAVER_SEARCH_CLIENT_ID or Config.NAVER_CLIENT_ID
        naver_secret = Config.NAVER_SEARCH_CLIENT_SECRET or Config.NAVER_CLIENT_SECRET
        dep = None
        dest = None
        from services.transit import reverse_geocode, geocode_address, estimate_transit_time_rough, haversine_km, lookup_village_coords
        dep = reverse_geocode(from_lat, from_lng, kakao_key, naver_id, naver_secret)
        if not dest:
            dest = geocode_address(to_address, kakao_key, naver_id, naver_secret)
        if not dest or not dest.get("lat"):
            lc = lookup_village_coords(user.curr_town, user.curr_village)
            if lc:
                dest = {"lat": lc[0], "lng": lc[1], "address": to_address}
        result = {
            "departure": dep or {"lat": from_lat, "lng": from_lng, "address": f"{from_lat:.5f}, {from_lng:.5f}"},
            "destination": dest or {"lat": 0, "lng": 0, "address": to_address},
            "distance_km": 0,
        }
        if dest and dest["lat"]:
            from services.transit import haversine_km
            result["distance_km"] = round(haversine_km(from_lat, from_lng, dest["lat"], dest["lng"]), 1)
        if not result.get("transit_routes"):
            from services.transit import estimate_transit_time_rough
            rough_min = estimate_transit_time_rough(from_lat, from_lng, (dest or {}).get("lat") or from_lat, (dest or {}).get("lng") or from_lng)
            result["rough_estimate_min"] = rough_min
        # 대중교통 막차 정보 (추정)
        if dest and dest.get("lat"):
            from services.transit import estimate_last_transit
            last_info = estimate_last_transit(from_lat, from_lng, dest["lat"], dest["lng"])
            if last_info:
                result["last_transit"] = [last_info]
        if dest and dest.get("lng"):
            dep_addr = quote(dep["address"] if dep else f"{from_lat},{from_lng}")
            dest_addr = quote(dest["address"])
            result["deep_links"] = {
                "kakao": f"https://map.kakao.com/?sX={from_lng}&sY={from_lat}&sName={dep_addr}&eX={dest['lng']}&eY={dest['lat']}&eName={dest_addr}",
                "naver": f"https://map.naver.com/index.nhn?slat={from_lat}&slng={from_lng}&stitle={dep_addr}&elat={dest['lat']}&elng={dest['lng']}&etitle={dest_addr}&pathType=1"
            }
        else:
            dep_addr = quote(dep["address"] if dep else f"{from_lat},{from_lng}")
            dest_addr = quote(to_address)
            result["deep_links"] = {
                "kakao": f"https://map.kakao.com/?sName={dep_addr}&eName={dest_addr}",
                "naver": f"https://map.naver.com/index.nhn?stitle={dep_addr}&etitle={dest_addr}&pathType=1"
            }
        return jsonify(result)

    @app.route('/construction/transit/suggest')
    def construction_transit_suggest():
        from_lat = request.args.get('from_lat', type=float)
        from_lng = request.args.get('from_lng', type=float)
        if not from_lat or not from_lng:
            return jsonify({"error": "출발 위치가 필요합니다."}), 400
        uid = session.get('user_id')
        if not uid:
            return jsonify({"error": "로그인이 필요합니다."}), 401
        from models import User
        user = User.query.get(uid)
        if not user or (not user.village and not user.curr_village):
            return jsonify({"error": "등록된 주소가 없습니다."}), 400
        home_town = user.town or user.curr_town or ''
        home_village = user.village or user.curr_village or ''
        # 보정 오프셋 적용: 학습된 GPS 오차 보정
        corrected_lat = from_lat + (user.curr_offset_lat or 0)
        corrected_lng = from_lng + (user.curr_offset_lng or 0)
        from services.transit import suggest_optimal_departure, lookup_village_coords, haversine_km
        from services.geocode import gps_to_town_village
        gps_result = gps_to_town_village(corrected_lat, corrected_lng)
        gps_town = gps_result[0] if gps_result else ""
        gps_village = gps_result[1] if gps_result else ""
        same_village = bool(gps_town and gps_town == home_town and gps_village == home_village)
        # 집 판정: 보정좌표와 등록좌표 거리 1km 이내면 집
        user_home_lat = user.curr_latitude or user.latitude or 0
        user_home_lng = user.curr_longitude or user.longitude or 0
        is_home = False
        if user_home_lat and user_home_lng:
            d = haversine_km(corrected_lat, corrected_lng, user_home_lat, user_home_lng)
            is_home = d <= 0.2
        if not is_home:
            same_village = bool(gps_town and gps_town == home_town and gps_village == home_village)
            is_home = same_village
        if is_home:
            home_addr = user.curr_address or f"{home_town} {home_village}"
            return jsonify({
                "already_home": True,
                "message": f"🏠 집입니다! 현재 위치가 {home_addr} 근처입니다.",
                "home_address": home_addr,
            })
        suggestion = suggest_optimal_departure(from_lat, from_lng, home_town, home_village)
        if not suggestion:
            return jsonify({"error": "경로를 찾을 수 없습니다."}), 404
        # 보정된 위치가 있으면 그걸로 집 좌표+주소 사용
        if user.curr_latitude and user.curr_longitude:
            home_coords = {"lat": user.curr_latitude, "lng": user.curr_longitude}
        else:
            home_coords = lookup_village_coords(home_town, home_village)
            if home_coords:
                home_coords = {"lat": home_coords[0], "lng": home_coords[1]}
        if home_coords:
            suggestion["home_coords"] = home_coords
            suggestion["home_distance_km"] = round(haversine_km(
                suggestion["station_coords"]["lat"], suggestion["station_coords"]["lng"],
                home_coords["lat"], home_coords["lng"]
            ), 1)
        suggestion["home_town"] = user.curr_town
        suggestion["home_village"] = user.curr_village
        suggestion["home_address"] = user.curr_address or user.address or ''
        suggestion["already_home"] = False
        suggestion["corrected"] = bool(user.curr_offset_lat or user.curr_offset_lng)
        suggestion["corrected_lat"] = corrected_lat
        suggestion["corrected_lng"] = corrected_lng
        from urllib.parse import quote
        sc = suggestion["station_coords"]
        sname = quote(suggestion["transfer_station"])
        suggestion["deep_links"] = {
            "kakao": f"https://map.kakao.com/?sX={from_lng}&sY={from_lat}&eX={sc['lng']}&eY={sc['lat']}&eName={sname}",
            "naver": f"https://map.naver.com/index.nhn?slat={from_lat}&slng={from_lng}&elat={sc['lat']}&elng={sc['lng']}&etitle={sname}&pathType=1"
        }
        return jsonify(suggestion)

    @app.route('/construction/traffic/gg')
    def construction_traffic_gg():
        import json
        # 캐시 우선 조회
        cache = VillageCache.query.filter_by(data_type='traffic').order_by(VillageCache.updated_at.desc()).first()
        if cache and cache.updated_at and (datetime.now() - cache.updated_at).seconds < 600:
            data = json.loads(cache.data_json or '[]')
            return jsonify({"available":True,"yangpyeong":cache.data_count,"incidents":data,"cached":True})
        from services.utic_traffic import traffic_summary as utic_summary
        return jsonify(utic_summary())

    def _resolve_canonical_store_name(report):
        """네이버 역지오코딩으로 건물명 조회 (Smartplace 대체), 실패시 카카오"""
        if not report.latitude or not report.longitude:
            return
        try:
            import requests
            best_name = None
            best_source = None
            smartplace = None

            # 1) 네이버 Reverse Geocoding: 좌표 → 건물명
            ncp_id = current_app.config.get('NAVER_SEARCH_CLIENT_ID','')
            ncp_secret = current_app.config.get('NAVER_SEARCH_CLIENT_SECRET','')
            if ncp_id and ncp_secret:
                resp = requests.get('https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc', params={
                    'coords': f'{report.longitude},{report.latitude}',
                    'orders': 'roadaddr',
                    'output': 'json'
                }, headers={
                    'x-ncp-apigw-api-key-id': ncp_id,
                    'x-ncp-apigw-api-key': ncp_secret,
                }, timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    for r in data.get('results', []):
                        if r.get('name') == 'roadaddr':
                            land = r.get('land', {})
                            bldg = next((a.get('value','') for a in [land.get('addition0',{}), land.get('addition1',{}), land.get('addition2',{}), land.get('addition3',{}), land.get('addition4',{})] if a.get('type') == 'building'), '')
                            if bldg:
                                best_name = bldg
                                best_source = 'naver'
                            # 네이버 지도 링크 생성
                            smartplace = f'https://map.naver.com/p?c={report.longitude},{report.latitude},16,0,0,0,dh'
                            break

            # 2) 카카오 키워드 검색 (fallback)
            if not best_name:
                kakao_key = current_app.config.get('KAKAO_REST_API_KEY','')
                if kakao_key:
                    resp = requests.get('https://dapi.kakao.com/v2/local/search/keyword.json', params={
                        'query': (report.title or '').strip()[:30],
                        'x': str(report.longitude),
                        'y': str(report.latitude),
                        'radius': 1000,
                        'size': 1
                    }, headers={'Authorization': f'KakaoAK {kakao_key}'}, timeout=3)
                    if resp.status_code == 200:
                        docs = resp.json().get('documents', [])
                        if docs:
                            from services.transit import haversine_km
                            p = docs[0]
                            d = haversine_km(report.latitude, report.longitude, float(p.get('y',0)), float(p.get('x',0)))
                            if d <= 1.0:
                                best_name = p.get('place_name','')
                                best_source = 'kakao'
                                smartplace = p.get('place_url','') or f'https://map.naver.com/p?c={report.longitude},{report.latitude},16,0,0,0,dh'

            if best_name:
                report.canonical_name = best_name
                report.canonical_source = best_source
            if smartplace:
                report.smartplace_url = smartplace
        except:
            pass

    def _normalize_store_name(title):
        """이름 정규화: 공백+특수문자 제거, 앞20자"""
        import re
        return re.sub(r'[\s\-_.,·]+', '', (title or '제목없음'))[:20]

    @app.route('/construction/local-stores')
    def construction_local_stores():
        uid = session.get('user_id')
        if not uid:
            return jsonify({"error": "로그인이 필요합니다."}), 401
        user = User.query.get(uid)
        if not user or (not user.town and not user.curr_town):
            return jsonify({"error": "등록된 주소가 없습니다."}), 400
        town = user.town or user.curr_town
        village = user.village or user.curr_village
        stores = ShareReport.query.filter_by(
            town=town, village=village, status='approved'
        ).order_by(ShareReport.created_at.desc()).limit(50).all()
        # 그룹화: 100m 이내 같은 위치 → 하나의 가게
        from services.transit import haversine_km
        grouped = {}
        for s in stores:
            slat = s.latitude or 0
            slng = s.longitude or 0
            matched_key = None
            for gk, gv in grouped.items():
                if slat and slng and gv["lat"] and gv["lng"]:
                    d = haversine_km(float(gv["lat"]), float(gv["lng"]), slat, slng)
                    if d <= 0.1:
                        matched_key = gk
                        break
            if matched_key:
                g = grouped[matched_key]
                g["posts"].append({
                    "id": s.id, "title": s.title, "desc": (s.description or "")[:100],
                    "user": s.author_name or "익명", "image": s.image_path,
                    "date": s.created_at.strftime("%m/%d") if s.created_at else ""
                })
                if s.image_path and not g["image"]:
                    g["image"] = s.image_path
            else:
                key = f"{round(slat,4)}|{round(slng,4)}"
                grouped[key] = {
                    "name": s.title or "제목없음",
                    "posts": [{
                        "id": s.id, "title": s.title, "desc": (s.description or "")[:100],
                        "user": s.author_name or "익명", "image": s.image_path,
                        "date": s.created_at.strftime("%m/%d") if s.created_at else ""
                    }],
                    "image": s.image_path,
                    "lat": s.latitude, "lng": s.longitude,
                }
        # StoreInfo 매칭: 각 그룹 좌표와 가장 가까운 StoreInfo(100m 이내) 찾기
        store_infos = StoreInfo.query.filter_by(town=town, village=village).all()
        for gk, gv in grouped.items():
            for si in store_infos:
                if si.latitude and si.longitude and gv["lat"] and gv["lng"]:
                    d = haversine_km(si.latitude, si.longitude, float(gv["lat"]), float(gv["lng"]))
                    if d <= 0.1:
                        gv["name"] = si.name
                        gv["store_link"] = si.our_link or si.store_homepage or si.smartplace or None
                        gv["link_label"] = "🏠 가게소개" if si.our_link else ("🌐 홈페이지" if si.store_homepage else ("📍 스마트플레이스" if si.smartplace else None))
                        break
        result = {
            "town": town, "village": village,
            "stores": list(grouped.values())[:20],
        }
        return jsonify(result)

    @app.route('/construction/store/<string:store_name>')
    def construction_store_detail(store_name):
        uid = session.get('user_id')
        user = User.query.get(uid) if uid else None
        town = request.args.get('town','')
        village = request.args.get('village','')
        target_lat = request.args.get('lat','0')
        target_lng = request.args.get('lng','0')
        stores = ShareReport.query.filter_by(
            town=town, village=village, status='approved'
        ).order_by(ShareReport.created_at.desc()).all()
        from services.transit import haversine_km
        target_lat_f = float(target_lat)
        target_lng_f = float(target_lng)
        grouped = []
        for s in stores:
            if s.latitude and s.longitude and target_lat_f and target_lng_f:
                d = haversine_km(target_lat_f, target_lng_f, s.latitude, s.longitude)
                if d <= 0.1:
                    grouped.append(s)
        if not grouped:
            from urllib.parse import unquote
            name = _normalize_store_name(unquote(store_name))
            grouped = [s for s in stores if _normalize_store_name(s.canonical_name or s.title) == name]
        if not grouped:
            return "가게를 찾을 수 없습니다.", 404

        # StoreInfo 매칭
        store_link = None
        link_label = None
        display_name = store_name
        if target_lat_f and target_lng_f:
            sis = StoreInfo.query.filter_by(town=town, village=village).all()
            for si in sis:
                if si.latitude and si.longitude:
                    if haversine_km(si.latitude, si.longitude, target_lat_f, target_lng_f) <= 0.1:
                        display_name = si.name
                        store_link = si.our_link or si.store_homepage or si.smartplace or None
                        link_label = "🏠 가게소개" if si.our_link else ("🌐 홈페이지" if si.store_homepage else ("📍 스마트플레이스" if si.smartplace else None))
                        break

        naver_map = f'https://map.naver.com/p?c={target_lng},{target_lat},16,0,0,0,dh' if target_lat_f and target_lng_f else None
        return render_template('store_detail.html', store_name=display_name, posts=grouped, town=town, village=village, store_link=store_link, link_label=link_label, naver_map=naver_map)

    @app.route('/construction/local-scenery')
    def construction_local_scenery():
        uid = session.get('user_id')
        if not uid:
            return jsonify({"error": "로그인이 필요합니다."}), 401
        user = User.query.get(uid)
        if not user or not user.curr_town or not user.curr_village:
            return jsonify({"error": "등록된 주소(리)가 없습니다."}), 400
        now = datetime.now()
        cur_month = now.month
        season_months = {1,2,12} if cur_month in (1,2,12) else {3,4,5} if cur_month in (3,4,5) else {6,7,8} if cur_month in (6,7,8) else {9,10,11}
        season_name = '겨울' if cur_month in (1,2,12) else '봄' if cur_month in (3,4,5) else '여름' if cur_month in (6,7,8) else '가을'
        all_approved = ShareReport.query.filter_by(
            town=user.curr_town,
            village=user.curr_village,
            status='approved'
        ).order_by(ShareReport.created_at.desc()).all()
        scenery = []
        for s in all_approved:
            if not s.image_path:
                continue
            if s.created_at and s.created_at.month in season_months and s.id:
                # 같은 게시물이 scenery와 stores에 모두 나오는 것 방지: 
                # ai_category가 'store'/'가게'면 건너뛰기
                cat = (s.ai_category or '').lower()
                if cat in ('store','가게','상점','마트','음식점','식당','카페'):
                    continue
                scenery.append(s)
        return jsonify({
            "town": user.curr_town,
            "village": user.curr_village,
            "season": season_name,
            "sceneries": [{
                "id": s.id,
                "title": s.title or "제목없음",
                "image_path": s.image_path,
                "description": (s.description or "")[:100],
                "created_at": s.created_at.strftime("%Y-%m-%d") if s.created_at else "",
            } for s in scenery[:30]],
        })

    # ---- 동네가게 관리 (Admin) ----
    @app.route('/admin/stores')
    def admin_stores():
        if session.get('role') not in ('admin','leader'):
            return "권한 없음", 403
        stores = StoreInfo.query.order_by(StoreInfo.town, StoreInfo.name).all()
        return render_template('admin_stores.html', stores=stores)

    @app.route('/admin/stores/new', methods=['GET','POST'])
    def admin_stores_new():
        if session.get('role') not in ('admin','leader'):
            return "권한 없음", 403
        if request.method == 'POST':
            s = StoreInfo(
                name=request.form.get('name','').strip(),
                latitude=float(request.form.get('latitude',0) or 0),
                longitude=float(request.form.get('longitude',0) or 0),
                town=request.form.get('town','').strip(),
                village=request.form.get('village','').strip(),
                our_link=request.form.get('our_link','').strip(),
                store_homepage=request.form.get('store_homepage','').strip(),
                smartplace=request.form.get('smartplace','').strip(),
            )
            db.session.add(s)
            db.session.commit()
            return redirect('/admin/stores')
        return render_template('admin_store_edit.html', store=None)

    @app.route('/admin/stores/edit/<int:store_id>', methods=['GET','POST'])
    def admin_stores_edit(store_id):
        if session.get('role') not in ('admin','leader'):
            return "권한 없음", 403
        s = StoreInfo.query.get_or_404(store_id)
        if request.method == 'POST':
            s.name = request.form.get('name','').strip()
            s.latitude = float(request.form.get('latitude',0) or 0)
            s.longitude = float(request.form.get('longitude',0) or 0)
            s.town = request.form.get('town','').strip()
            s.village = request.form.get('village','').strip()
            s.our_link = request.form.get('our_link','').strip()
            s.store_homepage = request.form.get('store_homepage','').strip()
            s.smartplace = request.form.get('smartplace','').strip()
            db.session.commit()
            return redirect('/admin/stores')
        return render_template('admin_store_edit.html', store=s)

    @app.route('/admin/stores/delete/<int:store_id>', methods=['POST'])
    def admin_stores_delete(store_id):
        if session.get('role') not in ('admin','leader'):
            return jsonify({"status":"error"}), 403
        s = StoreInfo.query.get_or_404(store_id)
        db.session.delete(s)
        db.session.commit()
        return jsonify({"status":"success"})

    @app.route('/admin/alerts')
    def admin_alerts():
        if session.get('role') not in ('admin', 'leader', 'village_leader'):
            return "권한 없음", 403
        role = session.get('role')
        user_town = session.get('town', '')
        user_village = session.get('village', '')
        if role == 'admin':
            alerts = VillageAlert.query.order_by(VillageAlert.created_at.desc()).all()
        elif role == 'leader':
            alerts = VillageAlert.query.filter_by(town=user_town).order_by(VillageAlert.created_at.desc()).all()
        else:
            alerts = VillageAlert.query.filter_by(town=user_town, village=user_village).order_by(VillageAlert.created_at.desc()).all()
        return render_template('admin_alerts.html', alerts=alerts, role=role, town=user_town, village=user_village)

    @app.route('/admin/alerts/new', methods=['GET', 'POST'])
    def admin_alerts_new():
        if session.get('role') not in ('admin', 'leader', 'village_leader'):
            return "권한 없음", 403
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            alert_type = request.form.get('alert_type', 'general')
            urgency = request.form.get('urgency', 'normal')
            town = request.form.get('town', '').strip()
            village = request.form.get('village', '').strip()
            if not title:
                return "<script>alert('제목을 입력하세요.'); history.back();</script>"
            alert = VillageAlert(
                title=title, content=content, alert_type=alert_type, urgency=urgency,
                town=town, village=village,
                author_id=session.get('user_id'),
                author_name=session.get('username', '')
            )
            db.session.add(alert)
            db.session.flush()
            # 마을주민 자동 쪽지
            if town:
                recipients = User.query.filter(User.village_notify != False, User.town == town)
                if village:
                    recipients = recipients.filter(User.village == village)
                for r in recipients.all():
                    db.session.add(Message(sender_id=session.get('user_id'), sender_name=session.get('username','관리자'),
                        receiver_id=r.id, subject=f'🚨 마을소식: {title}',
                        content=f'[{town} {village}] {title}\n\n{content}\n\n자세한 내용은 위치기반안내 > 알림에서 확인하세요.',
                        sender_role=session.get('role','admin')))
            db.session.commit()
            return redirect('/admin/alerts')
        user_town = session.get('town', '')
        user_village = session.get('village', '')
        towns = db.session.query(VillageAlert.town).distinct().all() if session.get('role') == 'admin' else [(user_town,)]
        return render_template('admin_alerts_new.html', town=user_town, village=user_village, role=session.get('role'), towns=[t[0] for t in towns if t[0]])

    @app.route('/admin/alerts/edit/<int:alert_id>', methods=['GET', 'POST'])
    def admin_alerts_edit(alert_id):
        if session.get('role') not in ('admin', 'leader', 'village_leader'):
            return "권한 없음", 403
        alert = VillageAlert.query.get_or_404(alert_id)
        if request.method == 'POST':
            alert.title = request.form.get('title', '').strip()
            alert.content = request.form.get('content', '').strip()
            alert.alert_type = request.form.get('alert_type', 'general')
            alert.urgency = request.form.get('urgency', 'normal')
            alert.is_active = request.form.get('is_active') == '1'
            if session.get('role') == 'admin':
                alert.town = request.form.get('town', '').strip()
                alert.village = request.form.get('village', '').strip()
            alert.updated_at = datetime.now()
            db.session.commit()
            return redirect('/admin/alerts')
        return render_template('admin_alerts_edit.html', alert=alert, role=session.get('role'))

    @app.route('/admin/alerts/delete/<int:alert_id>', methods=['POST'])
    def admin_alerts_delete(alert_id):
        if session.get('role') not in ('admin', 'leader', 'village_leader'):
            return "권한 없음", 403
        alert = VillageAlert.query.get_or_404(alert_id)
        db.session.delete(alert)
        db.session.commit()
        return redirect('/admin/alerts')

    @app.route('/api/user/unread')
    def api_user_unread():
        uid = session.get('user_id')
        if not uid: return jsonify({"count": 0})
        count = Message.query.filter_by(receiver_id=uid, is_read=False).count()
        return jsonify({"count": count})

    @app.route('/api/construction/unread')
    def api_construction_unread():
        uid = session.get('user_id')
        user = User.query.get(uid) if uid else None
        alerts = 0
        if user and user.town:
            alerts = VillageAlert.query.filter_by(is_active=True, town=user.town).count()
        return jsonify({"alerts": alerts, "heritage": 0, "scenery": 0})

    @app.route('/construction/safetydata')
    def construction_safetydata():
        from services.safetydata import get_yangpyeong_safety, TYPE_NAMES
        data = get_yangpyeong_safety()
        total = sum(len(v) for v in data.values())
        return jsonify({"available": True, "total": total, "types": {k: {"name": TYPE_NAMES.get(k,k), "items": v[:10]} for k, v in data.items() if v}}) 

    @app.route('/api/user/location', methods=['GET','POST'])
    def api_user_location():
        if request.method == 'POST':
            uid = session.get('user_id')
            if not uid: return jsonify({"status":"error","msg":"login"})
            user = User.query.get(uid)
            loc = request.get_json().get('manual_loc','')
            if not loc: return jsonify({"status":"error","msg":"need location"})
            parts = loc.strip().split()
            if len(parts) >= 2:
                user.curr_town = parts[0]
                user.curr_village = parts[1]
                user.location_updated_at = datetime.now()
                db.session.commit()
                return jsonify({"status":"success","msg":"ok"})
            return jsonify({"status":"error","msg":"format"})
        uid = session.get('user_id')
        if not uid:
            return jsonify({"error": "login"}), 401
        from models import User
        user = User.query.get(uid)
        if not user:
            return jsonify({"error": "not_found"}), 404
        return jsonify({"town": user.curr_town or "", "village": user.curr_village or "", "address": user.curr_address or ""})

    @app.route('/construction/refresh')
    def construction_refresh():
        if session.get('role') not in ('admin', 'leader'):
            return "권한 없음", 403
        from flask import current_app
        from config import Config
        dg_key = getattr(Config, 'DATA_GO_KR_API_KEY', '')
        gg_key = getattr(Config, 'GG_TRAFFIC_API_KEY', '')
        if not dg_key and not gg_key:
            return "<script>alert('API 키가 설정되지 않았습니다. config.py를 확인하세요.'); history.back();</script>"
        import threading
        if dg_key:
            threading.Thread(target=sync_construction_notices, args=(current_app._get_current_object(), dg_key)).start()
        if gg_key:
            threading.Thread(target=sync_traffic_incidents, args=(current_app._get_current_object(), gg_key)).start()
            threading.Thread(target=sync_congestion_info, args=(current_app._get_current_object(), gg_key)).start()
        return "<script>alert('정보 갱신이 시작되었습니다.'); location.href='/construction';</script>"

    # --- [상시 서비스 3종] ---
    @app.route('/service/ramp')
    def service_ramp():
        _cleanup_expired_posts()
        uid = session.get('user_id')
        role = session.get('role')
        raw_posts = Post.query.filter(
            Post.title.contains('경사로') | Post.content.contains('경사로') | Post.content.contains('휠체어') | Post.title.contains('휠체어')
        ).order_by(Post.created_at.desc()).all()
        ramp_posts = [p for p in raw_posts if not (p.total_score <= -50 and p.user_id != uid and role not in ('admin', 'leader'))]
        waiting_count = RampApplication.query.filter_by(status='pending').count()
        # static/videos/ramp/ 폴더의 동영상 파일 목록
        ramp_videos = []
        video_dir = os.path.join(current_app.root_path, 'static', 'videos', 'ramp')
        if os.path.exists(video_dir):
            for f in sorted(os.listdir(video_dir), reverse=True):
                if f.lower().endswith(('.mp4', '.webm', '.mov', '.avi', '.mkv')):
                    ramp_videos.append(f"/static/videos/ramp/{f}")
        return render_template('service_ramp.html', ramp_posts=ramp_posts, waiting_count=waiting_count, ramp_videos=ramp_videos)

    @app.route('/service/ramp/apply', methods=['POST'])
    def service_ramp_apply():
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        location = request.form['location']
        step_height = request.form['step_height']
        ownership = request.form['ownership']
        agree_removal = request.form.get('agree_removal') == 'on'
        agree_damage = request.form.get('agree_damage') == 'on'
        from datetime import datetime

        photo_path = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                from werkzeug.utils import secure_filename
                fname = f"ramp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                target_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'ramp')
                if not os.path.exists(target_dir): os.makedirs(target_dir)
                file.save(os.path.join(target_dir, fname))
                photo_path = f"/static/uploads/ramp/{fname}"

        appt = RampApplication(
            name=name, email=email, phone=phone, location=location,
            photo_path=photo_path, step_height=step_height,
            ownership=ownership, agree_removal=agree_removal,
            agree_damage=agree_damage, signed_at=datetime.now(),
            status='pending'
        )
        db.session.add(appt)
        db.session.commit()
        EmailService.send(email, "[양평마을] 경사로 설치 신청이 접수되었습니다",
            f"{name}님, 경사로 설치 신청이 접수되었습니다.\n\n접수 번호: {appt.id}번\n위치: {location}\n\n검토 후 연락드리겠습니다.\n\nhttps://test.unocum.kr")
        return "<script>alert('신청이 접수되었습니다. 검토 후 연락드립니다. (대기자 순번: " + str(appt.id) + "번)'); location.href='/service/ramp';</script>"

    @app.route('/service/ramp/volunteer', methods=['POST'])
    def service_ramp_volunteer():
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        admin_email = current_app.config.get('MAIL_FROM', 'yp@unocum.kr')
        EmailService.send(admin_email, "[양평마을] 경사로 봉사 신청 알림",
            f"경사로 봉사 신청이 접수되었습니다.\n\n이름: {name}\n이메일: {email}\n연락처: {phone}")
        return "<script>alert('봉사 신청이 접수되었습니다. 될 수 있는 한 회원가입 후 신청해 주시면 감사하겠습니다. (unocumyp@gmail.com)'); location.href='/service/ramp';</script>"

    @app.route('/service/legal')
    def service_legal(): return render_template('service_legal.html')

    @app.route('/service/psycho')
    def service_psycho(): return render_template('service_psycho.html')

    # --- [법률상담 게시판] ---
    @app.route('/legal/list')
    def legal_list():
        posts = LegalPost.query.order_by(LegalPost.created_at.desc()).all()
        return render_template('legal_board.html', posts=posts)

    @app.route('/legal/write', methods=['GET', 'POST'])
    def legal_write():
        if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']
            password = generate_password_hash(request.form['password'])
            email = request.form['email']
            author_name = request.form.get('author_name', '익명') or '익명'
            post = LegalPost(title=title, content=content, password=password, email=email, author_name=author_name)
            db.session.add(post)
            db.session.commit()
            return "<script>alert('상담 글이 등록되었습니다. 답변은 이메일로 알려드립니다.'); location.href='/legal/list';</script>"
        return render_template('legal_write.html')

    @app.route('/legal/post/<int:post_id>', methods=['GET', 'POST'])
    def legal_post(post_id):
        post = LegalPost.query.get_or_404(post_id)
        if request.method == 'POST':
            if check_password_hash(post.password, request.form['password']):
                return render_template('legal_post.html', post=post, need_password=False, error=False)
            return render_template('legal_post.html', post=post, need_password=True, error=True)
        return render_template('legal_post.html', post=post, need_password=True, error=False)

    @app.route('/legal/admin')
    def legal_admin():
        if session.get('role') not in ('admin', 'leader'):
            return "<script>alert('관리자 전용입니다.'); location.href='/service/legal';</script>"
        pending_posts = LegalPost.query.filter_by(answer=None).order_by(LegalPost.created_at.desc()).all()
        answered_posts = LegalPost.query.filter(LegalPost.answer.isnot(None)).order_by(LegalPost.answered_at.desc()).all()
        pending_appts = LegalAppointment.query.filter_by(status='pending').order_by(LegalAppointment.created_at.desc()).all()
        approved_appts = LegalAppointment.query.filter_by(status='approved').order_by(LegalAppointment.date.desc()).all()
        schedule_rows = LawyerSchedule.query.all()
        schedules = {str(s.day_of_week): {'is_available': s.is_available, 'start_hour': s.start_hour, 'end_hour': s.end_hour, 'slot_hours': s.slot_hours} for s in schedule_rows}
        gc = GoogleCalendarConfig.query.first()
        return render_template('legal_admin.html', pending_posts=pending_posts, answered_posts=answered_posts, pending_appointments=pending_appts, approved_appointments=approved_appts, schedules=schedules, gc=gc)

    @app.route('/legal/admin/answer/<int:post_id>', methods=['POST'])
    def legal_admin_answer(post_id):
        if session.get('role') not in ('admin', 'leader'):
            return "<script>alert('권한 없음'); history.back();</script>"
        post = LegalPost.query.get_or_404(post_id)
        post.answer = request.form['answer']
        post.answered_at = datetime.now()
        post.is_public = True
        post.fee = int(request.form.get('fee')) if request.form.get('fee') else None
        post.travel_allowance = int(request.form.get('travel_allowance')) if request.form.get('travel_allowance') else None
        db.session.commit()
        EmailService.send(post.email, f"[양평마을] 법률상담 답변이 등록되었습니다",
            f"문의하신 '{post.title}'에 대한 답변이 등록되었습니다.\n\nhttps://test.unocum.kr/legal/post/{post.id}")
        return "<script>alert('답변이 등록되었습니다.'); location.href='/legal/admin';</script>"

    @app.route('/legal/admin/appointment/<int:appt_id>/approve', methods=['POST'])
    def legal_appointment_approve(appt_id):
        if session.get('role') not in ('admin', 'leader'):
            return "<script>alert('권한 없음'); history.back();</script>"
        appt = LegalAppointment.query.get_or_404(appt_id)
        appt.status = 'approved'
        appt.approved_at = datetime.now()
        appt.approved_by = session.get('user_id')
        appt.fee = int(request.form.get('fee')) if request.form.get('fee') else None
        appt.travel_allowance = int(request.form.get('travel_allowance')) if request.form.get('travel_allowance') else None
        db.session.commit()
        EmailService.send(appt.email, "[양평마을] 법률상담 예약이 승인되었습니다",
            f"법률상담 예약이 승인되었습니다.\n\n일시: {appt.date} {appt.time_slot}\n\nhttps://test.unocum.kr/legal/schedule")
        return "<script>alert('예약이 승인되었습니다.'); location.href='/legal/admin';</script>"

    @app.route('/legal/admin/appointment/<int:appt_id>/reject', methods=['POST'])
    def legal_appointment_reject(appt_id):
        if session.get('role') not in ('admin', 'leader'):
            return "<script>alert('권한 없음'); history.back();</script>"
        appt = LegalAppointment.query.get_or_404(appt_id)
        appt.status = 'rejected'
        db.session.commit()
        return "<script>alert('예약이 거절되었습니다.'); location.href='/legal/admin';</script>"

    @app.route('/legal/admin/schedule', methods=['POST'])
    def legal_admin_schedule():
        if session.get('role') not in ('admin', 'leader'):
            return "<script>alert('권한 없음'); history.back();</script>"
        for day_id in range(7):
            key = f'day_{day_id}'
            if key in request.form:
                start_hour = int(request.form.get(f'start_{day_id}', 10))
                end_hour = int(request.form.get(f'end_{day_id}', 16))
                schedule = LawyerSchedule.query.filter_by(day_of_week=day_id).first()
                if schedule:
                    schedule.is_available = True
                    schedule.start_hour = start_hour
                    schedule.end_hour = end_hour
                else:
                    schedule = LawyerSchedule(day_of_week=day_id, is_available=True, start_hour=start_hour, end_hour=end_hour)
                    db.session.add(schedule)
            else:
                schedule = LawyerSchedule.query.filter_by(day_of_week=day_id).first()
                if schedule:
                    schedule.is_available = False
        db.session.commit()
        return "<script>alert('상담시간이 저장되었습니다.'); location.href='/legal/admin';</script>"

    @app.route('/legal/admin/google-calendar', methods=['POST'])
    def legal_admin_google_calendar():
        if session.get('role') not in ('admin', 'leader'):
            return "<script>alert('권한 없음'); history.back();</script>"
        gc = GoogleCalendarConfig.query.first()
        if not gc:
            gc = GoogleCalendarConfig()
            db.session.add(gc)
        if 'service_account_json' in request.files:
            file = request.files['service_account_json']
            if file and file.filename.endswith('.json'):
                gc.service_account_json = file.read().decode('utf-8')
        calendar_id = request.form.get('calendar_id', '').strip()
        if calendar_id:
            gc.calendar_id = calendar_id
        gc.is_connected = bool(gc.service_account_json and gc.calendar_id)
        gc.updated_at = datetime.now()
        db.session.commit()
        msg = '연동 저장 완료' if gc.is_connected else 'JSON 파일과 캘린더 ID를 모두 입력해야 합니다.'
        return f"<script>alert('{msg}'); location.href='/legal/admin';</script>"

    @app.route('/legal/schedule')
    def legal_schedule():
        from datetime import date, timedelta
        schedule_rows = LawyerSchedule.query.filter_by(is_available=True).all()
        available_day_ids = {s.day_of_week for s in schedule_rows}
        time_slots_by_day = {}
        for s in schedule_rows:
            slots = []
            for h in range(s.start_hour, s.end_hour, s.slot_hours):
                slots.append(f"{h:02d}:00-{h+s.slot_hours:02d}:00")
            time_slots_by_day[s.day_of_week] = slots

        # 앞으로 60일 중 예약 가능일 계산
        booked = db.session.query(LegalAppointment.date).filter(LegalAppointment.status.in_(['pending', 'approved'])).distinct().all()
        booked_dates = {b[0] for b in booked}
        available_dates = []
        today = date.today()
        for i in range(60):
            d = today + timedelta(days=i)
            if d.weekday() in available_day_ids and d not in booked_dates:
                available_dates.append(d.isoformat())

        all_slots = []
        for s in schedule_rows:
            for h in range(s.start_hour, s.end_hour, s.slot_hours):
                all_slots.append(f"{h:02d}:00-{h+s.slot_hours:02d}:00")

        return render_template('legal_schedule.html', available_dates=available_dates, time_slots=all_slots)

    @app.route('/legal/appointment/book', methods=['POST'])
    def legal_appointment_book():
        name = request.form['name']
        email = request.form['email']
        phone = request.form.get('phone', '')
        date_str = request.form['date']
        time_slot = request.form['time_slot']
        location_parts = [request.form.get('location', ''), request.form.get('location_detail', '')]
        location = ' '.join(p for p in location_parts if p)
        content = request.form.get('content', '')
        from datetime import date
        appt = LegalAppointment(
            user_id=session.get('user_id'),
            name=name, email=email, phone=phone,
            date=date.fromisoformat(date_str),
            time_slot=time_slot, location=location, content=content
        )
        db.session.add(appt)
        db.session.commit()
        return "<script>alert('예약이 신청되었습니다. 승인 후 이메일로 안내드립니다.'); location.href='/service/legal';</script>"

    # --- [심리상담소] ---
    @app.route('/psycho/list')
    def psycho_list():
        posts = PsychoPost.query.order_by(PsychoPost.created_at.desc()).all()
        return render_template('psycho_board.html', posts=posts)

    @app.route('/psycho/write', methods=['GET', 'POST'])
    def psycho_write():
        if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']
            password = generate_password_hash(request.form['password'])
            email = request.form['email']
            author_name = request.form.get('author_name', '익명') or '익명'
            post = PsychoPost(title=title, content=content, password=password, email=email, author_name=author_name)
            db.session.add(post)
            db.session.commit()
            return "<script>alert('상담 글이 등록되었습니다. 답변은 이메일로 알려드립니다.'); location.href='/psycho/list';</script>"
        return render_template('psycho_write.html')

    @app.route('/psycho/post/<int:post_id>', methods=['GET', 'POST'])
    def psycho_post(post_id):
        post = PsychoPost.query.get_or_404(post_id)
        if request.method == 'POST':
            if check_password_hash(post.password, request.form['password']):
                return render_template('psycho_post.html', post=post, need_password=False, error=False)
            return render_template('psycho_post.html', post=post, need_password=True, error=True)
        return render_template('psycho_post.html', post=post, need_password=True, error=False)

    @app.route('/psycho/admin')
    def psycho_admin():
        if session.get('role') not in ('admin', 'leader'):
            return "<script>alert('관리자 전용입니다.'); location.href='/service/psycho';</script>"
        pending_posts = PsychoPost.query.filter_by(answer=None).order_by(PsychoPost.created_at.desc()).all()
        answered_posts = PsychoPost.query.filter(PsychoPost.answer.isnot(None)).order_by(PsychoPost.answered_at.desc()).all()
        pending_appts = PsychoAppointment.query.filter_by(status='pending').order_by(PsychoAppointment.created_at.desc()).all()
        approved_appts = PsychoAppointment.query.filter_by(status='approved').order_by(PsychoAppointment.date.desc()).all()
        schedule_rows = PsychoDoctorSchedule.query.all()
        schedules = {str(s.day_of_week): {'is_available': s.is_available, 'start_hour': s.start_hour, 'end_hour': s.end_hour, 'slot_hours': s.slot_hours} for s in schedule_rows}
        gc = PsychoGoogleCalendarConfig.query.first()
        return render_template('psycho_admin.html', pending_posts=pending_posts, answered_posts=answered_posts, pending_appointments=pending_appts, approved_appointments=approved_appts, schedules=schedules, gc=gc)

    @app.route('/psycho/admin/answer/<int:post_id>', methods=['POST'])
    def psycho_admin_answer(post_id):
        if session.get('role') not in ('admin', 'leader'):
            return "<script>alert('권한 없음'); history.back();</script>"
        post = PsychoPost.query.get_or_404(post_id)
        post.answer = request.form['answer']
        post.answered_at = datetime.now()
        post.is_public = True
        post.fee = int(request.form.get('fee')) if request.form.get('fee') else None
        post.travel_allowance = int(request.form.get('travel_allowance')) if request.form.get('travel_allowance') else None
        db.session.commit()
        EmailService.send(post.email, f"[양평마을] 심리상담 답변이 등록되었습니다",
            f"문의하신 '{post.title}'에 대한 답변이 등록되었습니다.\n\nhttps://test.unocum.kr/psycho/post/{post.id}")
        return "<script>alert('답변이 등록되었습니다.'); location.href='/psycho/admin';</script>"

    @app.route('/psycho/admin/appointment/<int:appt_id>/approve', methods=['POST'])
    def psycho_appointment_approve(appt_id):
        if session.get('role') not in ('admin', 'leader'):
            return "<script>alert('권한 없음'); history.back();</script>"
        appt = PsychoAppointment.query.get_or_404(appt_id)
        appt.status = 'approved'
        appt.approved_at = datetime.now()
        appt.approved_by = session.get('user_id')
        appt.fee = int(request.form.get('fee')) if request.form.get('fee') else None
        appt.travel_allowance = int(request.form.get('travel_allowance')) if request.form.get('travel_allowance') else None
        db.session.commit()
        EmailService.send(appt.email, "[양평마을] 심리상담 예약이 승인되었습니다",
            f"심리상담 예약이 승인되었습니다.\n\n일시: {appt.date} {appt.time_slot}\n\nhttps://test.unocum.kr/psycho/schedule")
        return "<script>alert('예약이 승인되었습니다.'); location.href='/psycho/admin';</script>"

    @app.route('/psycho/admin/appointment/<int:appt_id>/reject', methods=['POST'])
    def psycho_appointment_reject(appt_id):
        if session.get('role') not in ('admin', 'leader'):
            return "<script>alert('권한 없음'); history.back();</script>"
        appt = PsychoAppointment.query.get_or_404(appt_id)
        appt.status = 'rejected'
        db.session.commit()
        return "<script>alert('예약이 거절되었습니다.'); location.href='/psycho/admin';</script>"

    @app.route('/psycho/admin/schedule', methods=['POST'])
    def psycho_admin_schedule():
        if session.get('role') not in ('admin', 'leader'):
            return "<script>alert('권한 없음'); history.back();</script>"
        for day_id in range(7):
            key = f'day_{day_id}'
            if key in request.form:
                start_hour = int(request.form.get(f'start_{day_id}', 10))
                end_hour = int(request.form.get(f'end_{day_id}', 16))
                schedule = PsychoDoctorSchedule.query.filter_by(day_of_week=day_id).first()
                if schedule:
                    schedule.is_available = True
                    schedule.start_hour = start_hour
                    schedule.end_hour = end_hour
                else:
                    schedule = PsychoDoctorSchedule(day_of_week=day_id, is_available=True, start_hour=start_hour, end_hour=end_hour)
                    db.session.add(schedule)
            else:
                schedule = PsychoDoctorSchedule.query.filter_by(day_of_week=day_id).first()
                if schedule:
                    schedule.is_available = False
        db.session.commit()
        return "<script>alert('상담시간이 저장되었습니다.'); location.href='/psycho/admin';</script>"

    @app.route('/psycho/admin/google-calendar', methods=['POST'])
    def psycho_admin_google_calendar():
        if session.get('role') not in ('admin', 'leader'):
            return "<script>alert('권한 없음'); history.back();</script>"
        gc = PsychoGoogleCalendarConfig.query.first()
        if not gc:
            gc = PsychoGoogleCalendarConfig()
            db.session.add(gc)
        if 'service_account_json' in request.files:
            file = request.files['service_account_json']
            if file and file.filename.endswith('.json'):
                gc.service_account_json = file.read().decode('utf-8')
        calendar_id = request.form.get('calendar_id', '').strip()
        if calendar_id:
            gc.calendar_id = calendar_id
        gc.is_connected = bool(gc.service_account_json and gc.calendar_id)
        gc.updated_at = datetime.now()
        db.session.commit()
        msg = '연동 저장 완료' if gc.is_connected else 'JSON 파일과 캘린더 ID를 모두 입력해야 합니다.'
        return f"<script>alert('{msg}'); location.href='/psycho/admin';</script>"

    @app.route('/psycho/schedule')
    def psycho_schedule():
        from datetime import date, timedelta
        schedule_rows = PsychoDoctorSchedule.query.filter_by(is_available=True).all()
        available_day_ids = {s.day_of_week for s in schedule_rows}
        for s in schedule_rows:
            pass
        booked = db.session.query(PsychoAppointment.date).filter(PsychoAppointment.status.in_(['pending', 'approved'])).distinct().all()
        booked_dates = {b[0] for b in booked}
        available_dates = []
        today = date.today()
        for i in range(60):
            d = today + timedelta(days=i)
            if d.weekday() in available_day_ids and d not in booked_dates:
                available_dates.append(d.isoformat())
        all_slots = []
        for s in schedule_rows:
            for h in range(s.start_hour, s.end_hour, s.slot_hours):
                all_slots.append(f"{h:02d}:00-{h+s.slot_hours:02d}:00")
        return render_template('psycho_schedule.html', available_dates=available_dates, time_slots=all_slots)

    @app.route('/psycho/appointment/book', methods=['POST'])
    def psycho_appointment_book():
        name = request.form['name']
        email = request.form['email']
        phone = request.form.get('phone', '')
        date_str = request.form['date']
        time_slot = request.form['time_slot']
        location_parts = [request.form.get('location', ''), request.form.get('location_detail', '')]
        location = ' '.join(p for p in location_parts if p)
        content = request.form.get('content', '')
        from datetime import date
        appt = PsychoAppointment(
            user_id=session.get('user_id'),
            name=name, email=email, phone=phone,
            date=date.fromisoformat(date_str),
            time_slot=time_slot, location=location, content=content
        )
        db.session.add(appt)
        db.session.commit()
        return "<script>alert('예약이 신청되었습니다. 승인 후 이메일로 안내드립니다.'); location.href='/service/psycho';</script>"

    # --- [벗 (친구) 시스템] ---

    @app.context_processor
    def inject_friend_info():
        uid = session.get('user_id')
        if not uid:
            return dict(has_friends=False, friend_count=0)
        friend_ids = [f.receiver_id for f in Friend.query.filter_by(requester_id=uid, status='accepted').all()] + \
                     [f.requester_id for f in Friend.query.filter_by(receiver_id=uid, status='accepted').all()]
        return dict(has_friends=True, friend_count=len(friend_ids))

    @app.route('/friends')
    def friends():
        uid = session.get('user_id')
        if not uid: return redirect(url_for('login', next='/friends'))
        friend_ids = [f.receiver_id for f in Friend.query.filter_by(requester_id=uid, status='accepted').all()] + \
                     [f.requester_id for f in Friend.query.filter_by(receiver_id=uid, status='accepted').all()]
        friend_users = User.query.filter(User.id.in_(friend_ids)).all() if friend_ids else []
        pending_friends = Friend.query.filter_by(receiver_id=uid, status='pending').all()
        pending_users = User.query.filter(User.id.in_([f.requester_id for f in pending_friends])).all() if pending_friends else []
        my_pending = Friend.query.filter_by(requester_id=uid, status='pending').all()
        my_pending_ids = [f.receiver_id for f in my_pending]
        my_pending_users = User.query.filter(User.id.in_(my_pending_ids)).all() if my_pending_ids else []
        groups = FriendGroup.query.filter_by(user_id=uid).all()
        return render_template('friends.html', friend_users=friend_users, pending_users=pending_users,
                               my_pending_ids=my_pending_ids, my_pending_users=my_pending_users, groups=groups)

    @app.route('/friends/list')
    def friends_list_json():
        if not session.get('user_id'):
            return jsonify({"friends": []})
        uid = session['user_id']
        friend_ids = [f.receiver_id for f in Friend.query.filter_by(requester_id=uid, status='accepted').all()] + \
                     [f.requester_id for f in Friend.query.filter_by(receiver_id=uid, status='accepted').all()]
        friends = User.query.filter(User.id.in_(friend_ids)).all() if friend_ids else []
        return jsonify({"friends": [{"id": f.id, "name": f.real_name or f.username, "town": f.town or '', "village": f.village or ''} for f in friends]})

    @app.route('/friends/map')
    def friends_map():
        if not session.get('user_id'): return redirect(url_for('login', next='/friends/map'))
        return render_template('friends_map.html')

    @app.route('/friends/request/<int:other_id>', methods=['POST'])
    def friend_request(other_id):
        uid = session.get('user_id')
        if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
        if uid == other_id: return jsonify({'status':'error','msg':'자기 자신에게 신청 불가'}), 400
        existing = Friend.query.filter(
            ((Friend.requester_id==uid) & (Friend.receiver_id==other_id)) |
            ((Friend.requester_id==other_id) & (Friend.receiver_id==uid))
        ).first()
        if existing:
            return jsonify({'status':'error','msg':'이미 신청했거나 벗 관계입니다'}), 400
        f = Friend(requester_id=uid, receiver_id=other_id)
        db.session.add(f)
        requester = User.query.get(uid)
        receiver = User.query.get(other_id)
        # 로그인 위치 공유 동의 저장
        requester.login_location_share = (request.form.get('share_login_location') == '1')
        msg = Message(
            sender_id=uid,
            sender_name=requester.real_name or requester.username,
            sender_role=requester.role,
            receiver_id=other_id,
            subject='👋 벗 신청',
            content=f'{requester.real_name or requester.username}님이 벗 신청을 보냈습니다. "내 벗 관리" 페이지에서 수락/거절할 수 있습니다.'
        )
        db.session.add(msg)
        db.session.commit()
        return jsonify({'status':'success'})

    @app.route('/friends/accept/<int:other_id>', methods=['POST'])
    def friend_accept(other_id):
        uid = session.get('user_id')
        if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
        f = Friend.query.filter_by(requester_id=other_id, receiver_id=uid, status='pending').first()
        if not f: return jsonify({'status':'error','msg':'요청 없음'}), 404
        f.status = 'accepted'
        accepter = User.query.get(uid)
        msg = Message(
            sender_id=uid,
            sender_name=accepter.real_name or accepter.username,
            sender_role=accepter.role,
            receiver_id=other_id,
            subject='✅ 벗 신청 수락',
            content=f'{accepter.real_name or accepter.username}님이 벗 신청을 수락했습니다. 이제 벗입니다!'
        )
        db.session.add(msg)
        from tongbot_routes import _rebuild_friend_cache
        _rebuild_friend_cache(uid)
        _rebuild_friend_cache(other_id)
        db.session.commit()
        return jsonify({'status':'success'})

    @app.route('/friends/reject/<int:other_id>', methods=['POST'])
    def friend_reject(other_id):
        uid = session.get('user_id')
        if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
        f = Friend.query.filter_by(requester_id=other_id, receiver_id=uid, status='pending').first()
        if not f: return jsonify({'status':'error','msg':'요청 없음'}), 404
        rejecter = User.query.get(uid)
        msg = Message(
            sender_id=uid,
            sender_name=rejecter.real_name or rejecter.username,
            sender_role=rejecter.role,
            receiver_id=other_id,
            subject='❌ 벗 신청 거절',
            content=f'{rejecter.real_name or rejecter.username}님이 벗 신청을 거절했습니다.'
        )
        db.session.add(msg)
        db.session.delete(f)
        db.session.commit()
        return jsonify({'status':'success'})

    @app.route('/friends/remove/<int:other_id>', methods=['POST'])
    def friend_remove(other_id):
        uid = session.get('user_id')
        if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
        if session.get('role') not in ['admin', 'leader']:
            return jsonify({'status':'error','msg':'관리자만 벗 관계를 삭제할 수 있습니다.'}), 403
        f = Friend.query.filter(
            ((Friend.requester_id==uid) & (Friend.receiver_id==other_id) & (Friend.status=='accepted')) |
            ((Friend.requester_id==other_id) & (Friend.receiver_id==uid) & (Friend.status=='accepted'))
        ).first()
        if not f: return jsonify({'status':'error','msg':'벗 관계 없음'}), 404
        db.session.delete(f)
        db.session.commit()
        return jsonify({'status':'success'})

    @app.route('/friends/group/create', methods=['POST'])
    def friend_group_create():
        uid = session.get('user_id')
        if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
        name = request.form.get('name', '').strip()
        if not name: return jsonify({'status':'error','msg':'그룹명 입력 필요'}), 400
        g = FriendGroup(user_id=uid, name=name)
        db.session.add(g)
        db.session.commit()
        return jsonify({'status':'success'})

    @app.route('/friends/group/delete/<int:group_id>', methods=['POST'])
    def friend_group_delete(group_id):
        uid = session.get('user_id')
        if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
        g = FriendGroup.query.filter_by(id=group_id, user_id=uid).first()
        if not g: return jsonify({'status':'error','msg':'그룹 없음'}), 404
        db.session.delete(g)
        db.session.commit()
        return jsonify({'status':'success'})