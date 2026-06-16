import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DB_MODE = os.getenv('DB_MODE', 'sqlite')  # sqlite or postgresql

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback_dev_key')
    INSTANCE_PATH = os.path.join(BASE_DIR, 'instance')
    if DB_MODE == 'postgresql':
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://yp_user:yp_pass@localhost:5432/yp_db')
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(INSTANCE_PATH, 'yangpyeong_v10.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    KAKAO_REST_API_KEY = os.getenv('KAKAO_REST_API_KEY', '')
    KAKAO_JAVASCRIPT_KEY = os.getenv('KAKAO_JAVASCRIPT_KEY', '')
    JUSO_API_KEY = os.getenv('JUSO_API_KEY', '')
    DATA_GO_KR_API_KEY = os.getenv('DATA_GO_KR_API_KEY', '')
    GG_TRAFFIC_API_KEY = os.getenv('GG_TRAFFIC_API_KEY', '')
    NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID', '')
    NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET', '')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    SMTP_HOST = os.getenv('SMTP_HOST', 'email-smtp.ap-northeast-2.amazonaws.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    MAIL_FROM = os.getenv('MAIL_FROM', 'yp@unocum.kr')