import requests, xml.etree.ElementTree as ET
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

def get_incidents():
    key = _get_key()
    if not key: return [], "키 없음"
    try:
        r = requests.get("http://www.utic.go.kr/guide/imsOpenData.do", params={"key": key}, timeout=15)
        if r.status_code != 200: return [], f"HTTP {r.status_code}"
        root = ET.fromstring(r.text)
        incidents = []
        for rec in root.findall(".//record"):
            x = rec.findtext("locationDataX","")
            y = rec.findtext("locationDataY","")
            try:
                lat = float(y) if y else None
                lng = float(x) if x else None
            except:
                lat = lng = None
            title = rec.findtext("incidentTitle","")
            typ = rec.findtext("incidenteSubTypeCd","")
            type_map = {'2':'사고','8':'고장','4':'공사','5':'정체'}
            title_clean = title.split(',')[0].strip() if title else ''
            incidents.append({
                "id": rec.findtext("incidentId",""),
                "title": title_clean,
                "desc": title,
                "type": type_map.get(typ, typ),
                "road": rec.findtext("roadName",""),
                "addr": rec.findtext("addressJibun",""),
                "lat": lat, "lng": lng,
                "start": rec.findtext("startDate",""),
                "end": rec.findtext("endDate",""),
                "update": rec.findtext("updateDate",""),
            })
        return incidents, None
    except Exception as e:
        return [], str(e)

def get_yangpyeong_incidents():
    incidents, err = get_incidents()
    if err: return [], err
    yangpyeong_roads = ['중앙고속','영동고속','서울양양','국도6호선','국도37호선','국도44호선']
    result = []
    for inc in incidents:
        text = f"{inc['title']} {inc['addr']} {inc['road']}"
        if '양평군' in inc.get('addr',''):
            result.append(inc)
            continue
        for r in yangpyeong_roads:
            if r in inc.get('road','') or r in inc.get('title',''):
                result.append(inc)
                break
    return result, None

def traffic_summary():
    key = _get_key()
    if not key: return {"error":"키 없음","available":False}
    all_inc, err = get_incidents()
    if err: return {"error":err,"available":False}
    yp_inc, _ = get_yangpyeong_incidents()
    return {
        "available": True,
        "total": len(all_inc),
        "yangpyeong": len(yp_inc),
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "incidents": [{
            "title": i["title"][:60],
            "desc": i["desc"][:100],
            "type": i["type"],
            "road": i["road"],
            "addr": i["addr"],
            "lat": i["lat"], "lng": i["lng"],
            "start": i["start"],
            "end": i["end"],
        } for i in yp_inc[:20]],
    }
