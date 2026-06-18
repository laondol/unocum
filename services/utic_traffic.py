import requests
from datetime import datetime

UTIC_BASE = "https://openapi.utic.go.kr"
UTIC_KEY = None

def _get_key():
    global UTIC_KEY
    if UTIC_KEY is not None:
        return UTIC_KEY
    try:
        from flask import current_app
        UTIC_KEY = current_app.config.get("UTIC_API_KEY", "")
    except:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        UTIC_KEY = os.getenv("UTIC_API_KEY", "")
    return UTIC_KEY

def get_traffic_info(from_lat=None, from_lng=None, radius_km=10):
    """
    경찰청 UTIC 실시간 교통정보 조회
    (승인 후 엔드포인트 URL 업데이트 필요)
    """
    key = _get_key()
    if not key:
        return {"error": "UTIC API 키가 설정되지 않았습니다.", "available": False}
    return {
        "available": False,
        "pending": True,
        "message": "UTIC API 승인 대기 중입니다.",
    }

def get_incident_info(from_lat=None, from_lng=None, radius_km=10):
    key = _get_key()
    if not key:
        return {"error": "UTIC API 키가 설정되지 않았습니다.", "available": False}
    return {
        "available": False,
        "pending": True,
        "message": "UTIC API 승인 대기 중입니다.",
    }

def traffic_summary():
    key = _get_key()
    if not key:
        return {"error": "키 미설정", "available": False}
    return {
        "available": False,
        "pending": True,
        "message": "UTIC API 승인 후 실시간 데이터가 반영됩니다.",
    }
