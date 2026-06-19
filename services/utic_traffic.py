import requests
from datetime import datetime

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

def _call_utic(url, params=None):
    key = _get_key()
    if not key:
        return None, "API 키가 설정되지 않았습니다."
    if params is None:
        params = {}
    params["key"] = key
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        data = r.json()
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            if data[0].get("resultCode") in ("03", "04"):
                return None, f"UTIC IP 제한: {data[0].get('resultMsg', '')}"
        return data, None
    except Exception as e:
        return None, str(e)

def get_traffic_info():
    data, err = _call_utic("http://www.utic.go.kr/etc/telMap.do")
    if err:
        return {"error": err, "available": False}
    return {"available": True, "data": data, "type": "소통정보"}

def get_incident_info():
    data, err = _call_utic("http://www.utic.go.kr/guide/imsOpenData.do")
    if err:
        return {"error": err, "available": False}
    return {"available": True, "data": data, "type": "돌발정보"}

def get_cctv_info():
    data, err = _call_utic("http://www.utic.go.kr/guide/cctvOpenData.do")
    if err:
        return {"error": err, "available": False}
    return {"available": True, "data": data, "type": "CCTV"}

def get_traffic_safety():
    data, err = _call_utic("http://www.utic.go.kr/guide/tsdmsOpenData.do")
    if err:
        return {"error": err, "available": False}
    return {"available": True, "data": data, "type": "교통안전"}

def get_road_risk_forecast():
    data, err = _call_utic("http://www.utic.go.kr/guide/getRoadAccJson.do")
    if err:
        return {"error": err, "available": False}
    return {"available": True, "data": data, "type": "도로위험예보"}

def get_construction_info():
    data, err = _call_utic("http://www.utic.go.kr/guide/tcsOpenData.do")
    if err:
        return {"error": err, "available": False}
    return {"available": True, "data": data, "type": "공사정보"}

def traffic_summary():
    key = _get_key()
    if not key:
        return {"error": "키 미설정", "available": False}
    traffic, _ = _call_utic("http://www.utic.go.kr/etc/telMap.do")
    incident, _ = _call_utic("http://www.utic.go.kr/guide/imsOpenData.do")
    construction, _ = _call_utic("http://www.utic.go.kr/guide/tcsOpenData.do")
    available = isinstance(traffic, list) or isinstance(incident, list) or isinstance(construction, list)
    return {
        "available": available,
        "traffic": len(traffic) if isinstance(traffic, list) else 0,
        "incident": len(incident) if isinstance(incident, list) else 0,
        "construction": len(construction) if isinstance(construction, list) else 0,
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
