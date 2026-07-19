from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app
from models import db, User, Post, Comment, PointHistory, AiKnowledge, NewsArticle

admin_bp = Blueprint('admin', __name__)



def add_points(user_id, amount, change_type, description, related_id=None):
    user = User.query.get(user_id)
    if not user: return
    user.points = (user.points or 0) + amount
    h = PointHistory(user_id=user_id, change_type=change_type, amount=amount,
                     balance_after=user.points, description=description, related_id=related_id)
    db.session.add(h)
    return user.points


@admin_bp.route('/admin/postgresql')
def admin_postgresql():
    if session.get('role') != 'leader':
        return "권한 없음", 403
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    tables = []
    for t in sorted(insp.get_table_names()):
        try:
            cnt = db.session.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
        except:
            cnt = 0
        tables.append({'name': t, 'rows': cnt})
    return render_template('admin_postgresql.html', tables=tables)
@admin_bp.route('/admin')
def admin():
    if session.get('role') != 'leader': return "권한 없음", 403
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('admin.html', posts=posts)

@admin_bp.route('/admin/post/<int:post_id>')
def admin_post_view(post_id):
    if session.get('role') != 'leader': return "권한 부족", 403
    post = Post.query.get_or_404(post_id)
    import json as _json
    debate_logs = _json.loads(post.ai_debate_log) if post.ai_debate_log else []
    return render_template('admin_view.html', post=post, debate_logs=debate_logs)

@admin_bp.route('/admin/update_scores/<int:post_id>', methods=['POST'])
def update_scores(post_id):
    if session.get('role') != 'leader': return "권한 부족", 403
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

@admin_bp.route('/admin/debate/<int:post_id>', methods=['POST'])
def admin_debate(post_id):
    if session.get('role') != 'leader': return jsonify({"status": "error", "msg": "권한 부족"}), 403
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
@admin_bp.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if session.get('role') != 'leader':
        return jsonify({"status":"error","msg":"권한 없음"}), 403
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        return jsonify({"status":"error","msg":"관리자는 삭제할 수 없습니다"})
    name = user.email or user.username
    db.session.delete(user)
    db.session.commit()
    return jsonify({"status":"success","msg":f"'{name}' 회원이 삭제되었습니다."})

@admin_bp.route('/admin/users/points/<int:user_id>', methods=['GET','POST'])
def admin_user_points(user_id):
    if session.get('role') != 'leader':
        return jsonify({"status":"error","msg":"최고책임자만 가능합니다"}), 403
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        amount = int(request.form.get('amount', 0))
        reason = request.form.get('reason', '관리자 조정')
        user.points = (user.points or 0) + amount
        db.session.add(PointHistory(user_id=user.id, change_type='admin_adjust', amount=amount,
            balance_after=user.points, description=reason))
        db.session.commit()
        return jsonify({"status":"success","msg":f"{amount}닢 조정 완료"})
    return jsonify({"id":user.id,"email":user.email,"username":user.username,"points":user.points})

@admin_bp.route('/admin/page-managers', methods=['GET','POST'])
def admin_page_managers():
    if session.get('role') != 'leader':
        return "최고책임자만 접근 가능", 403
    if request.method == 'POST':
        uid = request.form.get('user_id', type=int)
        page = request.form.get('page','')
        action = request.form.get('action','toggle')
        user = User.query.get(uid)
        if user:
            pages = (user.managed_pages or '').split(',')
            had_village = 'village' in pages
            # 마을지기 임명은 이웃인증 필수
            if page == 'village' and page not in pages and not user.is_verified_resident:
                return redirect(url_for('admin.admin_page_managers', user_id=uid))
            if action == 'toggle':
                if page in pages:
                    pages.remove(page)
                else:
                    pages.append(page)
                user.managed_pages = ','.join(filter(None, pages))
                if uid == session.get('user_id'):
                    session['managed_pages'] = user.managed_pages
            # 마을지기 임명 시 5만닢 일회성 지급
            if page == 'village' and page in pages and not had_village:
                already_got = PointHistory.query.filter_by(user_id=uid, change_type='village_appointment').first()
                if not already_got:
                    add_points(uid, 50000, 'village_appointment', '마을지기 임명 축하금')
        db.session.commit()
        return redirect(url_for('admin.admin_page_managers', user_id=uid))
    target_uid = request.args.get('user_id', type=int)
    if target_uid:
        admins = User.query.filter(User.id == target_uid).all()
    else:
        admins = User.query.filter(User.managed_pages.isnot(None), User.managed_pages != '').all()
    def vi_k(myeon, ri):
        return f'vi_{myeon}_{ri}'
    TOWNS = [
        ('강상면', ['교평리','대석리','병산리','세월리','송학리','신화리','화양리']),
        ('강하면', ['동오리','성덕리','왕창리','운심리','전수리','항금리']),
        ('개군면', ['계전리','공세리','구미리','내리','부리','불곡리','상자포리','석장리','수리','앙덕리','자연리','주읍리','하자포리']),
        ('단월면', ['덕수리','명성리','보룡리','봉상리','산음리','삼가리','석산리','향소리']),
        ('서종면', ['노문리','도장리','명달리','문호리','서후리','수능리','수입리','정배리']),
        ('양동면', ['고송리','계정리','금왕리','단석리','매월리','삼산리','석곡리','쌍학리']),
        ('양서면', ['국수리','대심리','도곡리','목왕리','복포리','부용리','신원리','양수리','용담리','증동리','청계리']),
        ('양평읍', ['공흥리','대흥리','덕평리','도곡리','백안리','신애리','양근리','오빈리','원덕리','창대리','회현리']),
        ('옥천면', ['신복리','아신리','옥천리','용천리']),
        ('용문면', ['광탄리','금곡리','다문리','대촌리','마룡리','망능리','산북리','삼성리','신점리','연수리','오촌리','조현리','중원리','화전리']),
        ('지평면', ['곡수리','대평리','망미리','무왕리','송현리','수곡리','옥현리','월산리','일신리','지평리']),
    ]
    village_groups = [{'label': myeon, 'pages': {vi_k(myeon, r): r for r in ris}} for myeon, ris in TOWNS]
    all_pages = [
        {
            'title': '소개',
            'pages': {'intro':'사업소개', 'operation':'운영계획', 'terms':'회원약관', 'charter':'정관'}
        },
        {
            'title': '소식',
            'pages': {'kr_news':'대한민국과양평', 'world_news':'세계와양평', 'share':'공유마당', 'construction':'위치기반안내', 'heritage':'국가유산', 'scenery':'풍경', 'home':'집으로', 'building':'건축공사'}
        },
        {
            'title': '하는일',
            'groups': [
                {
                    'label': '⚖️ 이훈노무사 노동법률상담실',
                    'pages': {'legal':'법률상담', 'legal_issues':'노동이슈', 'legal_visit':'방문상담'}
                },
                {
                    'label': '🫂 숨상담심리연구소',
                    'pages': {'psycho':'심리상담', 'psycho_board':'심리상담게시판', 'psycho_visit':'방문상담게시판'}
                },
                {
                    'label': '♿ 휠체어경사로보급사업',
                    'pages': {'ramp':'휠체어경사로사업'}
                },
            ]
        },
        {
            'title': '제안',
            'pages': {'proposals':'꿈꾸기', 'all_proposals':'누구의꿈'}
        },
        {
            'title': '관리',
            'pages': {'admin_proposals':'누구의꿈(관리)', 'admin_users':'회원관리', 'admin_news':'소식(관리)', 'admin_share':'공유(관리)', 'admin_stores':'동네가게(관리)', 'admin_alerts':'알림(관리)', 'admin_ai_train':'양평AI 가르치기'}
        },
        {
            'title': '기타',
            'pages': {'schedule':'일정', 'stores':'동네가게', 'news':'소식'}
        },
        {
            'title': '마을',
            'groups': village_groups
        },
    ]
    return render_template('admin_page_managers.html', admins=admins, all_pages=all_pages, target_uid=target_uid)

@admin_bp.route('/admin/users')
def admin_users():
    if session.get('role') != 'leader': return "권한 부족", 403
    sort = request.args.get('sort', 'id')
    order = request.args.get('order', 'desc')
    sort_map = {
        'email': User.email, 'village': User.village, 'points': User.points,
        'verified': User.is_verified_resident, 'role': User.role, 'id': User.id
    }
    col = sort_map.get(sort, User.id)
    if order == 'asc':
        users = User.query.order_by(col.asc()).all()
    else:
        users = User.query.order_by(col.desc()).all()
    return render_template('admin_users.html', users=users, sort=sort, order=order)

@admin_bp.route('/admin/users/verify/<int:user_id>/<string:action>')
def verify_user(user_id, action):
    if session.get('role') != 'leader': return "권한 부족", 403
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
        file_abs_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'bills', os.path.basename(user.bill_image_path))
        try:
            if os.path.exists(file_abs_path):
                os.remove(file_abs_path)
                print(f"🔥 주민 보안 자치 규약에 따라 {user.real_name}님의 고지서 사진 파일을 완전 파기했습니다.")
        except Exception as e:
            print(f"파일 삭제 에러: {e}")
        user.bill_image_path = None
        
    db.session.commit()
    return redirect(url_for('.admin_users'))

@admin_bp.route('/admin/ai-chat')
def admin_ai_chat():
    if session.get('role') != 'leader':
        return "권한 부족", 403
    return render_template('admin_ai_chat.html')

@admin_bp.route('/admin/ai-chat/send', methods=['POST'])
def admin_ai_chat_send():
    if session.get('role') != 'leader':
        return jsonify({"error":"권한 부족"}), 403
    msg = request.json.get('message','').strip()
    if not msg:
        return jsonify({"reply":"메시지를 입력하세요."})
    # 통계 수집
    user_count = User.query.count()
    post_count = Post.query.count()
    report_count = ShareReport.query.count()
    village_count = User.query.filter(User.managed_pages.contains('village')).count()
    context = f"현재 함께사는양평 현황: 총 회원 {user_count}명, 꿈꾸기 제안 {post_count}건, 공유마당 신고 {report_count}건, 마을지기 {village_count}명"
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=current_app.config.get('GROQ_API_KEY',''))
        system_prompt = f"""너는 함께사는양평 커뮤니티 플랫폼의 관리자 AI야. 최고책임자와 관리자를 도와 플랫폼 운영을 지원해.
{context}
네 역할:
1. 회원·게시글·신고·닢 관련 통계 분석 및 조언
2. 문제 상황 감지 시 해결 방안 제안
3. 회원이나 통벗에게 전달할 공지·제안 초안 작성
4. 플랫폼 개선 아이디어 제안
5. 관리자 질문에 친절하고 전문적으로 답변
답변은 한국어로, 필요시 마크다운 형식으로 구조화해서 제공해."""
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role":"system","content":system_prompt},
                {"role":"user","content":msg}
            ],
            temperature=0.7, max_tokens=1024
        )
        reply = resp.choices[0].message.content
    except Exception as e:
        reply = f"AI 응답 오류: {str(e)}"
    return jsonify({"reply": reply})

@admin_bp.route('/admin/ai-feedback')
def admin_ai_feedback():
    if session.get('role') != 'leader':
        return "권한 부족", 403
    feedbacks = VillageAlert.query.filter_by(alert_type='ai_feedback').order_by(VillageAlert.created_at.desc()).limit(50).all()
    return render_template('admin_ai_feedback.html', feedbacks=feedbacks)

@admin_bp.route('/admin/ai-train')
def admin_ai_train():
    if session.get('role') != 'leader':
        return "최고책임자만 접근 가능", 403
    knowledges = AiKnowledge.query.order_by(AiKnowledge.id.desc()).limit(100).all()
    return render_template('admin_ai_train.html', knowledges=knowledges)

@admin_bp.route('/admin/ai-train/save', methods=['POST'])
def admin_ai_train_save():
    if session.get('role') != 'leader':
        return jsonify({"error":"권한 부족"}), 403
    q = request.form.get('question','').strip()
    a = request.form.get('answer','').strip()
    if not q or not a:
        return jsonify({"error":"질문과 답변을 모두 입력하세요."})
    k = AiKnowledge(question=q, answer=a, created_by=session.get('user_id'))
    db.session.add(k)
    db.session.commit()
    return jsonify({"status":"success","msg":"저장되었습니다."})

@admin_bp.route('/admin/ai-train/delete/<int:kid>', methods=['POST'])
def admin_ai_train_delete(kid):
    if session.get('role') != 'leader':
        return jsonify({"error":"권한 부족"}), 403
    k = AiKnowledge.query.get_or_404(kid)
    db.session.delete(k)
    db.session.commit()
    return jsonify({"status":"success","msg":"삭제되었습니다."})

