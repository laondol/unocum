import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # 세션 보안 키
    SECRET_KEY = "yangpyeong_autonomous_platform_2026"
    
    # 1. SQLite 데이터베이스 경로를 instance 폴더 내부로 완전 격리
    INSTANCE_PATH = os.path.join(BASE_DIR, 'instance')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(INSTANCE_PATH, 'yangpyeong_v10.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 2. 업로드 스토리지 경로 설정
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 최대 16MB 제한