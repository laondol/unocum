from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from route_modules.common import has_page_access
from models import db, PsychoPost, PsychoAppointment, PsychoDoctorSchedule, PsychoGoogleCalendarConfig, TongBotSchedule, User, Message

psycho_bp = Blueprint('psycho', __name__)

def _serve_spa():
    import os
    from flask import current_app, send_file
    path = os.path.join(current_app.root_path, 'frontend', 'dist', 'index.html')
    if os.path.exists(path):
        return send_file(path)
    from flask import render_template
    return render_template('intro.html')

@psycho_bp.route('/psycho/list')
def psycho_list():
    uid = session.get('user_id')
    if has_page_access('psycho'):
        posts = PsychoPost.query.order_by(PsychoPost.created_at.desc()).all()
    elif uid:
        posts = PsychoPost.query.filter_by(user_id=uid).order_by(PsychoPost.created_at.desc()).all()
    else:
        verified_email = session.get('verify_email')
        if verified_email and session.get('email_verified_for_psycho'):
            posts = PsychoPost.query.filter_by(email=verified_email).order_by(PsychoPost.created_at.desc()).all()
        else:
            posts = []
    return _serve_spa()

@psycho_bp.route('/psycho/write', methods=['GET', 'POST'])
def psycho_write():
    if request.method == 'POST':
        email = request.form['email']
        uid = session.get('user_id')
        if not uid:
            if 'localhost' not in request.host and '127.0.0.1' not in request.host:
                if not session.get('email_verified_for_psycho'):
                    return "<script>alert('이메일 인증을 먼저 완료해 주세요.'); history.back();</script>"
                if session.get('verify_email') != email:
                    return "<script>alert('인증된 이메일과 일치하지 않습니다.'); history.back();</script>"
        title = request.form['title']
        content = request.form['content']
        if uid:
            pw_hash = generate_password_hash('')
        else:
            pw_hash = generate_password_hash(request.form.get('password',''))
        author_name = request.form.get('author_name', '익명') or '익명'
        post = PsychoPost(title=title, content=content, password=pw_hash, email=email, author_name=author_name, user_id=uid)
        try:
            ai_res = call_ai_judge(title, content)
            post.ai_score = ai_res.get('score', 0)
            post.ai_reason = ai_res.get('reason', '')
            if post.ai_score < -20:
                post.status = 'flagged'
        except:
            pass
        if uid:
            user_obj = User.query.get(uid)
            if user_obj and (user_obj.points or 0) >= 100:
                add_points(uid, -100, 'psycho_consult', f'심리상담: {title[:30]}')
            elif user_obj:
                return "<script>alert('닢이 부족합니다 (100닢 필요).'); history.back();</script>"
        db.session.add(post)
        db.session.commit()
        from services.email_service import EmailService
        admins = User.query.filter(User.role.in_(['admin','leader'])).all()
        for admin in admins:
            try:
                EmailService.send(admin.email, f'[심리상담] {title}',
                    f'작성자: {author_name}\n이메일: {email}\n제목: {title}\n내용: {content[:500]}')
            except:
                pass
        session.pop('email_verified_for_psycho', None)
        session.pop('verify_email', None)
        return "<script>alert('상담 글이 등록되었습니다.'); location.href='/psycho/list';</script>"
    return _serve_spa()

@psycho_bp.route('/psycho/post/<int:post_id>', methods=['GET', 'POST'])
def psycho_post(post_id):
    post = PsychoPost.query.get_or_404(post_id)
    uid = session.get('user_id')
    role = session.get('role','')
    is_author = uid and post.user_id == uid
    is_admin = role in ('admin','leader')
    if request.method == 'POST':
        if is_author or is_admin or check_password_hash(post.password, request.form.get('password','')):
            return _serve_spa()
        return _serve_spa()
    if is_author or is_admin:
        return _serve_spa()
    if session.get('email_verified_for_legal') and session.get('verify_email') == post.email:
        return _serve_spa()
    return _serve_spa()

@psycho_bp.route('/psycho/post/<int:post_id>/edit', methods=['GET','POST'])
def psycho_post_edit(post_id):
    post = PsychoPost.query.get_or_404(post_id)
    uid = session.get('user_id')
    role = session.get('role','')
    if not uid or (post.user_id != uid and role not in ('admin','leader')):
        return "<script>alert('수정 권한이 없습니다.'); history.back();</script>"
    if post.viewed_at and role not in ('admin','leader'):
        return "<script>alert('관리자가 확인한 글은 수정할 수 없습니다.'); history.back();</script>"
    if request.method == 'POST':
        post.title = request.form.get('title', post.title)
        post.content = request.form.get('content', post.content)
        try:
            ai_res = call_ai_judge(post.title, post.content)
            post.ai_score = ai_res.get('score', 0)
            post.ai_reason = ai_res.get('reason', '')
            post.status = 'flagged' if post.ai_score < -20 else 'pending'
        except:
            pass
        db.session.commit()
        return redirect(url_for('psycho_post', post_id=post.id))
    return _serve_spa()

@psycho_bp.route('/psycho/admin')
def psycho_admin():
    if session.get('role') not in ('admin', 'leader'):
        return "<script>alert('관리자 전용입니다.'); location.href='/service/psycho';</script>"
    pending_posts = PsychoPost.query.filter_by(answer=None).order_by(PsychoPost.created_at.desc()).all()
    answered_posts = PsychoPost.query.filter(PsychoPost.answer.isnot(None)).order_by(PsychoPost.answered_at.desc()).all()
    return _serve_spa()

@psycho_bp.route('/psycho/admin/appointments')
def psycho_admin_appointments():
    if session.get('role') not in ('admin', 'leader'):
        return "<script>alert('관리자 전용입니다.'); location.href='/service/psycho';</script>"
    pending_appts = PsychoAppointment.query.filter_by(status='pending').order_by(PsychoAppointment.created_at.desc()).all()
    approved_appts = PsychoAppointment.query.filter_by(status='approved').order_by(PsychoAppointment.date.desc()).all()
    schedule_rows = PsychoDoctorSchedule.query.all()
    schedules = {str(s.day_of_week): {'is_available': s.is_available, 'start_hour': s.start_hour, 'end_hour': s.end_hour, 'slot_hours': s.slot_hours} for s in schedule_rows}
    gc = PsychoGoogleCalendarConfig.query.first()
    return _serve_spa()

@psycho_bp.route('/psycho/admin/answer/<int:post_id>', methods=['POST'])
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
        f"문의하신 '{post.title}'에 대한 답변이 등록되었습니다.\n\n{request.host_url}psycho/post/{post.id}")
    admins = User.query.filter(User.role.in_(['admin','leader'])).all()
    for admin in admins:
        try:
            EmailService.send(admin.email, f'[심리상담 답변] {post.title}',
                f'{session.get("username","")}님이 답변을 등록했습니다.\n\n{request.host_url}psycho/admin')
        except:
            pass
    return "<script>alert('답변이 등록되었습니다.'); location.href='/psycho/admin';</script>"

@psycho_bp.route('/psycho/admin/appointment/<int:appt_id>/approve', methods=['POST'])
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
        f"심리상담 예약이 승인되었습니다.\n\n일시: {appt.date} {appt.time_slot}\n\n{request.host_url}psycho/schedule")
    admins = User.query.filter(User.role.in_(['admin','leader'])).all()
    for admin in admins:
        try:
            EmailService.send(admin.email, f'[심리상담 예약승인] {appt.content[:30]}',
                f'{session.get("username","")}님이 예약을 승인했습니다.\n\n{request.host_url}psycho/admin/appointments')
        except:
            pass
    return "<script>alert('예약이 승인되었습니다.'); location.href='/psycho/admin/appointments';</script>"

@psycho_bp.route('/psycho/admin/appointment/<int:appt_id>/reject', methods=['POST'])
def psycho_appointment_reject(appt_id):
    if session.get('role') not in ('admin', 'leader'):
        return "<script>alert('권한 없음'); history.back();</script>"
    appt = PsychoAppointment.query.get_or_404(appt_id)
    appt.status = 'rejected'
    db.session.commit()
    return "<script>alert('예약이 거절되었습니다.'); location.href='/psycho/admin/appointments';</script>"

@psycho_bp.route('/psycho/admin/schedule', methods=['POST'])
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
    return "<script>alert('상담시간이 저장되었습니다.'); location.href='/psycho/admin/appointments';</script>"

@psycho_bp.route('/psycho/admin/google-calendar', methods=['POST'])
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
    return f"<script>alert('{msg}'); location.href='/psycho/admin/appointments';</script>"

@psycho_bp.route('/psycho/schedule')
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
    for i in range(2, 62):
        d = today + timedelta(days=i)
        if d.weekday() in available_day_ids and d not in booked_dates:
            available_dates.append(d.isoformat())
    all_slots = []
    for s in schedule_rows:
        for h in range(s.start_hour, s.end_hour, s.slot_hours):
            all_slots.append(f"{h:02d}:00-{h+s.slot_hours:02d}:00")
    uid = session.get('user_id')
    my_appointments = []
    if uid:
        my_appointments = PsychoAppointment.query.filter_by(user_id=uid).order_by(PsychoAppointment.date.desc()).limit(10).all()
    return _serve_spa()

# --- API endpoints ---

@psycho_bp.route('/api/psycho/posts')
def api_psycho_posts():
    uid = session.get('user_id')
    if not uid: return jsonify({'error': 'login'}), 401
    posts = PsychoPost.query.filter_by(user_id=uid).order_by(PsychoPost.created_at.desc()).limit(20).all()
    return jsonify([{
        'id': p.id, 'title': p.title, 'author_name': p.author_name,
        'status': p.status, 'is_public': p.is_public,
        'answer': p.answer, 'fee': p.fee,
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'answered_at': p.answered_at.isoformat() if p.answered_at else None,
    } for p in posts])

@psycho_bp.route('/api/psycho/post/<int:post_id>')
def api_psycho_post(post_id):
    post = PsychoPost.query.get_or_404(post_id)
    return jsonify({
        'id': post.id, 'title': post.title, 'content': post.content,
        'author_name': post.author_name, 'answer': post.answer,
        'status': post.status, 'is_public': post.is_public,
        'fee': post.fee, 'travel_allowance': post.travel_allowance,
        'ai_score': post.ai_score, 'ai_reason': post.ai_reason,
        'created_at': post.created_at.isoformat() if post.created_at else None,
        'answered_at': post.answered_at.isoformat() if post.answered_at else None,
    })

@psycho_bp.route('/api/psycho/appointments')
def api_psycho_appointments():
    uid = session.get('user_id')
    if not uid: return jsonify({'error': 'login'}), 401
    appts = PsychoAppointment.query.filter_by(user_id=uid).order_by(PsychoAppointment.date.desc()).limit(20).all()
    return jsonify([{
        'id': a.id, 'name': a.name, 'date': a.date.isoformat() if a.date else None,
        'time_slot': a.time_slot, 'status': a.status, 'location': a.location,
    } for a in appts])

@psycho_bp.route('/api/psycho/create', methods=['POST'])
def api_psycho_create():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    if not title or not content:
        return jsonify({'status': 'error', 'msg': '제목과 내용을 입력하세요.'})
    post = PsychoPost(
        title=title, content=content,
        author_name=request.form.get('author_name', '익명'),
        email=request.form.get('email', ''),
        password=request.form.get('password', ''),
        user_id=session.get('user_id'),
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({'status': 'success', 'id': post.id})

@psycho_bp.route('/api/psycho/post/<int:post_id>/comment', methods=['POST'])
def api_psycho_comment(post_id):
    content = request.form.get('content', '').strip()
    if not content:
        return jsonify({'status': 'error', 'msg': '내용을 입력하세요.'})
    post = PsychoPost.query.get_or_404(post_id)
    comments = post.comments or ''
    name = session.get('real_name') or session.get('username', '익명')
    from datetime import datetime
    comments += f'\n[{name}] {content} ({datetime.now().strftime("%m/%d %H:%M")})'
    post.comments = comments
    db.session.commit()
    return jsonify({'status': 'success'})

@psycho_bp.route('/api/psycho/schedules')
def api_psycho_schedules():
    from datetime import date, timedelta
    rows = PsychoDoctorSchedule.query.filter_by(is_available=True).all()
    available_day_ids = {s.day_of_week for s in rows}
    booked = db.session.query(PsychoAppointment.date).filter(PsychoAppointment.status.in_(['pending', 'approved'])).distinct().all()
    booked_dates = {b[0] for b in booked}
    available_dates = []
    today = date.today()
    for i in range(2, 62):
        d = today + timedelta(days=i)
        if d.weekday() in available_day_ids and d not in booked_dates:
            available_dates.append(d.isoformat())
    all_slots = []
    for s in rows:
        for h in range(s.start_hour, s.end_hour, s.slot_hours):
            all_slots.append({"start": f"{h:02d}:00", "end": f"{h+s.slot_hours:02d}:00"})
    return jsonify({'available_dates': available_dates, 'time_slots': all_slots})

# --- 기존 라우트 ---

@psycho_bp.route('/psycho/appointment/book', methods=['POST'])
def psycho_appointment_book():
    name = request.form['name']
    email = request.form['email']
    from models import BlockedEmail
    if BlockedEmail.query.filter_by(email=email).first():
        return "<script>alert('이 이메일은 예약이 제한되었습니다.'); history.back();</script>"
    phone = request.form.get('phone', '')
    date_str = request.form['date']
    time_slot = request.form['time_slot']
    title = request.form.get('title', '심리상담')
    from datetime import date
    appt_date = date.fromisoformat(date_str)
    if appt_date <= date.today() + timedelta(days=1):
        return "<script>alert('이틀 후부터 예약 가능합니다.'); history.back();</script>"
    uid = session.get('user_id')
    if uid:
        conflict = TongBotSchedule.query.filter(
            TongBotSchedule.user_id == uid,
            db.func.date(TongBotSchedule.event_date) == appt_date
        ).first()
        if conflict:
            return "<script>alert('해당 날짜에 통벗 일정이 있습니다. 상담 예약이 불가능합니다.'); history.back();</script>"
    location_parts = [request.form.get('location', ''), request.form.get('location_detail', '')]
    location = ' '.join(p for p in location_parts if p)
    content = request.form.get('content', '')
    appt = PsychoAppointment(
        user_id=uid, name=name, email=email, phone=phone,
        date=appt_date,
        time_slot=time_slot, location=location, content=content
    )
    db.session.add(appt)
    db.session.commit()
    from services.email_service import EmailService
    admins = User.query.filter(User.role.in_(['admin','leader'])).all()
    for admin in admins:
        try:
            EmailService.send(admin.email, f'[심리상담 예약] {title}',
                f'신청자: {name}\n이메일: {email}\n연락처: {phone}\n날짜: {date_str} {time_slot}\n장소: {location}\n내용: {content}')
        except:
            pass
    return "<script>alert('예약이 신청되었습니다. 승인 후 이메일로 안내드립니다.'); location.href='/service/psycho';</script>"


