from flask import Flask
from config import Config, DB_MODE
from models import db, User
from routes import register_routes
from werkzeug.security import generate_password_hash
import sys
import os
        
# 🎯 [경로 패치]: 이 파일(run.py)이 있는 폴더를 파이썬 탐색 경로 1순위로 강제 지정합니다.
# 이 코드가 있으면 이중 폴더 구조에서도 절대 에러가 나지 않습니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 🎯 [오류 해결 핵심]: DB 파일이 들어갈 instance 폴더가 진짜 존재하는지 확인하고 강제로 만듭니다.
    # 이 폴더가 없으면 SQLite는 가동을 시작하자마자 멈춥니다.
    instance_dir = os.path.join(current_dir, 'instance')
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
        print(f"[OK] Created instance folder: {instance_dir}")
    
    # DB 초기화 (순환 참조 원천 해결)
    db.init_app(app)
    
    # OAuth2 초기화 (Google/Kakao/Naver)
    from services.oauth import init_oauth
    init_oauth(app)
    
    # Jinja2 커스텀 필터 등록
    import json as _json
    app.jinja_env.filters['fromjson'] = lambda s: _json.loads(s) if s else []
    from markupsafe import Markup
    app.jinja_env.globals['nip'] = lambda: '닢'

    # 웹 경로 등록
    register_routes(app)
    
    # DB 마이그레이션: 누락된 컬럼 자동 추가
    def migrate_news_article():
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            cols = [c['name'] for c in inspector.get_columns('news_article')]
            with db.engine.connect() as conn:
                if 'like_count' not in cols:
                    conn.execute(db.text('ALTER TABLE news_article ADD COLUMN like_count INTEGER DEFAULT 0'))
                    print('[OK] like_count column added')
                if 'dislike_count' not in cols:
                    conn.execute(db.text('ALTER TABLE news_article ADD COLUMN dislike_count INTEGER DEFAULT 0'))
                    print('[OK] dislike_count column added')
                if 'ai_score' not in cols:
                    conn.execute(db.text('ALTER TABLE news_article ADD COLUMN ai_score INTEGER DEFAULT 0'))
                    print('[OK] news_article.ai_score column added')
                if 'ai_reason' not in cols:
                    try:
                        conn.execute(db.text('ALTER TABLE news_article ADD COLUMN ai_reason TEXT'))
                        print('[OK] news_article.ai_reason column added')
                    except:
                        print('[SKIP] news_article.ai_reason already exists')
            # User 테이블 마이그레이션
            user_cols = [c['name'] for c in inspector.get_columns('user')]
            with db.engine.connect() as conn:
                if 'last_payout' not in user_cols:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN last_payout DATETIME'))
                    print('[OK] user.last_payout column added')
                # 기존 회원 last_payout NULL → 지금 시각으로 설정 (추가 지급 방지)
                conn.execute(db.text("UPDATE user SET last_payout = datetime('now') WHERE last_payout IS NULL"))
                conn.commit()
                print('[OK] user last_payout NULL backfilled')
                # 잘못 지급된 닢 정정 (가입 시 1000P만 유지, 불량 내역 삭제)
                conn.execute(db.text("UPDATE user SET points = 1000 WHERE points > 1000 OR points IS NULL"))
                conn.execute(db.text("DELETE FROM point_history WHERE change_type = 'monthly'"))
                conn.commit()
                print('[OK] user points reset to 1000, erroneous monthly payouts removed')
                # 신규 컬럼들
                new_user_cols = {
                    'email': 'VARCHAR(100)',
                    'email_verified': 'BOOLEAN DEFAULT 0',
                    'reg_town': 'VARCHAR(50)',
                    'reg_village': 'VARCHAR(50)',
                    'reg_latitude': 'REAL',
                    'reg_longitude': 'REAL',
                    'curr_latitude': 'REAL',
                    'curr_longitude': 'REAL',
                    'curr_town': 'VARCHAR(50)',
                    'curr_village': 'VARCHAR(50)',
                    'location_updated_at': 'DATETIME'
                }
                for col_name, col_type in new_user_cols.items():
                    if col_name not in user_cols:
                        conn.execute(db.text(f'ALTER TABLE user ADD COLUMN {col_name} {col_type}'))
                        print(f'[OK] user.{col_name} column added')
                # 기존 town/village를 reg_town/reg_village로 복사 (최초 1회)
                if 'reg_town' in user_cols and 'town' in user_cols:
                    conn.execute(db.text('UPDATE user SET reg_town = town, reg_village = village WHERE reg_town IS NULL'))
            
            # VillageReport 테이블 마이그레이션
            vr_cols = [c['name'] for c in inspector.get_columns('village_report')]
            with db.engine.connect() as conn:
                if 'ai_category' not in vr_cols:
                    conn.execute(db.text('ALTER TABLE village_report ADD COLUMN ai_category VARCHAR(50)'))
                    print('[OK] village_report.ai_category column added')
                if 'ai_summary' not in vr_cols:
                    conn.execute(db.text('ALTER TABLE village_report ADD COLUMN ai_summary TEXT'))
                    print('[OK] village_report.ai_summary column added')
                if 'ai_confidence' not in vr_cols:
                    conn.execute(db.text('ALTER TABLE village_report ADD COLUMN ai_confidence REAL'))
                    print('[OK] village_report.ai_confidence column added')
                if 'like_count' not in vr_cols:
                    conn.execute(db.text('ALTER TABLE village_report ADD COLUMN like_count INTEGER DEFAULT 0'))
                    print('[OK] village_report.like_count column added')
                if 'dislike_count' not in vr_cols:
                    conn.execute(db.text('ALTER TABLE village_report ADD COLUMN dislike_count INTEGER DEFAULT 0'))
                    print('[OK] village_report.dislike_count column added')
            
            # NewsArticle 승인 컬럼 마이그레이션
            na_cols = [c['name'] for c in inspector.get_columns('news_article')]
            with db.engine.connect() as conn:
                for col in ['world_ai_approved', 'world_admin_approved', 'kr_yp_ai_approved', 'kr_yp_admin_approved']:
                    if col not in na_cols:
                        conn.execute(db.text(f'ALTER TABLE news_article ADD COLUMN {col} BOOLEAN DEFAULT 0'))
                        print(f'[OK] news_article.{col} column added')
            
            # ShareReport 테이블 생성 (마이그레이션으로 처리)
            try:
                sr_cols = [c['name'] for c in inspector.get_columns('share_report')]
            except:
                # 테이블이 없으면 생성
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE share_report (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            author_name VARCHAR(50),
                            title VARCHAR(200),
                            description TEXT,
                            image_path VARCHAR(300),
                            drawing_path VARCHAR(300),
                            video_path VARCHAR(300),
                            latitude REAL,
                            longitude REAL,
                            town VARCHAR(50),
                            village VARCHAR(50),
                            address VARCHAR(200),
                            status VARCHAR(20) DEFAULT 'pending',
                            admin_note TEXT,
                            ai_category VARCHAR(50),
                            ai_summary TEXT,
                            ai_confidence REAL,
                            ai_region_news TEXT,
                            ai_news_links TEXT,
                            ai_danger_alert BOOLEAN DEFAULT 0,
                            like_count INTEGER DEFAULT 0,
                            dislike_count INTEGER DEFAULT 0,
                            admin_score INTEGER DEFAULT 0,
                            leader_score INTEGER DEFAULT 0,
                            member_score INTEGER DEFAULT 0,
                            total_score INTEGER DEFAULT 0,
                            is_moderated BOOLEAN DEFAULT 0,
                            moderation_result VARCHAR(20) DEFAULT 'pending',
                            moderation_reason TEXT,
                            moderation_at DATETIME,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] share_report table created')
            else:
                # 기존 테이블에 누락 컬럼 추가
                with db.engine.connect() as conn:
                    for col in ['video_path', 'address', 'admin_score', 'leader_score', 'member_score', 'total_score', 'is_moderated', 'moderation_result', 'moderation_reason', 'moderation_at']:
                        if col not in sr_cols:
                            if col in ('admin_score', 'leader_score', 'member_score', 'total_score'):
                                conn.execute(db.text(f'ALTER TABLE share_report ADD COLUMN {col} INTEGER DEFAULT 0'))
                            elif col in ('is_moderated',):
                                conn.execute(db.text(f'ALTER TABLE share_report ADD COLUMN {col} BOOLEAN DEFAULT 0'))
                            elif col in ('video_path', 'address'):
                                conn.execute(db.text(f'ALTER TABLE share_report ADD COLUMN {col} VARCHAR(300)'))
                            elif col in ('moderation_result',):
                                conn.execute(db.text(f'ALTER TABLE share_report ADD COLUMN {col} VARCHAR(20) DEFAULT "pending"'))
                            elif col in ('moderation_reason',):
                                conn.execute(db.text(f'ALTER TABLE share_report ADD COLUMN {col} TEXT'))
                            elif col in ('moderation_at',):
                                conn.execute(db.text(f'ALTER TABLE share_report ADD COLUMN {col} DATETIME'))
                            print(f'[OK] share_report.{col} column added')
                    # user_id nullable 변경 (기존 NOT NULL → NULL 허용)
                    # SQLite는 ALTER COLUMN을 지원하지 않으므로 스킵
            
            # Post 테이블 마이그레이션
            post_cols = [c['name'] for c in inspector.get_columns('post')]
            with db.engine.connect() as conn:
                for col in ['penalty_applied', 'like_count', 'dislike_count', 'is_finalized']:
                    if col not in post_cols:
                        col_type = 'BOOLEAN DEFAULT 0' if col in ('penalty_applied', 'is_finalized') else 'INTEGER DEFAULT 0'
                        conn.execute(db.text(f'ALTER TABLE post ADD COLUMN {col} {col_type}'))
                        print(f'[OK] post.{col} column added')
            
            # Comment 테이블 마이그레이션
            comment_cols = [c['name'] for c in inspector.get_columns('comment')]
            with db.engine.connect() as conn:
                if 'user_id' not in comment_cols:
                    conn.execute(db.text('ALTER TABLE comment ADD COLUMN user_id INTEGER REFERENCES user(id)'))
                    print('[OK] comment.user_id column added')
                if 'parent_id' not in comment_cols:
                    conn.execute(db.text('ALTER TABLE comment ADD COLUMN parent_id INTEGER REFERENCES comment(id)'))
                    print('[OK] comment.parent_id column added')
            
            # User 테이블 마이그레이션 (추가)
            with db.engine.connect() as conn:
                if 'last_login' not in user_cols:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN last_login DATETIME'))
                    print('[OK] user.last_login column added')
                if 'location_share' not in user_cols:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN location_share BOOLEAN DEFAULT 0'))
                    print('[OK] user.location_share column added')
                if 'last_logout' not in user_cols:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN last_logout DATETIME'))
                    print('[OK] user.last_logout column added')
                if 'login_location_share' not in user_cols:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN login_location_share BOOLEAN DEFAULT 0'))
                    print('[OK] user.login_location_share column added')
                if 'login_town' not in user_cols:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN login_town VARCHAR(50)'))
                    print('[OK] user.login_town column added')
                if 'login_village' not in user_cols:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN login_village VARCHAR(50)'))
                    print('[OK] user.login_village column added')
                if 'login_latitude' not in user_cols:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN login_latitude FLOAT'))
                    print('[OK] user.login_latitude column added')
                if 'login_longitude' not in user_cols:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN login_longitude FLOAT'))
                    print('[OK] user.login_longitude column added')
                if 'social_id' not in user_cols:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN social_id VARCHAR(200)'))
                    print('[OK] user.social_id column added')
                if 'social_provider' not in user_cols:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN social_provider VARCHAR(20)'))
                    print('[OK] user.social_provider column added')
                if 'social_email' not in user_cols:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN social_email VARCHAR(100)'))
                    print('[OK] user.social_email column added')
            
            # ShareComment 테이블 생성
            try:
                sc_cols = [c['name'] for c in inspector.get_columns('share_comment')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE share_comment (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            share_id INTEGER NOT NULL REFERENCES share_report(id),
                            user_id INTEGER REFERENCES user(id),
                            author VARCHAR(50),
                            content TEXT NOT NULL,
                            parent_id INTEGER REFERENCES share_comment(id),
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] share_comment table created')
            
            # ConstructionNotice 테이블 생성
            try:
                cn_cols = [c['name'] for c in inspector.get_columns('construction_notice')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE construction_notice (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title VARCHAR(300) NOT NULL,
                            description TEXT,
                            location VARCHAR(200),
                            latitude REAL,
                            longitude REAL,
                            source VARCHAR(50),
                            source_url VARCHAR(500),
                            notice_type VARCHAR(50),
                            start_date DATETIME,
                            end_date DATETIME,
                            is_active BOOLEAN DEFAULT 1,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] construction_notice table created')

            # VillageAlert 테이블 생성
            try:
                va_cols = [c['name'] for c in inspector.get_columns('village_alert')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE village_alert (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title VARCHAR(200) NOT NULL,
                            content TEXT,
                            town VARCHAR(50),
                            village VARCHAR(50),
                            alert_type VARCHAR(30) DEFAULT 'general',
                            urgency VARCHAR(20) DEFAULT 'normal',
                            author_id INTEGER REFERENCES user(id),
                            author_name VARCHAR(50),
                            is_active BOOLEAN DEFAULT 1,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] village_alert table created')

            # HeritageStamp 테이블 생성
            try:
                hs_cols = [c['name'] for c in inspector.get_columns('heritage_stamp')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE heritage_stamp (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL REFERENCES user(id),
                            heritage_name VARCHAR(200) NOT NULL,
                            heritage_lat REAL,
                            heritage_lng REAL,
                            stamped_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] heritage_stamp table created')

            # LegalPost 테이블 생성 (fee/travel_allowance 누락 방지)
            try:
                cols = [c['name'] for c in inspector.get_columns('legal_post')]
                if 'fee' not in cols:
                    with db.engine.connect() as conn:
                        conn.execute(db.text('ALTER TABLE legal_post ADD COLUMN fee INTEGER'))
                        print('[OK] legal_post.fee column added')
                if 'travel_allowance' not in cols:
                    with db.engine.connect() as conn:
                        conn.execute(db.text('ALTER TABLE legal_post ADD COLUMN travel_allowance INTEGER'))
                        print('[OK] legal_post.travel_allowance column added')
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE legal_post (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title VARCHAR(200) NOT NULL,
                            content TEXT NOT NULL,
                            password VARCHAR(200) NOT NULL,
                            email VARCHAR(100) NOT NULL,
                            author_name VARCHAR(50) DEFAULT '익명',
                            answer TEXT,
                            answered_at DATETIME,
                            fee INTEGER,
                            travel_allowance INTEGER,
                            is_public BOOLEAN DEFAULT 0,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] legal_post table created')

            # LegalAppointment 테이블 생성
            try:
                _ = [c['name'] for c in inspector.get_columns('legal_appointment')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE legal_appointment (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER REFERENCES user(id),
                            name VARCHAR(50) NOT NULL,
                            email VARCHAR(100) NOT NULL,
                            phone VARCHAR(20),
                            date DATE NOT NULL,
                            time_slot VARCHAR(20) NOT NULL,
                            content TEXT,
                            status VARCHAR(20) DEFAULT 'pending',
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            approved_at DATETIME,
                            approved_by INTEGER REFERENCES user(id)
                        )
                    '''))
                    print('[OK] legal_appointment table created')

            # LawyerSchedule 테이블 생성
            try:
                _ = [c['name'] for c in inspector.get_columns('lawyer_schedule')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE lawyer_schedule (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            day_of_week INTEGER NOT NULL,
                            is_available BOOLEAN DEFAULT 1,
                            start_hour INTEGER DEFAULT 10,
                            end_hour INTEGER DEFAULT 16,
                            slot_hours INTEGER DEFAULT 2,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] lawyer_schedule table created')

            # GoogleCalendarConfig 테이블 생성
            try:
                _ = [c['name'] for c in inspector.get_columns('google_calendar_config')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE google_calendar_config (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            service_account_json TEXT,
                            calendar_id VARCHAR(200),
                            is_connected BOOLEAN DEFAULT 0,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] google_calendar_config table created')

            # PsychoPost 테이블 생성
            try:
                _ = [c['name'] for c in inspector.get_columns('psycho_post')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE psycho_post (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title VARCHAR(200) NOT NULL,
                            content TEXT NOT NULL,
                            password VARCHAR(200) NOT NULL,
                            email VARCHAR(100) NOT NULL,
                            author_name VARCHAR(50) DEFAULT '익명',
                            answer TEXT, answered_at DATETIME,
                            fee INTEGER, travel_allowance INTEGER,
                            is_public BOOLEAN DEFAULT 0,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] psycho_post table created')

            # PsychoAppointment 테이블 생성
            try:
                _ = [c['name'] for c in inspector.get_columns('psycho_appointment')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE psycho_appointment (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER REFERENCES user(id),
                            name VARCHAR(50) NOT NULL, email VARCHAR(100) NOT NULL,
                            phone VARCHAR(20), date DATE NOT NULL,
                            time_slot VARCHAR(20) NOT NULL, location VARCHAR(200),
                            content TEXT, status VARCHAR(20) DEFAULT 'pending',
                            fee INTEGER, travel_allowance INTEGER,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            approved_at DATETIME, approved_by INTEGER REFERENCES user(id)
                        )
                    '''))
                    print('[OK] psycho_appointment table created')

            # PsychoDoctorSchedule 테이블 생성
            try:
                _ = [c['name'] for c in inspector.get_columns('psycho_doctor_schedule')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE psycho_doctor_schedule (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            day_of_week INTEGER NOT NULL, is_available BOOLEAN DEFAULT 1,
                            start_hour INTEGER DEFAULT 10, end_hour INTEGER DEFAULT 16,
                            slot_hours INTEGER DEFAULT 2,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] psycho_doctor_schedule table created')

            # PsychoGoogleCalendarConfig 테이블 생성
            try:
                _ = [c['name'] for c in inspector.get_columns('psycho_google_calendar_config')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE psycho_google_calendar_config (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            service_account_json TEXT, calendar_id VARCHAR(200),
                            is_connected BOOLEAN DEFAULT 0,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] psycho_google_calendar_config table created')

            # RampApplication 테이블 생성
            try:
                _ = [c['name'] for c in inspector.get_columns('ramp_application')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE ramp_application (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name VARCHAR(50) NOT NULL, email VARCHAR(100) NOT NULL,
                            phone VARCHAR(20) NOT NULL, location VARCHAR(200) NOT NULL,
                            photo_path VARCHAR(300), step_height VARCHAR(50) NOT NULL,
                            ownership VARCHAR(20) NOT NULL,
                            agree_removal BOOLEAN DEFAULT 0, agree_damage BOOLEAN DEFAULT 0,
                            signed_at DATETIME, status VARCHAR(20) DEFAULT 'pending',
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] ramp_application table created')

            # FriendGroup 테이블 생성
            try:
                _ = [c['name'] for c in inspector.get_columns('friend_group')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE friend_group (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL REFERENCES user(id),
                            name VARCHAR(100) NOT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] friend_group table created')

            # Friend 테이블 생성
            try:
                _ = [c['name'] for c in inspector.get_columns('friend')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE friend (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            requester_id INTEGER NOT NULL REFERENCES user(id),
                            receiver_id INTEGER NOT NULL REFERENCES user(id),
                            group_id INTEGER REFERENCES friend_group(id),
                            status VARCHAR(20) DEFAULT 'pending',
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] friend table created')

            # Friend 테이블 컬럼 마이그레이션 (이미 존재하는 테이블에 누락 컬럼 추가)
            try:
                friend_cols = [c['name'] for c in inspector.get_columns('friend')]
                with db.engine.connect() as conn:
                    for col, col_type in [('requester_id', 'INTEGER DEFAULT 0'),
                                          ('receiver_id', 'INTEGER DEFAULT 0'),
                                          ('group_id', 'INTEGER'),
                                          ('status', "VARCHAR(20) DEFAULT 'pending'"),
                                          ('updated_at', 'DATETIME')]:
                        if col not in friend_cols:
                            conn.execute(db.text(f'ALTER TABLE friend ADD COLUMN {col} {col_type}'))
                            print(f'[OK] friend.{col} column added')
            except:
                pass

            # PostVote 테이블 생성
            try:
                _ = [c['name'] for c in inspector.get_columns('post_vote')]
            except:
                with db.engine.connect() as conn:
                    conn.execute(db.text('''
                        CREATE TABLE post_vote (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            post_id INTEGER NOT NULL REFERENCES post(id),
                            user_id INTEGER NOT NULL REFERENCES user(id),
                            vote_type VARCHAR(10),
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] post_vote table created')

    if DB_MODE != 'postgresql':
        try:
            migrate_news_article()
        except Exception as e:
            print(f'[SKIP] news_article migration: {e}')

    # Friend 요청 메시지 ↔ Friend 레코드 불일치 보정
    try:
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
        from models import Post
        from datetime import datetime
        expired = Post.query.filter(Post.total_score <= -50, Post.deadline != None, Post.deadline < datetime.now()).all()
        for p in expired:
            db.session.delete(p)
        if expired:
            db.session.commit()
            print(f'[OK] {len(expired)} expired post(s) deleted at startup')
    except Exception as e:
        print(f'[SKIP] expired post cleanup: {e}')

    # User 테이블 social_id 등 신규 컬럼 별도 마이그레이션 (기존 migrate_news_article 스킵 방지)
    try:
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            user_cols = [c['name'] for c in inspector.get_columns('user')]
            with db.engine.connect() as conn:
                for col in ['social_id', 'social_provider', 'social_email', 'email_verification_token', 'email_verification_sent_at', 'is_neighbor']:
                    if col not in user_cols:
                        col_type = 'VARCHAR(200)' if col in ('social_id', 'email_verification_token') else 'VARCHAR(100)' if col in ('social_email',) else 'VARCHAR(20)' if col in ('social_provider',) else 'BOOLEAN DEFAULT 0' if col in ('is_neighbor',) else 'DATETIME'
                        conn.execute(db.text(f'ALTER TABLE user ADD COLUMN {col} {col_type}'))
                        print(f'[OK] user.{col} column added')
    except Exception as e:
        print(f'[SKIP] social column migration: {e}')

    # gunicorn에서도 실행되도록 초기화 보장
    with app.app_context():
        if DB_MODE != 'postgresql':
            db.create_all()
        if not User.query.first():
            hashed_pw = generate_password_hash('pw1234')
            demo_users = [
                User(username='admin1', password=hashed_pw, role='admin', real_name="홍길동", phone="010-1111-2222", town="양평읍", village="양근리", is_verified_resident=True),
                User(username='leader1', password=hashed_pw, role='leader', real_name="이순신", phone="010-3333-4444", town="강상면", village="병산리", is_verified_resident=True),
                User(username='user1', password=hashed_pw, role='user', real_name="강감찬", phone="010-5555-6666", town="용문면", village="다문리", is_verified_resident=False)
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

if __name__ == '__main__':
    print("[함께사는양평] 통합 관제 서버가 켜졌습니다. http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)