import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, session, current_app, send_file
from models import db, User, GuideSection, GuideTemplate

guide_bp = Blueprint('guide', __name__)


# ──────────────── SPA Route ────────────────

def _serve_guide_html():
    react_index = os.path.join(current_app.root_path, 'frontend', 'dist', 'index.html')
    if os.path.exists(react_index):
        return send_file(react_index)
    return '<h3>Not found</h3>', 404


@guide_bp.route('/guide')
@guide_bp.route('/guide/<path:path>')
@guide_bp.route('/guide/templates')
def guide_spa(path=''):
    return _serve_guide_html()


# ──────────────── Guide Section API ────────────────

@guide_bp.route('/api/guide/sections')
def api_guide_sections():
    lang = request.args.get('lang', 'ko')
    sections = GuideSection.query.filter_by(language=lang, status='published').order_by(GuideSection.order_index).all()
    return jsonify([s.to_dict() for s in sections if not s.parent_id])


@guide_bp.route('/api/guide/section', methods=['POST'])
def api_guide_section_create():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    user = User.query.get(uid)
    if not user or user.role not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "관리자만 가능합니다."}), 403
    data = request.get_json(silent=True) or {}
    section = GuideSection(
        title=data.get('title', '새 섹션'),
        content=data.get('content', ''),
        icon=data.get('icon', ''),
        order_index=data.get('order_index', 0),
        parent_id=data.get('parent_id'),
        layout_type=data.get('layout_type', 'card'),
        style_json=json.dumps(data.get('style_json', {})),
        language=data.get('language', 'ko'),
    )
    db.session.add(section)
    db.session.commit()
    return jsonify({"status": "success", "id": section.id})


@guide_bp.route('/api/guide/section/<int:section_id>', methods=['PUT'])
def api_guide_section_update(section_id):
    uid = session.get('user_id')
    if not uid:
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    user = User.query.get(uid)
    if not user or user.role not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "관리자만 가능합니다."}), 403
    section = GuideSection.query.get(section_id)
    if not section:
        return jsonify({"status": "error", "msg": "섹션을 찾을 수 없습니다."}), 404
    data = request.get_json(silent=True) or {}
    if 'title' in data: section.title = data['title']
    if 'content' in data: section.content = data['content']
    if 'icon' in data: section.icon = data['icon']
    if 'order_index' in data: section.order_index = data['order_index']
    if 'parent_id' in data: section.parent_id = data['parent_id']
    if 'layout_type' in data: section.layout_type = data['layout_type']
    if 'style_json' in data: section.style_json = json.dumps(data['style_json'])
    if 'language' in data: section.language = data['language']
    if 'status' in data: section.status = data['status']
    section.updated_at = datetime.now()
    db.session.commit()
    return jsonify({"status": "success"})


@guide_bp.route('/api/guide/section/<int:section_id>', methods=['DELETE'])
def api_guide_section_delete(section_id):
    uid = session.get('user_id')
    if not uid:
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    user = User.query.get(uid)
    if not user or user.role not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "관리자만 가능합니다."}), 403
    section = GuideSection.query.get(section_id)
    if not section:
        return jsonify({"status": "error", "msg": "섹션을 찾을 수 없습니다."}), 404
    db.session.delete(section)
    db.session.commit()
    return jsonify({"status": "success"})


# ──────────────── Guide Template API ────────────────

@guide_bp.route('/api/guide/templates')
def api_guide_templates():
    featured = request.args.get('featured')
    q = GuideTemplate.query.filter_by(is_active=True)
    if featured:
        q = q.filter_by(is_featured=True)
    templates = q.order_by(GuideTemplate.use_count.desc()).all()
    return jsonify([t.to_dict() for t in templates])


@guide_bp.route('/api/guide/template', methods=['POST'])
def api_guide_template_create():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    data = request.get_json(silent=True) or {}
    tpl = GuideTemplate(
        name=data.get('name', '새 템플릿'),
        description=data.get('description', ''),
        html_content=data.get('html_content', ''),
        source_type=data.get('source_type', 'manual'),
        source_id=data.get('source_id'),
        layout_type=data.get('layout_type', 'card'),
        style_guide=json.dumps(data.get('style_guide', {})),
        preview_image=data.get('preview_image', ''),
    )
    db.session.add(tpl)
    db.session.commit()
    return jsonify({"status": "success", "id": tpl.id})


@guide_bp.route('/api/guide/template/<int:tpl_id>/use', methods=['POST'])
def api_guide_template_use(tpl_id):
    tpl = GuideTemplate.query.get(tpl_id)
    if not tpl:
        return jsonify({"status": "error", "msg": "템플릿을 찾을 수 없습니다."}), 404
    tpl.use_count += 1
    db.session.commit()
    return jsonify({"status": "success", "html_content": tpl.html_content, "style_guide": json.loads(tpl.style_guide or "{}")})


@guide_bp.route('/api/guide/template/<int:tpl_id>', methods=['PUT'])
def api_guide_template_update(tpl_id):
    uid = session.get('user_id')
    if not uid:
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    user = User.query.get(uid)
    if not user or user.role not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "관리자만 가능합니다."}), 403
    tpl = GuideTemplate.query.get(tpl_id)
    if not tpl:
        return jsonify({"status": "error", "msg": "템플릿을 찾을 수 없습니다."}), 404
    data = request.get_json(silent=True) or {}
    if 'name' in data: tpl.name = data['name']
    if 'description' in data: tpl.description = data['description']
    if 'html_content' in data: tpl.html_content = data['html_content']
    if 'layout_type' in data: tpl.layout_type = data['layout_type']
    if 'style_guide' in data: tpl.style_guide = json.dumps(data['style_guide'])
    if 'preview_image' in data: tpl.preview_image = data['preview_image']
    if 'is_featured' in data: tpl.is_featured = data['is_featured']
    if 'is_active' in data: tpl.is_active = data['is_active']
    tpl.updated_at = datetime.now()
    db.session.commit()
    return jsonify({"status": "success"})


@guide_bp.route('/api/guide/template/<int:tpl_id>', methods=['DELETE'])
def api_guide_template_delete(tpl_id):
    uid = session.get('user_id')
    if not uid:
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    user = User.query.get(uid)
    if not user or user.role not in ('admin', 'leader'):
        return jsonify({"status": "error", "msg": "관리자만 가능합니다."}), 403
    tpl = GuideTemplate.query.get(tpl_id)
    if not tpl:
        return jsonify({"status": "error", "msg": "템플릿을 찾을 수 없습니다."}), 404
    db.session.delete(tpl)
    db.session.commit()
    return jsonify({"status": "success"})


# ──────────────── From Share Report → Template ────────────────

@guide_bp.route('/api/guide/template/from-share/<int:report_id>', methods=['POST'])
def api_template_from_share(report_id):
    uid = session.get('user_id')
    if not uid:
        return jsonify({"status": "error", "msg": "로그인이 필요합니다."}), 401
    from models import ShareReport
    report = ShareReport.query.get(report_id)
    if not report:
        return jsonify({"status": "error", "msg": "공유글을 찾을 수 없습니다."}), 404
    data = request.get_json(silent=True) or {}
    html = f"<h2>{report.title}</h2><p>{report.content}</p>"
    if report.image_path:
        html += f'<img src="{report.image_path}" style="width:100%;border-radius:12px;" />'
    tpl = GuideTemplate(
        name=data.get('name', report.title or '공유글 템플릿'),
        description=data.get('description', f'{report.town} {report.village}에서 공유된 레이아웃'),
        html_content=html,
        source_type='share_report',
        source_id=report_id,
        layout_type=data.get('layout_type', 'card'),
        preview_image=report.image_path or '',
    )
    db.session.add(tpl)
    db.session.commit()
    return jsonify({"status": "success", "id": tpl.id})


# ──────────────── Init Seed Data ────────────────

def seed_guide_data():
    """Insert default guide sections if table is empty."""
    if GuideSection.query.count() > 0:
        return
    sections = [
        GuideSection(title="함께사는양평이란?", icon="🏠", order_index=1,
                     content="<h3>함께사는양평</h3><p>양평 지역 공동체 플랫폼입니다. 소식을 공유하고, 제안을 나누며, 이웃과 소통합니다.</p>",
                     layout_type="hero"),
        GuideSection(title="회원가입과 로그인", icon="👤", order_index=2,
                     content="<h3>회원가입</h3><p>이메일 또는 소셜 계정으로 간편하게 가입하세요.</p><h3>로그인</h3><p>가입한 계정으로 로그인하면 모든 기능을 이용할 수 있습니다.</p>",
                     layout_type="steps"),
        GuideSection(title="소식 공유하기", icon="📰", order_index=3,
                     content="<h3>소식지 작성</h3><p>사진과 함께 우리 마을 소식을 공유하세요. GPS 정보가 있으면 지도에 표시됩니다.</p><h3>AI 도우미</h3><p>작성이 어려우면 AI가 초안을 도와줍니다.</p>",
                     layout_type="card"),
        GuideSection(title="제안하기", icon="💡", order_index=4,
                     content="<h3>마을을 위한 제안</h3><p>개선하고 싶은 점, 하고 싶은 일을 제안하세요. 주민들이 투표하고 함께 만들어갑니다.</p>",
                     layout_type="card"),
        GuideSection(title="동네가게", icon="🏪", order_index=5,
                     content="<h3>우리 동네 가게</h3><p>주변 가게를 검색하고 메뉴를 확인하세요. 가게 사장님이 직접 메뉴를 등록할 수도 있습니다.</p>",
                     layout_type="card"),
        GuideSection(title="상담 서비스", icon="📞", order_index=6,
                     content="<h3>법률상담 · 심리상담</h3><p>무료 법률상담과 심리상담을 예약하고 이용할 수 있습니다.</p>",
                     layout_type="card"),
        GuideSection(title="위치기반 안내", icon="📍", order_index=7,
                     content="<h3>내 주변 정보</h3><p>GPS를 기반으로 주변 공유글, 가게, 시설 정보를 확인할 수 있습니다.</p>",
                     layout_type="card"),
        GuideSection(title="통벗 채팅", icon="🤖", order_index=8,
                     content="<h3>AI 통벗</h3><p>양평 관련 질문에 AI가 답변해 줍니다. 24시간 이용 가능합니다.</p>",
                     layout_type="card"),
    ]
    db.session.add_all(sections)
    db.session.commit()

    if GuideTemplate.query.count() == 0:
        tpls = [
            GuideTemplate(name="소식지 기본", description="사진+제목+본문 형태의 소식지 템플릿",
                          html_content='<div style="max-width:600px;margin:0 auto;"><h2 style="font-size:24px;font-weight:bold;">제목</h2><p style="color:#666;">날짜 · 마을</p><img src="" style="width:100%;border-radius:12px;margin:16px 0;" /><p style="line-height:1.8;">본문 내용</p></div>',
                          layout_type="card", is_featured=True, source_type="manual"),
            GuideTemplate(name="가이드북 기본", description="섹션별 구성의 가이드북 템플릿",
                          html_content='<div style="max-width:700px;margin:0 auto;"><div style="background:#f0f8f0;padding:24px;border-radius:16px;margin-bottom:16px;"><h2 style="font-size:22px;color:#2c5f2d;">섹션 제목</h2><p style="line-height:1.8;">섹션 설명</p></div></div>',
                          layout_type="guidebook", is_featured=True, source_type="manual"),
            GuideTemplate(name="수기 기본", description="개인 경험 공유 수기 템플릿",
                          html_content='<div style="max-width:600px;margin:0 auto;"><blockquote style="border-left:4px solid #27ae60;padding-left:16px;font-style:italic;color:#555;">한 줄 인용</blockquote><p style="line-height:1.8;margin-top:16px;">경험 이야기</p></div>',
                          layout_type="journal", is_featured=True, source_type="manual"),
        ]
        db.session.add_all(tpls)
        db.session.commit()
