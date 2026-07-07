import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DB_MODE = os.getenv('DB_MODE', 'sqlite')  # sqlite or postgresql

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback_dev_key')
    INSTANCE_PATH = os.path.join(BASE_DIR, 'instance')
    if DB_MODE == 'postgresql':
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://yp_user:yp_pass@localhost:5432/yp_db')
    else:
        db_name = os.getenv('DB_NAME', 'yangpyeong_v10.db')
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(INSTANCE_PATH, db_name)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = bool(os.getenv('SESSION_COOKIE_SECURE', os.getenv('SITE_URL','').startswith('https')))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024
    JUSO_API_KEY = os.getenv('JUSO_API_KEY', '')
    DATA_GO_KR_API_KEY = os.getenv('DATA_GO_KR_API_KEY', '')
    GG_TRAFFIC_API_KEY = os.getenv('GG_TRAFFIC_API_KEY', '')
    GG_BUILDING_API_KEY = os.getenv('GG_BUILDING_API_KEY', '')
    EX_CONSTRUCTION_API_KEY = os.getenv('EX_CONSTRUCTION_API_KEY', '8485113604')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    SMTP_HOST = os.getenv('SMTP_HOST', 'email-smtp.ap-northeast-2.amazonaws.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    MAIL_FROM = os.getenv('MAIL_FROM', 'yp@unocum.kr')
    SITE_URL = os.getenv('SITE_URL', 'https://test.unocum.kr')

    # OAuth2
    KAKAO_REST_API_KEY = os.getenv('KAKAO_REST_API_KEY', '')
    KAKAO_JAVASCRIPT_KEY = os.getenv('KAKAO_JAVASCRIPT_KEY', '')
    NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID', '')
    NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET', '')
    NAVER_SEARCH_CLIENT_ID = os.getenv('NAVER_SEARCH_CLIENT_ID', 'Vi403Ckfdg8NGRPDfBin')
    NAVER_SEARCH_CLIENT_SECRET = os.getenv('NAVER_SEARCH_CLIENT_SECRET', 'bepKiJZvWx')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')

    GOOGLE_OAUTH = {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
    } if GOOGLE_CLIENT_ID else None

    KAKAO_OAUTH = {
        'client_id': KAKAO_REST_API_KEY,
    } if KAKAO_REST_API_KEY else None

    NAVER_OAUTH = {
        'client_id': NAVER_CLIENT_ID,
        'client_secret': NAVER_CLIENT_SECRET,
    } if NAVER_CLIENT_ID else None