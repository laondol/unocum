from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app, send_file
from models import db, Post, Comment, User, Message, PointHistory, ShareReport, NewsArticle
from services.security import save_village_file
from services.ai_service import call_ai_judge
import base64, os
from datetime import datetime

board_bp = Blueprint('board', __name__)

def _serve_spa():
    import os
    from flask import current_app, send_file
    path = os.path.join(current_app.root_path, 'frontend', 'dist', 'index.html')
    if os.path.exists(path):
        return send_file(path)
    from flask import render_template
    return render_template('intro.html')

@board_bp.route('/post/<int:post_id>')
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
    return _serve_spa()

@board_bp.route('/submit', methods=['POST'])
def submit_post():
    if 'user_id' not in session:
        return jsonify({"status": "fail", "msg": "로그인이 필요합니다."}), 401
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    if not title or not content:
        return jsonify({"status": "fail", "msg": "제목과 내용을 모두 입력해주세요."})
    user = User.query.get(session['user_id'])
    post = Post(title=title, content=content, user_id=user.id, author_name=user.real_name or user.username)
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename != '':
            file_url = save_village_file(file, current_app.config['UPLOAD_FOLDER'], post.author_name, user.town or 'unknown')
            post.file_path = file_url
    drawing = request.form.get('drawing_data')
    if drawing and len(drawing) > 2000:
        data = base64.b64decode(drawing.split(",")[1])
        fname = f"draw_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{post.author_name}_{user.town or 'unknown'}")
        if not os.path.exists(target_dir): os.makedirs(target_dir)
        with open(os.path.join(target_dir, fname), "wb") as f: f.write(data)
        post.file_path = f"/static/uploads/{post.author_name}_{user.town or 'unknown'}/{fname}"
    db.session.add(post)
    db.session.commit()
    ai_res = call_ai_judge(post.title, post.content)
    post.ai_score = ai_res.get('score', 0)
    post.total_score = post.ai_score + post.admin_score + post.leader_score + post.member_score
    post.ai_summary = ai_res.get('summary')
    post.ai_reason = ai_res.get('reason')
    post.ai_improvement_tip = ai_res.get('improvement_tip')
    db.session.commit()
    return jsonify({"status": "success", "id": post.id})

# --- [주민 전용] 제안 보완 수정 및 48시간 리셋 ---
@board_bp.route('/post/edit/<int:post_id>', methods=['GET', 'POST'])
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
                file_url = save_village_file(file, current_app.config['UPLOAD_FOLDER'], post.author_name, post.user.town if post.user else 'unknown')
                post.file_path = file_url
        
        # 그림판 드로잉 저장
        drawing = request.form.get('drawing_data')
        if drawing and len(drawing) > 2000:
            data = base64.b64decode(drawing.split(",")[1])
            fname = f"draw_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{post.author_name}_{post.user.town if post.user else 'unknown'}")
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

@board_bp.route('/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    content = request.form.get('content')
    ai_res = call_ai_judge("", content, is_comment=True)
    new_cm = Comment(post_id=post_id, author=session.get('username', '이웃'), content=content, total_score=ai_res.get('score', 0))
    db.session.add(new_cm)
    db.session.commit()
    return redirect(url_for('.view', post_id=post_id))

# ============================================================
# [관리자 전용] AI 뉴스 큐레이션 시스템
# ============================================================

@board_bp.route('/post/like/<int:post_id>', methods=['POST'])
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
    if voter.is_verified_resident:
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

@board_bp.route('/post/dislike/<int:post_id>', methods=['POST'])
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
    if voter.is_verified_resident:
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

# --- API endpoints ---

@board_bp.route('/api/posts')
def api_posts():
    category = request.args.get('category', '')
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    q = Post.query
    if category: q = q.filter(Post.category == category)
    if status_filter: q = q.filter(Post.status == status_filter)
    posts = q.order_by(Post.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return jsonify([{
        'id': p.id, 'title': p.title, 'author_name': p.author_name,
        'category': p.category, 'status': p.status,
        'ai_score': p.ai_score, 'total_score': p.total_score,
        'like_count': p.like_count, 'dislike_count': p.dislike_count,
        'ai_summary': p.ai_summary,
        'created_at': p.created_at.isoformat() if p.created_at else None,
    } for p in posts.items])

@board_bp.route('/api/board/post/<int:post_id>')
def api_board_post(post_id):
    post = Post.query.get_or_404(post_id)
    uid = session.get('user_id')
    role = session.get('role')
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.asc()).all()
    return jsonify({
        'post': {
            'id': post.id, 'title': post.title, 'content': post.content,
            'author_name': post.author_name, 'user_id': post.user_id,
            'file_path': post.file_path, 'category': post.category, 'status': post.status,
            'ai_score': post.ai_score, 'ai_summary': post.ai_summary, 'ai_reason': post.ai_reason,
            'admin_score': post.admin_score, 'leader_score': post.leader_score,
            'member_score': post.member_score, 'total_score': post.total_score,
            'is_forced_approved': post.is_forced_approved,
            'like_count': post.like_count, 'dislike_count': post.dislike_count,
            'is_finalized': post.is_finalized,
            'created_at': post.created_at.isoformat() if post.created_at else None,
            'updated_at': post.updated_at.isoformat() if post.updated_at else None,
        },
        'comments': [{
            'id': c.id, 'author': c.author, 'content': c.content,
            'parent_id': c.parent_id, 'total_score': c.total_score,
            'created_at': c.created_at.isoformat() if c.created_at else None,
        } for c in comments],
        'is_owner': post.user_id == uid,
        'role': role,
    })

@board_bp.route('/api/board/search')
def api_board_search():
    q = request.args.get('q', '').strip()
    results = {'posts': [], 'shares': [], 'news': []}
    if q:
        results['posts'] = [{'id': p.id, 'title': p.title, 'content': (p.content or '')[:100], 'author_name': p.author_name, 'created_at': p.created_at.isoformat() if p.created_at else None} for p in Post.query.filter(db.or_(Post.title.ilike(f'%{q}%'), Post.content.ilike(f'%{q}%'))).order_by(Post.created_at.desc()).limit(20).all()]
        results['shares'] = [{'id': s.id, 'title': s.title, 'description': (s.description or '')[:100], 'author_name': s.author_name, 'created_at': s.created_at.isoformat() if s.created_at else None} for s in ShareReport.query.filter(db.or_(ShareReport.title.ilike(f'%{q}%'), ShareReport.description.ilike(f'%{q}%'))).order_by(ShareReport.created_at.desc()).limit(20).all()]
        results['news'] = [{'id': n.id, 'title': n.title, 'summary': (n.summary or '')[:100], 'created_at': n.created_at.isoformat() if n.created_at else None} for n in NewsArticle.query.filter(db.or_(NewsArticle.title.ilike(f'%{q}%'), NewsArticle.summary.ilike(f'%{q}%')), db.or_(NewsArticle.world_admin_approved == True, NewsArticle.kr_yp_admin_approved == True)).order_by(NewsArticle.created_at.desc()).limit(20).all()]
        return jsonify(results)
    return jsonify(results)

@board_bp.route('/api/post/<int:post_id>')
def api_post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    uid = session.get('user_id')
    user_vote = None
    if uid:
        from models import PostVote
        v = PostVote.query.filter_by(post_id=post_id, user_id=uid).first()
        if v: user_vote = v.vote_type
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.asc()).all()
    return jsonify({
        'id': post.id, 'title': post.title, 'content': post.content,
        'author_name': post.author_name, 'user_id': post.user_id,
        'category': post.category, 'status': post.status,
        'ai_score': post.ai_score, 'ai_summary': post.ai_summary, 'ai_reason': post.ai_reason,
        'admin_score': post.admin_score, 'leader_score': post.leader_score, 'member_score': post.member_score,
        'total_score': post.total_score, 'file_path': post.file_path,
        'like_count': post.like_count, 'dislike_count': post.dislike_count,
        'user_vote': user_vote,
        'created_at': post.created_at.isoformat() if post.created_at else None,
        'comments': [{
            'id': c.id, 'author': c.author, 'content': c.content,
            'total_score': c.total_score, 'parent_id': c.parent_id,
            'created_at': c.created_at.isoformat() if c.created_at else None,
        } for c in comments],
    })


