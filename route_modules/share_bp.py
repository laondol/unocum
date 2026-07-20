import os
import threading
import base64
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app, send_file, send_from_directory
from datetime import datetime, timedelta
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from models import db, User, ShareReport, ShareComment, Message, Post, Comment, NewsArticle, VillagePage, RampApplication, PointHistory, Friend, VillageWish, LegalPost, ChatMessage, FriendGroup, LegalAppointment, TongBot, TongBotDraft, ConstructionNotice, GpsCalibration, StoreSuggestion, StoreMenu
from services.security import save_village_file
from services.ai_service import background_process_share, moderate_image
from services.geocode import haversine, gps_to_town_village, get_nearby_reports, is_in_yangpyeong, YANGPYEONG_BOUNDS, YANGPYEONG_VILLAGES
from route_modules.construction_bp import _resolve_canonical_store_name
import requests as _requests

share_bp = Blueprint('share', __name__)


def _serve_react_share():
    react_index = os.path.join(current_app.root_path, 'frontend', 'dist', 'index.html')
    if os.path.exists(react_index):
        return send_file(react_index)
    return render_template('intro.html')

_react_dist = None  # computed per-request

@share_bp.route('/assets/<path:filename>')
def react_assets(filename):
    react_dist = os.path.join(current_app.root_path, 'frontend', 'dist')
    return send_from_directory(os.path.join(react_dist, 'assets'), filename)

@share_bp.route('/favicon.svg')
def react_favicon():
    react_dist = os.path.join(current_app.root_path, 'frontend', 'dist')
    return send_from_directory(react_dist, 'favicon.svg')

@share_bp.route('/share')
@share_bp.route('/share/report')
@share_bp.route('/share/detail/<path:path>')
@share_bp.route('/share/edit/<path:path>')
def share_spa(path=''):
    return _serve_react_share()

@share_bp.route('/share-report', methods=['GET', 'POST'])
def share_report():
    if request.method == 'GET':
        return redirect('/share/report')
    user = User.query.get(session.get('user_id')) if session.get('username') else None
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    latitude = request.form.get('latitude', type=float)
    longitude = request.form.get('longitude', type=float)

    if not latitude or not longitude:
        return jsonify({"status": "error", "msg": "위치 수집이 필요합니다. 새로고침 후 위치 허용해주세요."}), 400

    from services.geocode import calibrate_gps
    latitude, longitude = calibrate_gps(latitude, longitude)

    from services.security import validate_upload, secure_save
    image_paths = []
    img_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'share_reports')
    if not os.path.exists(img_dir): os.makedirs(img_dir)

    for file in request.files.getlist('image'):
        ok, msg = validate_upload(file)
        if ok:
            try:
                path = secure_save(file, img_dir)
                image_paths.append(path)
            except Exception:
                pass

    image_path = image_paths[0] if image_paths else None
    extra_images = ','.join(image_paths[1:]) if len(image_paths) > 1 else ''

    drawing_path = None
    drawing = request.form.get('drawing_data')
    if drawing and len(drawing) > 2000:
        data = base64.b64decode(drawing.split(",")[1])
        fname = f"draw_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        target_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'share_reports')
        if not os.path.exists(target_dir): os.makedirs(target_dir)
        with open(os.path.join(target_dir, fname), "wb") as f: f.write(data)
        drawing_path = f"/static/uploads/share_reports/{fname}"

    video_path = None
    if 'video' in request.files:
        file = request.files['video']
        if file and file.filename and '.' in file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower()
            if ext in ('mp4', 'avi', 'mov', 'mkv', 'webm'):
                img_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'share_reports')
                fname = f"video_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
                file.save(os.path.join(img_dir, fname))
                video_path = f"/static/uploads/share_reports/{fname}"

    from services.geocode import gps_to_town_village
    resolved_town, resolved_village = gps_to_town_village(latitude, longitude)
    share_town = resolved_town or (user.town if user else '')
    share_village = resolved_village or (user.village if user else '')
    share_address = f"경기도 양평군 {share_town} {share_village}".strip()

    report = ShareReport(
        user_id=user.id if user else 0,
        author_name=user.username if user else '익명',
        title=title or '공유',
        description=description,
        image_path=image_path,
        extra_images=extra_images,
        drawing_path=drawing_path,
        video_path=video_path,
        latitude=latitude,
        longitude=longitude,
        town=share_town,
        village=share_village,
        address=share_address,
        ai_category='분석중',
        ai_summary='',
        ai_confidence=0.5,
        ai_region_news='',
        ai_news_links='[]',
        ai_danger_alert=False
    )
    if video_path:
        report.status = 'pending_review'
        report.moderation_result = 'video'
        report.moderation_reason = '동영상은 승인 후 공개됩니다'
    else:
        # 모든 공유는 기본 보류. AI가 백그라운드에서 검증 후 독단 승인/보류 결정
        report.status = 'pending'
        report.moderation_result = 'pending'
        report.moderation_reason = 'AI 검증 대기중'
    report.is_moderated = False
    db.session.add(report)
    db.session.commit()

    app_obj = current_app._get_current_object()
    uid = user.id if user else 0
    threading.Thread(target=background_process_share,
        args=(app_obj, report.id, title, description, latitude, longitude, image_path, drawing_path, uid)).start()

    return jsonify({"status": "success", "msg": "공유가 접수되었습니다.", "report_id": report.id})

@share_bp.route('/admin/share-reports')
def admin_share_reports():
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    filter_type = request.args.get('filter', 'all')
    base = ShareReport.query
    if filter_type == 'unmoderated':
        base = base.filter(db.or_(ShareReport.is_moderated == False, ShareReport.is_moderated == None))
    elif filter_type == 'moderated':
        base = base.filter(ShareReport.is_moderated == True)
    reports = base.order_by(ShareReport.created_at.desc()).all()
    
    danger_reports = [r for r in reports if r.ai_danger_alert]
    
    total_all = ShareReport.query.count()
    return render_template('admin_share_reports.html', 
        reports=reports, 
        danger_reports=danger_reports,
        filter_type=filter_type,
        total_all=total_all)

@share_bp.route('/admin/ramp-applications')
def admin_ramp_applications():
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    apps = RampApplication.query.order_by(RampApplication.created_at.desc()).all()
    return render_template('admin_ramp_applications.html', apps=apps)

@share_bp.route('/admin/message/send', methods=['GET', 'POST'])
def admin_message_send():
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    if request.method == 'POST':
        send_type = request.form.get('send_type', 'all')
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        if not content:
            return jsonify({'status':'error', 'msg':'내용을 입력하세요.'})
        recipients = []
        if send_type == 'all':
            recipients = User.query.filter(User.role.notin_(['admin', 'leader'])).all()
        elif send_type == 'individual':
            receiver_id = request.form.get('receiver_id', type=int)
            if receiver_id:
                user = User.query.get(receiver_id)
                if user:
                    recipients = [user]
        elif send_type == 'town':
            town = request.form.get('town', '')
            if town:
                recipients = User.query.filter(
                    db.or_(User.reg_town == town, User.curr_town == town),
                    User.role.notin_(['admin', 'leader'])
                ).all()
        elif send_type == 'village':
            town = request.form.get('town', '')
            village = request.form.get('village', '')
            if town and village:
                recipients = User.query.filter(
                    db.or_(
                        db.and_(User.reg_town == town, User.reg_village == village),
                        db.and_(User.curr_town == town, User.curr_village == village)
                    ),
                    User.role.notin_(['admin', 'leader'])
                ).all()
        elif send_type == 'group':
            group_id = request.form.get('group_id', type=int)
            if group_id:
                members = Friend.query.filter_by(group_id=group_id, status='accepted').all()
                recipient_ids = set()
                for m in members:
                    if m.user_id != session['user_id']:
                        recipient_ids.add(m.user_id)
                    if m.friend_id != session['user_id']:
                        recipient_ids.add(m.friend_id)
                recipients = User.query.filter(User.id.in_(recipient_ids)).all()
        if not recipients:
            return jsonify({'status':'error', 'msg':'발송 대상을 찾을 수 없습니다.'})
        sender = User.query.get(session['user_id'])
        total_cost = len(recipients) * 10
        if sender.points < total_cost:
            return jsonify({'status':'error', 'msg':f'닢이 부족합니다. (필요: {total_cost}닢, 보유: {sender.points}닢)'})
        sender.points -= total_cost
        ph = PointHistory(user_id=sender.id, change_type='message', amount=-total_cost, balance_after=sender.points, description=f'관리자 대량 쪽지 발송 ({len(recipients)}명)')
        db.session.add(ph)
        for user in recipients:
            msg = Message(
                sender_id=sender.id,
                sender_name=sender.username,
                sender_role=sender.role or 'admin',
                receiver_id=user.id,
                subject=subject or '(제목 없음)',
                content=content
            )
            db.session.add(msg)
        db.session.commit()
        return jsonify({'status':'success', 'msg':f'{len(recipients)}명에게 쪽지를 발송했습니다. ({total_cost}닢 차감)'})
    towns = list(YANGPYEONG_BOUNDS.keys())
    villages = YANGPYEONG_VILLAGES
    groups = FriendGroup.query.filter_by(user_id=session['user_id']).all()
    users = User.query.order_by(User.real_name, User.username).all()
    return render_template('admin_message.html', towns=towns, villages=villages, groups=groups, users=users)

@share_bp.route('/leader/share-reports')
def leader_share_reports():
    if session.get('role') not in ['admin', 'leader']:
        return "권한 없음", 403
    user = User.query.get(session['user_id'])
    reports = ShareReport.query.filter_by(town=user.town, village=user.village).order_by(ShareReport.created_at.desc()).all()
    return render_template('leader_share_reports.html', reports=reports, town=user.town, village=user.village)

@share_bp.route('/share-report/edit/<int:report_id>', methods=['GET', 'POST'])
def share_report_edit(report_id):
    report = ShareReport.query.get_or_404(report_id)
    try:
        with open('/tmp/edit_dbg.log', 'a') as _df:
            _df.write(f"HIT edit {report_id} | method={request.method} uid={session.get('user_id')} files={list(request.files.keys())} image_count={len(request.files.getlist('image'))} replace_blob={len(request.files.getlist('replace_blob'))} form_keys={list(request.form.keys())}\n")
            _df.flush()
    except Exception:
        pass
    is_admin = session.get('role') in ['admin', 'leader']
    is_author = report.user_id == session.get('user_id')
    is_anonymous_share = not report.user_id or report.user_id == 0
    if not (is_author or (is_admin and is_anonymous_share)):
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    if request.method == 'POST':
        try:
            with open('/tmp/edit_dbg.log', 'a') as _f:
                _f.write('EDIT req: replace_rotate=%r rotate_angle_keys=%r replace_image=%r\n' % (
                    request.form.getlist('replace_rotate'),
                    [k for k in request.form if k.startswith('rotate_angle_')],
                    request.form.getlist('replace_image')[:3]))
        except Exception:
            pass
        report.title = request.form.get('title', '').strip()
        report.description = request.form.get('description', '').strip()
        # AI 추천 카테고리 (기본값 채움, 회원 수정 가능)
        cat = request.form.get('ai_category', '').strip()
        if cat:
            report.ai_category = cat
        # 하위 분류(가게 메뉴 카테고리 등)
        sub = request.form.get('sub_category', '').strip()
        if sub:
            report.sub_category = sub
        # 가게 연결 (store_suggestion_id)
        ssid = request.form.get('store_suggestion_id', type=int)
        if ssid:
            report.store_suggestion_id = ssid
        # 기존 사진 삭제 처리
        delete_imgs = request.form.getlist('delete_image')
        if delete_imgs:
            def _norm(p): return p.strip() if p else ''
            existing = []
            if report.image_path: existing.append(_norm(report.image_path))
            if report.extra_images:
                existing += [_norm(e) for e in report.extra_images.split(',') if e.strip()]
            kept = [e for e in existing if e not in delete_imgs]
            # 실제 파일 삭제
            import os as _os
            for d in delete_imgs:
                try:
                    fp = _os.path.join(current_app.root_path, d.lstrip('/'))
                    if _os.path.exists(fp): _os.remove(fp)
                except Exception:
                    pass
            report.image_path = kept[0] if kept else ''
            report.extra_images = ','.join(kept[1:]) if len(kept) > 1 else ''
        
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)
        if latitude and longitude:
            original_lat = request.form.get('original_lat', type=float)
            original_lon = request.form.get('original_lon', type=float)
            report.latitude = latitude
            report.longitude = longitude
            resolved_town, resolved_village = gps_to_town_village(latitude, longitude)
            if not resolved_town:
                from services.geocode import _fallback_lookup
                resolved_town, resolved_village = _fallback_lookup(latitude, longitude)
            if resolved_town:
                report.town = resolved_town
            if resolved_village:
                report.village = resolved_village
            report.address = f"경기도 양평군 {report.town} {report.village}".strip()
            # 사용자가 마커를 드래그해서 위치 보정한 경우 → GPS 보정값 누적
            if original_lat and original_lon and (abs(original_lat - latitude) > 1e-8 or abs(original_lon - longitude) > 1e-8):
                try:
                    from models import GpsCalibration
                    cal_town = resolved_town or report.town or ''
                    cal_village = resolved_village or report.village or ''
                    cal = GpsCalibration.query.filter_by(town=cal_town, village=cal_village).first()
                    if not cal and cal_village:
                        cal = GpsCalibration.query.filter_by(town=cal_town).order_by(GpsCalibration.sample_count.desc()).first()
                    delta_lat = latitude - original_lat
                    delta_lon = longitude - original_lon
                    if cal:
                        cal.offset_lat += delta_lat / (cal.sample_count + 1)
                        cal.offset_lon += delta_lon / (cal.sample_count + 1)
                        cal.sample_count += 1
                    else:
                        cal = GpsCalibration(
                            town=cal_town or '',
                            village=cal_village or '',
                            offset_lat=delta_lat,
                            offset_lon=delta_lon,
                            sample_count=1
                        )
                        db.session.add(cal)
                except:
                    pass
        
        # 기존 사진 재편집 처리 (replace_image: "oldpath||blobname", replace_blob: File)
        from services.security import validate_upload, secure_save
        replace_pairs = request.form.getlist('replace_image')
        if replace_pairs:
            img_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'share_reports')
            if not os.path.exists(img_dir): os.makedirs(img_dir)
            blobs = request.files.getlist('replace_blob')
            blob_map = {b.filename: b for b in blobs}
            for pair in replace_pairs:
                if '||' not in pair:
                    continue
                old_path, blobname = pair.split('||', 1)
                blob = blob_map.get(blobname)
                if not blob:
                    continue
                try:
                    ok, msg = validate_upload(blob)
                    if ok:
                        new_rel = secure_save(blob, img_dir)
                        # DB 필드에서 old_path 교체
                        if report.image_path == old_path:
                            report.image_path = new_rel
                        elif report.extra_images:
                            parts = [p.strip() for p in report.extra_images.split(',') if p.strip()]
                            if old_path in parts:
                                parts[parts.index(old_path)] = new_rel
                                report.extra_images = ','.join(parts)
                        # 실제 구 파일 삭제
                        try:
                            old_abs = os.path.join(current_app.root_path, old_path.lstrip('/'))
                            if os.path.exists(old_abs): os.remove(old_abs)
                        except Exception:
                            pass
                except Exception:
                    pass

        # 기존 사진 회전 편집 처리 (replace_rotate: "oldpath||angle") - 서버 Pillow 1회 적용
        from PIL import Image as _PILImage
        replace_rotations = request.form.getlist('replace_rotate')
        try:
            with open('/tmp/edit_dbg.log', 'a') as _f:
                _f.write('RR_START replace_rotate=%r count=%d\n' % (replace_rotations, len(replace_rotations)))
        except Exception:
            pass
        for pair in replace_rotations:
            if '||' not in pair:
                continue
            old_path, angle_s = pair.split('||', 1)
            try:
                angle = int(angle_s)
            except Exception:
                continue
            if angle not in (90, 180, 270):
                continue
            try:
                abs_path = os.path.join(current_app.root_path, old_path.lstrip('/'))
                exists = os.path.exists(abs_path)
                try:
                    with open('/tmp/edit_dbg.log', 'a') as _f:
                        _f.write('RR_TRY path=%s abs=%s exists=%s angle=%s\n' % (old_path, abs_path, exists, angle))
                except Exception:
                    pass
                if not exists:
                    continue
                im = _PILImage.open(abs_path).convert('RGB').rotate(angle, expand=True)
                im.save(abs_path, format='JPEG', optimize=True)
                try:
                    with open('/tmp/edit_dbg.log', 'a') as _f:
                        _f.write('ROTATED %s by %s -> %s\n' % (old_path, angle, im.size))
                except Exception:
                    pass
            except Exception as _e:
                try:
                    with open('/tmp/edit_dbg.log', 'a') as _f:
                        _f.write('RR_FAIL %s: %s\n' % (old_path, _e))
                except Exception:
                    pass

        # 새 이미지 업로드 처리
        from services.security import validate_upload, secure_save
        new_paths = []
        img_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'share_reports')
        if not os.path.exists(img_dir): os.makedirs(img_dir)
        rotate_angles = {}
        for k, v in request.form.items():
            if k.startswith('rotate_angle_'):
                try:
                    rotate_angles[k.replace('rotate_angle_', '')] = int(v)
                except Exception:
                    pass
        for idx, file in enumerate(request.files.getlist('image')):
            ok, msg = validate_upload(file)
            if ok:
                try:
                    path = secure_save(file, img_dir)
                    angle = rotate_angles.get(str(idx))
                    if angle in (90, 180, 270):
                        try:
                            ap = os.path.join(current_app.root_path, path.lstrip('/'))
                            _im = _PILImage.open(ap).convert('RGB')
                            _im = _im.rotate(angle, expand=True)
                            _im.save(ap, format='JPEG', optimize=True)
                        except Exception:
                            pass
                    new_paths.append(path)
                except Exception:
                    pass
        
        if new_paths:
            # 기존 이미지 목록
            existing = []
            if report.image_path: existing.append(report.image_path)
            if report.extra_images:
                existing += [e.strip() for e in report.extra_images.split(',') if e.strip()]
            existing += new_paths
            report.image_path = existing[0]
            report.extra_images = ','.join(existing[1:]) if len(existing) > 1 else ''
            
            # AI 검사 (새 이미지만)
            from services.ai_service import moderate_image
            for np in new_paths:
                try:
                    abs_path = os.path.join(current_app.root_path, np.lstrip('/'))
                    flagged, reason, cat = moderate_image(abs_path)
                    if cat == 'unanalyzable':
                        report.status = 'pending'
                        report.moderation_result = 'unanalyzable'
                        report.moderation_reason = reason
                        report.is_moderated = True
                        report.moderation_at = datetime.now()
                        break
                    if flagged:
                        report.status = 'pending_person' if cat == 'person' else 'flagged'
                        report.moderation_result = cat
                        report.moderation_reason = reason
                        report.is_moderated = True
                        report.moderation_at = datetime.now()
                        break
                except:
                    pass

        # 메뉴 AI 분류 저장 (menu_text -> StoreMenu)
        menu_text = request.form.get('menu_text', '').strip()
        if menu_text:
            # 기존 메뉴 초기화 후 재저장
            StoreMenu.query.filter_by(place_id=(report.store_suggestion_id and str(report.store_suggestion_id) or None)).delete()
            lines = [l.strip() for l in menu_text.split('\n') if l.strip()]
            if lines:
                try:
                    r = _requests.post('https://api.groq.com/openai/v1/chat/completions',
                        headers={'Authorization': 'Bearer ' + current_app.config.get('GROQ_API_KEY',''), 'Content-Type': 'application/json'},
                        json={'model': 'llama-3.1-8b-instant',
                              'messages': [{'role': 'user', 'content':
                                '다음 메뉴 항목 각각을 "식사","음료","디저트","기타" 중 하나로 분류하세요. '
                                '각 항목 앞에 라벨을 붙여 줄바꿈으로 출력하세요.\n' + '\n'.join(lines)}],
                              'temperature': 0}, timeout=20)
                    out = r.json()['choices'][0]['message']['content']
                    labels = []
                    for line in out.splitlines():
                        if line.strip().startswith('식사'): labels.append('식사')
                        elif line.strip().startswith('음료'): labels.append('음료')
                        elif line.strip().startswith('디저트'): labels.append('디저트')
                        else: labels.append('기타')
                except Exception:
                    labels = ['기타'] * len(lines)
                for i, l in enumerate(lines):
                    db.session.add(StoreMenu(
                        store_suggestion_id=report.store_suggestion_id,
                        place_id=(report.store_suggestion_id and str(report.store_suggestion_id) or None),
                        name=l, sub_category=(labels[i] if i < len(labels) else '기타'), ai_generated=True))

        db.session.commit()
        return jsonify({"status": "success", "msg": "수정되었습니다."})
    return render_template('share_report_edit.html', report=report)

@share_bp.route('/share-report/delete-image/<int:report_id>', methods=['POST'])
def share_report_delete_image(report_id):
    report = ShareReport.query.get_or_404(report_id)
    is_admin = session.get('role') in ['admin', 'leader']
    is_author = report.user_id == session.get('user_id')
    is_anonymous_share = not report.user_id or report.user_id == 0
    if not (is_author or (is_admin and is_anonymous_share)):
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    data = request.get_json()
    path = data.get('image_path', '')
    if not path:
        return jsonify({"status": "error", "msg": "경로 없음"}), 400
            
    paths = [report.image_path] + (report.extra_images.split(',') if report.extra_images else [])
    if path not in paths:
        return jsonify({"status": "error", "msg": "해당 사진이 없습니다"}), 400
    if len(paths) <= 1:
        return jsonify({"status": "error", "msg": "최소 1장은 남겨야 합니다"}), 400
            
    paths.remove(path)
    report.image_path = paths[0]
    report.extra_images = ','.join(paths[1:]) if len(paths) > 1 else ''
    db.session.commit()
            
        # 실제 파일 삭제
    abs_path = os.path.join(current_app.root_path, path.lstrip('/'))
    if os.path.exists(abs_path):
        os.remove(abs_path)
            
    return jsonify({"status": "success", "msg": "삭제되었습니다."})

@share_bp.route('/api/share/reports')
def api_share_reports():
    town = request.args.get('town', '')
    village = request.args.get('village', '')
    category = request.args.get('category', '')
    uid = session.get('user_id')
    
    if uid:
        query = ShareReport.query.filter(
            db.or_(ShareReport.status == 'approved', ShareReport.user_id == uid)
        )
    else:
        query = ShareReport.query.filter_by(status='approved')
    if town: query = query.filter_by(town=town)
    if village: query = query.filter_by(village=village)
    if category: query = query.filter_by(ai_category=category)
    
    reports = query.order_by(ShareReport.created_at.desc()).limit(50).all()
    return jsonify([{
        "id": r.id, "title": r.title, "description": r.description,
        "image_path": r.image_path, "drawing_path": r.drawing_path,
        "video_path": r.video_path, "latitude": r.latitude,
        "longitude": r.longitude, "town": r.town, "village": r.village,
        "address": r.address, "author_name": r.author_name,
        "ai_category": r.ai_category, "ai_summary": r.ai_summary,
        "like_count": r.like_count, "dislike_count": r.dislike_count,
        "status": r.status, "user_id": r.user_id,
        "created_at": r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else None
    } for r in reports])

@share_bp.route('/api/share/towns')
def api_share_towns():
    town = request.args.get('town', '')
    query = ShareReport.query.filter_by(status='approved')
    base = query
    if town:
        villages = base.filter_by(town=town).with_entities(ShareReport.village).distinct().all()
        villages = [v[0] for v in villages if v[0]]
        return jsonify({"villages": villages})
    towns = base.with_entities(ShareReport.town).distinct().all()
    towns = [t[0] for t in towns if t[0]]
    return jsonify({"towns": towns})

@share_bp.route('/share/map')
def share_map():
    category = request.args.get('category', '')
    role = session.get('role', '')
    if role in ('admin', 'leader'):
        query = ShareReport.query
    else:
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

@share_bp.route('/share/nearby')
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

@share_bp.route('/share-report/toggle/<int:report_id>/<string:action>', methods=['GET', 'POST'])
def share_report_toggle(report_id, action):
    if session.get('role') not in ['admin', 'leader']:
        return jsonify({"status":"error","msg":"권한 없음"}), 403
    report = ShareReport.query.get_or_404(report_id)
    if action == 'approve':
        report.status = 'approved'
        _resolve_canonical_store_name(report)
        report.updated_at = datetime.now()
    elif action == 'reject':
        report.status = 'rejected'
        report.updated_at = datetime.now()
        # AI 학습: rejected 이미지는 AI가 다시 참고하도록 기록
        report.moderation_reason = (report.moderation_reason or '') + ' | 관리자 반려'
        # 작성자(회원)에게 보류 통보
        try:
            if report.user_id and report.user_id != 0:
                admin_user = User.query.filter(User.role == 'admin').first()
                db.session.add(Message(
                    sender_id=admin_user.id if admin_user else 0,
                    sender_name=admin_user.username if admin_user else '관리자',
                    sender_role='admin',
                    receiver_id=report.user_id,
                    subject='공유가 보류(반려)되었습니다',
                    content=f'회원님이 올리신 공유글(#{report.id})은 관리자/리더에 의해 보류되어 게시되지 않습니다.\n사유: {(report.moderation_reason or "검토 결과 부적합")}'
                ))
        except Exception:
            pass
    db.session.commit()
    if request.method == 'POST':
        return jsonify({"status":"success","action":action})
    return redirect(request.referrer or url_for('admin_share_reports'))

@share_bp.route('/share-report/like/<int:report_id>', methods=['POST'])
def share_report_like(report_id):
    if not session.get('username'):
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    report = ShareReport.query.get_or_404(report_id)
    if report.status != 'approved':
        return jsonify({"status": "error", "msg": "승인된 공유만 평가 가능합니다."}), 403
    report.like_count += 1
    db.session.commit()
    return jsonify({"status": "success", "likes": report.like_count, "dislikes": report.dislike_count})

@share_bp.route('/share-report/dislike/<int:report_id>', methods=['POST'])
def share_report_dislike(report_id):
    if not session.get('username'):
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    report = ShareReport.query.get_or_404(report_id)
    if report.status != 'approved':
        return jsonify({"status": "error", "msg": "승인된 공유만 평가 가능합니다."}), 403
    report.dislike_count += 1
    db.session.commit()
    return jsonify({"status": "success", "likes": report.like_count, "dislikes": report.dislike_count})

@share_bp.route('/share-report/delete/<int:report_id>', methods=['POST'])
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

@share_bp.route('/share-report/accept-person/<int:report_id>')
def share_accept_person(report_id):
    uid = session.get('user_id')
    if not uid:
        return "<script>alert('로그인이 필요합니다.'); location.href='/login';</script>"
    report = ShareReport.query.get_or_404(report_id)
    if report.user_id != uid:
        return "<script>alert('본인의 공유만 동의할 수 있습니다.'); location.href='/main';</script>"
    if report.status != 'pending_person':
        return "<script>alert('현재 상태에서 동의할 수 없습니다.'); location.href='/main';</script>"
    report.moderation_result = 'person_accepted'
    report.status = 'approved'
    _resolve_canonical_store_name(report)
    report.moderation_reason = (report.moderation_reason or '') + ' | 회원 책임 동의함'
    db.session.commit()
    return "<script>alert('✅ 책임 동의가 완료되었습니다. 공유글이 게시되었습니다.'); location.href='/share/detail/"+str(report_id)+"';</script>"

@share_bp.route('/share-report/mosaic/<int:report_id>', methods=['POST'])
def share_mosaic(report_id):
    uid = session.get('user_id')
    if not uid: return jsonify({'status':'error','msg':'로그인 필요'}), 401
    report = ShareReport.query.get_or_404(report_id)
    role = session.get('role', '')
    if report.user_id != uid and role not in ('admin', 'leader'):
        return jsonify({'status':'error','msg':'권한 없음'}), 403
    from services.ai_service import mosaic_image_faces
    img_path = None
    for attr in ['image_path', 'drawing_path']:
        p = getattr(report, attr, None)
        if p:
            abs_p = os.path.join(current_app.root_path, '..', p.lstrip('/')).replace('/', os.sep)
            if os.path.exists(abs_p):
                img_path = abs_p
                break
    if not img_path:
        return jsonify({'status':'error','msg':'모자이크 처리할 이미지가 없습니다.'})
    result = mosaic_image_faces(img_path)
    if result is None:
        return jsonify({'status':'error','msg':'얼굴을 감지할 수 없거나 처리에 실패했습니다.'})
    rel = os.path.relpath(result, os.path.join(current_app.root_path, '..')).replace(os.sep, '/')
    report.image_path = '/' + rel
    report.moderation_result = 'mosaic_applied'
    report.moderation_reason = (report.moderation_reason or '') + ' | AI 모자이크 처리됨'
    report.status = 'pending'
    db.session.commit()
    return jsonify({'status':'success','msg':'AI 모자이크 처리 완료, 재검토 대기 중입니다.'})

# --- [공유 댓글] ---
@share_bp.route('/api/share/report/<int:report_id>')
def api_share_detail(report_id):
    r = ShareReport.query.get_or_404(report_id)
    uid = session.get('user_id')
    
    # 가까운 공유
    nearby_shares = []
    if r.latitude and r.longitude and r.town:
        from services.geocode import haversine
        all_approved = ShareReport.query.filter(
            ShareReport.status == 'approved',
            ShareReport.id != report_id,
            ShareReport.latitude.isnot(None),
            ShareReport.longitude.isnot(None)
        ).all()
        scored = []
        for s in all_approved:
            try:
                d = haversine(r.latitude, r.longitude, s.latitude, s.longitude)
                if d > 20: continue
                scored.append((d, s))
            except: pass
        scored.sort(key=lambda x: x[0])
        nearby_shares = [{"id": s.id, "title": s.title, "town": s.town, "village": s.village, "image_path": s.image_path, "ai_category": s.ai_category, "distance": round(d, 1)} for d, s in scored[:10]]
    
    # 지역 소식
    local_news = []
    local_links = []
    try:
        from services.local_sources import get_local_news, get_quick_links
        local_news = get_local_news(town=r.town, village=r.village)
        local_links = get_quick_links(town=r.town, village=r.village)
    except: pass
    
    # 주변 공사
    nearby_construction = []
    if r.latitude and r.longitude:
        from services.geocode import haversine
        from models import ConstructionNotice
        notices = ConstructionNotice.query.filter_by(is_active=True).all()
        for n in notices:
            if n.latitude and n.longitude:
                if haversine(r.latitude, r.longitude, n.latitude, n.longitude) < 10:
                    nearby_construction.append({"title": n.title, "location": n.location, "notice_type": n.notice_type, "start_date": n.start_date.strftime('%Y-%m-%d') if n.start_date else None, "end_date": n.end_date.strftime('%Y-%m-%d') if n.end_date else None})
    
    # 댓글
    from models import ShareComment
    comments_data = []
    comments = ShareComment.query.filter_by(share_id=report_id, parent_id=None).order_by(ShareComment.created_at.asc()).all()
    for c in comments:
        c_item = {"id": c.id, "author": c.author, "content": c.content, "user_id": c.user_id, "created_at": c.created_at.strftime('%m/%d %H:%M') if c.created_at else None, "replies": []}
        for rc in c.replies:
            c_item["replies"].append({"id": rc.id, "author": rc.author, "content": rc.content, "user_id": rc.user_id, "created_at": rc.created_at.strftime('%m/%d %H:%M') if rc.created_at else None})
        comments_data.append(c_item)
    
    store_menus_data = []
    if r.store_suggestion_id:
        menus = StoreMenu.query.filter_by(store_suggestion_id=r.store_suggestion_id).all()
        store_menus_data = [{"id": m.id, "name": m.name, "price": m.price, "sub_category": m.sub_category, "ai_generated": m.ai_generated} for m in menus]

    return jsonify({
        "id": r.id, "title": r.title, "description": r.description,
        "image_path": r.image_path, "extra_images": r.extra_images,
        "drawing_path": r.drawing_path, "video_path": r.video_path,
        "latitude": r.latitude, "longitude": r.longitude,
        "town": r.town, "village": r.village, "address": r.address,
        "author_name": r.author_name, "user_id": r.user_id,
        "ai_category": r.ai_category, "ai_summary": r.ai_summary,
        "ai_confidence": r.ai_confidence, "ai_region_news": r.ai_region_news,
        "ai_news_links": r.ai_news_links, "ai_danger_alert": r.ai_danger_alert,
        "like_count": r.like_count, "dislike_count": r.dislike_count,
        "status": r.status,
        "created_at": r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else None,
        "moderation_at": r.moderation_at.strftime('%Y-%m-%d') if r.moderation_at else None,
        "store_suggestion_id": r.store_suggestion_id,
        "store_menus": store_menus_data,
        "sub_category": r.sub_category or '',
        "my_role": session.get('role') or '',
        "nearby_shares": nearby_shares,
        "local_news": local_news,
        "local_links": local_links,
        "nearby_construction": nearby_construction,
        "comments": comments_data
    })

@share_bp.route('/api/me')
def api_me():
    uid = session.get('user_id')
    if uid:
        user = User.query.get(uid)
        if user:
            from tongbot_routes import _get_bot
            bot = _get_bot(user.id)
            return jsonify({
                "id": user.id, "username": user.username, "role": user.role,
                "managed_pages": (user.managed_pages or '').split(','),
                "office_latitude": user.office_latitude,
                "office_longitude": user.office_longitude,
                "office_address": user.office_address or '',
                "work_start_time": user.work_start_time or '',
                "temp_address": user.temp_address or '',
                "temp_latitude": user.temp_latitude,
                "temp_longitude": user.temp_longitude,
                "temp_start_date": user.temp_start_date.strftime('%Y-%m-%d') if user.temp_start_date else '',
                "temp_end_date": user.temp_end_date.strftime('%Y-%m-%d') if user.temp_end_date else '',
                "bot": {
                    "bot_name": bot.bot_name, "mood": bot.mood or 'warm',
                    "level": bot.level or 1, "exp": bot.exp or 0,
                    "intimacy": bot.intimacy or 0, "tone": bot.tone or 'friendly',
                    "chat_count": bot.chat_count or 0, "bot_id": bot.bot_id
                }
            })
    return jsonify({"id": None})

@share_bp.route('/api/user/office', methods=['POST'])
def api_user_office():
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"login"}), 401
    user = User.query.get(uid)
    if not user: return jsonify({"error":"user not found"}), 404
    data = request.get_json() or {}
    if 'office_address' in data:
        addr = data['office_address'].strip()
        user.office_address = addr
        if addr:
            from services.transit import geocode_address
            from config import Config
            geo = geocode_address(addr, Config.KAKAO_REST_API_KEY,
                naver_id=Config.NAVER_SEARCH_CLIENT_ID or Config.NAVER_CLIENT_ID,
                naver_secret=Config.NAVER_SEARCH_CLIENT_SECRET or Config.NAVER_CLIENT_SECRET)
            if geo:
                user.office_latitude = geo['lat']
                user.office_longitude = geo['lng']
    if 'work_start_time' in data:
        user.work_start_time = data['work_start_time'].strip()
    db.session.commit()
    return jsonify({"status":"success","office_address":user.office_address or '','office_latitude':user.office_latitude,'office_longitude':user.office_longitude,'work_start_time':user.work_start_time or ''})

@share_bp.route('/api/user/temp', methods=['POST'])
def api_user_temp():
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"login"}), 401
    user = User.query.get(uid)
    if not user: return jsonify({"error":"user not found"}), 404
    data = request.get_json() or {}
    if 'temp_address' in data:
        addr = data['temp_address'].strip()
        user.temp_address = addr
        if addr:
            from services.transit import geocode_address
            from config import Config
            geo = geocode_address(addr, Config.KAKAO_REST_API_KEY,
                naver_id=Config.NAVER_SEARCH_CLIENT_ID or Config.NAVER_CLIENT_ID,
                naver_secret=Config.NAVER_SEARCH_CLIENT_SECRET or Config.NAVER_CLIENT_SECRET)
            if geo:
                user.temp_latitude = geo['lat']
                user.temp_longitude = geo['lng']
    if 'temp_start_date' in data and data['temp_start_date']:
        try: user.temp_start_date = datetime.fromisoformat(data['temp_start_date'])
        except: pass
    if 'temp_end_date' in data and data['temp_end_date']:
        try: user.temp_end_date = datetime.fromisoformat(data['temp_end_date'])
        except: pass
    if 'temp_address' in data and not data['temp_address'].strip():
        user.temp_address = ''; user.temp_latitude = None; user.temp_longitude = None
        user.temp_start_date = None; user.temp_end_date = None
    db.session.commit()
    return jsonify({"status":"success","temp_address":user.temp_address or '','temp_latitude':user.temp_latitude,'temp_longitude':user.temp_longitude,
        'temp_start_date':user.temp_start_date.strftime('%Y-%m-%d') if user.temp_start_date else '',
        'temp_end_date':user.temp_end_date.strftime('%Y-%m-%d') if user.temp_end_date else ''})

@share_bp.route('/api/user/<int:user_id>')
def api_user_profile(user_id):
    uid = session.get('user_id')
    if not uid: return jsonify({"error":"login"}), 401
    user = User.query.get_or_404(user_id)
    is_own = (uid == user.id)
    is_admin = session.get('role') in ('admin','leader')
    result = {
        "id": user.id, "username": user.username, "real_name": user.real_name or user.username,
        "email": user.email, "phone": user.phone, "social_provider": user.social_provider or '',
        "town": user.town or '', "village": user.village or '',
        "is_neighbor": user.is_neighbor or False,
        "role": user.role, "managed_pages": (user.managed_pages or '').split(','),
        "points": user.points or 0, "is_paid": user.is_paid or False,
        "location_share": user.location_share or False,
        "village_notify": user.village_notify if user.village_notify is not None else True,
        "is_own": is_own, "is_admin": is_admin,
    }
    result['p_is_village'] = 'village' in (user.managed_pages or '') or ((user.managed_pages or '')[:3] == 'vi_')
    # is_friend
    is_friend = False
    if uid and uid != user.id:
        f = Friend.query.filter(
            ((Friend.requester_id==uid) & (Friend.receiver_id==user.id) & (Friend.status=='accepted')) |
            ((Friend.requester_id==user.id) & (Friend.receiver_id==uid) & (Friend.status=='accepted'))
        ).first()
        is_friend = bool(f)
    result['is_friend'] = is_friend
    result['office_latitude'] = user.office_latitude
    result['office_longitude'] = user.office_longitude
    result['office_address'] = user.office_address or ''
    result['work_start_time'] = user.work_start_time or ''
    # Point history
    raw_history = PointHistory.query.filter_by(user_id=user.id).order_by(PointHistory.created_at.desc()).limit(50).all()
    running = user.points
    ph = []
    for h in raw_history:
        running -= h.amount
        h.balance_after = running
        ph.append({"id":h.id,"created_at":h.created_at.strftime('%m/%d %H:%M') if h.created_at else '','change_type':h.change_type,'amount':h.amount,'balance_after':h.balance_after,'description':h.description})
    result['point_history'] = ph
    # Messages
    if is_own:
        msgs = Message.query.filter_by(receiver_id=user.id).order_by(
            db.case((Message.sender_role == 'admin', 0),(Message.sender_role == 'leader', 1),else_=2),
            Message.created_at.desc()).all()
    elif is_admin:
        msgs = []
    else:
        msgs = Message.query.filter(
            ((Message.sender_id==uid) & (Message.receiver_id==user.id)) |
            ((Message.sender_id==user.id) & (Message.receiver_id==uid))
        ).order_by(Message.created_at.desc()).all()
    result['messages'] = [{"id":m.id,"subject":m.subject,"content":m.content[:200],"created_at":m.created_at.strftime('%m/%d %H:%M') if m.created_at else '','sender_role':m.sender_role or '','is_read':m.is_read} for m in msgs]
    # Posts
    posts = []
    for p in Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).all():
        posts.append({'title':p.title,'date':p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else '','type':'꿈꾸기','url':f'/post/{p.id}'})
    for s in ShareReport.query.filter_by(user_id=user.id).order_by(ShareReport.created_at.desc()).all():
        posts.append({'title':s.title,'date':s.created_at.strftime('%Y-%m-%d %H:%M') if s.created_at else '','type':'공유','url':f'/share/detail/{s.id}'})
    for w in VillageWish.query.filter_by(user_id=user.id).order_by(VillageWish.created_at.desc()).all():
        posts.append({'title':w.content[:50] if w.content else '','date':w.created_at.strftime('%Y-%m-%d %H:%M') if w.created_at else '','type':'바람','url':'/village/my-wishes'})
    if hasattr(LegalPost, 'user_id'):
        for l in LegalPost.query.filter_by(user_id=user.id).order_by(LegalPost.created_at.desc()).all():
            posts.append({'title':l.title,'date':l.created_at.strftime('%Y-%m-%d %H:%M') if l.created_at else '','type':'법률','url':f'/legal/post/{l.id}'})
    posts.sort(key=lambda x: x['date'], reverse=True)
    result['posts'] = posts[:20]
    # Appointments
    appts = LegalAppointment.query.filter_by(user_id=user.id).order_by(LegalAppointment.date.desc()).limit(10).all()
    result['appointments'] = [{"id":a.id,"title":a.content or '상담예약','date':a.date.isoformat() if a.date else '','time_slot':a.time_slot,'location':a.location or '','status':a.status,'edit_url':f'/legal/appointment/{a.id}/edit'} for a in appts]
    # Tongbot info
    bot = TongBot.query.filter_by(user_id=user.id).first()
    bot_name = bot.bot_name if bot else ''
    bot_memory = (bot.memory or '')[-500:] if bot else ''
    from tongbot_routes import _get_bot
    if is_own:
        b = _get_bot(uid)
        bot_name = b.bot_name
    result['bot_name'] = bot_name
    result['bot_memory'] = bot_memory
    bot_drafts = TongBotDraft.query.filter_by(user_id=user.id).order_by(TongBotDraft.updated_at.desc()).limit(5).all()
    result['bot_drafts'] = [{"id":d.id,"title":d.title or '제목없음',"category":d.category or "","status":d.status,"updated_at":d.updated_at.strftime('%m/%d') if d.updated_at else ""} for d in bot_drafts]
    # Bot message
    bot_message = ''
    if is_own and bot_name:
        try:
            h = (datetime.now() + timedelta(hours=9)).hour
            time_ctx = '아침' if h < 12 else ('오후' if h < 18 else '저녁')
            import random
            tips = ['오늘 양평 날씨에 맞는 옷차림을 추천해 드릴까요?','잠시 스트레칭 어떠세요? 건강이 최고예요!','오늘 하루 감사한 일 세 가지만 떠올려 보세요.','좋아하는 음악 한 곡 들으면서 잠시 쉬어 가세요.','오늘 양평의 맛집 정보가 궁금하신가요?']
            bot_message = random.choice(tips)
        except:
            bot_message = '오늘도 행복한 하루 되세요! 💕'
    result['bot_message'] = bot_message
    # Location
    curr_location = ''
    if is_own or is_admin:
        if user.curr_address: curr_location = user.curr_address
        if not curr_location and user.curr_town:
            curr_location = f"{user.curr_town or ''} {user.curr_village or ''}".strip() or '위치 없음'
    if not curr_location: curr_location = f"{user.curr_town or ''} {user.curr_village or ''}".strip() or '위치 없음'
    result['curr_location'] = curr_location
    result['curr_town'] = user.curr_town or user.town or ''
    result['curr_village'] = user.curr_village or user.village or ''
    # Recent friends (only for own profile)
    recent_friends = []
    if is_own:
        f1 = Friend.query.filter_by(requester_id=uid, status='accepted').all()
        f2 = Friend.query.filter_by(receiver_id=uid, status='accepted').all()
        friend_ids = set()
        for f in f1: friend_ids.add(f.receiver_id)
        for f in f2: friend_ids.add(f.requester_id)
        if friend_ids:
            recent = []
            for fid in friend_ids:
                last_msg = ChatMessage.query.filter(ChatMessage.user_id==fid).order_by(ChatMessage.created_at.desc()).first()
                recent.append({"id":fid, "last":last_msg.created_at.isoformat() if last_msg and last_msg.created_at else None})
            recent.sort(key=lambda x: x["last"] or '', reverse=True)
            for r in recent:
                u = User.query.get(r["id"])
                if u:
                    recent_friends.append({"id":u.id,"username":u.username,"name":u.real_name or u.username,"town":u.town or "","village":u.village or ""})
    result['recent_friends'] = recent_friends
    # Share images
    share_images = []
    img_shares = ShareReport.query.filter(ShareReport.user_id==user.id, ShareReport.image_path.isnot(None), ShareReport.image_path!='').order_by(ShareReport.created_at.desc()).limit(12).all()
    for s in img_shares:
        share_images.append({'path':s.image_path,'title':s.title,'url':f'/share/detail/{s.id}'})
    result['share_images'] = share_images
    return jsonify(result)

@share_bp.route('/share/comment/<int:report_id>', methods=['POST'])
def share_add_comment(report_id):
    if not session.get('username'):
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    content = request.form.get('content', '').strip()
    parent_id = request.form.get('parent_id', type=int)
    if not content:
        return jsonify({"status": "error", "msg": "내용을 입력하세요."}), 400
    report = ShareReport.query.get_or_404(report_id)
    if report.status != 'approved':
        return jsonify({"status": "error", "msg": "승인된 공유만 댓글을 달 수 있습니다."}), 403
    user = User.query.get(session['user_id'])
    comment = ShareComment(
        share_id=report_id,
        user_id=user.id,
        author=user.username,
        content=content,
        parent_id=parent_id
    )
    db.session.add(comment)
    db.session.commit()
    return jsonify({"status": "success", "msg": "댓글이 등록되었습니다."})

@share_bp.route('/share/comment/delete/<int:comment_id>', methods=['POST'])
def share_delete_comment(comment_id):
    if not session.get('username'):
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    comment = ShareComment.query.get_or_404(comment_id)
    if comment.user_id != session.get('user_id') and session.get('role') not in ['admin', 'leader']:
        return jsonify({"status": "error", "msg": "삭제 권한이 없습니다."}), 403
    ShareComment.query.filter_by(parent_id=comment_id).delete()
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"status": "success", "msg": "삭제되었습니다."})

# --- [공유마당 고도화: 가게 검색/투표/메뉴분류] ---

@share_bp.route('/api/share/store-search')
def api_store_search():
    """카카오맵 장소 검색 (위치 기반)"""
    q = request.args.get('q', '').strip()
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if not q:
        return jsonify({"results": []})
    key = current_app.config.get('KAKAO_REST_API_KEY', '')
    if not key:
        return jsonify({"results": [], "error": "kakao_key_missing"})
    params = {'query': q, 'size': 10}
    if lat and lon:
        params['x'] = lon
        params['y'] = lat
        params['radius'] = 10000
    try:
        resp = _requests.get('https://dapi.kakao.com/v2/local/search/keyword.json',
                              headers={'Authorization': 'KakaoAK ' + key}, params=params, timeout=10)
        docs = resp.json().get('documents', [])
        out = [{
            'place_id': d.get('id'), 'name': d.get('place_name'),
            'address': d.get('road_address_name') or d.get('address_name'),
            'lat': float(d['y']) if d.get('y') else None,
            'lon': float(d['x']) if d.get('x') else None,
            'phone': d.get('phone', ''), 'place_url': d.get('place_url', '')
        } for d in docs]
        return jsonify({"results": out})
    except Exception as e:
        return jsonify({"results": [], "error": str(e)[:100]})


@share_bp.route('/api/share/store-suggest', methods=['POST'])
def api_store_suggest():
    """가게명 제안/투표. 같은 place_id 중 최다 득표 이름이 기본."""
    data = request.get_json(silent=True) or {}
    place_id = data.get('place_id')
    name = (data.get('name') or '').strip()
    if not place_id or not name:
        return jsonify({"status": "error", "msg": "필수값 누락"}), 400
    uid = session.get('user_id')
    # 이미 같은 회원이 같은 place_id+name 제안했으면 투표 +1
    existing = StoreSuggestion.query.filter_by(place_id=place_id, name=name).first()
    if existing:
        existing.vote_count += 1
        # 제안 이력 기록
        if uid:
            db.session.add(StoreSuggestionVote(suggestion_id=existing.id, user_id=uid))
    else:
        existing = StoreSuggestion(
            place_id=place_id, name=name, suggested_by=uid,
            vote_count=1, lat=data.get('lat'), lon=data.get('lon'),
            address=data.get('address', ''), place_url=data.get('place_url', ''),
            phone=data.get('phone', ''))
        db.session.add(existing)
        db.session.flush()
        if uid:
            db.session.add(StoreSuggestionVote(suggestion_id=existing.id, user_id=uid))
    db.session.commit()
    # 해당 place_id의 모든 제안 집계
    from sqlalchemy import func
    votes = db.session.query(StoreSuggestion.name, func.sum(StoreSuggestion.vote_count).label('v'))\
                    .filter_by(place_id=place_id).group_by(StoreSuggestion.name)\
                    .order_by(func.sum(StoreSuggestion.vote_count).desc()).all()
    return jsonify({
        "status": "success",
        "suggestion_id": existing.id,
        "top_name": votes[0][0] if votes else name,
        "suggestions": [{"name": v[0], "votes": v[1]} for v in votes]
    })


@share_bp.route('/api/share/menu-classify', methods=['POST'])
def api_menu_classify():
    """메뉴 텍스트 -> 식사/음료/디저트/기타 AI 분류 (GROQ)"""
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({"status": "error", "msg": "메뉴를 입력하세요"}), 400
    groq_key = current_app.config.get('GROQ_API_KEY', '')
    if not groq_key:
        return jsonify({"labels": ["기타"]})
    try:
        r = _requests.post('https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': 'Bearer ' + groq_key, 'Content-Type': 'application/json'},
            json={'model': 'llama-3.1-8b-instant',
                  'messages': [{'role': 'user', 'content':
                    '다음 메뉴 항목 각각을 "식사","음료","디저트","기타" 중 하나로 분류하세요. '
                    '각 항목을 줄바꿈하고 가장 앞에 라벨을 붙이세요. 예시:\n식사: 된장찌개\n음료: 아메리카노\n디저트: 티라미수\n---\n' + text}],
                  'temperature': 0}, timeout=20)
        out = r.json()['choices'][0]['message']['content']
        labels = []
        for line in out.splitlines():
            line = line.strip()
            if line.startswith('식사'): labels.append('식사')
            elif line.startswith('음료'): labels.append('음료')
            elif line.startswith('디저트'): labels.append('디저트')
            else: labels.append('기타')
        if not labels:
            labels = ['기타']
        return jsonify({"labels": labels})
    except Exception as e:
        return jsonify({"labels": ["기타"], "error": str(e)[:80]})


@share_bp.route('/api/share/menu-search', methods=['POST'])
def api_menu_search():
    """가게명으로 카카오맵 API 검색 + Groq AI 메뉴 추출"""
    data = request.get_json(silent=True) or {}
    store_name = (data.get('store_name') or '').strip()
    if not store_name:
        return jsonify({"status": "error", "msg": "가게명을 입력하세요"}), 400
    groq_key = current_app.config.get('GROQ_API_KEY', '')
    kakao_key = current_app.config.get('KAKAO_REST_API_KEY', '')
    store_info = None
    if kakao_key:
        try:
            r = _requests.get('https://dapi.kakao.com/v2/local/search/keyword.json',
                headers={'Authorization': 'Bearer ' + kakao_key},
                params={'query': store_name, 'size': 3}, timeout=10)
            docs = r.json().get('documents', [])
            if docs:
                store_info = {
                    'name': docs[0].get('place_name', ''),
                    'address': docs[0].get('address_name', ''),
                    'phone': docs[0].get('phone', ''),
                    'place_url': docs[0].get('place_url', ''),
                    'lat': float(docs[0].get('y', 0)),
                    'lon': float(docs[0].get('x', 0)),
                    'place_id': docs[0].get('id', ''),
                }
        except Exception:
            pass
    menus = []
    if groq_key:
        try:
            ctx = '가게명: ' + store_name
            if store_info:
                ctx += '\n주소: ' + store_info['address'] + '\n전화: ' + store_info['phone']
            r = _requests.post('https://api.groq.com/openai/v1/chat/completions',
                headers={'Authorization': 'Bearer ' + groq_key, 'Content-Type': 'application/json'},
                json={'model': 'llama-3.1-8b-instant',
                      'messages': [{'role': 'user', 'content':
                        '다음 가게의 대표 메뉴 5~10개를 JSON 배열로 출력하세요. '
                        '각 항목은 {"name": "메뉴명", "price": "가격(원)", "category": "식사/음료/디저트/기타"} 형식입니다. '
                        '가격을 모르면 ""로 하세요.\n\n' + ctx}],
                      'temperature': 0, 'response_format': {'type': 'json_object'}}, timeout=30)
            import json as _json
            out = r.json()['choices'][0]['message']['content']
            parsed = _json.loads(out)
            if isinstance(parsed, list):
                menus = parsed
            elif isinstance(parsed, dict) and 'menus' in parsed:
                menus = parsed['menus']
            elif isinstance(parsed, dict) and 'menu' in parsed:
                menus = parsed['menu']
        except Exception as e:
            return jsonify({"status": "error", "msg": "메뉴 검색 실패: " + str(e)[:80]})
    return jsonify({"status": "success", "store": store_info, "menus": menus})


@share_bp.route('/api/share/watermark', methods=['POST'])
def api_watermark():
    """이미지에 워터마크 추가"""
    data = request.get_json(silent=True) or {}
    image_path = (data.get('image_path') or '').strip()
    text = (data.get('text') or '').strip()
    position = data.get('position', 'bottom-right')
    opacity = float(data.get('opacity', 0.5))
    if not image_path or not text:
        return jsonify({"status": "error", "msg": "이미지 경로와 워터마크 텍스트가 필요합니다."}), 400
    abs_path = os.path.join(current_app.root_path, image_path.lstrip('/'))
    if not os.path.exists(abs_path):
        return jsonify({"status": "error", "msg": "이미지를 찾을 수 없습니다."}), 404
    from services.security import apply_watermark
    ok = apply_watermark(abs_path, text, position=position, opacity=opacity)
    if ok:
        return jsonify({"status": "success", "msg": "워터마크가 적용되었습니다."})
    return jsonify({"status": "error", "msg": "워터마크 적용 실패"}), 500


@share_bp.route('/api/share/store-menus/<int:store_suggestion_id>')
def api_store_menus(store_suggestion_id):
    """가게 메뉴 목록 조회"""
    menus = StoreMenu.query.filter_by(store_suggestion_id=store_suggestion_id).order_by(StoreMenu.sub_category, StoreMenu.name).all()
    return jsonify([{
        "id": m.id, "name": m.name, "sub_category": m.sub_category,
        "price": m.price or '', "description": m.description or '', "ai_generated": m.ai_generated
    } for m in menus])


@share_bp.route('/api/share/store-menu/add', methods=['POST'])
def api_store_menu_add():
    """메뉴 수동 추가"""
    data = request.get_json(silent=True) or {}
    ssid = data.get('store_suggestion_id')
    name = (data.get('name') or '').strip()
    if not ssid or not name:
        return jsonify({"status": "error", "msg": "가게와 메뉴명이 필요합니다."}), 400
    menu = StoreMenu(
        store_suggestion_id=ssid, place_id=str(ssid), name=name,
        sub_category=data.get('sub_category', '기타'),
        price=data.get('price', ''), description=data.get('description', ''),
        ai_generated=False)
    db.session.add(menu)
    db.session.commit()
    return jsonify({"status": "success", "id": menu.id})


@share_bp.route('/api/share/store-menu/delete/<int:menu_id>', methods=['POST'])
def api_store_menu_delete(menu_id):
    """메뉴 삭제"""
    menu = StoreMenu.query.get_or_404(menu_id)
    db.session.delete(menu)
    db.session.commit()
    return jsonify({"status": "success"})


# --- [외부링크 중계] ---