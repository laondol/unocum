from flask import render_template, request, redirect, url_for, jsonify, session, current_app
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import json, base64, os, threading

from models import db, User, Post, Comment
from services.security import save_village_file
from services.ai_service import call_ai_judge, call_ai_debate, background_ai_judge

# --- [공개 경로] 인트로 및 대시보드 ---
def register_routes(app):
    
    @app.route('/')
    @app.route('/intro')
    def intro():
        return render_template('intro.html')

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
            if p.total_score <= -50:
                if p.user_id == user_id: posts.append(p)
                continue
            if p.is_forced_approved:
                posts.append(p)
                continue
            if p.created_at and p.created_at <= now - timedelta(hours=48):
                posts.append(p)
                continue
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
            town = request.form['town']
            village = request.form['village']
            gps_verified = request.form.get('gps_verified') == 'true'
            
            if User.query.filter_by(username=username).first():
                return "<script>alert('이미 있는 아이디입니다.'); history.back();</script>"

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
            new_user = User(
                username=username, password=hashed_pw,
                real_name=real_name, phone=phone, town=town, village=village,
                is_verified_resident=is_verified, verified_method=verified_method,
                bill_image_path=file_url, points=1000
            )
            db.session.add(new_user)
            db.session.commit()
            return "<script>alert('가입 신청 완료! 로그인을 진행하세요.'); location.href='/login';</script>"
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            u = User.query.filter_by(username=request.form['username']).first()
            if u and check_password_hash(u.password, request.form['password']):
                session.update({'user_id': u.id, 'username': u.username, 'role': u.role})
                return redirect(url_for('index'))
            return "<script>alert('로그인 정보 오류'); history.back();</script>"
        return render_template('login.html')

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
            post.updated_at = datetime.now() # 수정일 리셋 (카운트다운 리스타트)
            post.is_forced_approved = False 
            
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

    # --- [상시 서비스 3종] ---
    @app.route('/service/ramp')
    def service_ramp(): return render_template('service_ramp.html')

    @app.route('/service/legal')
    def service_legal(): return render_template('service_legal.html')

    @app.route('/service/psycho')
    def service_psycho(): return render_template('service_psycho.html')