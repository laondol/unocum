from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app, send_file
from models import db, User, Post, Comment, PointHistory, AiKnowledge, NewsArticle

admin_bp = Blueprint('admin', __name__)

def _serve_spa():
    import os
    path = os.path.join(current_app.root_path, 'frontend', 'dist', 'index.html')
    if os.path.exists(path):
        return send_file(path)
    return render_template('intro.html')



def add_points(user_id, amount, change_type, description, related_id=None):
    user = User.query.get(user_id)
    if not user: return
    user.points = (user.points or 0) + amount
    h = PointHistory(user_id=user_id, change_type=change_type, amount=amount,
                     balance_after=user.points, description=description, related_id=related_id)
    db.session.add(h)
    return user.points


# --- API endpoints for SPA admin ---

@admin_bp.route('/api/admin/posts')
def api_admin_posts():
    if session.get('role') != 'leader': return jsonify({'error': '권한 없음'}), 403
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return jsonify([{
        'id': p.id, 'title': p.title, 'content': p.content[:100],
        'file_path': p.file_path, 'total_score': p.total_score,
        'is_forced_approved': p.is_forced_approved,
        'created_at': p.created_at.isoformat() if p.created_at else None,
    } for p in posts])

@admin_bp.route('/api/admin/users')
def api_admin_users():
    if session.get('role') != 'leader': return jsonify({'error': '권한 없음'}), 403
    users = User.query.order_by(User.id.desc()).all()
    from models import DIDDocument, VerifiableCredential
    return jsonify([{
        'id': u.id, 'email': u.email, 'username': u.username,
        'real_name': u.real_name, 'role': u.role, 'town': u.town,
        'village': u.village, 'points': u.points,
        'is_verified_resident': u.is_verified_resident,
        'managed_pages': u.managed_pages,
        'has_did': DIDDocument.query.filter_by(user_id=u.id).first() is not None,
        'has_vc': VerifiableCredential.query.filter_by(subject_user_id=u.id, revoked=False).first() is not None,
    } for u in users])

@admin_bp.route('/api/admin/users/search')
def api_admin_users_search():
    if session.get('role') not in ('admin', 'leader'): return jsonify({'error': '권한 없음'}), 403
    q = request.args.get('q', '').strip()
    if not q: return jsonify([])
    pattern = f'%{q}%'
    users = User.query.filter(
        db.or_(User.email.ilike(pattern), User.real_name.ilike(pattern), User.username.ilike(pattern))
    ).limit(20).all()
    from models import DIDDocument
    return jsonify([{
        'id': u.id, 'username': u.username, 'real_name': u.real_name,
        'town': u.town, 'village': u.village,
        'is_verified_resident': u.is_verified_resident,
        'did': DIDDocument.query.filter_by(user_id=u.id).first().did if DIDDocument.query.filter_by(user_id=u.id).first() else None,
    } for u in users])

@admin_bp.route('/api/admin/stores')
def api_admin_stores():
    if session.get('role') not in ('admin', 'leader'): return jsonify({'error': '권한 없음'}), 403
    from models import StoreInfo
    stores = StoreInfo.query.order_by(StoreInfo.name).all()
    return jsonify([{
        'id': s.id, 'name': s.name, 'town': s.town, 'village': s.village,
        'our_link': s.our_link, 'store_homepage': s.store_homepage,
        'smartplace': s.smartplace, 'latitude': s.latitude, 'longitude': s.longitude,
    } for s in stores])

@admin_bp.route('/api/admin/alerts')
def api_admin_alerts():
    if session.get('role') not in ('admin', 'leader'): return jsonify({'error': '권한 없음'}), 403
    from models import VillageAlert
    alerts = VillageAlert.query.order_by(VillageAlert.created_at.desc()).all()
    return jsonify([{
        'id': a.id, 'title': a.title, 'content': a.content,
        'town': a.town, 'village': a.village, 'alert_type': a.alert_type,
        'urgency': a.urgency, 'author_name': a.author_name,
        'is_active': a.is_active,
        'created_at': a.created_at.isoformat() if a.created_at else None,
    } for a in alerts])

@admin_bp.route('/api/admin/share-reports')
def api_admin_share_reports():
    if session.get('role') not in ('admin', 'leader'): return jsonify({'error': '권한 없음'}), 403
    from models import ShareReport
    reports = ShareReport.query.order_by(ShareReport.created_at.desc()).all()
    return jsonify([{
        'id': r.id, 'title': r.title, 'description': r.description,
        'image_path': r.image_path, 'drawing_path': r.drawing_path,
        'video_path': r.video_path, 'author_name': r.author_name,
        'town': r.town, 'village': r.village, 'latitude': r.latitude, 'longitude': r.longitude,
        'ai_category': r.ai_category, 'ai_summary': r.ai_summary,
        'is_moderated': r.is_moderated, 'moderation_result': r.moderation_result,
        'status': r.status, 'ai_danger_alert': r.ai_danger_alert,
        'created_at': r.created_at.isoformat() if r.created_at else None,
    } for r in reports])

@admin_bp.route('/api/admin/ai-knowledge')
def api_admin_ai_knowledge():
    if session.get('role') not in ('admin', 'leader'): return jsonify({'error': '권한 없음'}), 403
    knowledge = AiKnowledge.query.order_by(AiKnowledge.created_at.desc()).all()
    return jsonify([{
        'id': k.id, 'question': k.question, 'answer': k.answer,
        'category': k.category, 'created_at': k.created_at.isoformat() if k.created_at else None,
    } for k in knowledge])

@admin_bp.route('/api/admin/news')
def api_admin_news():
    if session.get('role') not in ('admin', 'leader'): return jsonify({'error': '권한 없음'}), 403
    tab = request.args.get('tab', 'all')
    page = int(request.args.get('page', 1))
    per_page = 20
    q = NewsArticle.query
    if tab == 'world':
        q = q.filter(NewsArticle.category.in_(['세계뉴스', '환경뉴스', '건강정보', '복지정보', '농업정보', '관광소식']))
    elif tab == 'kr_yp':
        q = q.filter(NewsArticle.category.in_(['대한민국뉴스', '양평소식', '정책정보', '지역소식']))
    total = q.count()
    items = q.order_by(NewsArticle.created_at.desc()).offset((page-1)*per_page).limit(per_page).all()
    world_cats = {'세계뉴스', '환경뉴스', '건강정보', '복지정보', '농업정보', '관광소식'}
    kr_yp_cats = {'대한민국뉴스', '양평소식', '정책정보', '지역소식'}
    def _approval(a):
        if tab == 'world':
            return a.world_ai_approved, a.world_admin_approved
        if tab == 'kr_yp':
            return a.kr_yp_ai_approved, a.kr_yp_admin_approved
        if a.category in world_cats:
            return a.world_ai_approved, a.world_admin_approved
        if a.category in kr_yp_cats:
            return a.kr_yp_ai_approved, a.kr_yp_admin_approved
        return a.is_selected, a.is_selected
    return jsonify({'items': [{
        'id': a.id, 'title': a.title, 'summary': (a.summary or '')[:200],
        'category': a.category, 'ai_reason': a.ai_reason,
        'source_url': a.source_url, 'ai_generated': a.is_ai_generated,
        'created_at': a.created_at.isoformat() if a.created_at else None,
        'ai_approved': _approval(a)[0],
        'admin_approved': _approval(a)[1],
        'is_selected': getattr(a, 'is_selected', False),
    } for a in items], 'total_pages': max(1, (total + per_page - 1) // per_page)})

@admin_bp.route('/api/admin/pending-letters')
def api_admin_pending_letters():
    if session.get('role') not in ('admin', 'leader'): return jsonify({'error': '권한 없음'}), 403
    from models import Message
    pending = Message.query.filter_by(is_pending=True).order_by(Message.created_at.desc()).all()
    return jsonify([{
        'id': m.id, 'subject': m.subject, 'content': m.content,
        'sender_name': m.sender_name, 'sender_id': m.sender_id,
        'receiver_id': m.receiver_id,
        'created_at': m.created_at.isoformat() if m.created_at else None,
    } for m in pending])

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
    return _serve_spa()
@admin_bp.route('/admin')
def admin():
    if session.get('role') != 'leader': return "권한 없음", 403
    return _serve_spa()

@admin_bp.route('/api/admin/post/<int:post_id>')
def api_admin_post_detail(post_id):
    if session.get('role') != 'leader': return jsonify({'error': '권한 부족'}), 403
    post = Post.query.get_or_404(post_id)
    import json as _json
    logs = _json.loads(post.ai_debate_log) if post.ai_debate_log else []
    return jsonify({
        'id': post.id, 'title': post.title, 'content': post.content,
        'file_path': post.file_path, 'author_name': post.author_name,
        'category': post.category, 'status': post.status,
        'ai_score': post.ai_score, 'admin_score': post.admin_score,
        'leader_score': post.leader_score, 'member_score': post.member_score,
        'total_score': post.total_score, 'ai_summary': post.ai_summary,
        'ai_reason': post.ai_reason, 'ai_improvement_tip': post.ai_improvement_tip,
        'is_forced_approved': post.is_forced_approved, 'is_finalized': post.is_finalized,
        'created_at': post.created_at.isoformat() if post.created_at else None,
        'debate_logs': logs,
    })

@admin_bp.route('/api/admin/post/<int:post_id>/scores', methods=['POST'])
def api_admin_update_scores(post_id):
    if session.get('role') != 'leader': return jsonify({'error': '권한 부족'}), 403
    post = Post.query.get_or_404(post_id)
    data = request.get_json() or {}
    role = session.get('role')
    if role == 'admin':
        post.admin_score = int(data.get('admin_score', post.admin_score))
    elif role == 'leader':
        post.leader_score = int(data.get('leader_score', post.leader_score))
    if 'is_forced_approved' in data:
        post.is_forced_approved = bool(data['is_forced_approved'])
    post.total_score = post.ai_score + post.admin_score + post.leader_score + post.member_score
    if post.admin_score != 0 and post.leader_score != 0 and post.total_score > -50:
        post.is_forced_approved = True
    db.session.commit()
    return jsonify({'status': 'success', 'total_score': post.total_score, 'is_forced_approved': post.is_forced_approved})

@admin_bp.route('/admin/post/<int:post_id>')
def admin_post_view(post_id):
    if session.get('role') != 'leader': return "권한 부족", 403
    return _serve_spa()

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
            if page == 'village' and page not in pages and not user.is_verified_resident:
                return jsonify({'error': '이웃인증 필요'}), 400
            if action == 'toggle':
                if page in pages:
                    pages.remove(page)
                else:
                    pages.append(page)
                user.managed_pages = ','.join(filter(None, pages))
                if uid == session.get('user_id'):
                    session['managed_pages'] = user.managed_pages
            if page == 'village' and page in pages and not had_village:
                already_got = PointHistory.query.filter_by(user_id=uid, change_type='village_appointment').first()
                if not already_got:
                    add_points(uid, 50000, 'village_appointment', '마을지기 임명 축하금')
        db.session.commit()
        return jsonify({'status': 'success'})
    return _serve_spa()

@admin_bp.route('/api/admin/page-managers')
def api_admin_page_managers():
    if session.get('role') != 'leader':
        return jsonify({'error': '권한 없음'}), 403
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
        {'title': '소개', 'pages': {'intro':'사업소개', 'operation':'운영계획', 'terms':'회원약관', 'charter':'정관'}},
        {'title': '소식', 'pages': {'kr_news':'대한민국과양평', 'world_news':'세계와양평', 'share':'공유마당', 'construction':'위치기반안내', 'heritage':'국가유산', 'scenery':'풍경', 'home':'집으로', 'building':'건축공사'}},
        {'title': '하는일', 'groups': [
            {'label': '⚖️ 이훈노무사 노동법률상담실', 'pages': {'legal':'법률상담', 'legal_issues':'노동이슈', 'legal_visit':'방문상담'}},
            {'label': '🫂 숨상담심리연구소', 'pages': {'psycho':'심리상담', 'psycho_board':'심리상담게시판', 'psycho_visit':'방문상담게시판'}},
            {'label': '♿ 휠체어경사로보급사업', 'pages': {'ramp':'휠체어경사로사업'}},
        ]},
        {'title': '제안', 'pages': {'proposals':'꿈꾸기', 'all_proposals':'누구의꿈'}},
        {'title': '관리', 'pages': {'admin_proposals':'누구의꿈(관리)', 'admin_users':'회원관리', 'admin_news':'소식(관리)', 'admin_share':'공유(관리)', 'admin_stores':'동네가게(관리)', 'admin_alerts':'알림(관리)', 'admin_ai_train':'양평AI 가르치기'}},
        {'title': '기타', 'pages': {'schedule':'일정', 'stores':'동네가게', 'news':'소식'}},
        {'title': '마을', 'groups': village_groups},
    ]
    return jsonify({
        'admins': [{
            'id': u.id, 'username': u.username, 'email': u.email,
            'real_name': u.real_name, 'role': u.role,
            'town': u.town, 'village': u.village,
            'is_verified_resident': u.is_verified_resident,
            'managed_pages': u.managed_pages or '',
        } for u in admins],
        'all_pages': all_pages,
    })

@admin_bp.route('/admin/users')
def admin_users():
    if session.get('role') != 'leader': return "권한 부족", 403
    return _serve_spa()

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
    return _serve_spa()

@admin_bp.route('/admin/did/issue')
def admin_did_issue():
    if session.get('role') != 'leader':
        return "권한 부족", 403
    return _serve_spa()

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
    return _serve_spa()

@admin_bp.route('/admin/ai-train')
def admin_ai_train():
    if session.get('role') != 'leader':
        return "최고책임자만 접근 가능", 403
    return _serve_spa()

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

