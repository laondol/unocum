import requests
from datetime import datetime

BASE = "https://www.safetydata.go.kr/V2/api/DSSP-IF-"
KEYS = {
    "bike": "10016", "fog": "10011", "flood": "10019",
    "disabled": "10031", "elder": "10040", "block": "10677",
}

def _get_key(api_type):
    key_map = {
        "bike": "SAFETYDATA_BIKE_KEY", "fog": "SAFETYDATA_FOG_KEY",
        "flood": "SAFETYDATA_FLOOD_KEY", "disabled": "SAFETYDATA_DISABLED_KEY",
        "elder": "SAFETYDATA_ELDER_KEY", "block": "SAFETYDATA_BLOCK_KEY",
    }
    try:
        from flask import current_app
        return current_app.config.get(key_map.get(api_type, ""), "")
    except:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        return os.getenv(key_map.get(api_type, ""), "")

def get_safety_data(api_type):
    eid = KEYS.get(api_type)
    key = _get_key(api_type)
    if not eid or not key:
        return [], "키 없음"
    try:
        r = requests.get(BASE + eid, params={"serviceKey": key, "numOfRows": 100, "pageNo": 1}, timeout=15)
        d = r.json()
        if d.get("header",{}).get("resultCode") != "00":
            return [], d.get("header",{}).get("resultMsg","error")
        items = d.get("body",[])
        return items, None
    except Exception as e:
        return [], str(e)

def get_yangpyeong_safety():
    yangpyeong_kw = ["양평","용문","지평","옥천","양서","양동","서종","단월","청운","개군","강상","강하"]
    result = {}
    for api_type in ["bike","fog","flood","block"]:
        items, err = get_safety_data(api_type)
        if err: continue
        yp_items = []
        for item in items:
            addr = item.get("LOTNO_ADDR","") + item.get("ROAD_NM_ADDR","")
            if any(kw in addr for kw in yangpyeong_kw):
                yp_items.append({
                    "type": api_type,
                    "addr": item.get("LOTNO_ADDR","") or item.get("ROAD_NM_ADDR",""),
                    "desc": item.get("DTL_CN",""),
                    "lat": float(item.get("LAT",0)) if item.get("LAT") else None,
                    "lng": float(item.get("LOT",0)) if item.get("LOT") else None,
                })
        result[api_type] = yp_items
    return result

TYPE_NAMES = {"bike":"🚲 자전거위험","fog":"🌫️ 안개","flood":"🌊 침수","block":"🚧 교통두절"}
