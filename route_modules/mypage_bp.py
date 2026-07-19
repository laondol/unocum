from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app
from models import db, User, PointHistory

mypage_bp = Blueprint('mypage', __name__)

@mypage_bp.route('/mypage/points')
def mypage_points():
    if not session.get('username'):
        return redirect(url_for('auth.login', next=request.path))
    user = User.query.get(session['user_id'])
    raw_history = PointHistory.query.filter_by(user_id=user.id).order_by(PointHistory.created_at.desc()).limit(100).all()
    # 잔액을 실제 user.points 기준으로 재계산 (내역 불일치 방지)
    running = user.points
    for h in raw_history:
        h.balance_after = running
        running -= h.amount
    return render_template('mypage_points.html', user=user, history=raw_history)

@mypage_bp.route('/mypage/points/charge')
def points_charge():
    if not session.get('username'):
        return redirect(url_for('auth.login', next='/mypage/points/charge'))
    user = User.query.get(session['user_id'])
    history = PointHistory.query.filter_by(user_id=user.id).order_by(PointHistory.created_at.desc()).limit(20).all()
    portone_store = current_app.config.get('PORTONE_STORE_ID', 'store-12345678')
    portone_channel = current_app.config.get('PORTONE_CHANNEL_KEY', 'channel-key-12345678')
    return render_template('points_charge.html', user=user, point_history=history,
        portone_store_id=portone_store, portone_channel=portone_channel)

@mypage_bp.route('/api/payment/prepare', methods=['POST'])
def payment_prepare():
    if not session.get('username'):
        return jsonify({"error": "로그인이 필요합니다."}), 401
    data = request.get_json()
    nip = data.get('nip', 0)
    if nip < 1000:
        return jsonify({"error": "최소 1,000닢부터 충전 가능합니다."})
    payment_id = f"nip_{session['user_id']}_{int(datetime.now().timestamp())}"
    return jsonify({"payment_id": payment_id, "nip": nip})

@mypage_bp.route('/api/payment/verify', methods=['POST'])
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
