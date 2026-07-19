from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app
from models import db, Message, User, Friend, PointHistory
from datetime import datetime

message_bp = Blueprint('message', __name__)

LETTER_COST = 10  # 편지 1通당 닢 10 차감
INTERNAL_ADMIN_ID = 1  # 전체관리자 수신용 내부 ID (운영 db의 admin1)
INTERNAL_AI_ADMIN_ID = 9  # AI관리자 발송용 내부 ID (herb2727)


def _get_balance(uid):
    """사용자의 닢 잔액 반환"""
    user = User.query.get(uid)
    return user.points if user else 0


def _get_internal_admin():
    """전체관리자용 내부 계정 반환"""
    return User.query.get(INTERNAL_ADMIN_ID)

def _get_ai_admin():
    """AI관리자 발송용 내부 계정 반환"""
    return User.query.get(INTERNAL_AI_ADMIN_ID)

def _get_village_leader(user_town, user_village):
    """해당 읍/면/리의 마을지기 반환"""
    if not user_town or not user_village:
        return None
    return User.query.filter(
        User.role == 'leader', User.town == user_town, User.village == user_village
    ).first()

def _deduct_points(uid, amount, desc):
    """坭 차감 (성공 시 True, 실패 시 False)"""
    user = User.query.get(uid)
    if not user or (user.points or 0) < amount:
        return False
    user.points -= amount
    h = PointHistory(user_id=uid, change_type='letter', amount=-amount,
                     balance_after=user.points, description=desc)
    db.session.add(h)
    return True


@message_bp.route('/message/count')
def message_count():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'count': 0})
    cnt = Message.query.filter_by(receiver_id=uid, is_read=False).count()
    return jsonify({'count': cnt})


@message_bp.route('/message/inbox')
def message_inbox():
    if not session.get('username'):
        return redirect(url_for('auth.login', next='/message/inbox'))
    uid = session['user_id']
    role = session.get('role', 'user')
    tab = request.args.get('tab', 'received')

    # 받은 편지: 본인 수신 + (관리자/책임자는 공개편지도 열람 가능)
    received = Message.query.filter(
        (Message.receiver_id == uid) |
        ((Message.is_public == True) & (role in ['admin', 'leader']))
    ).order_by(Message.created_at.desc()).all()

    # 보낸 편지
    sent = Message.query.filter_by(sender_id=uid).order_by(Message.created_at.desc()).all()
    for m in sent:
        u = User.query.get(m.receiver_id)
        m.receiver_name = u.real_name or u.username if u else '알수없음'

    # 벗 목록 (편지 보낼 수 있는 대상)
    friends = Friend.query.filter(
        (Friend.requester_id == uid) & (Friend.status == 'accepted')
    ).all()
    friend_ids = [f.receiver_id for f in friends]
    friends2 = Friend.query.filter(
        (Friend.receiver_id == uid) & (Friend.status == 'accepted')
    ).all()
    friend_ids += [f.requester_id for f in friends2]
    friend_users = User.query.filter(User.id.in_(friend_ids)).all() if friend_ids else []

    # 전체관리자 (단일 내부 계정)
    internal_admin = _get_internal_admin()

    # 마을지기 (같은 읍/면/리의 마을지기)
    me = User.query.get(uid)
    village_leader = None
    if me and me.town and me.village:
        village_leader = _get_village_leader(me.town, me.village)

    return render_template('message_inbox.html',
                           received=received, sent=sent, tab=tab,
                           friends=friend_users, internal_admin=internal_admin,
                           village_leader=village_leader,
                           user_points=_get_balance(uid),
                           letter_cost=LETTER_COST)


@message_bp.route('/message/send/global', methods=['GET', 'POST'])
def send_message_global():
    if not session.get('username'):
        return redirect(url_for('auth.login', next=request.path))
    uid = session['user_id']
    # 전체관리자(내부 ID) 조회
    from models import User
    admin_user = User.query.filter(User.role == 'admin').first()
    if not admin_user:
        return jsonify({'error': '전체관리자 없음'}), 404
    receiver = admin_user
    is_admin = True
    is_village_leader = False
    admin_type = 'global'

    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        agree_public = request.form.get('agree_public')
        agree_conduct = request.form.get('agree_conduct')

        if not subject or not content:
            return jsonify({'error': '제목과 내용을 입력하세요.'}), 400

        balance = _get_balance(uid)
        if balance < LETTER_COST:
            return jsonify({'error': f'坭가 부족합니다. (현재 {balance}坭, 필요 {LETTER_COST}坭)'}), 400

        if not agree_public:
            return jsonify({'error': '공개편지 동의가 필요합니다.'}), 400
        if not agree_conduct:
            return jsonify({'error': '행동강령 동의가 필요합니다.'}), 400

        if not _deduct_points(uid, LETTER_COST, f'편지 발송 → 전체관리자'):
            return jsonify({'error': '坭 차감 실패'}), 400

        msg = Message(
            sender_id=uid,
            sender_name=session.get('real_name', session['username']),
            sender_role=session.get('role', 'user'),
            receiver_id=receiver.id,
            subject=subject,
            content=content,
            is_public=True,
            letter_type='pending',
            town=User.query.get(uid).town or '',
            village=User.query.get(uid).village or '',
            original_receiver_type='global',
            moderation_status='pending'
        )
        db.session.add(msg)
        db.session.commit()

        return jsonify({'success': True, 'msg': f'{LETTER_COST}坭이 차감되었습니다. ({_get_balance(uid)}坭 남음)'})

    return render_template('send_message.html', receiver=receiver,
                           is_admin=is_admin, is_village_leader=is_village_leader,
                           admin_type='global',
                           user_points=_get_balance(uid), letter_cost=LETTER_COST)


@message_bp.route('/message/send/admin', methods=['GET', 'POST'])
def send_message_admin():
    """전체관리자에게 편지 보내기 (내부 관리자 ID로 발송)"""
    if not session.get('username'):
        return redirect(url_for('auth.login', next=request.path))
    uid = session['user_id']
    internal_admin = _get_internal_admin()
    if not internal_admin:
        return jsonify({'error': '내부 관리자 계정을 찾을 수 없습니다.'}), 500

    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        agree_public = request.form.get('agree_public')
        agree_conduct = request.form.get('agree_conduct')

        if not subject or not content:
            return jsonify({'error': '제목과 내용을 입력하세요.'}), 400

        balance = _get_balance(uid)
        if balance < LETTER_COST:
            return jsonify({'error': f'坭가 부족합니다. (현재 {balance}坭, 필요 {LETTER_COST}坭)'}), 400
        if not agree_public:
            return jsonify({'error': '공개편지 동의가 필요합니다.'}), 400
        if not agree_conduct:
            return jsonify({'error': '행동강령 동의가 필요합니다.'}), 400
        if not _deduct_points(uid, LETTER_COST, '편지 발송 → 전체관리자'):
            return jsonify({'error': '坭 차감에 실패했습니다.'}), 400

        msg = Message(
            sender_id=uid,
            sender_name=session.get('real_name', session['username']),
            sender_role=session.get('role', 'user'),
            receiver_id=INTERNAL_ADMIN_ID,  # 내부 관리자 ID로 발송
            subject=subject,
            content=content,
            is_public=True,
            letter_type='admin'
        )
        db.session.add(msg)
        db.session.commit()
        return jsonify({'success': True, 'msg': f'{LETTER_COST}坭이 차감되었습니다. ({_get_balance(uid)}坭 남음)'})

    return render_template('send_message.html', receiver=internal_admin,
                           is_admin=True, is_village_leader=False,
                           user_points=_get_balance(uid), letter_cost=LETTER_COST,
                           admin_type='global')

@message_bp.route('/message/send/village_leader', methods=['GET', 'POST'])
def send_message_village_leader():
    """마을지기에게 편지 보내기 (해당 읍/면/리 마을지기)"""
    if not session.get('username'):
        return redirect(url_for('auth.login', next=request.path))
    uid = session['user_id']
    me = User.query.get(uid)
    village_leader = _get_village_leader(me.town, me.village) if me else None
    
    if not village_leader:
        return jsonify({'error': '해당 지역의 마을지기가 없습니다.'}), 404

    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        agree_public = request.form.get('agree_public')
        agree_conduct = request.form.get('agree_conduct')

        if not subject or not content:
            return jsonify({'error': '제목과 내용을 입력하세요.'}), 400

        balance = _get_balance(uid)
        if balance < LETTER_COST:
            return jsonify({'error': f'坭가 부족합니다. (현재 {balance}坭, 필요 {LETTER_COST}坭)'}), 400
        if not agree_public:
            return jsonify({'error': '공개편지 동의가 필요합니다.'}), 400
        if not agree_conduct:
            return jsonify({'error': '행동강령 동의가 필요합니다.'}), 400
        if not _deduct_points(uid, LETTER_COST, f'편지 발송 → 마을지기({village_leader.real_name or village_leader.username})'):
            return jsonify({'error': '坭 차감에 실패했습니다.'}), 400

        msg = Message(
            sender_id=uid,
            sender_name=session.get('real_name', session['username']),
            sender_role=session.get('role', 'user'),
            receiver_id=village_leader.id,
            subject=subject,
            content=content,
            is_public=True,
            letter_type='village_leader'
        )
        db.session.add(msg)
        db.session.commit()
        return jsonify({'success': True, 'msg': f'{LETTER_COST}坭이 차감되었습니다. ({_get_balance(uid)}坭 남음)'})

    return render_template('send_message.html', receiver=village_leader,
                           is_admin=False, is_village_leader=True,
                           user_points=_get_balance(uid), letter_cost=LETTER_COST,
                           admin_type='village')


@message_bp.route('/message/read/<int:msg_id>', methods=['GET', 'POST'])
def read_message(msg_id):
    if not session.get('username'):
        return redirect(url_for('auth.login', next=request.path))
    uid = session['user_id']
    role = session.get('role', 'user')
    msg = Message.query.get_or_404(msg_id)

    # 열람 권한: 받은 사람 본인, 또는 공개편지且 관리자/책임자
    if msg.receiver_id != uid and not (msg.is_public and role in ['admin', 'leader']):
        return jsonify({'error': '권한 없음'}), 403

    msg.is_read = True
    db.session.commit()

    if request.method == 'POST':
        return jsonify({'status': 'success'})
    return redirect(url_for('.message_inbox'))


@message_bp.route('/friends/list')
def friends_list():
    """JSON으로 벗 목록 반환 (편지 대상 선택용)"""
    uid = session.get('user_id')
    if not uid:
        return jsonify({'friends': []})
    f1 = Friend.query.filter_by(requester_id=uid, status='accepted').all()
    f2 = Friend.query.filter_by(receiver_id=uid, status='accepted').all()
    ids = set([f.receiver_id for f in f1] + [f.requester_id for f in f2])
    users = User.query.filter(User.id.in_(ids)).all() if ids else []
    return jsonify({'friends': [{'id': u.id, 'name': u.real_name or u.username, 'town': u.town or '', 'village': u.village or ''} for u in users]})

@message_bp.route('/message/admin/pending')
def admin_pending_letters():
    """관리자용 보류 편지함 (관리자/마을지기 공통 접근)"""
    if not session.get('username'):
        return redirect(url_for('auth.login', next=request.path))
    uid = session['user_id']
    role = session.get('role', 'user')
    
    # 관리자 또는 마을지기만 접근 가능
    if role not in ['admin', 'leader']:
        return '권한 없음', 403
    
    me = User.query.get(uid)
    
    # 관리자는 전체, 마을지기는 자기 읍/면/리만
    if role == 'admin':
        pending = Message.query.filter_by(letter_type='pending').order_by(Message.created_at.desc()).all()
    else:
        pending = Message.query.filter(
            Message.letter_type == 'pending',
            Message.town == me.town,
            Message.village == me.village
        ).order_by(Message.created_at.desc()).all()
    
    return render_template('admin_pending_letters.html', pending=pending, role=role)

@message_bp.route('/message/admin/pending/<int:msg_id>/approve', methods=['POST'])
def admin_approve_pending(msg_id):
    """보류 편지 승인 -> 실제 수신자에게 전달"""
    if not session.get('username'):
        return jsonify({'error': '로그인 필요'}), 401
    role = session.get('role', 'user')
    if role not in ['admin', 'leader']:
        return jsonify({'error': '권한 없음'}), 403
    
    msg = Message.query.get_or_404(msg_id)
    if msg.letter_type != 'pending':
        return jsonify({'error': '잘못된 요청'}), 400
    
    # 원래 수신자 결정 (전체관리자 또는 마을지기)
    if msg.original_receiver_type == 'global':
        real_receiver_id = INTERNAL_ADMIN_ID
    else:
        me = User.query.get(session['user_id'])
        leader = _get_village_leader(me.town, me.village)
        real_receiver_id = leader.id if leader else INTERNAL_ADMIN_ID
    
    msg.receiver_id = real_receiver_id
    msg.letter_type = 'admin' if msg.original_receiver_type == 'global' else 'village_leader'
    msg.is_public = True
    msg.moderation_status = 'approved'
    db.session.commit()
    
    return jsonify({'success': True})

@message_bp.route('/message/admin/pending/<int:msg_id>/reject', methods=['POST'])
def admin_reject_pending(msg_id):
    """보류 편지 반려 -> 발송자에게 AI관리자 명의로 통보"""
    if not session.get('username'):
        return jsonify({'error': '로그인 필요'}), 401
    role = session.get('role', 'user')
    if role not in ['admin', 'leader']:
        return jsonify({'error': '권한 없음'}), 403
    
    msg = Message.query.get_or_404(msg_id)
    if msg.letter_type != 'pending':
        return jsonify({'error': '잘못된 요청'}), 400
    
    ai_admin = _get_ai_admin()
    reason = request.form.get('reason', '내용 검토 결과 부적절함')
    
    # 발송자에게 반려 통보 (AI관리자 명의)
    reject_msg = Message(
        sender_id=INTERNAL_AI_ADMIN_ID,
        sender_name='AI 관리자',
        sender_role='admin',
        receiver_id=msg.sender_id,
        subject='편지 발송 반려: ' + msg.subject,
        content=('[AI 관리자 알림] 귀하가 보낸 편지(제목: ' + msg.subject + ')가 검토 결과 반려되었습니다.\n\n'
                 '반려 사유: ' + reason + '\n\n'
                 '※ 이 메시지는 자동 검토 시스템에 의해 발송되었습니다.'),
        is_public=False,
        letter_type='ai_reject'
    )
    db.session.add(reject_msg)
    
    # 원본 편지 상태 업데이트
    msg.moderation_status = 'rejected'
    msg.rejection_reason = reason
    db.session.commit()
    
    return jsonify({'success': True})
