from flask import render_template, request, redirect, url_for, jsonify, session, current_app
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import json, base64, os, threading, requests

from models import db, User, Post, Comment, NewsArticle, NewsComment, NewsRecommendation, PointHistory, ShareReport, Message
from services.security import save_village_file
from services.ai_service import call_ai_judge, call_ai_debate, background_ai_judge
from services.news_service import ai_search_news, ai_translate_and_format, ai_summarize_url
from services.geocode import haversine, gps_to_town_village, get_nearby_reports, is_in_yangpyeong

# --- [공개 경로] 인트로 및 대시보드 ---
def register_routes(app):
    
    @app.route('/')
    @app.route('/intro')
    def intro():
        selected_news = NewsArticle.query.filter_by(is_selected=True).order_by(NewsArticle.updated_at.desc()).limit(6).all()
        return render_template('intro.html', selected_news=selected_news)

    @app.route('/presentation')
    def presentation():
        return render_template('presentation.html')

    @app.route('/main')
    def index():
        now = datetime.now()
        posts = Post.query.filter(Post.total_score > -50, ((Post.created_at <= now - timedelta(hours=48)) | (Post.is_forced_approved == True))).order_by(Post.created_at.desc()).all()
        return render_template('index.html', posts=posts)

    @app.route('/all-proposals')
    def all_proposals():
        now = datetime.now()
        user_id = session.get('user_id')
        
        all_posts = Post.query.order_by(Post.created_at.desc()).all()
        posts = []
        for p in all_posts:
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
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            real_name = request.form['real_name']
            phone = request.form['phone']
            email = request.form.get('email', '').strip()
            town = request.form['town']
            village = request.form['village']
            reg_latitude = request.form.get('reg_latitude', type=float)
            reg_longitude = request.form.get('reg_longitude', type=float)
            gps_verified = request.form.get('gps_verified') == 'true'
            
            if User.query.filter_by(username=username).first():
                return "<script>alert('이미 있는 아이디입니다.'); history.back();</script>"
            if email and User.query.filter_by(email=email).first():
                return "<script>alert('이미 등록된 이메일입니다.'); history.back();</script>"

            file_url = None
            verified_method = 'none'
            is_verified = False

            if gps_verified:
                verified_method = 'gps'
                is_verified = True

            # 🏡 [보안 패치]: 이웃의 주소지에 맞게 static/uploads/bills/읍면_리/ 폴더 자동 생성 및 저장
            if 'bill_image' in request.files:
                file = request.files['bill_image']
                if file and file.filename != '':
                    file_url = save_village_file(file, app.config['UPLOAD_FOLDER'], town, village)
                    verified_method = 'bill'

            hashed_pw = generate_password_hash(password)
            now = datetime.now()
            new_user = User(
                username=username, password=hashed_pw,
                real_name=real_name, phone=phone, email=email,
                town=town, village=village,
                reg_town=town, reg_village=village,
                reg_latitude=reg_latitude, reg_longitude=reg_longitude,
                curr_latitude=reg_latitude, curr_longitude=reg_longitude,
                curr_town=town, curr_village=village,
                location_updated_at=now,
                is_verified_resident=is_verified, verified_method=verified_method,
                bill_image_path=file_url, points=1000
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
            
            # 이메일 인증 메일 발송 (개발환경에서는 콘솔 출력)
            if email:
                print(f"[이메일 인증] {email} 로 인증 메일 발송 (username: {username})")
            
            return "<script>alert('가입 신청 완료! 로그인을 진행하세요.'); location.href='/login';</script>"
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        next_url = request.args.get('next') or request.form.get('next') or url_for('index')
        if next_url and not next_url.startswith('/'):
            next_url = url_for('index')
        if request.method == 'POST':
            u = User.query.filter_by(username=request.form['username']).first()
            if u and check_password_hash(u.password, request.form['password']):
                session.update({'user_id': u.id, 'username': u.username, 'role': u.role})
                # 30일 주기 포인트 지급 (가입일 기준, 가입 시 1000P만 지급)
                now = datetime.now()
                if u.last_payout:
                    if (now - u.last_payout).days >= 30:
                        add_points(u.id, 1000, 'monthly', '30일 주기 물맑은머니 지급')
                        u.last_payout = now
                        db.session.commit()
                else:
                    u.last_payout = now
                    db.session.commit()
                return redirect(next_url)
            return "<script>alert('로그인 정보 오류'); history.back();</script>"
        return render_template('login.html', next=next_url)

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('intro'))

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
        db.session.commit()

        # 백그라운드 AI 처리 스레드 기동
        threading.Thread(target=background_ai_judge, args=(current_app._get_current_object(), new_post.id)).start()
        return jsonify({"status": "success"})

    @app.route('/post/<int:post_id>')
    def view(post_id):
        post = Post.query.get_or_404(post_id)
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
        return render_template('admin_view.html', post=post)

    @app.route('/admin/update_scores/<int:post_id>', methods=['POST'])
    def update_scores(post_id):
        if session.get('role') not in ['admin', 'leader']: return "권한 부족", 403
        post = Post.query.get_or_404(post_id)
        post.admin_score = int(request.form.get('admin_score', 0))
        post.leader_score = int(request.form.get('leader_score', 0))
        post.is_forced_approved = 'force_approve' in request.form
        post.total_score = post.ai_score + post.admin_score + post.leader_score + post.member_score
        db.session.commit()
        return redirect(url_for('admin_post_view', post_id=post.id))

    @app.route('/admin/debate/<int:post_id>', methods=['POST'])
    def admin_debate(post_id):
        if session.get('role') not in ['admin', 'leader']: return "권한 부족", 403
        post = Post.query.get_or_404(post_id)
        admin_opinion = request.form.get('admin_opinion')
        suggested_score = int(request.form.get('suggested_score', post.ai_score))
        
        res = call_ai_debate(post, admin_opinion, suggested_score)
        logs = json.loads(post.ai_debate_log)
        logs.append({"time": datetime.now().strftime('%H:%M'), "admin": admin_opinion, "ai": res.get('ai_reply', '오류')})
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
            print(f"[{user.real_name}] 이웃 인증 승인 완료. 500포인트 가점.")
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
        if tab == 'world':
            query = query.filter(NewsArticle.category.in_(['세계뉴스', '환경뉴스', '건강정보', '복지정보', '농업정보', '관광소식']))
        elif tab == 'kr_yp':
            query = query.filter(NewsArticle.category.in_(['대한민국뉴스', '양평소식', '정책정보', '지역소식']))
        news_list = query.order_by(NewsArticle.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
        return render_template('admin_news.html', news_list=news_list, tab=tab)

    @app.route('/admin/news/ai-suggest', methods=['POST'])
    def admin_news_ai_suggest():
        if session.get('role') not in ['admin', 'leader']:
            return jsonify({"status": "error", "msg": "권한 없음"}), 403
        suggestions = ai_search_news()
        if not suggestions:
            return jsonify({"status": "error", "msg": "AI 뉴스 생성 실패. Ollama 서버를 확인하세요."})
        count = 0
        for item in suggestions:
            article = NewsArticle(
                title=item.get('title', '제목 없음'),
                summary=item.get('summary', ''),
                content=f"<p><strong>양평군민 관련성:</strong> {item.get('reason', '')}</p><p>{item.get('summary', '')}</p>",
                category=item.get('category', '세계뉴스'),
                source_url=item.get('url', ''),
                is_ai_generated=True,
                created_by=session.get('user_id'),
                source_name='AI 추천'
            )
            db.session.add(article)
            count += 1
        db.session.commit()
        return jsonify({"status": "success", "count": count})

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
                is_selected='is_selected' in request.form,
                created_by=session.get('user_id')
            )
            try:
                ai_res = call_ai_judge(title, request.form.get('content', '')[:500])
                article.ai_score = ai_res.get('score', 0)
            except:
                article.ai_score = 0
            db.session.add(article)
            db.session.commit()
            return redirect(url_for('admin_news'))
        return render_template('admin_news_create.html', article=None)

    @app.route('/admin/news/edit/<int:news_id>', methods=['GET', 'POST'])
    def admin_news_edit(news_id):
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        article = NewsArticle.query.get_or_404(news_id)
        if request.method == 'POST':
            article.title = request.form.get('title', '').strip()
            article.summary = request.form.get('summary', '')
            article.content = request.form.get('content', '')
            article.source_url = request.form.get('source_url', '')
            article.source_name = request.form.get('source_name', '')
            article.category = request.form.get('category', '세계뉴스')
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
            db.session.commit()
            return redirect(url_for('admin_news'))
        return render_template('admin_news_create.html', article=article)

    @app.route('/admin/news/import-url', methods=['POST'])
    def admin_news_import_url():
        if session.get('role') not in ['admin', 'leader']:
            return jsonify({"status": "error", "msg": "권한 없음"}), 403
        url = request.form.get('url', '').strip()
        if not url:
            return jsonify({"status": "error", "msg": "URL을 입력하세요."})
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'utf-8'
            text = resp.text
        except Exception as e:
            return jsonify({"status": "error", "msg": f"페이지를 가져올 수 없습니다: {str(e)}"})
        result = ai_summarize_url(text[:4000])
        if not result:
            result = {"title": "URL에서 가져온 기사", "summary": "AI 요약 실패", "category": "세계뉴스", "is_useful": True}
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(text, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']): tag.decompose()
            body_text = soup.get_text(separator='\n', strip=True)[:3000]
        except:
            body_text = text[:2000]
        article = NewsArticle(
            title=result.get('title', '가져온 기사'),
            summary=result.get('summary', ''),
            content=f"<p>{body_text[:2000].replace(chr(10), '</p><p>')}</p>",
            source_url=url,
            category=result.get('category', '세계뉴스'),
            is_ai_generated=True,
            created_by=session.get('user_id')
        )
        db.session.add(article)
        db.session.commit()
        return jsonify({"status": "success", "news_id": article.id})

    @app.route('/news/like/<int:news_id>', methods=['POST'])
    def news_like(news_id):
        if not session.get('username'):
            return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
        article = NewsArticle.query.get_or_404(news_id)
        article.like_count += 1
        add_points(session['user_id'], 5, 'like', '뉴스 좋아요', news_id)
        db.session.commit()
        return jsonify({"status": "success", "likes": article.like_count, "dislikes": article.dislike_count})

    @app.route('/news/dislike/<int:news_id>', methods=['POST'])
    def news_dislike(news_id):
        if not session.get('username'):
            return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
        article = NewsArticle.query.get_or_404(news_id)
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

    def _get_news_with_recs(news_list):
        """각 뉴스에 승인된 추천링크 로드"""
        for a in news_list.items:
            a.recs = NewsRecommendation.query.filter_by(news_id=a.id, is_approved=True).order_by(NewsRecommendation.created_at.desc()).limit(3).all()
        return news_list

    @app.route('/world-news')
    def world_news():
        page = request.args.get('page', 1, type=int)
        news_list = NewsArticle.query.filter_by(is_selected=True).order_by(NewsArticle.like_count.desc(), NewsArticle.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
        return render_template('world_news.html', news_list=_get_news_with_recs(news_list), title="세계 뉴스")

    @app.route('/yp-news')
    def yp_news():
        page = request.args.get('page', 1, type=int)
        news_list = NewsArticle.query.filter_by(is_selected=True).order_by(NewsArticle.like_count.desc(), NewsArticle.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
        return render_template('yp_news.html', news_list=_get_news_with_recs(news_list), title="양평 소식")

    @app.route('/kr-yp-news')
    def kr_yp_news():
        page = request.args.get('page', 1, type=int)
        news_list = NewsArticle.query.filter(
            NewsArticle.is_selected == True,
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

    # ========== 포인트 시스템 ==========
    def add_points(user_id, amount, change_type, description, related_id=None):
        """포인트 적립/차감 + 내역 기록"""
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

    @app.route('/mypage/points')
    def mypage_points():
        if not session.get('username'):
            return redirect(url_for('login', next=request.path))
        user = User.query.get(session['user_id'])
        history = PointHistory.query.filter_by(user_id=user.id).order_by(PointHistory.created_at.desc()).limit(100).all()
        return render_template('mypage_points.html', user=user, history=history)

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

    def check_paid_transition():
        """유료전환 체크: 총 회원 1만명 초과 시"""
        total_users = User.query.count()
        if total_users > 10000:
            # 무료회원 중 미전환자에게 알림 등 처리 가능
            pass
        return total_users > 10000

    # --- [회원 프로필 & 쪽지] ---
    @app.route('/user/<int:user_id>')
    def user_profile(user_id):
        if not session.get('username'):
            return redirect(url_for('login', next=request.path))
        user = User.query.get_or_404(user_id)
        point_history = PointHistory.query.filter_by(user_id=user.id).order_by(PointHistory.created_at.desc()).limit(50).all()
        
        # 받은 쪽지 (관리자/리더 우선 정렬)
        messages = Message.query.filter_by(receiver_id=user.id).order_by(
            db.case(
                (Message.sender_role == 'admin', 0),
                (Message.sender_role == 'leader', 1),
                else_=2
            ),
            Message.created_at.desc()
        ).all()
        
        return render_template('user_profile.html', 
            profile_user=user, 
            point_history=point_history, 
            messages=messages,
            is_own=(session.get('user_id') == user.id)
        )

    @app.route('/user/location/refresh', methods=['POST'])
    def user_location_refresh():
        if not session.get('username'):
            return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
        user = User.query.get(session['user_id'])
        data = request.get_json() or {}
        lat = data.get('lat', type=float)
        lon = data.get('lon', type=float)
        if not lat or not lon:
            return jsonify({"status": "error", "msg": "GPS 위치가 필요합니다."}), 400
        if not is_in_yangpyeong(lat, lon):
            return jsonify({"status": "error", "msg": "양평군 내에서만 위치 갱신이 가능합니다."}), 400
        town, village = gps_to_town_village(lat, lon)
        user.curr_latitude = lat
        user.curr_longitude = lon
        user.curr_town = town
        user.curr_village = village
        user.location_updated_at = datetime.now()
        db.session.commit()
        return jsonify({
            "status": "success",
            "lat": lat, "lon": lon,
            "town": town or user.town,
            "village": village or user.village
        })

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

    @app.route('/message/read/<int:msg_id>')
    def read_message(msg_id):
        if not session.get('username'):
            return redirect(url_for('login', next=request.path))
        msg = Message.query.get_or_404(msg_id)
        if msg.receiver_id != session['user_id'] and session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        msg.is_read = True
        db.session.commit()
        return redirect(url_for('user_profile', user_id=session['user_id']))

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
        if not session.get('username'):
            return redirect(url_for('login', next=request.path))
        
        user = User.query.get(session['user_id'])
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            latitude = request.form.get('latitude', type=float)
            longitude = request.form.get('longitude', type=float)
            
            # 사진 필수 체크
            if not latitude or not longitude:
                return jsonify({"status": "error", "msg": "위치 수집이 필요합니다. 새로고침 후 위치 허용해주세요."}), 400
            
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    img_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'share_reports')
                    if not os.path.exists(img_dir): os.makedirs(img_dir)
                    fname = f"share_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                    file.save(os.path.join(img_dir, fname))
                    image_path = f"/static/uploads/share_reports/{fname}"
            
            # 그리기 이미지 저장
            drawing_path = None
            drawing = request.form.get('drawing_data')
            if drawing and len(drawing) > 2000:
                data = base64.b64decode(drawing.split(",")[1])
                fname = f"draw_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                target_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'share_reports')
                if not os.path.exists(target_dir): os.makedirs(target_dir)
                with open(os.path.join(target_dir, fname), "wb") as f: f.write(data)
                drawing_path = f"/static/uploads/share_reports/{fname}"
            
            # AI 분류 + 지역 뉴스 검색
            ai_result = ai_classify_share_report(title, description, latitude, longitude, image_path, drawing_path)
            
            report = ShareReport(
                user_id=user.id,
                author_name=user.username,
                title=title or f"{ai_result.get('category', '공유')} - {user.town} {user.village}",
                description=description,
                image_path=image_path,
                drawing_path=drawing_path,
                latitude=latitude,
                longitude=longitude,
                town=user.town,
                village=user.village,
                ai_category=ai_result.get('category', '기타'),
                ai_summary=ai_result.get('summary', ''),
                ai_confidence=ai_result.get('confidence', 0.5),
                ai_region_news=ai_result.get('region_news', ''),
                ai_news_links=ai_result.get('news_links', '[]'),
                ai_danger_alert=ai_result.get('danger_alert', False)
            )
            db.session.add(report)
            add_points(user.id, 50, 'share_report', '공유하기', report.id)
            db.session.commit()
            
            # 위험 알림 시 관리자/리더에게 알림 (나중에 구현)
            if ai_result.get('danger_alert'):
                # TODO: 관리자 알림 발송
                pass
            
            if request.is_json:
                return jsonify({"status": "success", "msg": "공유가 접수되었습니다.", "report_id": report.id})
            return "<script>alert('공유가 접수되었습니다. 관리자 검토 후 게시됩니다.'); location.href='/share';</script>"
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
        
        query = ShareReport.query.filter_by(status='approved')
        if town:
            query = query.filter_by(town=town)
        if village:
            query = query.filter_by(village=village)
        if category:
            query = query.filter_by(ai_category=category)
        
        reports = query.order_by(ShareReport.created_at.desc()).limit(50).all()
        
        # 면/리 목록 조회 (필터용)
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

    @app.route('/share/detail/<int:report_id>')
    def share_detail(report_id):
        report = ShareReport.query.get_or_404(report_id)
        if report.status != 'approved':
            return "승인된 공유만 볼 수 있습니다.", 403
        return render_template('share_detail.html', report=report)

    @app.route('/share/map')
    def share_map():
        category = request.args.get('category', '')
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

    @app.route('/share-report/toggle/<int:report_id>/<string:action>')
    def share_report_toggle(report_id, action):
        if session.get('role') not in ['admin', 'leader']:
            return "권한 없음", 403
        report = ShareReport.query.get_or_404(report_id)
        if action == 'approve':
            report.status = 'approved'
        elif action == 'reject':
            report.status = 'rejected'
        report.updated_at = datetime.now()
        db.session.commit()
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

    # --- [상시 서비스 3종] ---
    @app.route('/service/ramp')
    def service_ramp(): return render_template('service_ramp.html')

    @app.route('/service/legal')
    def service_legal(): return render_template('service_legal.html')

    @app.route('/service/psycho')
    def service_psycho(): return render_template('service_psycho.html')