import json, os, base64, threading, subprocess, tempfile
from datetime import datetime, timedelta
from openai import OpenAI
from models import db, Post, User, ShareReport
from services.naver_news import get_local_share_context
from services.geocode import gps_to_town_village

HAAR_FACE = None
def _get_face_cascade():
    global HAAR_FACE
    if HAAR_FACE is None:
        try:
            import cv2
            path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(path):
                HAAR_FACE = cv2.CascadeClassifier(path)
        except: pass
    return HAAR_FACE

def mosaic_image_faces(image_path):
    try:
        import cv2
        from PIL import Image as PILImage
    except:
        return None
    cascade = _get_face_cascade()
    if cascade is None:
        return None
    img = cv2.imread(image_path)
    if img is None:
        return None
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if len(faces) == 0:
        return None
    for (x, y, fw, fh) in faces:
        x = max(0, x - int(fw * 0.2))
        y = max(0, y - int(fh * 0.2))
        fw = min(w - x, int(fw * 1.4))
        fh = min(h - y, int(fh * 1.4))
        face_roi = img[y:y+fh, x:x+fw]
        small = cv2.resize(face_roi, (max(8, fw // 12), max(8, fh // 12)), interpolation=cv2.INTER_LINEAR)
        mosaic = cv2.resize(small, (fw, fh), interpolation=cv2.INTER_NEAREST)
        img[y:y+fh, x:x+fw] = mosaic
    base, ext = os.path.splitext(image_path)
    mosaic_path = f"{base}_mosaic{ext}"
    cv2.imwrite(mosaic_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    return mosaic_path

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

def _groq_client():
    from flask import current_app
    key = current_app.config.get("GROQ_API_KEY", "")
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")

def _groq_json(system, user, model=GROQ_MODEL, timeout=60):
    try:
        client = _groq_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            response_format={"type": "json_object"},
            timeout=timeout
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"[GROQ JSON] error: {e}")
        return {}

def _groq_vision(system, user, b64_image, model=GROQ_VISION_MODEL, timeout=30):
    try:
        client = _groq_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{system}\n{user}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                ]
            }],
            response_format={"type": "json_object"},
            timeout=timeout
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"[GROQ VISION] error: {e}")
        return {}

def _image_to_base64(image_path):
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        print(f"[IMAGE BASE64] error: {e}")
        return None

def _load_rag_context(title, content, timeout=3):
    result = [""]
    def _work():
        try:
            from services.rag import build_context
            ctx = build_context(f"{title} {content}", top_k=3)
            if ctx:
                result[0] = f"\n\n[참고 자료 - 커뮤니티 내 관련 게시글]\n{ctx}\n\n위 자료를 참고하여 분석하세요."
        except Exception as e:
            print(f"[RAG CONTEXT] error: {e}")
    t = threading.Thread(target=_work, daemon=True)
    t.start()
    t.join(timeout=timeout)
    return result[0]

def call_ai_judge(title, content, is_comment=False):
    role = "댓글 방역 지킴이" if is_comment else "공동체 자치 지킴이"
    system = f"당신은 '함께사는양평' {role}입니다. 반드시 한국어로 JSON 형식으로만 대답하세요."
    context = _load_rag_context(title, content, timeout=3) if not is_comment else ""
    user = f'{{"score": 숫자(-50~50), "category": "8대사회권분야", "summary": "3줄요약", "reason": "이유", "improvement_tip": "제안 보완을 위해 주민에게 제시할 대안 1가지"}}\n분석대상: 제목: {title}\n본문: {content}{context}' if not is_comment else content
    data = _groq_json(system, user)
    data['score'] = max(-50, min(50, int(data.get('score', 0))))
    return data

def call_ai_debate(post, admin_opinion, suggested_score):
    system = "당신은 자치 지킴이 AI입니다. 정중한 답변과 최종 점수를 합의하여 JSON을 출력하세요."
    user = f"관리자: '{admin_opinion}' / 요청점수: {suggested_score}\nJSON: {{{{'ai_reply': '답변', 'final_ai_score': 점수}}}}"
    data = _groq_json(system, user, timeout=120)
    data['final_ai_score'] = max(-50, min(50, int(data.get('final_ai_score', suggested_score))))
    return data

def background_ai_judge(app, post_id):
    with app.app_context():
        post = Post.query.get(post_id)
        if not post: return
        ai_res = call_ai_judge(post.title, post.content)
        post.ai_score = ai_res.get('score', 0)
        post.total_score = post.ai_score + post.admin_score + post.leader_score + post.member_score
        post.ai_category = ai_res.get('category', '일반제안')
        post.ai_summary = ai_res.get('summary', '요약 완료')
        post.ai_reason = ai_res.get('reason', '분석 완료')
        post.ai_improvement_tip = ai_res.get('improvement_tip', '보안 계획을 보완해 보세요.')
        if post.total_score <= -50 and not post.penalty_applied:
            user = User.query.get(post.user_id)
            if user:
                user.points -= 100
                user.points = max(0, user.points)
                post.penalty_applied = True
                post.deadline = datetime.now() + timedelta(days=30)
        db.session.commit()

def moderate_image(image_path, app=None):
    b64 = _image_to_base64(image_path)
    if not b64:
        return False, "", "clean"
    system = "당신은 양평군 공유 이미지 방역관입니다. 개인정보보호법을 엄격히 적용합니다."
    user = """다음 이미지가 아래 기준에 하나라도 해당하면 반드시 flagged=true로 판단하세요.
1. 인물 사진 (얼굴, 신체 일부, 실루엣, 뒷모습 포함 모든 인물)
2. 개인정보 노출 (주민등록증, 면허증, 여권, 번호판, 신용카드, 명함)
3. 폭력적/혐오적/선정적 내용
4. 불법 촬영물, 스팸/광고성 이미지
※ 조금이라도 의심되면 flagged=true로 판단하세요. 확실한 풍경/사물/음식/동물만 false입니다.
JSON: {"flagged": true/false, "reason": "이유", "category": "person/privacy/violence/adult/illegal/spam/clean"}"""
    data = _groq_vision(system, user, b64)
    flagged = data.get('flagged', False)
    category = data.get('category', 'clean')
    return flagged, data.get('reason', '') if flagged else "", category

VALUABLE_CATEGORIES = {'사건', '풍경', '장소', '맛집'}

def extract_video_frames(video_path, max_frames=3):
    frames = []
    try:
        import subprocess as sp
        duration_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', video_path]
        dur = sp.check_output(duration_cmd).decode().strip()
        try:
            duration = float(dur)
        except:
            return frames
        if duration < 1:
            return frames
        intervals = [duration * i / (max_frames + 1) for i in range(1, max_frames + 1)]
        for i, ts in enumerate(intervals):
            fd, tmp = tempfile.mkstemp(suffix='.jpg')
            os.close(fd)
            sp.run(['ffmpeg', '-y', '-ss', str(ts), '-i', video_path,
                    '-vframes', '1', '-q:v', '2', tmp],
                   capture_output=True, timeout=15)
            with open(tmp, 'rb') as f:
                frames.append(base64.b64encode(f.read()).decode())
            try: os.remove(tmp)
            except: pass
    except Exception as e:
        print(f"[VIDEO FRAMES] error: {e}")
    return frames

def moderate_video_frames(video_path, app=None):
    if not video_path or not os.path.exists(video_path):
        return False, "", "clean"
    frames = extract_video_frames(video_path)
    if not frames:
        return False, "", "clean"
    system = "당신은 양평군 공유 동영상 방역관입니다."
    user = """다음 동영상에서 추출한 장면 이미지입니다. 아래 기준에 해당하는지 판단해주세요.
1. 인물 사진 (얼굴 전체 및 일부, 신체 일부 포함)
2. 폭력적/혐오적 내용
3. 선정적/음란적 내용
4. 개인정보 노출 (주민등록증, 번호판 등)
5. 불법 촬영물
6. 스팸/광고성 이미지
※ 1번(인물 사진)은 단체 사진, 뒷모습, 흐릿한 실루엣, 셀카, 프로필 사진, 얼굴이 조금이라도 나온 모든 사진 포함. 인물이 전혀 없는 풍경/사물/음식/동물 장면만 허용.
위 내용이 하나라도 해당되면 flagged=true, 아니면 false.
JSON: {"flagged": true/false, "reason": "이유", "category": "person/violence/adult/privacy/illegal/spam/clean"}"""
    for b64 in frames:
        data = _groq_vision(system, user, b64)
        if data.get('flagged', False):
            return True, data.get('reason', ''), data.get('category', '')
    return False, "", "clean"

def background_process_share(app, report_id, title, description, latitude, longitude, image_path=None, drawing_path=None, user_id=0):
    with app.app_context():
        report = ShareReport.query.get(report_id)
        if not report: return

        try:
            location_info = f"위도: {latitude}, 경도: {longitude}" if latitude and longitude else "위치 미제공"
            prompt = f"양평군 공유 내용을 분석해주세요.\n제목: {title or '제목 없음'}\n내용: {description or '내용 없음'}\n위치: {location_info}\n이미지: {'있음' if image_path else '없음'}\n그리기: {'있음' if drawing_path else '없음'}\n\nJSON: {{{{'category': '사건/풍경/장소/맛집/기타', 'summary': '3줄 요약', 'confidence': 0.0~1.0, 'danger_alert': true/false}}}}"
            data = _groq_json("양평군 공유 분석 AI입니다.", prompt)
            if isinstance(data, str): data = json.loads(data)
            report.ai_category = data.get('category', '기타')
            report.ai_summary = data.get('summary', '')
            report.ai_confidence = data.get('confidence', 0.5)
            report.ai_danger_alert = data.get('danger_alert', False)
        except Exception as e:
            print(f"[BG PROCESS] classify error: {e}")
            report.ai_category = '기타'

        if latitude and longitude:
            tw, vl = gps_to_town_village(latitude, longitude)
            news_summary, news_links, _ = get_local_share_context(title, description, tw, vl, exclude_id=report_id)
        else:
            news_summary, news_links, _ = get_local_share_context(title, description, '', '', exclude_id=report_id)
        report.ai_region_news = news_summary or ''
        report.ai_news_links = news_links or '[]'

        # 동영상은 무조건 보류
        v_path = getattr(report, 'video_path', None)
        if v_path and not flagged:
            flagged = True
            reason = "동영상은 관리자 승인 후 공개됩니다"
            mod_category = "video"

        if not flagged:
            for path_key in ['image_path', 'drawing_path']:
                rel_path = getattr(report, path_key, None)
                if not rel_path: continue
                abs_path = os.path.join(app.root_path, '..', rel_path.lstrip('/')).replace('/', os.sep)
                f, r, c = moderate_image(abs_path, app)
                if f:
                    flagged = True
                    reason = r
                    mod_category = c
                    break
        
        # AI danger_alert가 true이면 강제 보류
        if not flagged and report.ai_danger_alert:
            flagged = True
            reason = "AI가 개인정보 위험을 감지했습니다"
            mod_category = "privacy"

        report.is_moderated = True
        report.moderation_at = datetime.now()
        if flagged and mod_category == 'person':
            report.moderation_result = 'person'
            report.moderation_reason = reason
            report.status = 'pending_person'
            if user_id:
                from models import User, Message
                uploader = User.query.get(user_id)
                admin_user = User.query.filter(User.role == 'admin').first()
                if uploader and admin_user:
                    accept_url = f"{app.config.get('SITE_URL', 'https://test.unocum.kr')}/share-report/accept-person/{report.id}"
                    msg = Message(
                        sender_id=admin_user.id,
                        sender_name=admin_user.username,
                        sender_role='admin',
                        receiver_id=uploader.id,
                        subject='⚠️ 공유 이미지에 인물이 포함되어 있습니다',
                        content=f'{uploader.real_name or uploader.username}님, 올리신 공유글(#{report.id})에 인물 사진이 포함되어 있습니다.\n\n게시를 원하시면 아래 링크에서 모든 책임을 지겠다는 데 동의해 주세요.\n{accept_url}\n\n동의하지 않으시면 별도 조치 없이 게시가 보류됩니다.'
                    )
                    db.session.add(msg)
        elif flagged:
            report.moderation_result = 'flagged'
            report.moderation_reason = reason
            report.status = 'flagged'
        elif user_id == 0:
            report.moderation_result = 'pending'
            report.status = 'pending'
        elif report.ai_category in VALUABLE_CATEGORIES:
            report.moderation_result = 'clean'
            report.status = 'approved'
        else:
            report.moderation_result = 'clean'
            report.status = 'pending'
        db.session.commit()