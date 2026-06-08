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
    town = db.Column(db.String(50))                      # 읍/면
    village = db.Column(db.String(50))                   # 리
    is_verified_resident = db.Column(db.Boolean, default=False) # 주민 자치인증 완료 여부
    verified_method = db.Column(db.String(30), default='none')  # gps, bill, none
    bill_image_path = db.Column(db.String(300))                  # 고지서 사진 경로 (인증 후 즉시 파기)
    
    points = db.Column(db.Integer, default=1000)         # 물맑은머니 포인트
    is_paid = db.Column(db.Boolean, default=False)       # 유료회원 여부

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