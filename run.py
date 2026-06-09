from flask import Flask
from config import Config
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
                # 잘못 지급된 포인트 정정 (가입 시 1000P만 유지, 불량 내역 삭제)
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
                            user_id INTEGER NOT NULL,
                            author_name VARCHAR(50),
                            title VARCHAR(200),
                            description TEXT,
                            image_path VARCHAR(300),
                            drawing_path VARCHAR(300),
                            latitude REAL,
                            longitude REAL,
                            town VARCHAR(50),
                            village VARCHAR(50),
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
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    print('[OK] share_report table created')
    
    migrate_news_article()
    
    return app

app = create_app()

# 프리젠테이션용 데모 데이터베이스 세팅 로직
def init_demo_system():
    if User.query.first(): return
    hashed_pw = generate_password_hash('pw1234')
    demo_users = [
        User(username='admin1', password=hashed_pw, role='admin', real_name="홍길동", phone="010-1111-2222", town="양평읍", village="양근리", is_verified_resident=True),
        User(username='leader1', password=hashed_pw, role='leader', real_name="이순신", phone="010-3333-4444", town="강상면", village="병산리", is_verified_resident=True),
        User(username='user1', password=hashed_pw, role='user', real_name="강감찬", phone="010-5555-6666", town="용문면", village="다문리", is_verified_resident=False)
    ]
    for u in demo_users:
        db.session.add(u)
    db.session.commit()
    # 데모 계정 last_payout 설정 (가입 시각, 30일 지나야 월급 지급)
    for u in demo_users:
        from datetime import datetime
        u.last_payout = datetime.now()
    db.session.commit()
    print("[OK] Demo accounts created (pw: pw1234)")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_demo_system()
        
    print("[함께사는양평] 통합 관제 서버가 켜졌습니다. http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)