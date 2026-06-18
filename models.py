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
    
    points = db.Column(db.Integer, default=1000)         # 물맑은머니 닢
    is_paid = db.Column(db.Boolean, default=False)       # 유료회원 여부
    last_payout = db.Column(db.DateTime)                 # 마지막 지급일 (가입일 기준 30일 주기)
    last_login = db.Column(db.DateTime)                  # 마지막 로그인 일시
    last_logout = db.Column(db.DateTime)                 # 마지막 로그아웃 일시
    login_latitude = db.Column(db.Float)                 # 마지막 로그인 위도
    login_longitude = db.Column(db.Float)                # 마지막 로그인 경도
    login_town = db.Column(db.String(50))                # 마지막 로그인 읍/면
    login_village = db.Column(db.String(50))             # 마지막 로그인 리
    login_location_share = db.Column(db.Boolean, default=False) # 벗에게 로그인 위치 공유 동의
    location_share = db.Column(db.Boolean, default=False) # 위치 공유 동의
    is_neighbor = db.Column(db.Boolean, default=False)  # 이웃주민 (집에서 위치인증 완료)

    # SNS 연동 로그인
    social_id = db.Column(db.String(200), unique=True, nullable=True)
    social_provider = db.Column(db.String(20), nullable=True)  # google, kakao, naver
    social_email = db.Column(db.String(100), nullable=True)
    email_verification_token = db.Column(db.String(100), nullable=True)
    email_verification_sent_at = db.Column(db.DateTime, nullable=True)

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
    penalty_applied = db.Column(db.Boolean, default=False)
    like_count = db.Column(db.Integer, default=0)
    dislike_count = db.Column(db.Integer, default=0)
    is_finalized = db.Column(db.Boolean, default=False)         # admin+leader 점수 확정

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    author = db.Column(db.String(50))
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    total_score = db.Column(db.Integer, default=0)              # 댓글 AI 방역용
    created_at = db.Column(db.DateTime, default=datetime.now)

    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)

class ShareComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    share_id = db.Column(db.Integer, db.ForeignKey('share_report.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    author = db.Column(db.String(50))
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('share_comment.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    replies = db.relationship('ShareComment', backref=db.backref('parent', remote_side=[id]), lazy=True)

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
    ai_reason = db.Column(db.Text)
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

class NewsVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    news_id = db.Column(db.Integer, db.ForeignKey('news_article.id'), nullable=False)
    vote = db.Column(db.String(10), default='like')  # 'like' or 'dislike'
    created_at = db.Column(db.DateTime, default=datetime.now)
    __table_args__ = (db.UniqueConstraint('user_id', 'news_id'),)

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    author_name = db.Column(db.String(50))
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    image_path = db.Column(db.String(300))
    drawing_path = db.Column(db.String(300))
    video_path = db.Column(db.String(300))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    town = db.Column(db.String(50))
    village = db.Column(db.String(50))
    address = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')
    admin_note = db.Column(db.Text)
    ai_category = db.Column(db.String(50))
    ai_summary = db.Column(db.Text)
    ai_confidence = db.Column(db.Float)
    ai_region_news = db.Column(db.Text)
    ai_news_links = db.Column(db.Text)
    ai_danger_alert = db.Column(db.Boolean, default=False)
    like_count = db.Column(db.Integer, default=0)
    dislike_count = db.Column(db.Integer, default=0)
    admin_score = db.Column(db.Integer, default=0)
    leader_score = db.Column(db.Integer, default=0)
    member_score = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, default=0)
    is_moderated = db.Column(db.Boolean, default=False)
    moderation_result = db.Column(db.String(20), default='pending')
    moderation_reason = db.Column(db.Text)
    moderation_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now)

class ConstructionNotice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    source = db.Column(db.String(50))
    source_url = db.Column(db.String(500))
    notice_type = db.Column(db.String(50))
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now)

class LegalPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    author_name = db.Column(db.String(50), default='익명')
    answer = db.Column(db.Text)
    answered_at = db.Column(db.DateTime)
    fee = db.Column(db.Integer)
    travel_allowance = db.Column(db.Integer)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class LegalAppointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(200))
    content = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    fee = db.Column(db.Integer)
    travel_allowance = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.now)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class LawyerSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    start_hour = db.Column(db.Integer, default=10)
    end_hour = db.Column(db.Integer, default=16)
    slot_hours = db.Column(db.Integer, default=2)
    created_at = db.Column(db.DateTime, default=datetime.now)

class GoogleCalendarConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_account_json = db.Column(db.Text)
    calendar_id = db.Column(db.String(200))
    is_connected = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.now)

class PsychoPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    author_name = db.Column(db.String(50), default='익명')
    answer = db.Column(db.Text)
    answered_at = db.Column(db.DateTime)
    fee = db.Column(db.Integer)
    travel_allowance = db.Column(db.Integer)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class PsychoAppointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(200))
    content = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    fee = db.Column(db.Integer)
    travel_allowance = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.now)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class PsychoDoctorSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    start_hour = db.Column(db.Integer, default=10)
    end_hour = db.Column(db.Integer, default=16)
    slot_hours = db.Column(db.Integer, default=2)
    created_at = db.Column(db.DateTime, default=datetime.now)

class PsychoGoogleCalendarConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_account_json = db.Column(db.Text)
    calendar_id = db.Column(db.String(200))
    is_connected = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.now)

class FriendGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class PostVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vote_type = db.Column(db.String(10))  # 'like' or 'dislike'
    created_at = db.Column(db.DateTime, default=datetime.now)

class Friend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('friend_group.id'), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now)

class RampApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    photo_path = db.Column(db.String(300))
    step_height = db.Column(db.String(50), nullable=False)
    ownership = db.Column(db.String(20), nullable=False)
    agree_removal = db.Column(db.Boolean, default=False)
    agree_damage = db.Column(db.Boolean, default=False)
    signed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.now)