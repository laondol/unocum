from flask import render_template, request, redirect, url_for, jsonify, session, current_app, send_file, send_from_directory
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from urllib.parse import quote
import json, base64, os, threading, requests

from models import db, User, Post, Comment, NewsArticle, NewsComment, NewsRecommendation, NewsVote, PointHistory, ShareReport, Message, ShareComment, ConstructionNotice, VillageAlert, HeritageStamp, TongBot, TongBotDraft, TongBotSchedule, ChatRoom, ChatMessage, VillageCache, LegalPost, LegalAppointment, LawyerSchedule, GoogleCalendarConfig, PsychoPost, PsychoAppointment, PsychoDoctorSchedule, PsychoGoogleCalendarConfig, RampApplication, Friend, FriendGroup, PostVote, StoreInfo, AiKnowledge, VillagePage, VillageEvent, VillageEventAttendee, VillageEventChat, VillageWish
from services.oauth import oauth
from services.security import save_village_file
from services.ai_service import call_ai_judge, call_ai_debate, background_ai_judge, moderate_image, background_process_share
from services.email_service import EmailService
from services.construction import sync_construction_notices, sync_traffic_incidents, sync_congestion_info
from services.news_service import ai_search_news, ai_translate_and_format, ai_summarize_url
from services.geocode import haversine, gps_to_town_village, get_nearby_reports, is_in_yangpyeong, YANGPYEONG_BOUNDS, YANGPYEONG_VILLAGES

# --- [페이지 관리 권한] ---
def has_page_access(page):
    """특정 페이지 관리 권한 확인
    - leader: 모든 권한 (단, 마을은 체크 필요)
    - managed_pages에 체크된 페이지만 접근 가능
    """
    role = session.get('role','')
    uid = session.get('user_id')
    # 마을 관련 권한은 leader도 체크 필요
    if page == 'village' or page.startswith('vi_'):
        if uid:
            user = User.query.get(uid)
            if user and user.managed_pages:
                pages = user.managed_pages.split(',')
                if page in pages or 'village' in pages:
                    return True
                for p in pages:
                    if p.startswith('vi_'):
                        return True
        return False
    # 마을 외 페이지: leader 자동 권한
    if role == 'leader':
        return True
    if uid:
        user = User.query.get(uid)
        if user and user.managed_pages:
            pages = user.managed_pages.split(',')
            if page in pages:
                return True
    return False

# --- [공개 경로] 인트로 및 대시보드 ---
def register_routes(app):
    # React SPA 폴백
    import os as _os
    spa_dir = _os.path.join(app.root_path, 'static', 'spa')


    # --- [공유하기 시스템] ---
