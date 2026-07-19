from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app
from datetime import datetime
from sqlalchemy import or_
from models import db, User, ShareReport, VillageWish, Post, Message, VillageCache, VillagePage, VillageEvent, VillageEventAttendee, VillageEventChat, StoreInfo, NewsArticle
from route_modules.common import has_page_access
from services.geocode import haversine

village_bp = Blueprint('village', __name__)

@village_bp.route('/village')
def village_admin():
    if not has_page_access('village'):
        return "권한 없음", 403
    uid = session.get('user_id')
    user = User.query.get(uid)
    # 마을지기의 담당 리 목록 추출
    mp = (user.managed_pages or '').split(',') if user else []
    village_ris = []
    for p in mp:
        if p.startswith('vi_'):
            parts = p[3:].split('_')
            if len(parts) >= 2:
                village_ris.append({'myeon': parts[0], 'ri': parts[1]})
    # 리가 없으면 전체 village 쿼리
    if village_ris:
        conditions = []
        for vr in village_ris:
            conditions.append((User.town == vr['myeon']) & (User.village == vr['ri']))
        from sqlalchemy import or_
        village_users = User.query.filter(or_(*conditions)).all() if conditions else []
    else:
        village_users = []
    # QR 등록 회원 추가
    qr_member_ids = [int(p.split('_')[1]) for p in mp if p.startswith('member_')]
    qr_users = User.query.filter(User.id.in_(qr_member_ids)).all() if qr_member_ids else []
    # 중복 제거 후 통합
    all_users = {u.id: u for u in village_users + qr_users}
    village_users = list(all_users.values())
    # 마을에 바란다
    village_wishes = VillageWish.query.filter(
        VillageWish.village_ri.in_([vr['ri'] for vr in village_ris])
    ).order_by(VillageWish.created_at.desc()).limit(20).all() if village_ris else []
    # 마을의 게시글 (제안)
    village_posts = Post.query.filter(
        Post.user_id.in_([u.id for u in village_users])
    ).order_by(Post.created_at.desc()).limit(20).all()
    # 마을의 공유마당
    village_shares = ShareReport.query.filter(
        ShareReport.user_id.in_([u.id for u in village_users])
    ).order_by(ShareReport.created_at.desc()).limit(20).all()
    # 마을의 뉴스
    village_news = []
    if village_users:
        village_news = NewsArticle.query.filter(
            NewsArticle.created_by.in_([u.id for u in village_users])
        ).order_by(NewsArticle.created_at.desc()).limit(10).all()
    # 마을 전체 회원 (쪽지 발송용)
    member_count = len(village_users)
    # 진 인증 회원 목록
    jin_users = [u for u in village_users if u.is_verified_resident]
    return render_template('village_admin.html',
        village_ris=village_ris, village_posts=village_posts,
        village_shares=village_shares, village_news=village_news,
        village_users=village_users, jin_users=jin_users,
        member_count=member_count, village_wishes=village_wishes)

@village_bp.route('/village/ai-categorize', methods=['POST'])
def village_ai_categorize():
    if not has_page_access('village'):
        return jsonify({"error":"권한 없음"}), 403
    content = request.json.get('content','')[:1000]
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=current_app.config.get('GROQ_API_KEY',''))
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role":"system","content":"다음 글을 분석해서 '개인' 또는 '공공'으로 분류하고 한줄 요약해줘. JSON: {\"category\":\"개인\" or \"공공\",\"summary\":\"한줄요약\"}"},
                      {"role":"user","content":content}],
            temperature=0.3, max_tokens=200
        )
        import json as _json
        result = _json.loads(resp.choices[0].message.content)
    except:
        result = {"category":"공공","summary":content[:50]}
    return jsonify(result)

@village_bp.route('/village/edit-post/<int:post_id>', methods=['POST'])
def village_edit_post(post_id):
    if not has_page_access('village'):
        return jsonify({"error":"권한 없음"}), 403
    post = Post.query.get_or_404(post_id)
    post.title = request.form.get('title', post.title)
    post.content = request.form.get('content', post.content)
    db.session.commit()
    return jsonify({"status":"success"})

@village_bp.route('/village/message-all', methods=['POST'])
def village_message_all():
    if not has_page_access('village'):
        return jsonify({"error":"권한 없음"}), 403
    uid = session.get('user_id')
    user = User.query.get(uid)
    mp = (user.managed_pages or '').split(',') if user else []
    village_ris = [p[3:].split('_')[1] for p in mp if p.startswith('vi_') and '_' in p[3:]]
    subject = request.form.get('subject','')
    content = request.form.get('content','')
    if not subject or not content:
        return jsonify({"error":"제목과 내용을 입력하세요."})
    # 파일 첨부 처리
    attachment_path = None
    file = request.files.get('attachment')
    if file and file.filename:
        from services.security import validate_upload, secure_save
        ok, msg = validate_upload(file)
        if ok:
            try:
                import os as _os
                upload_dir = _os.path.join(current_app.config['UPLOAD_FOLDER'], 'village_msg')
                _os.makedirs(upload_dir, exist_ok=True)
                attachment_path = secure_save(file, upload_dir)
            except Exception:
                pass
    from sqlalchemy import or_
    conditions = [User.village == ri for ri in village_ris]
    receivers = User.query.filter(User.id != uid, or_(*conditions)).all() if conditions else []
    count = 0
    for r in receivers:
        try:
            msg = Message(sender_id=uid, sender_name=user.real_name or user.username,
                receiver_id=r.id, subject=subject, content=content,
                attachment=attachment_path)
            db.session.add(msg)
            count += 1
        except:
            pass
    db.session.commit()
    return jsonify({"status":"success","msg":f"{count}명에게 쪽지 발송 완료"})

@village_bp.route('/village/qr')
def village_qr():
    if not has_page_access('village'):
        return "권한 없음", 403
    import secrets, time
    uid = session.get('user_id')
    code = secrets.token_urlsafe(12)
    expiry = int(time.time()) + 600
    user = User.query.get(uid)
    mp = (user.managed_pages or '').split(',') if user else []
    ris = []
    for p in mp:
        if p.startswith('vi_'):
            parts = p[3:].split('_')
            if len(parts) >= 2:
                ris.append(parts[1])
    # 캐시에 QR 코드 정보 저장
    vc = VillageCache.query.filter_by(data_type='qr_code').first()
    if not vc:
        vc = VillageCache(data_type='qr_code')
    vc.town = str(uid)
    vc.village = code
    vc.data_json = f'{{"expiry":{expiry},"ris":{",".join(ris)}}}'
    db.session.add(vc)
    db.session.commit()
    site_url = current_app.config.get('SITE_URL', request.host_url.rstrip('/'))
    qr_url_base = f'{site_url}/village/invite'
    # 마을지기가 만든 페이지 목록
    myeon = ris[0] if ris else ''
    pages = VillagePage.query.filter_by(myeon=myeon, created_by=uid).all()
    return render_template('village_qr.html', qr_url_base=qr_url_base, code=code, expiry=expiry, ris=ris, pages=pages)

@village_bp.route('/village/jin-verify/<int:member_id>', methods=['POST'])
def village_jin_verify(member_id):
    if not has_page_access('village'):
        return jsonify({"error":"권한 없음"}), 403
    member = User.query.get_or_404(member_id)
    member.is_verified_resident = True
    member.jin_verified_at = datetime.now()
    db.session.commit()
    return jsonify({"status":"success","msg":f"{member.real_name or member.username}님 진 인증 완료"})

@village_bp.route('/village/register-member', methods=['POST'])
def village_register_member():
    if not has_page_access('village'):
        return jsonify({"error":"권한 없음"}), 403
    name = request.form.get('name','').strip()
    phone = request.form.get('phone','').strip()
    if not name:
        return jsonify({"error":"이름은 필수입니다."})
    uid = session.get('user_id')
    caretaker = User.query.get(uid)
    # 중복 확인 (이름+전화번호)
    member = None
    if phone:
        member = User.query.filter_by(phone=phone).first()
    if not member:
        # 신규 회원 생성 (이메일 없이)
        from werkzeug.security import generate_password_hash
        import random, string
        username = f'마을{random.randint(10000,99999)}'
        member = User(
            username=username,
            real_name=name,
            phone=phone or '',
            role='user',
            password=generate_password_hash(''.join(random.choices(string.digits, k=6))),
            is_verified_resident=True
        )
        db.session.add(member)
        db.session.flush()
    # 사진 처리
    photo = request.files.get('photo')
    if photo and photo.filename:
        from services.security import validate_upload, secure_save
        ok, msg = validate_upload(photo)
        if ok:
            try:
                import os as _os
                upload_dir = _os.path.join(current_app.config['UPLOAD_FOLDER'], 'village_members')
                _os.makedirs(upload_dir, exist_ok=True)
                member.photo_path = secure_save(photo, upload_dir)
            except Exception:
                pass
    # 마을지기의 managed_pages에 등록
    cp = (caretaker.managed_pages or '').split(',')
    member_key = f'member_{member.id}'
    if member_key not in cp:
        cp.append(member_key)
        caretaker.managed_pages = ','.join(filter(None, cp))
    db.session.commit()
    return jsonify({"status":"success","msg":f"{name}님 등록 완료"})

@village_bp.route('/village/page', methods=['GET','POST'])
def village_page_edit():
    if not has_page_access('village'):
        return "권한 없음", 403
    uid = session.get('user_id')
    user = User.query.get(uid)
    mp = (user.managed_pages or '').split(',') if user else []
    # 첫 번째 담당 리 찾기
    myeon = ri = None
    for p in mp:
        if p.startswith('vi_'):
            parts = p[3:].split('_')
            if len(parts) >= 2:
                myeon, ri = parts[0], parts[1]
                break
    if not myeon:
        return "담당 마을이 지정되지 않았습니다.", 400
    page = VillagePage.query.filter_by(myeon=myeon, ri=ri).first()
    if not page:
        page = VillagePage(myeon=myeon, ri=ri, title=ri+' 마을', content='', visibility='members', created_by=uid)
        db.session.add(page)
        db.session.flush()
    if request.method == 'POST':
        page.title = request.form.get('title', page.title)
        page.content = request.form.get('content', page.content)
        page.visibility = request.form.get('visibility', page.visibility)
        db.session.commit()
        return "<script>alert('저장되었습니다.'); location.reload();</script>"
    return render_template('village_page_edit.html', page=page)

@village_bp.route('/village/view/<string:tmyeon>/<string:tri>')
def village_page_view(tmyeon, tri):
    page = VillagePage.query.filter_by(myeon=tmyeon, ri=tri).first()
    if not page or page.visibility == 'off':
        return "<script>alert('마을 페이지가 준비되지 않았습니다.'); history.back();</script>"
    uid = session.get('user_id')
    at_location = False
    if uid:
        user = User.query.get(uid)
        if user:
            at_location = (user.curr_village == tri) or (user.village == tri)
    is_member = False
    if uid:
        mp_users = []
        # 마을지기 찾기
        all_u = User.query.filter(User.managed_pages.contains('village')).all()
        for u in all_u:
            if any(p.startswith(f'vi_{tmyeon}_{tri}') for p in (u.managed_pages or '').split(',')):
                member_ids = [int(p.split('_')[1]) for p in (u.managed_pages or '').split(',') if p.startswith('member_')]
                mp_users.extend(member_ids)
            if uid in mp_users:
                is_member = True
                break
    if page.visibility == 'members' and not is_member:
        return "<script>alert('마을 주민만 볼 수 있습니다.'); history.back();</script>"
    # 쇼트코드 처리
    content = page.content or ''
    # [gallery] → 공유마당 사진
    if '[gallery]' in content:
        shares = ShareReport.query.filter(ShareReport.image_path.isnot(None), ShareReport.image_path != '').order_by(ShareReport.created_at.desc()).limit(12).all()
        imgs = ''.join([f'<div class="col-4 col-md-3 mb-2"><img src="{s.image_path}" class="img-fluid rounded" style="height:150px;object-fit:cover;width:100%;"></div>' for s in shares if s.image_path])
        gallery_html = f'<div class="row g-2 my-3">{imgs}</div>' if imgs else '<p class="text-muted">갤러리 이미지가 없습니다.</p>'
        content = content.replace('[gallery]', gallery_html)
    # [stores] → 동네가게 목록
    if '[stores]' in content:
        stores = StoreInfo.query.filter(StoreInfo.is_active == True).order_by(StoreInfo.created_at.desc()).limit(10).all()
        store_items = ''.join([f'<div class="col-6 mb-2"><div class="card p-2"><strong>{s.name}</strong><br><small>{s.address or ""}</small></div></div>' for s in stores])
        stores_html = f'<div class="row g-2 my-3">{store_items}</div>' if store_items else '<p class="text-muted">등록된 가게가 없습니다.</p>'
        content = content.replace('[stores]', stores_html)
    # [posts] → 마을 게시글
    if '[posts]' in content:
        recent_posts = Post.query.filter(Post.total_score > -50).order_by(Post.created_at.desc()).limit(10).all()
        post_items = ''.join([f'<div class="mb-2"><a href="/post/{p.id}" class="text-decoration-none"><strong>{p.title}</strong></a><br><small class="text-muted">{p.created_at.strftime("%m/%d") if p.created_at else ""} | 👍 {p.like_count or 0}</small></div>' for p in recent_posts])
        posts_html = f'<div class="my-3">{post_items}</div>' if post_items else '<p class="text-muted">게시글이 없습니다.</p>'
        content = content.replace('[posts]', posts_html)
    return render_template('village_page_view.html', page=page, is_member=is_member, content=content, at_location=at_location)

@village_bp.route('/village/page/toggle', methods=['POST'])
def village_page_toggle():
    if not has_page_access('village'):
        return jsonify({"error":"권한 없음"}), 403
    uid = session.get('user_id')
    user = User.query.get(uid)
    mp = (user.managed_pages or '').split(',') if user else []
    myeon = ri = None
    for p in mp:
        if p.startswith('vi_'):
            parts = p[3:].split('_')
            if len(parts) >= 2:
                myeon, ri = parts[0], parts[1]
                break
    if not myeon:
        return jsonify({"error":"담당 마을 없음"})
    page = VillagePage.query.filter_by(myeon=myeon, ri=ri).first()
    if not page:
        return jsonify({"error":"페이지 없음"})
    page.visibility = 'off' if page.visibility != 'off' else 'public'
    db.session.commit()
    return jsonify({"status":"success","visibility":page.visibility})

@village_bp.route('/village/events')
def village_events():
    if not has_page_access('village'):
        return "권한 없음", 403
    uid = session.get('user_id')
    user = User.query.get(uid)
    mp = (user.managed_pages or '').split(',') if user else []
    myeon = ri = None
    for p in mp:
        if p.startswith('vi_'):
            parts = p[3:].split('_')
            if len(parts) >= 2:
                myeon, ri = parts[0], parts[1]; break
    events = VillageEvent.query.filter_by(myeon=myeon, ri=ri).order_by(VillageEvent.event_date.desc()).all()
    return render_template('village_event_list.html', events=events, myeon=myeon, ri=ri)

@village_bp.route('/village/event/create', methods=['GET','POST'])
def village_event_create():
    if not has_page_access('village'):
        return "권한 없음", 403
    uid = session.get('user_id')
    user = User.query.get(uid)
    mp = (user.managed_pages or '').split(',') if user else []
    myeon = ri = None
    for p in mp:
        if p.startswith('vi_'):
            parts = p[3:].split('_')
            if len(parts) >= 2:
                myeon, ri = parts[0], parts[1]; break
    if request.method == 'POST':
        ev = VillageEvent(
            myeon=myeon, ri=ri,
            title=request.form['title'],
            event_type=request.form.get('event_type','meeting'),
            description=request.form.get('description',''),
            location=request.form.get('location',''),
            video_url=request.form.get('video_url',''),
            event_date=datetime.strptime(request.form['event_date'],'%Y-%m-%dT%H:%M') if request.form.get('event_date') else datetime.now(),
            created_by=uid
        )
        db.session.add(ev)
        db.session.commit()
        return redirect(url_for('village_event_view', event_id=ev.id))
    return render_template('village_event_create.html', myeon=myeon, ri=ri)

@village_bp.route('/village/event/<int:event_id>')
def village_event_view(event_id):
    ev = VillageEvent.query.get_or_404(event_id)
    uid = session.get('user_id')
    attendee = None
    if uid:
        attendee = VillageEventAttendee.query.filter_by(event_id=event_id, user_id=uid).first()
    chat = VillageEventChat.query.filter_by(event_id=event_id).order_by(VillageEventChat.created_at.asc()).limit(50).all()
    attendees = VillageEventAttendee.query.filter_by(event_id=event_id).all()
    return render_template('village_event_view.html', event=ev, attendee=attendee, chat=chat, attendees=attendees)

@village_bp.route('/village/event/<int:event_id>/join', methods=['POST'])
def village_event_join(event_id):
    ev = VillageEvent.query.get_or_404(event_id)
    uid = session.get('user_id')
    consented = request.form.get('consented') == 'true'
    email = request.form.get('email','').strip()
    name = request.form.get('name','').strip()
    attendee = None
    if uid:
        attendee = VillageEventAttendee.query.filter_by(event_id=event_id, user_id=uid).first()
    elif email:
        attendee = VillageEventAttendee.query.filter_by(event_id=event_id, email=email).first()
    if not attendee:
        attendee = VillageEventAttendee(event_id=event_id, user_id=uid, email=email, name=name, consented=consented)
        db.session.add(attendee)
    else:
        attendee.consented = consented
        attendee.email = email or attendee.email
        attendee.name = name or attendee.name
    db.session.commit()
    return jsonify({"status":"success","consented":attendee.consented})

@village_bp.route('/village/event/<int:event_id>/chat', methods=['POST'])
def village_event_chat(event_id):
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error":"로그인 필요"}), 401
    msg = request.form.get('message','').strip()
    if not msg:
        return jsonify({"error":"메시지 입력"})
    user = User.query.get(uid)
    # AI 프로텍터: 욕설/비방 필터링
    blocked = False
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=current_app.config.get('GROQ_API_KEY',''))
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role":"system","content":"다음 채팅 메시지가 욕설,비방,광고성인지 'clean'또는'block'으로만 답변"},{"role":"user","content":msg}],
            temperature=0, max_tokens=10
        )
        if 'block' in resp.choices[0].message.content.lower():
            blocked = True
    except:
        pass
    if blocked:
        return jsonify({"status":"blocked","msg":"AI가 부적절한 메시지로 판단했습니다."})
    chat = VillageEventChat(event_id=event_id, user_id=uid, author=user.real_name or user.username, message=msg)
    db.session.add(chat)
    db.session.commit()
    return jsonify({"status":"success"})

@village_bp.route('/village/event/<int:event_id>/ai-summary', methods=['POST'])
def village_event_ai_summary(event_id):
    if not has_page_access('village'):
        return jsonify({"error":"권한 없음"}), 403
    chat = VillageEventChat.query.filter_by(event_id=event_id).order_by(VillageEventChat.created_at.asc()).all()
    if not chat:
        return jsonify({"summary":"대화 내용이 없습니다."})
    messages = '\n'.join([f'{c.author}: {c.message}' for c in chat])
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=current_app.config.get('GROQ_API_KEY',''))
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role":"system","content":"회의 채팅 내용을 주제별로 묶어서 정리해줘. 비슷한 질문은 그룹화하고, 주요 논의사항과 결정사항을 구분해. 마크다운으로."},
                      {"role":"user","content":messages[:3000]}],
            temperature=0.5, max_tokens=800
        )
        summary = resp.choices[0].message.content
    except Exception as e:
        summary = f"요약 실패: {e}"
    return jsonify({"summary":summary})

@village_bp.route('/village/event/<int:event_id>/role', methods=['POST'])
def village_event_role(event_id):
    if not has_page_access('village'):
        return jsonify({"error":"권한 없음"}), 403
    attendee_id = request.form.get('attendee_id', type=int)
    role = request.form.get('role','').strip()
    att = VillageEventAttendee.query.get_or_404(attendee_id)
    att.role = role
    db.session.commit()
    return jsonify({"status":"success"})

@village_bp.route('/village/event/<int:event_id>/status', methods=['POST'])
def village_event_status(event_id):
    if not has_page_access('village'):
        return jsonify({"error":"권한 없음"}), 403
    ev = VillageEvent.query.get_or_404(event_id)
    ev.status = request.form.get('status', ev.status)
    db.session.commit()
    return jsonify({"status":"success"})

@village_bp.route('/village/event/<int:event_id>/attend/<int:attendee_id>', methods=['POST'])
def village_event_attend(event_id, attendee_id):
    if not has_page_access('village'):
        return jsonify({"error":"권한 없음"}), 403
    att = VillageEventAttendee.query.get_or_404(attendee_id)
    att.status = request.form.get('status', 'confirmed')
    db.session.commit()
    return jsonify({"status":"success"})

@village_bp.route('/village/event/<int:event_id>/qr')
def village_event_qr(event_id):
    if not has_page_access('village'):
        return "권한 없음", 403
    ev = VillageEvent.query.get_or_404(event_id)
    site_url = current_app.config.get('SITE_URL', request.host_url.rstrip('/'))
    qr_url = f'{site_url}/village/event/{ev.id}'
    return render_template('village_event_qr.html', event=ev, qr_url=qr_url)

@village_bp.route('/village/event/<int:event_id>/message', methods=['POST'])
def village_event_message(event_id):
    if not has_page_access('village'):
        return jsonify({"error":"권한 없음"}), 403
    ev = VillageEvent.query.get_or_404(event_id)
    subject = request.form.get('subject','').strip()
    msg_content = request.form.get('content','').strip()
    if not subject or not msg_content:
        return jsonify({"error":"제목과 내용을 입력하세요."})
    scope = request.form.get('scope','attendees')
    uid = session.get('user_id')
    user = User.query.get(uid)
    # 대상자 선정
    receivers = []
    if scope == 'attendees':
        attendees = VillageEventAttendee.query.filter_by(event_id=event_id).all()
        for a in attendees:
            if a.user_id:
                u = User.query.get(a.user_id)
                if u: receivers.append(u)
    elif scope == 'village':
        receivers = User.query.filter(User.village == ev.ri).all()
    elif scope == 'myeon':
        receivers = User.query.filter(User.town == ev.myeon).all()
    elif scope == 'all':
        receivers = User.query.all()
    # 비용 체크
    cost = len(receivers)
    if (user.points or 0) < cost:
        return jsonify({"error":f"닢이 부족합니다. (필요: {cost}닢, 보유: {user.points or 0}닢)"})
    # 발송
    count = 0
    for r in receivers:
        if r.id == uid: continue
        msg = Message(sender_id=uid, sender_name=user.real_name or user.username,
            receiver_id=r.id, subject=subject, content=msg_content)
        db.session.add(msg)
        count += 1
    add_points(uid, -cost, 'event_message', f'활동 쪽지: {ev.title[:30]} ({count}명)')
    db.session.commit()
    return jsonify({"status":"success","msg":f"{count}명에게 쪽지 발송 완료 ({cost}닢 차감)"})

@village_bp.route('/village/event/<int:event_id>/ping', methods=['POST'])
def village_event_ping(event_id):
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error":"로그인 필요"}), 401
    att = VillageEventAttendee.query.filter_by(event_id=event_id, user_id=uid).first()
    if att:
        att.last_ping = datetime.now()
        db.session.commit()
    attendees = VillageEventAttendee.query.filter_by(event_id=event_id).all()
    now = datetime.now()
    away = []
    for a in attendees:
        if a.last_ping and (now - a.last_ping).total_seconds() > 30:
            away.append({'id':a.id,'name':a.name or a.email or '익명','seconds':int((now - a.last_ping).total_seconds())})
    return jsonify({"status":"ok","away":away})

@village_bp.route('/village/invite/<path:target>')
def village_invite(target):
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login', next=request.path))
    user = User.query.get(uid)
    # 진 인증 체크 (6개월)
    if not user.jin_verified_at or (datetime.now() - user.jin_verified_at).days > 150:
        return render_template('village_jin_consent.html', target=target)
    # target에 따라 이동
    if target == 'join':
        return redirect(url_for('village_join', code=request.args.get('code','')))
    elif target.startswith('page_'):
        page_id = int(target.split('_')[1])
        page = VillagePage.query.get(page_id)
        if page:
            return redirect(url_for('village_page_view', tmyeon=page.myeon, tri=page.ri))
    return "<script>alert('페이지를 찾을 수 없습니다.'); history.back();</script>"

@village_bp.route('/village/invite-jin', methods=['POST'])
def village_invite_jin():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error":"로그인 필요"})
    user = User.query.get(uid)
    user.jin_verified_at = datetime.now()
    user.is_verified_resident = True
    db.session.commit()
    target = request.json.get('target','')
    redirect = '/village/join' if target == 'join' else '/intro'
    if target.startswith('page_'):
        page_id = int(target.split('_')[1])
        page = VillagePage.query.get(page_id)
        if page:
            redirect = url_for('village_page_view', tmyeon=page.myeon, tri=page.ri)
    return jsonify({"status":"success","redirect":redirect})

@village_bp.route('/village/wish', methods=['POST'])
def village_wish_create():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error":"로그인 필요"}), 401
    user = User.query.get(uid)
    content = request.form.get('content','').strip()
    ri = user.village or user.curr_village or ''
    if not content:
        return jsonify({"error":"내용을 입력하세요."})
    w = VillageWish(user_id=uid, content=content, village_ri=ri)
    db.session.add(w)
    db.session.commit()
    return jsonify({"status":"success","msg":"마을에 전달되었습니다."})

@village_bp.route('/village/wish/<int:wish_id>/reply', methods=['POST'])
def village_wish_reply(wish_id):
    if not has_page_access('village'):
        return jsonify({"error":"권한 없음"}), 403
    w = VillageWish.query.get_or_404(wish_id)
    w.status = request.form.get('status', w.status)
    w.reply = request.form.get('reply','')
    w.replied_by = session.get('user_id')
    db.session.commit()
    return jsonify({"status":"success"})

@village_bp.route('/village/my-wishes')
def village_my_wishes():
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login'))
    wishes = VillageWish.query.filter_by(user_id=uid).order_by(VillageWish.created_at.desc()).all()
    return render_template('village_my_wishes.html', wishes=wishes)

@village_bp.route('/api/village/images')
def village_images():
    myeon = request.args.get('myeon','')
    ri = request.args.get('ri','')
    images = []
    shares = ShareReport.query.filter(ShareReport.image_path.isnot(None), ShareReport.image_path != '').order_by(ShareReport.created_at.desc()).limit(20).all()
    images = [s.image_path for s in shares if s.image_path]
    return jsonify({"images": images})

@village_bp.route('/village/join', methods=['GET','POST'])
def village_join():
    code = request.args.get('code') or request.form.get('code')
    if not code:
        return "<script>alert('QR 코드가 필요합니다.'); location.href='/intro';</script>"
    # 캐시에서 정보 조회
    vc = VillageCache.query.filter_by(village=code).first()
    if not vc:
        return "<script>alert('만료되었거나 잘못된 QR입니다.'); location.href='/intro';</script>"
    import json as _json
    try:
        data = _json.loads(vc.data_json or '{}')
    except:
        return "<script>alert('잘못된 QR 정보입니다.'); location.href='/intro';</script>"
    expiry = data.get('expiry', 0)
    import time
    if time.time() > expiry:
        return "<script>alert('QR 코드가 만료되었습니다. (10분 유효)'); location.href='/intro';</script>"
    ris = data.get('ris','').split(',') if data.get('ris') else []
    caretaker_uid = int(vc.town) if vc.town and vc.town.isdigit() else None
    caretaker = User.query.get(caretaker_uid) if caretaker_uid else None

    if request.method == 'POST':
        uid = session.get('user_id')
        if not uid:
            return "<script>alert('로그인이 필요합니다.'); location.href='/login';</script>"
        member = User.query.get(uid)
        if not member:
            return "<script>alert('회원 정보를 찾을 수 없습니다.'); location.href='/intro';</script>"
        # 동의 처리: 마을지기의 managed_pages에 회원 등록
        if caretaker:
            cp = (caretaker.managed_pages or '').split(',')
            member_key = f'member_{uid}'
            if member_key not in cp:
                cp.append(member_key)
                caretaker.managed_pages = ','.join(filter(None, cp))
            # 회원 사진 처리
            photo = request.files.get('photo')
            if photo and photo.filename:
                import os as _os
                upload_dir = _os.path.join(current_app.config['UPLOAD_FOLDER'], 'village_members')
                _os.makedirs(upload_dir, exist_ok=True)
                fname = f'{uid}_{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg'
                fpath = _os.path.join(upload_dir, fname)
                photo.save(fpath)
                member.photo_path = '/static/uploads/village_members/' + fname
            db.session.commit()
        return "<script>alert('마을 등록이 완료되었습니다!'); location.href='/user/%d';</script>" % uid
    return render_template('village_join.html', code=code, caretaker=caretaker, ris=ris)

