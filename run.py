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
        print(f"📁 보안 저장소 폴더를 생성했습니다: {instance_dir}")
    
    # DB 초기화 (순환 참조 원천 해결)
    db.init_app(app)
    
    # 웹 경로 등록
    register_routes(app)
    
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
    db.session.bulk_save_objects(demo_users)
    db.session.commit()
    print("🌳 [함께사는양평] 가입자 데이터베이스 & 데모 계정이 생성되었습니다. (PW: pw1234)")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_demo_system()
        
    print("🚀 [함께사는양평] 통합 관제 서버가 켜졌습니다. http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)