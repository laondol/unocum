import os
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app, send_file
from datetime import datetime, timedelta
from models import db, User, Post, Message, NewsArticle, ShareReport

page_bp = Blueprint('page', __name__)
from route_modules.user_bp import _cleanup_expired_posts

def _serve_spa():
    path = os.path.join(current_app.root_path, 'frontend', 'dist', 'index.html')
    if os.path.exists(path):
        return send_file(path)
    return render_template('intro.html')

@page_bp.route('/spa')
@page_bp.route('/spa/<path:path>')
def spa_fallback(path=''):
    return _serve_spa()


@page_bp.route('/')
@page_bp.route('/intro')
def intro():
    # 최신 국내 소식 5개
    yp_news = NewsArticle.query.filter(NewsArticle.is_selected == True, NewsArticle.world_admin_approved == True, NewsArticle.category.notin_(['세계뉴스', '해외뉴스'])).order_by(NewsArticle.updated_at.desc()).limit(5).all()
    # 최신 세계 소식 5개
    world_news = NewsArticle.query.filter(NewsArticle.is_selected == True, NewsArticle.world_admin_approved == True, NewsArticle.category.in_(['세계뉴스', '해외뉴스'])).order_by(NewsArticle.updated_at.desc()).limit(5).all()
    # 배경 이미지: 공유마당 승인된 모든 사진
    bg_images = db.session.query(ShareReport.image_path).filter(
        ShareReport.status == 'approved',
        ShareReport.image_path.isnot(None),
        ShareReport.image_path != ''
    ).order_by(db.func.random()).limit(30).all()
    bg_images = [img[0] for img in bg_images if img[0]]
    return render_template('intro.html', yp_news=yp_news, world_news=world_news, bg_images=bg_images)

@page_bp.route('/ai/chat')
def ai_chat():
    return _serve_spa()

@page_bp.route('/ai/chat/send', methods=['POST'])
def ai_chat_send():
    msg = request.json.get('message','').strip()
    if not msg:
        return jsonify({"reply":"메시지를 입력하세요."})
    # 문맥 정보
    user_count = User.query.count()
    post_count = Post.query.count()
    uid = session.get('user_id')
    user_info = ''
    if uid:
        u = User.query.get(uid)
        if u:
            user_info = f'현재 대화중인 사용자: {u.real_name or u.username} (이웃인증: {"O" if u.is_verified_resident else "X"})'
    context = f"함께사는양평 현황: 회원 {user_count}명, 꿈꾸기 제안 {post_count}건. {user_info}"
    # 최고책임자가 등록한 지식베이스
    knowledges = AiKnowledge.query.order_by(AiKnowledge.id.desc()).limit(30).all()
    kb_text = ''
    if knowledges:
        kb_text = '\n[최고책임자가 가르친 정보]\n' + '\n'.join([f'Q: {k.question}\nA: {k.answer}' for k in knowledges])
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=current_app.config.get('GROQ_API_KEY',''))
        system_prompt = f"""너는 함께사는양평의 '양평AI'야. 네 존재 목적은 회원과 비회원이 함께사는양평 플랫폼을 편리하게 이용하도록 돕는 거야.
{context}
{kb_text}
주요 역할:
1. 함께사는양평 이용 방법, 메뉴 위치, 기능 설명 (최우선)
   - 꿈꾸기(/main): 공동체 제안 등록
   - 공유마당(/share): 지역 정보·물품 나눔
   - 법률상담(/legal/list): 노무사 상담 예약
   - 심리상담(/psycho/list): 심리상담사 예약
   - 휠체어경사로(/service/ramp): 경사로 설치 신청
   - 마을지기: 동네 소식·알림
   - 통벗: AI 개인비서 채팅
   - 위치기반안내(/construction): 공사·관광·귀가
2. 양평 생활 관련 질문엔 사실만 답변, 모르면 관공서 문의 안내
3. 자연스럽게 "좋았던 경험"이나 "불편했던 점" 물어보기
4. 불편·불만엔 공감하고 꿈꾸기 제안 권유
5. 비회원에겐 가입 혜택 설명 후 회원가입 권유
절대 금지: 지어내기, 정치·종교 논쟁, 개인정보 수집
말투: ~요, ~입니다 체. 이모지 적당히. 한국어."""
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role":"system","content":system_prompt},
                {"role":"user","content":msg}
            ],
            temperature=0.7, max_tokens=1024
        )
        reply = resp.choices[0].message.content
    except Exception as e:
        reply = f"죄송합니다, 일시적인 오류가 발생했습니다: {str(e)}"
    # 불편·불만 자동 감지 → 관리자 피드백 저장
    complaint_kw = ['불편','불만','문제','고쳐','아쉽','힘들','짜증','화나','답답','민원','건의']
    if any(kw in msg for kw in complaint_kw):
        try:
            alert = VillageAlert(
                title=f'AI대화 민원: {msg[:40]}',
                content=f'사용자: {msg}\n\nAI답변: {reply[:300]}',
                alert_type='ai_feedback',
                urgency='normal',
                author_name=session.get('real_name') or session.get('username') or '익명'
            )
            db.session.add(alert)
            db.session.commit()
        except:
            pass
    return jsonify({"reply": reply})


@page_bp.route('/presentation')
def presentation():
    return _serve_spa()
@page_bp.route('/proposal')
def proposal():
    return _serve_spa()

@page_bp.route('/terms')
def terms():
    return _serve_spa()

@page_bp.route('/charter')
def charter():
    return _serve_spa()

@page_bp.route('/main')
def index():
    return _serve_spa()

@page_bp.route('/all-proposals')
def all_proposals():
    now = datetime.now()
    user_id = session.get('user_id')
    _cleanup_expired_posts()
    
    all_posts = Post.query.order_by(Post.created_at.desc()).all()
    posts = []
    for p in all_posts:
        # AI 검토전 (ai_score==0): 작성자만 볼 수 있음
        if p.ai_score == 0 and p.created_at and p.created_at > now - timedelta(hours=48):
            if p.user_id == user_id: posts.append(p)
            continue
        # 점수 -50 이하: 본인만 볼 수 있음
        if p.total_score <= -50:
            if p.user_id == user_id: posts.append(p)
            continue
        # 관리자 강제 승인: 모두에게 공개
        if p.is_forced_approved:
            posts.append(p)
            continue
        # 점수 0 초과(양성): 모두에게 공개
        if p.total_score > 0:
            posts.append(p)
            continue
        # 48시간 경과: 모두에게 공개
        if p.created_at and p.created_at <= now - timedelta(hours=48):
            posts.append(p)
            continue
        # 본인 글: 심사 중에도 본인에게 공개
        if p.user_id == user_id:
            posts.append(p)
            continue
    return _serve_spa()

# --- [회원가입] 이웃 가입 및 선택적 주민 인증 수집 ---
@page_bp.route('/api/correct-address', methods=['POST'])
def correct_address_nologin():
    """회원가입용: 주소 보정 (로그인 불필요)"""
    data = request.get_json()
    manual_loc = data.get('manual_loc','').strip()
    gps_lat = data.get('gps_lat', type=float) or 0
    gps_lng = data.get('gps_lng', type=float) or 0
    if not manual_loc:
        return jsonify({"status":"error","msg":"주소를 입력하세요"})
    from services.transit import geocode_address, haversine_km
    from config import Config
    geo = geocode_address(manual_loc, Config.KAKAO_REST_API_KEY)
    if not geo or not geo.get('lat'):
        # Kakao 실패시 Naver로 시도
        naver_id = Config.NAVER_SEARCH_CLIENT_ID or Config.NAVER_CLIENT_ID
        naver_secret = Config.NAVER_SEARCH_CLIENT_SECRET or Config.NAVER_CLIENT_SECRET
        if naver_id:
            geo = geocode_address(manual_loc, kakao_key=None, naver_id=naver_id, naver_secret=naver_secret)
    if geo and geo.get('lat'):
        d = haversine_km(gps_lat, gps_lng, geo['lat'], geo['lng']) if gps_lat else 99
        corrected = gps_lat > 0 and d <= 0.5
        return jsonify({
            "status":"success",
            "msg": f"'{geo.get('address',manual_loc)}'(으)로 보정됨 (거리 {d:.2f}km)" + (" → 기본주소 저장" if corrected else " → 1회성"),
            "address": geo.get('address', manual_loc),
            "corrected": corrected,
            "lat": geo['lat'], "lng": geo['lng']
        })
    return jsonify({"status":"error","msg":"주소를 찾을 수 없습니다"})

@page_bp.route('/api/check-neighbor')
def check_neighbor():
    """회원가입용: GPS가 양평군 내인지 확인 (로그인 불필요)"""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if not lat or not lon:
        return jsonify({"in_yangpyeong": False})
    from services.geocode import is_in_yangpyeong, gps_to_town_village
    ok = is_in_yangpyeong(lat, lon)
    town, village = ('', '')
    if ok:
        town, village = gps_to_town_village(lat, lon)
    return jsonify({"in_yangpyeong": ok, "town": town or '', "village": village or ''})

@page_bp.route('/api/reverse-geocode-detail')
def reverse_geocode_detail():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if not lat or not lon:
        return jsonify({"error": "위도/경도 필요"})
    from services.transit import reverse_geocode
    from config import Config
    geo = reverse_geocode(lat, lon,
        kakao_key=Config.KAKAO_REST_API_KEY,
        naver_id=Config.NAVER_SEARCH_CLIENT_ID or Config.NAVER_CLIENT_ID,
        naver_secret=Config.NAVER_SEARCH_CLIENT_SECRET or Config.NAVER_CLIENT_SECRET)
    from services.geocode import gps_to_town_village
    town, village = gps_to_town_village(lat, lon)
    return jsonify({
        "address": geo.get('address','') if geo else '',
        "town": town or '', "village": village or ''
    })

@page_bp.route('/api/reverse-geocode')
def reverse_geocode():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if not lat or not lon:
        return jsonify({"status": "error", "msg": "위도/경도 필요"})
    from services.geocode import gps_to_town_village, is_in_yangpyeong
    if not is_in_yangpyeong(lat, lon):
        return jsonify({"status": "outside", "msg": "관외 지역"})
    town, village = gps_to_town_village(lat, lon)
    return jsonify({"status": "success", "town": town or '', "village": village or ''})


    return jsonify({'status':'success','msg':'주소가 수정되었습니다.'})

@page_bp.route('/api/page/intro')
def api_intro():
    yp_news = NewsArticle.query.filter(NewsArticle.is_selected == True, NewsArticle.world_admin_approved == True, ~NewsArticle.category.in_(['세계뉴스', '해외뉴스'])).order_by(NewsArticle.updated_at.desc()).limit(5).all()
    world_news = NewsArticle.query.filter(NewsArticle.is_selected == True, NewsArticle.world_admin_approved == True, NewsArticle.category.in_(['세계뉴스', '해외뉴스'])).order_by(NewsArticle.updated_at.desc()).limit(5).all()
    bg_images = db.session.query(ShareReport.image_path).filter(ShareReport.status == 'approved', ShareReport.image_path.isnot(None), ShareReport.image_path != '').order_by(db.func.random()).limit(30).all()
    return jsonify({
        'yp_news': [{'id': n.id, 'title': n.title, 'category': n.category, 'created_at': n.created_at.isoformat() if n.created_at else None} for n in yp_news],
        'world_news': [{'id': n.id, 'title': n.title, 'category': n.category, 'created_at': n.created_at.isoformat() if n.created_at else None} for n in world_news],
        'bg_images': [i[0] for i in bg_images if i[0]]
    })

@page_bp.route('/api/page/all-proposals')
def api_all_proposals():
    from datetime import timedelta
    now = datetime.now()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    result = []
    uid = session.get('user_id')
    role = session.get('role')
    for p in posts:
        is_own = p.user_id == uid
        visible = False
        if is_own or role in ('admin', 'leader'):
            visible = True
        elif p.is_forced_approved:
            visible = True
        elif p.total_score > -50 and (p.created_at and now - p.created_at >= timedelta(hours=48)):
            visible = True
        elif p.total_score > 0:
            visible = True
        if not visible:
            continue
        result.append({
            'id': p.id, 'title': p.title, 'content': p.content[:150] if p.content else '',
            'file_path': p.file_path, 'author_name': p.author_name, 'user_id': p.user_id,
            'like_count': p.like_count, 'dislike_count': p.dislike_count,
            'ai_score': p.ai_score, 'admin_score': p.admin_score,
            'leader_score': p.leader_score, 'member_score': p.member_score,
            'total_score': p.total_score,
            'is_forced_approved': p.is_forced_approved,
            'created_at': p.created_at.isoformat() if p.created_at else None,
        })
    return jsonify(result)

@page_bp.route('/api/page/index-posts')
def api_index_posts():
    from datetime import timedelta
    now = datetime.now()
    posts = Post.query.filter(Post.total_score > -50, ((Post.created_at <= now - timedelta(hours=48)) | (Post.is_forced_approved == True))).order_by(Post.created_at.desc()).all()
    return jsonify([{
        'id': p.id, 'title': p.title, 'content': p.content[:150] if p.content else '',
        'file_path': p.file_path, 'author_name': p.author_name, 'user_id': p.user_id,
        'like_count': p.like_count, 'dislike_count': p.dislike_count,
        'ai_score': p.ai_score, 'total_score': p.total_score,
        'is_forced_approved': p.is_forced_approved,
        'created_at': p.created_at.isoformat() if p.created_at else None,
    } for p in posts])

@page_bp.route('/api/page/charter')
def api_charter():
    import markdown
    md_path = os.path.join(current_app.root_path, 'charter.md')
    content = ''
    if os.path.exists(md_path):
        with open(md_path, 'r', encoding='utf-8') as f:
            content = markdown.markdown(f.read(), extensions=['extra'])
    return jsonify({'content': content})
