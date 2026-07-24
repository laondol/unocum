from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app, send_file
from models import db, User, Friend, FriendGroup, Message
from route_modules.common import has_page_access

friends_bp = Blueprint('friends', __name__)

def _serve_spa():
    import os
    path = os.path.join(current_app.root_path, 'frontend', 'dist', 'index.html')
    if os.path.exists(path):
        return send_file(path)
    return render_template('intro.html')

@friends_bp.route('/friends')
def friends():
    if not session.get('user_id'):
        return redirect(url_for('auth.login', next='/friends'))
    return _serve_spa()

@friends_bp.route('/friends/list')
def friends_list_json():
    if not session.get('user_id'):
        return jsonify({"friends": []})
    uid = session['user_id']
    friend_ids = [f.receiver_id for f in Friend.query.filter_by(requester_id=uid, status='accepted').all()] + \
                 [f.requester_id for f in Friend.query.filter_by(receiver_id=uid, status='accepted').all()]
    friends = User.query.filter(User.id.in_(friend_ids)).all() if friend_ids else []
    # 받은 벗 신청
    pending = Friend.query.filter_by(receiver_id=uid, status='pending').all()
    requests = []
    for p in pending:
        req_user = User.query.get(p.requester_id)
        if req_user:
            requests.append({"id": req_user.id, "name": req_user.real_name or req_user.username})
    return jsonify({"friends": [{"id": f.id, "name": f.real_name or f.username, "town": f.town or '', "village": f.village or ''} for f in friends], "requests": requests})

@friends_bp.route('/friends/map')
def friends_map():
    if not session.get('user_id'): return redirect(url_for('auth.login', next='/friends/map'))
    return _serve_spa()

@friends_bp.route('/friends/request/<int:other_id>', methods=['POST'])
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

@friends_bp.route('/friends/accept/<int:other_id>', methods=['POST'])
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

@friends_bp.route('/friends/reject/<int:other_id>', methods=['POST'])
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

@friends_bp.route('/friends/remove/<int:other_id>', methods=['POST'])
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

@friends_bp.route('/friends/group/create', methods=['POST'])
def friend_group_create():
    uid = session.get('user_id')
    if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
    name = request.form.get('name', '').strip()
    if not name: return jsonify({'status':'error','msg':'그룹명 입력 필요'}), 400
    g = FriendGroup(user_id=uid, name=name)
    db.session.add(g)
    db.session.commit()
    return jsonify({'status':'success'})

@friends_bp.route('/friends/group/delete/<int:group_id>', methods=['POST'])
def friend_group_delete(group_id):
    uid = session.get('user_id')
    if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
    g = FriendGroup.query.filter_by(id=group_id, user_id=uid).first()
    if not g: return jsonify({'status':'error','msg':'그룹 없음'}), 404
    db.session.delete(g)
    db.session.commit()
    return jsonify({'status':'success'})
