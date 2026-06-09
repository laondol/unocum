from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user') # admin, leader, user
    
    # 이웃 자치 데이터
    real_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))                    # 이메일 (인증용)
    email_verified = db.Column(db.Boolean, default=False)
    town = db.Column(db.String(50))                      # 읍/면 (현재)
    village = db.Column(db.String(50))                   # 리 (현재)
    # 가입 시 위치 (과거 위치)
    reg_town = db.Column(db.String(50))                  # 가입 시 읍/면
    reg_village = db.Column(db.String(50))               # 가입 시 리
    reg_latitude = db.Column(db.Float)                   # 가입 시 위도
    reg_longitude = db.Column(db.Float)                  # 가입 시 경도
    # 현재 위치 (갱신용)
    curr_latitude = db.Column(db.Float)                  # 현재 위도
    curr_longitude = db.Column(db.Float)                 # 현재 경도
    curr_town = db.Column(db.String(50))                 # 현재 읍/면
    curr_village = db.Column(db.String(50))              # 현재 리
    location_updated_at = db.Column(db.DateTime)         # 위치 갱신 일시
    
    is_verified_resident = db.Column(db.Boolean, default=False) # 주민 자치인증 완료 여부
    verified_method = db.Column(db.String(30), default='none')  # gps, bill, none
    bill_image_path = db.Column(db.String(300))                  # 고지서 사진 경로 (인증 후 즉시 파기)
    
    points = db.Column(db.Integer, default=1000)         # 물맑은머니 포인트
    is_paid = db.Column(db.Boolean, default=False)       # 유료회원 여부
    last_payout = db.Column(db.DateTime)                 # 마지막 지급일 (가입일 기준 30일 주기)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author_name = db.Column(db.String(50))
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    category = db.Column(db.String(50), default='일반제안')     # 일반제안, 양평소식, 마을제보
    status = db.Column(db.String(20), default='제안')           # 제안, 하고싶은, 하고있는, 했던거, 하는일
    
    # AI 지킴이 심사 데이터
    ai_score = db.Column(db.Integer, default=0)
    ai_summary = db.Column(db.Text)
    ai_reason = db.Column(db.Text)
    ai_debate_log = db.Column(db.Text, default="[]")
    ai_improvement_tip = db.Column(db.Text)
    
    # 거버넌스 채점단 가중치
    admin_score = db.Column(db.Integer, default=0)
    leader_score = db.Column(db.Integer, default=0)
    member_score = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, default=0)
    
    file_path = db.Column(db.String(300))                       # 주민 업로드/그림 저장 경로
    is_forced_approved = db.Column(db.Boolean, default=False)   # 지킴이 즉시 승인 여부
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now)   # 수정일 (48시간 대기 리셋용)
    deadline = db.Column(db.DateTime)                           # 낙제 시 30일 수정 기한

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    author = db.Column(db.String(50))
    content = db.Column(db.Text, nullable=False)
    total_score = db.Column(db.Integer, default=0)              # 댓글 AI 방역용
    created_at = db.Column(db.DateTime, default=datetime.now)

class NewsArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    ai_score = db.Column(db.Integer, default=0)
    summary = db.Column(db.Text)
    content = db.Column(db.Text)
    source_url = db.Column(db.String(500))
    source_name = db.Column(db.String(200))
    image_path = db.Column(db.String(300))
    category = db.Column(db.String(50), default='세계뉴스')
    is_selected = db.Column(db.Boolean, default=False)
    is_ai_generated = db.Column(db.Boolean, default=False)
    like_count = db.Column(db.Integer, default=0)
    dislike_count = db.Column(db.Integer, default=0)
    # 승인 상태 (탭별)
    world_ai_approved = db.Column(db.Boolean, default=False)
    world_admin_approved = db.Column(db.Boolean, default=False)
    kr_yp_ai_approved = db.Column(db.Boolean, default=False)
    kr_yp_admin_approved = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now)

class NewsComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    news_id = db.Column(db.Integer, db.ForeignKey('news_article.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author_name = db.Column(db.String(50))
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('news_comment.id'))  # 답글용
    ai_score = db.Column(db.Integer, default=0)
    is_hidden = db.Column(db.Boolean, default=False)  # AI 낙제 시 숨김
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now)
    
    replies = db.relationship('NewsComment', backref=db.backref('parent', remote_side=[id]), lazy=True)

class NewsRecommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    news_id = db.Column(db.Integer, db.ForeignKey('news_article.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author_name = db.Column(db.String(50))
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    is_approved = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)

class PointHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    change_type = db.Column(db.String(30))  # signup, monthly, post, comment, like, admin_adjust, payment
    amount = db.Column(db.Integer, default=0)  # 양수: 적립, 음수: 차감
    balance_after = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    related_id = db.Column(db.Integer)  # post_id, comment_id 등
    created_at = db.Column(db.DateTime, default=datetime.now)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender_name = db.Column(db.String(50))
    sender_role = db.Column(db.String(20))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200))
    content = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class ShareReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author_name = db.Column(db.String(50))
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    image_path = db.Column(db.String(300))
    drawing_path = db.Column(db.String(300))       # 그리기 이미지 경로
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    town = db.Column(db.String(50))                # 읍/면
    village = db.Column(db.String(50))             # 리
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    admin_note = db.Column(db.Text)
    # AI 분류
    ai_category = db.Column(db.String(50))         # 사건, 풍경, 장소, 맛집, 기타
    ai_summary = db.Column(db.Text)                # AI 요약
    ai_confidence = db.Column(db.Float)            # 분류 신뢰도
    ai_region_news = db.Column(db.Text)            # 동일 지역 관련 뉴스 요약
    ai_news_links = db.Column(db.Text)             # 관련 뉴스 원본 링크 (JSON)
    ai_danger_alert = db.Column(db.Boolean, default=False)  # 위험 알림 여부
    like_count = db.Column(db.Integer, default=0)
    dislike_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now)