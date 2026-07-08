import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from run import app
from models import db, ShareReport, User, Message
from services.ai_service import moderate_image, _groq_json
from datetime import datetime

INTERVAL = 5
VALUABLE_CATEGORIES = {'사건', '풍경', '장소', '맛집', '가게', '음식'}

def moderate_report(report):
    if report.video_path:
        report.status = 'pending_review'
        report.moderation_result = 'video'
        report.moderation_reason = '동영상은 관리자 승인 후 공개됩니다'
        report.is_moderated = True
        report.moderation_at = datetime.now()
        print(f"[WORKER] #{report.id} video → pending_review")
        return

    paths = []
    if report.image_path: paths.append(report.image_path)
    if report.extra_images:
        paths += [e.strip() for e in report.extra_images.split(',') if e.strip()]
    if report.drawing_path: paths.append(report.drawing_path)

    for rel_path in paths:
        abs_path = os.path.join(app.root_path, rel_path.lstrip('/'))
        if not os.path.exists(abs_path): continue
        flagged, reason, cat = moderate_image(abs_path)
        if not flagged and cat != 'unanalyzable':
            continue

        report.is_moderated = True
        report.moderation_at = datetime.now()
        report.moderation_reason = reason
        report.moderation_result = cat

        if cat == 'unanalyzable':
            report.status = 'pending'
            print(f"[WORKER] #{report.id} unanalyzable → pending")
        elif cat == 'person':
            report.status = 'pending_person'
            print(f"[WORKER] #{report.id} person → pending_person")
            _notify_person(report)
        else:
            report.status = 'flagged'
            print(f"[WORKER] #{report.id} {cat} → flagged")
        return

    report.is_moderated = True
    report.moderation_at = datetime.now()
    report.moderation_result = 'clean'
    report.status = 'approved' if report.ai_category in VALUABLE_CATEGORIES else 'pending'
    print(f"[WORKER] #{report.id} clean → {report.status}")

def _notify_person(report):
    try:
        uploader = User.query.get(report.user_id)
        admin_user = User.query.filter(User.role == 'admin').first()
        if uploader and admin_user:
            accept_url = f"{app.config.get('SITE_URL', 'https://test.unocum.kr')}/share-report/accept-person/{report.id}"
            msg = Message(
                sender_id=admin_user.id, sender_name=admin_user.username, sender_role='admin',
                receiver_id=uploader.id,
                subject='공유 이미지에 인물이 포함되어 있습니다',
                content=f'{uploader.real_name or uploader.username}님, 올리신 공유글(#{report.id})에 인물 사진이 포함되어 있습니다.\n\n게시를 원하시면 아래 링크에서 모든 책임을 지겠다는 데 동의해 주세요.\n{accept_url}\n\n동의하지 않으시면 별도 조치 없이 게시가 보류됩니다.'
            )
            db.session.add(msg)
    except:
        pass

def process_all():
    with app.app_context():
        reports = ShareReport.query.filter(
            db.or_(ShareReport.is_moderated == False, ShareReport.is_moderated == None)
        ).order_by(ShareReport.created_at.asc()).all()
        if not reports:
            return
        for report in reports:
            try:
                moderate_report(report)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"[WORKER] #{report.id} error: {e}")

if __name__ == '__main__':
    print("[AI MODERATION WORKER] 시작됨")
    while True:
        try:
            process_all()
        except Exception as e:
            print(f"[WORKER] error: {e}")
        time.sleep(INTERVAL)
