from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app
from models import db, Post, Comment, User, Message, PointHistory

board_bp = Blueprint('board', __name__)

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
    return render_template('view.html', post=post, comments=comments)

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



