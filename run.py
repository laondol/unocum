import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
from flask import Flask
from config import Config
from models import db, User
from routes import register_routes
from tongbot_routes import tongbot_bp
from route_modules.construction_bp import construction_bp
from route_modules.share_bp import share_bp
from route_modules.legal_bp import legal_bp
from route_modules.village_bp import village_bp
from route_modules.friends_bp import friends_bp
from route_modules.user_bp import user_bp
from route_modules.board_bp import board_bp
from route_modules.admin_bp import admin_bp
from route_modules.news_bp import news_bp
from route_modules.mypage_bp import mypage_bp
from route_modules.search_bp import search_bp
from route_modules.message_bp import message_bp
from route_modules.service_bp import service_bp
from route_modules.auth_bp import auth_bp
from route_modules.page_bp import page_bp
from route_modules.legal_bp import legal_bp
from route_modules.psycho_bp import psycho_bp
from route_modules.epub_bp import epub_bp
from route_modules.guide_bp import guide_bp
from route_modules.did_bp import did_bp
from werkzeug.security import generate_password_hash
import sys
import os
import time

# 한국 시간 (KST, UTC+9) 사용
os.environ['TZ'] = 'Asia/Seoul'
try:
    time.tzset()
except AttributeError:
    pass  # Windows는 tzset() 미지원
        
# 🎯 [경로 패치]: 이 파일(run.py)이 있는 폴더를 파이썬 탐색 경로 1순위로 강제 지정합니다.
# 이 코드가 있으면 이중 폴더 구조에서도 절대 에러가 나지 않습니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # DB 초기화 (순환 참조 원천 해결)
    db.init_app(app)

    # OAuth2 초기화 (Google/Kakao/Naver)
    from services.oauth import init_oauth
    init_oauth(app)
    
    # Jinja2 커스텀 필터 등록
    import json as _json
    app.jinja_env.filters['fromjson'] = lambda s: _json.loads(s) if s else []
    app.jinja_env.filters['comma'] = lambda v: f'{int(v or 0):,}'
    from markupsafe import Markup
    app.jinja_env.globals['nip'] = lambda: '닢'

    # 웹 경로 등록
    register_routes(app)
    app.register_blueprint(tongbot_bp)
    app.register_blueprint(construction_bp)
    app.register_blueprint(share_bp)
    app.register_blueprint(legal_bp)
    app.register_blueprint(village_bp)
    app.register_blueprint(friends_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(board_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(news_bp)
    app.register_blueprint(mypage_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(message_bp)
    app.register_blueprint(service_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(page_bp)
    app.register_blueprint(psycho_bp)
    app.register_blueprint(epub_bp)
    app.register_blueprint(guide_bp)
    app.register_blueprint(did_bp)
    
    # 백그라운드 캐시 갱신 스케줄러
    import threading, time
    def cache_scheduler():
        time.sleep(10)  # 앱 시작 후 10초 대기
        while True:
            try:
                with app.app_context():
                    from services.cache_refresh import refresh_all_caches
                    refresh_all_caches()
            except Exception as e:
                print(f"[CACHE] error: {e}")
            time.sleep(600)  # 10분마다 갱신
    threading.Thread(target=cache_scheduler, daemon=True).start()
    # 알림 체크 스레드
    def notification_scheduler():
        import time
        while True:
            time.sleep(5)
            try:
                from tongbot_routes import run_notification_check
                run_notification_check()
            except Exception as e:
                print(f'[NOTI] error: {e}')
            time.sleep(30)
    threading.Thread(target=notification_scheduler, daemon=True).start()

    # 경로 재계산 주기 워커 (스레드 우선 보강용 safety net)
    def route_recalc_scheduler():
        import time
        from models import User
        time.sleep(60)  # 앱 시작 후 60초 대기
        while True:
            try:
                with app.app_context():
                    for u in User.query.all():
                        try:
                            from services.route_recalc import recalc_user_routes
                            recalc_user_routes(u.id)
                        except Exception as e:
                            print(f'[ROUTE] user {u.id} recalc error: {e}')
            except Exception as e:
                print(f'[ROUTE] scheduler error: {e}')
            time.sleep(600)  # 10분마다 전체 사용자 재계산
    threading.Thread(target=route_recalc_scheduler, daemon=True).start()
    
    # Friend 요청 메시지 ↔ Friend 레코드 불일치 보정
    try:
        with app.app_context():
            from models import Message, Friend
            orphan_msgs = Message.query.filter(
                Message.subject.in_(['👋 벗 맺기 신청', '👋 벗 신청'])
            ).all()
            for m in orphan_msgs:
                existing = Friend.query.filter(
                    ((Friend.requester_id == m.sender_id) & (Friend.receiver_id == m.receiver_id)) |
                    ((Friend.requester_id == m.receiver_id) & (Friend.receiver_id == m.sender_id))
                ).first()
                if not existing:
                    f = Friend(requester_id=m.sender_id, receiver_id=m.receiver_id, status='pending')
                    db.session.add(f)
            if orphan_msgs:
                db.session.commit()
                print(f'[OK] {len(orphan_msgs)} orphaned friend request(s) fixed')
    except Exception as e:
        print(f'[SKIP] orphan friend fix: {e}')

    # PointHistory balance_after 일괄 보정 (실제 user.points 기준)
    try:
        with app.app_context():
            from models import User, PointHistory
            from sqlalchemy import inspect as sa_inspect
            inspector = sa_inspect(db.engine)
            if 'point_history' in [t for t in inspector.get_table_names()]:
                all_users = User.query.all()
                for u in all_users:
                    records = PointHistory.query.filter_by(user_id=u.id).order_by(PointHistory.created_at.asc()).all()
                    running = 0
                    for r in records:
                        running += r.amount
                        r.balance_after = running
                db.session.commit()
                print('[OK] point_history balance_after recalculated for all users')
    except Exception as e:
        print(f'[SKIP] point_history recalculation: {e}')

    # 낙제 게시물 30일 deadline 초과 자동 삭제
    try:
        with app.app_context():
            from models import Post
            from datetime import datetime, timedelta
            expired = Post.query.filter(Post.total_score <= -50, Post.deadline != None, Post.deadline < datetime.now()).all()
            for p in expired:
                db.session.delete(p)
            if expired:
                db.session.commit()
                print(f'[OK] {len(expired)} expired post(s) deleted at startup')
    except Exception as e:
        print(f'[SKIP] expired post cleanup: {e}')

    # 상담게시판 보류글 1일 자동 삭제
    try:
        with app.app_context():
            from models import LegalPost, PsychoPost
            from sqlalchemy import or_
            cutoff = datetime.now() - timedelta(days=1)
            flagged_legal = LegalPost.query.filter(
                LegalPost.status == 'flagged',
                LegalPost.created_at < cutoff,
                or_(
                    LegalPost.flagged_decision_at == None,
                    LegalPost.flagged_decision_at < cutoff
                )
            ).all()
            for p in flagged_legal:
                db.session.delete(p)
            flagged_psycho = PsychoPost.query.filter(
                PsychoPost.status == 'flagged',
                PsychoPost.created_at < cutoff
            ).all()
            for p in flagged_psycho:
                db.session.delete(p)
            if flagged_legal or flagged_psycho:
                db.session.commit()
                print(f'[OK] {len(flagged_legal)+len(flagged_psycho)} flagged consultation post(s) auto-deleted')
    except Exception as e:
        print(f'[SKIP] flagged post cleanup: {e}')

    # gps_calibration 테이블 생성
    try:
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'gps_calibration' not in inspector.get_table_names():
                db.create_all()
                print('[OK] gps_calibration table created')
    except Exception as e:
        print(f'[SKIP] gps_calibration migration: {e}')

    # temp_email_verify.redirect 컬럼 마이그레이션
    try:
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tbl_names = inspector.get_table_names()
            if 'temp_email_verify' in tbl_names:
                tev_cols = [c['name'] for c in inspector.get_columns('temp_email_verify')]
                if 'redirect' not in tev_cols:
                    with db.engine.connect() as conn:
                        conn.execute(db.text('ALTER TABLE temp_email_verify ADD COLUMN redirect VARCHAR(200) DEFAULT "/legal/list"'))
                        conn.commit()
                        print('[OK] temp_email_verify.redirect column added')
    except Exception as e:
        print(f'[SKIP] temp_email_verify migration: {e}')

    # TongBotSchedule 반복/종일 컬럼 마이그레이션
    try:
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            sched_cols = [c['name'] for c in inspector.get_columns('tong_bot_schedule')]
            with db.engine.connect() as conn:
                for col, ct in [('is_allday','BOOLEAN DEFAULT 0'),('is_recurring','BOOLEAN DEFAULT 0'),('repeat_type','VARCHAR(20) DEFAULT \'\''),('repeat_end_date','TIMESTAMP'),('repeat_interval','INTEGER DEFAULT 1'),('repeat_infinite','BOOLEAN DEFAULT 0'),('repeat_weekdays','INTEGER DEFAULT 0'),('repeat_week_of_month','INTEGER DEFAULT 0'),('repeat_month_of_year','INTEGER DEFAULT 0'),('reminder_minutes','INTEGER DEFAULT 0')]:
                    if col not in sched_cols:
                        conn.execute(db.text(f'ALTER TABLE tong_bot_schedule ADD COLUMN {col} {ct}'))
                        conn.commit()
                        print(f'[OK] tong_bot_schedule.{col} column added')
    except Exception as e:
        print(f'[SKIP] schedule recurring migration: {e}')
    # ScheduleReminderLog 테이블 생성
    try:
        with app.app_context():
            from sqlalchemy import inspect as _insp2
            insp2 = _insp2(db.engine)
            if 'schedule_reminder_log' not in insp2.get_table_names():
                with db.engine.connect() as _c:
                    _c.execute(db.text("CREATE TABLE schedule_reminder_log (id SERIAL PRIMARY KEY, user_id INTEGER, schedule_id INTEGER, occ_date VARCHAR(20), title VARCHAR(200), event_date TIMESTAMP, sent_at TIMESTAMP, seen BOOLEAN DEFAULT FALSE)"))
                    _c.commit()
                print('[OK] schedule_reminder_log table created')
    except Exception as e:
        print(f'[SKIP] schedule_reminder_log migration: {e}')
    try:
        with app.app_context():
            from sqlalchemy import inspect as _insp3
            insp3 = _insp3(db.engine)
            if 'message_reminder_log' not in insp3.get_table_names():
                with db.engine.connect() as _c:
                    _c.execute(db.text("CREATE TABLE message_reminder_log (id SERIAL PRIMARY KEY, user_id INTEGER, message_id INTEGER, sender_name VARCHAR(50), subject VARCHAR(200), sent_at TIMESTAMP, seen BOOLEAN DEFAULT FALSE)"))
                    _c.commit()
                print('[OK] message_reminder_log table created')
    except Exception as e:
        print(f'[SKIP] message_reminder_log migration: {e}')

    # 이동/귀가 기존 메모 → format_memo_compact 백필
    try:
        with app.app_context():
            from models import TongBotSchedule
            from services.directions import format_memo_compact
            import json
            targets = TongBotSchedule.query.filter(
                TongBotSchedule.content.isnot(None),
                TongBotSchedule.content != ''
            ).all()
            updated = 0
            for t in targets:
                if not (t.title and ('이동' in t.title or '귀가' in t.title)):
                    continue
                try:
                    plan = json.loads(t.content)
                    if plan.get("compact"):
                        continue
                    compact = format_memo_compact(plan)
                    plan["compact"] = compact
                    t.content = json.dumps(plan, ensure_ascii=False)
                    t.memo = compact
                    updated += 1
                except:
                    pass
            if updated:
                db.session.commit()
                print(f'[OK] {updated} 이동/귀가 entries backfilled with compact memo')
    except Exception as e:
        print(f'[SKIP] compact memo backfill: {e}')

    # gunicorn에서도 실행되도록 초기화 보장
    with app.app_context():
        db.create_all()
        if not User.query.first():
            hashed_pw = generate_password_hash('pw1234')
            demo_users = [
                User(username='admin1', email='admin@unocum.kr', password=hashed_pw, role='admin', real_name="홍길동", phone="010-1111-2222", town="양평읍", village="양근리", is_verified_resident=True),
                User(username='leader1', email='eou@kakao.com', password=hashed_pw, role='leader', real_name="이순신", phone="010-3333-4444", town="강상면", village="병산리", is_verified_resident=True, managed_pages='legal,psycho,village,ramp'),
                User(username='user1', email='user@test.com', password=hashed_pw, role='user', real_name="강감찬", phone="010-5555-6666", town="용문면", village="다문리", is_verified_resident=False)
            ]
            for u in demo_users:
                db.session.add(u)
            db.session.commit()
            for u in demo_users:
                u.last_payout = datetime.now()
            db.session.commit()
            print("[OK] Demo accounts created (pw: pw1234)")
        try:
            import threading
            t = threading.Thread(target=lambda: (
                __import__('services.rag', fromlist=['rebuild_index']).rebuild_index(app)
            ), daemon=True)
            t.start()
        except Exception as e:
            print(f"[RAG] 인덱스 재구축 스킵: {e}")

    return app

app = create_app()



@app.after_request
def security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'SAMEORIGIN'
    resp.headers['X-XSS-Protection'] = '1; mode=block'
    resp.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if resp.mimetype == 'text/html':
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
    return resp

if __name__ == '__main__':
    print("[함께사는양평] 통합 관제 서버가 켜졌습니다. http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)