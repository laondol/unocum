import os
import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, session, current_app, send_file, send_from_directory
from models import db, User, EpubBook, EpubPage, EpubMedia, EpubTemplate

epub_bp = Blueprint('epub', __name__)


def _serve_epub_html():
    react_index = os.path.join(current_app.root_path, 'frontend', 'dist', 'index.html')
    if os.path.exists(react_index):
        return send_file(react_index)
    return '<h3>Not found</h3>', 404


def _extract_gps(file_obj, saved_path):
    """Extract GPS from EXIF via Pillow. Returns (lat, lon) or (None, None)."""
    try:
        from PIL import Image
        img = Image.open(saved_path)
        exif = img.getexif()
        if not exif:
            return None, None
        gps = exif.get(0x8825)
        if not gps:
            return None, None
        def _to_deg(val):
            d, m, s = val
            return float(d) + float(m) / 60 + float(s) / 3600
        lat = _to_deg(gps[2])
        lon = _to_deg(gps[4])
        if gps[1] == 'S': lat = -lat
        if gps[3] == 'W': lon = -lon
        return lat, lon
    except Exception:
        return None, None


def _apply_template(book_id, template_id):
    """Create pages from template sections."""
    t = EpubTemplate.query.get(template_id)
    if not t:
        return
    sections = json.loads(t.sections) if t.sections else []
    for i, sec in enumerate(sections):
        page = EpubPage(
            book_id=book_id, order_index=i,
            title=sec.get('title', ''),
            content=sec.get('placeholder', ''))
        db.session.add(page)
    db.session.commit()


# ──────────────── SPA Routes ────────────────

@epub_bp.route('/epub')
@epub_bp.route('/epub/list')
@epub_bp.route('/epub/new')
@epub_bp.route('/epub/edit/<path:path>')
@epub_bp.route('/epub/view/<path:path>')
@epub_bp.route('/epub/embed/<path:path>')
def epub_spa(path=''):
    return _serve_epub_html()


# ──────────────── Book CRUD ────────────────

@epub_bp.route('/api/epub/books')
def api_epub_books():
    uid = session.get('user_id')
    role = session.get('role', '')
    q = EpubBook.query
    if role not in ('admin', 'leader'):
        q = q.filter(db.or_(EpubBook.status == 'published', EpubBook.user_id == uid))
    books = q.order_by(EpubBook.created_at.desc()).all()
    return jsonify([{
        "id": b.id, "title": b.title, "description": b.description or '',
        "layout_type": b.layout_type, "town": b.town or '', "village": b.village or '',
        "cover_image": b.cover_image or '', "status": b.status,
        "page_count": EpubPage.query.filter_by(book_id=b.id).count(),
        "author_name": (User.query.get(b.user_id).username if User.query.get(b.user_id) else '') or '익명',
        "created_at": b.created_at.strftime('%Y-%m-%d %H:%M') if b.created_at else None,
        "updated_at": b.updated_at.strftime('%Y-%m-%d %H:%M') if b.updated_at else None,
    } for b in books])


@epub_bp.route('/api/epub/book/create', methods=['POST'])
def api_epub_create():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '새 콘텐츠').strip()
    layout_type = data.get('layout_type', 'newsletter')
    template_id = data.get('template_id')
    initial_content = data.get('initial_content', '')
    initial_style = data.get('initial_style', '')
    user = User.query.get(uid)
    book = EpubBook(
        user_id=uid, title=title,
        description=(data.get('description') or '').strip(),
        layout_type=layout_type, template_id=template_id,
        town=user.town if user else '', village=user.village if user else '',
        status='draft')
    db.session.add(book)
    db.session.commit()
    if template_id:
        _apply_template(book.id, template_id)
    elif initial_content:
        page = EpubPage(
            book_id=book.id, order_index=0,
            title=title, content=initial_content)
        db.session.add(page)
        db.session.commit()
    return jsonify({"status": "success", "id": book.id, "msg": "생성되었습니다."})


@epub_bp.route('/api/epub/book/<int:book_id>')
def api_epub_book_detail(book_id):
    book = EpubBook.query.get_or_404(book_id)
    uid = session.get('user_id')
    role = session.get('role', '')
    if book.status != 'published' and book.user_id != uid and role not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    pages = EpubPage.query.filter_by(book_id=book_id).order_by(EpubPage.order_index).all()
    pages_data = []
    for p in pages:
        media = EpubMedia.query.filter_by(page_id=p.id).order_by(EpubMedia.order_index).all()
        pages_data.append({
            "id": p.id, "title": p.title or '', "content": p.content or '',
            "order_index": p.order_index, "latitude": p.latitude, "longitude": p.longitude,
            "media": [{
                "id": m.id, "file_path": m.file_path, "media_type": m.media_type,
                "latitude": m.latitude, "longitude": m.longitude,
                "caption": m.caption or '', "alt_text": m.alt_text or '',
                "order_index": m.order_index,
                "editor_state": json.loads(m.editor_state) if m.editor_state else None
            } for m in media]
        })
    template = None
    if book.template_id:
        t = EpubTemplate.query.get(book.template_id)
        if t:
            template = {
                "id": t.id, "name": t.name,
                "sections": json.loads(t.sections) if t.sections else [],
                "style_guide": json.loads(t.style_guide) if t.style_guide else {}
            }
    return jsonify({
        "id": book.id, "title": book.title, "description": book.description or '',
        "layout_type": book.layout_type, "town": book.town or '', "village": book.village or '',
        "cover_image": book.cover_image or '', "status": book.status,
        "template": template, "pages": pages_data,
        "created_at": book.created_at.strftime('%Y-%m-%d %H:%M') if book.created_at else None,
        "updated_at": book.updated_at.strftime('%Y-%m-%d %H:%M') if book.updated_at else None,
    })


@epub_bp.route('/api/epub/book/<int:book_id>', methods=['PUT'])
def api_epub_book_update(book_id):
    book = EpubBook.query.get_or_404(book_id)
    uid = session.get('user_id')
    if book.user_id != uid and session.get('role') not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    data = request.get_json(silent=True) or {}
    if 'title' in data: book.title = data['title'].strip()
    if 'description' in data: book.description = data['description'].strip()
    if 'layout_type' in data: book.layout_type = data['layout_type']
    if 'cover_image' in data: book.cover_image = data['cover_image']
    if 'status' in data: book.status = data['status']
    if 'town' in data: book.town = data['town']
    if 'village' in data: book.village = data['village']
    book.updated_at = datetime.now()
    db.session.commit()
    return jsonify({"status": "success", "msg": "수정되었습니다."})


@epub_bp.route('/api/epub/book/<int:book_id>', methods=['DELETE'])
def api_epub_book_delete(book_id):
    book = EpubBook.query.get_or_404(book_id)
    uid = session.get('user_id')
    if book.user_id != uid and session.get('role') not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    for p in EpubPage.query.filter_by(book_id=book_id).all():
        for m in EpubMedia.query.filter_by(page_id=p.id).all():
            try:
                fp = os.path.join(current_app.root_path, m.file_path.lstrip('/'))
                if os.path.exists(fp): os.remove(fp)
            except Exception:
                pass
            db.session.delete(m)
        db.session.delete(p)
    db.session.delete(book)
    db.session.commit()
    return jsonify({"status": "success", "msg": "삭제되었습니다."})


# ──────────────── Page CRUD ────────────────

@epub_bp.route('/api/epub/page/add', methods=['POST'])
def api_epub_page_add():
    data = request.get_json(silent=True) or {}
    book_id = data.get('book_id')
    if not book_id:
        return jsonify({"status": "error", "msg": "book_id가 필요합니다."}), 400
    book = EpubBook.query.get_or_404(book_id)
    uid = session.get('user_id')
    if book.user_id != uid and session.get('role') not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    max_order = db.session.query(db.func.max(EpubPage.order_index)).filter_by(book_id=book_id).scalar() or 0
    page = EpubPage(
        book_id=book_id, order_index=max_order + 1,
        title=(data.get('title') or '').strip(),
        content=(data.get('content') or '').strip(),
        latitude=data.get('latitude'), longitude=data.get('longitude'))
    db.session.add(page)
    db.session.commit()
    return jsonify({"status": "success", "id": page.id})


@epub_bp.route('/api/epub/page/<int:page_id>', methods=['PUT'])
def api_epub_page_update(page_id):
    page = EpubPage.query.get_or_404(page_id)
    book = EpubBook.query.get(page.book_id)
    uid = session.get('user_id')
    if book and book.user_id != uid and session.get('role') not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    data = request.get_json(silent=True) or {}
    if 'title' in data: page.title = data['title']
    if 'content' in data: page.content = data['content']
    if 'order_index' in data: page.order_index = data['order_index']
    if 'latitude' in data: page.latitude = data['latitude']
    if 'longitude' in data: page.longitude = data['longitude']
    db.session.commit()
    return jsonify({"status": "success"})


@epub_bp.route('/api/epub/page/<int:page_id>', methods=['DELETE'])
def api_epub_page_delete(page_id):
    page = EpubPage.query.get_or_404(page_id)
    book = EpubBook.query.get(page.book_id)
    uid = session.get('user_id')
    if book and book.user_id != uid and session.get('role') not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    for m in EpubMedia.query.filter_by(page_id=page_id).all():
        try:
            fp = os.path.join(current_app.root_path, m.file_path.lstrip('/'))
            if os.path.exists(fp): os.remove(fp)
        except Exception:
            pass
        db.session.delete(m)
    db.session.delete(page)
    db.session.commit()
    return jsonify({"status": "success"})


@epub_bp.route('/api/epub/page/reorder', methods=['POST'])
def api_epub_page_reorder():
    data = request.get_json(silent=True) or {}
    orders = data.get('orders', [])
    for item in orders:
        pid = item.get('page_id')
        idx = item.get('order_index')
        if pid is not None and idx is not None:
            page = EpubPage.query.get(pid)
            if page:
                page.order_index = idx
    db.session.commit()
    return jsonify({"status": "success"})


# ──────────────── Media CRUD ────────────────

@epub_bp.route('/api/epub/media/upload', methods=['POST'])
def api_epub_media_upload():
    page_id = request.form.get('page_id', type=int)
    if not page_id:
        return jsonify({"status": "error", "msg": "page_id가 필요합니다."}), 400
    page = EpubPage.query.get_or_404(page_id)
    book = EpubBook.query.get(page.book_id)
    uid = session.get('user_id')
    if book and book.user_id != uid and session.get('role') not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    from services.security import validate_upload, secure_save
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'epub_media')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    results = []
    for file in request.files.getlist('media'):
        ok, msg = validate_upload(file)
        if not ok:
            continue
        try:
            path = secure_save(file, upload_dir)
        except Exception:
            continue
        lat, lon = _extract_gps(file, path)
        max_order = db.session.query(db.func.max(EpubMedia.order_index)).filter_by(page_id=page_id).scalar() or 0
        media = EpubMedia(
            page_id=page_id, file_path=path,
            media_type='image', latitude=lat, longitude=lon,
            caption=request.form.get('caption', ''),
            alt_text=request.form.get('alt_text', ''),
            order_index=max_order + 1)
        db.session.add(media)
        db.session.commit()
        results.append({
            "id": media.id, "file_path": media.file_path,
            "latitude": media.latitude, "longitude": media.longitude,
            "caption": media.caption})
    return jsonify({"status": "success", "media": results})


@epub_bp.route('/api/epub/media/<int:media_id>', methods=['PUT'])
def api_epub_media_update(media_id):
    media = EpubMedia.query.get_or_404(media_id)
    page = EpubPage.query.get(media.page_id)
    book = EpubBook.query.get(page.book_id) if page else None
    uid = session.get('user_id')
    if book and book.user_id != uid and session.get('role') not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    data = request.get_json(silent=True) or {}
    if 'caption' in data: media.caption = data['caption']
    if 'alt_text' in data: media.alt_text = data['alt_text']
    if 'latitude' in data: media.latitude = data['latitude']
    if 'longitude' in data: media.longitude = data['longitude']
    if 'order_index' in data: media.order_index = data['order_index']
    if 'editor_state' in data: media.editor_state = json.dumps(data['editor_state'])
    db.session.commit()
    return jsonify({"status": "success"})


@epub_bp.route('/api/epub/media/<int:media_id>', methods=['DELETE'])
def api_epub_media_delete(media_id):
    media = EpubMedia.query.get_or_404(media_id)
    page = EpubPage.query.get(media.page_id)
    book = EpubBook.query.get(page.book_id) if page else None
    uid = session.get('user_id')
    if book and book.user_id != uid and session.get('role') not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    try:
        fp = os.path.join(current_app.root_path, media.file_path.lstrip('/'))
        if os.path.exists(fp): os.remove(fp)
    except Exception:
        pass
    db.session.delete(media)
    db.session.commit()
    return jsonify({"status": "success"})


# ──────────────── Templates ────────────────

@epub_bp.route('/api/epub/templates')
def api_epub_templates():
    templates = EpubTemplate.query.filter_by(is_active=True).order_by(
        EpubTemplate.is_default.desc(), EpubTemplate.name).all()
    return jsonify([{
        "id": t.id, "name": t.name, "description": t.description or '',
        "layout_type": t.layout_type, "is_default": t.is_default,
        "sections": json.loads(t.sections) if t.sections else [],
        "style_guide": json.loads(t.style_guide) if t.style_guide else {}
    } for t in templates])


@epub_bp.route('/api/epub/template/create', methods=['POST'])
def api_epub_template_create():
    if session.get('role') not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "권한 없음"}), 403
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({"status": "error", "msg": "템플릿 이름이 필요합니다."}), 400
    t = EpubTemplate(
        name=name, description=(data.get('description') or '').strip(),
        layout_type=data.get('layout_type', 'newsletter'),
        sections=json.dumps(data.get('sections', []), ensure_ascii=False),
        style_guide=json.dumps(data.get('style_guide', {}), ensure_ascii=False),
        is_default=data.get('is_default', False), is_active=True)
    db.session.add(t)
    db.session.commit()
    return jsonify({"status": "success", "id": t.id})


# ──────────────── AI Assist ────────────────

@epub_bp.route('/api/epub/ai/assist', methods=['POST'])
def api_epub_ai_assist():
    data = request.get_json(silent=True) or {}
    section_title = (data.get('section_title') or '').strip()
    context = (data.get('context') or '').strip()
    layout_type = data.get('layout_type', 'newsletter')
    book_title = (data.get('book_title') or '').strip()
    if not section_title:
        return jsonify({"status": "error", "msg": "섹션 제목이 필요합니다."}), 400
    groq_key = current_app.config.get('GROQ_API_KEY', '')
    if not groq_key:
        return jsonify({"suggestion": "AI 서비스가 설정되지 않았습니다.", "status": "fallback"})
    import requests as _requests
    layout_name = {'newsletter': '마을 소식지', 'guidebook': '지역 가이드북', 'journal': '체험 수기/여행기'}.get(layout_type, '콘텐츠')
    prompt = (
        '당신은 "' + layout_name + '" 작성 전문가입니다.\n'
        '콘텐츠 제목: ' + book_title + '\n'
        '작성 중인 섹션: ' + section_title + '\n'
        '현재까지의 내용: ' + (context or '(비어있음)') + '\n\n'
        '이 섹션에 어울리는 글쓰기 가이드와 초안을 작성하세요.\n'
        '구체적인 예시와 함께 3~5문장 정도의 초안을 제시하세요.')
    try:
        r = _requests.post('https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': 'Bearer ' + groq_key, 'Content-Type': 'application/json'},
            json={'model': 'llama-3.1-8b-instant',
                  'messages': [{'role': 'user', 'content': prompt}],
                  'temperature': 0.7}, timeout=30)
        suggestion = r.json()['choices'][0]['message']['content']
        return jsonify({"suggestion": suggestion, "status": "success"})
    except Exception as e:
        return jsonify({"suggestion": "AI 생성 실패: " + str(e)[:80], "status": "error"})


@epub_bp.route('/api/epub/ai/headline', methods=['POST'])
def api_epub_ai_headline():
    data = request.get_json(silent=True) or {}
    topic = (data.get('topic') or '').strip()
    layout_type = data.get('layout_type', 'newsletter')
    if not topic:
        return jsonify({"status": "error", "msg": "주제가 필요합니다."}), 400
    groq_key = current_app.config.get('GROQ_API_KEY', '')
    if not groq_key:
        return jsonify({"headlines": [topic], "status": "fallback"})
    import requests as _requests
    layout_name = {'newsletter': '마을 소식지', 'guidebook': '지역 가이드북', 'journal': '체험 수기'}.get(layout_type, '콘텐츠')
    prompt = (
        '"' + layout_name + '"을 위한 헤드라인 5개를 제안하세요.\n'
        '주제: ' + topic + '\n'
        '각 줄에 하나씩, 따옴표 없이 출력하세요.')
    try:
        r = _requests.post('https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': 'Bearer ' + groq_key, 'Content-Type': 'application/json'},
            json={'model': 'llama-3.1-8b-instant',
                  'messages': [{'role': 'user', 'content': prompt}],
                  'temperature': 0.8}, timeout=20)
        out = r.json()['choices'][0]['message']['content']
        headlines = [line.strip().lstrip('0123456789.-) ') for line in out.splitlines() if line.strip()]
        return jsonify({"headlines": headlines[:5], "status": "success"})
    except Exception as e:
        return jsonify({"headlines": [topic], "status": "error"})


@epub_bp.route('/api/epub/ai/proofread', methods=['POST'])
def api_epub_ai_proofread():
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({"status": "error", "msg": "교정할 텍스트가 필요합니다."}), 400
    groq_key = current_app.config.get('GROQ_API_KEY', '')
    if not groq_key:
        return jsonify({"corrected": text, "status": "fallback"})
    import requests as _requests
    prompt = (
        '다음 텍스트를 한국어 맞춤법/문법에 맞게 교정하세요.\n'
        '원문의 의미를 유지하면서 자연스럽게 다듬어 주세요.\n'
        '교정된 텍스트만 출력하세요.\n\n' + text)
    try:
        r = _requests.post('https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': 'Bearer ' + groq_key, 'Content-Type': 'application/json'},
            json={'model': 'llama-3.1-8b-instant',
                  'messages': [{'role': 'user', 'content': prompt}],
                  'temperature': 0}, timeout=20)
        corrected = r.json()['choices'][0]['message']['content']
        return jsonify({"corrected": corrected, "status": "success"})
    except Exception as e:
        return jsonify({"corrected": text, "status": "error"})
