import requests
import xml.etree.ElementTree as ET
from datetime import datetime

GG_API_BASE = "https://openapigits.gg.go.kr/api/rest"
GG_KEY = None

def _get_key():
    global GG_KEY
    if GG_KEY is not None:
        return GG_KEY
    try:
        from flask import current_app
        GG_KEY = current_app.config.get("GG_TRAFFIC_API_KEY", "")
    except:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        GG_KEY = os.getenv("GG_TRAFFIC_API_KEY", "")
    return GG_KEY

def _call_api(endpoint, params=None):
    key = _get_key()
    if not key:
        return None, "API 키가 설정되지 않았습니다."
    url = f"{GG_API_BASE}/{endpoint}"
    if params is None:
        params = {}
    params["serviceKey"] = key
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        root = ET.fromstring(r.text)
        header = root.find(".//msgHeader")
        if header is not None:
            cd = header.findtext("headerCd", "")
            msg = header.findtext("headerMsg", "")
            if cd != "0":
                return None, f"[{cd}] {msg}"
        return root, None
    except Exception as e:
        return None, str(e)

def get_road_list():
    root, err = _call_api("getRoadInfoList")
    if err:
        return [], err
    roads = []
    for item in root.findall(".//item") or root.findall(".//roadList"):
        roads.append({
            "routeId": item.findtext("routeId", ""),
            "roadRank": item.findtext("roadRank", ""),
            "routeTp": item.findtext("routeTp", ""),
            "routeNo": item.findtext("routeNo", ""),
            "routeNm": item.findtext("routeNm", ""),
        })
    return roads, None

def get_all_traffic(route_id=None):
    params = {}
    if route_id:
        params["routeId"] = route_id
    root, err = _call_api("getRoadTrafficInfoList", params)
    if err:
        return [], err
    items = []
    for item in root.findall(".//item") or root.findall(".//trafficList"):
        spd = item.findtext("spd", "0")
        vol = item.findtext("vol", "0")
        cong = item.findtext("congGrade", "0")
        items.append({
            "routeId": item.findtext("routeId", ""),
            "routeNm": item.findtext("routeNm", ""),
            "routeWay": item.findtext("routeWay", ""),
            "routeSeq": item.findtext("routeSeq", ""),
            "startNodeNm": item.findtext("startNodeNm", ""),
            "endNodeNm": item.findtext("endNodeNm", ""),
            "collDate": item.findtext("collDate", ""),
            "spd": int(spd) if spd.isdigit() else 0,
            "vol": int(vol) if vol.isdigit() else 0,
            "trvlTime": item.findtext("trvlTime", ""),
            "linkDelayTime": item.findtext("linkDelayTime", ""),
            "congGrade": int(cong) if cong.isdigit() else 0,
        })
    return items, None

def get_congested_sections():
    all_traffic, err = get_all_traffic()
    if err:
        return [], err
    congested = [t for t in all_traffic if t.get("congGrade", 0) >= 2]
    congested.sort(key=lambda t: t.get("congGrade", 0), reverse=True)
    return congested, None

def get_cctv_list():
    root, err = _call_api("getCctvInfoList")
    if err:
        return [], err
    cctvs = []
    for item in root.findall(".//item") or root.findall(".//cctvList"):
        cctvs.append({
            "cctvId": item.findtext("cctvId", ""),
            "cctvNm": item.findtext("cctvNm", ""),
            "routeNm": item.findtext("routeNm", ""),
            "lat": item.findtext("lat", ""),
            "lng": item.findtext("lng", ""),
            "url": item.findtext("url", ""),
        })
    return cctvs, None

YANGPYEONG_ROADS = [
    "중앙고속도로", "영동고속도로", "서울양양고속도로",
    "국도6호선", "국도37호선", "국도44호선",
]

def get_yangpyeong_traffic():
    all_traffic, err = get_all_traffic()
    if err:
        return [], err
    yp_routes = [r.lower() for r in YANGPYEONG_ROADS]
    yp_traffic = []
    for t in all_traffic:
        rn = t.get("routeNm", "").lower()
        for yr in yp_routes:
            if yr in rn:
                yp_traffic.append(t)
                break
    return yp_traffic, None

CONG_LABEL = {0: "정보없음", 1: "원활", 2: "지체", 3: "정체"}
CONG_COLOR = {0: "secondary", 1: "success", 2: "warning", 3: "danger"}

def traffic_summary():
    yp, err = get_yangpyeong_traffic()
    if err:
        return {"error": err, "available": False}
    congested = [t for t in yp if t.get("congGrade", 0) >= 2]
    smooth = [t for t in yp if t.get("congGrade", 0) == 1]
    avg_spd = sum(t["spd"] for t in yp) / len(yp) if yp else 0
    return {
        "available": True,
        "total_sections": len(yp),
        "congested": len(congested),
        "smooth": len(smooth),
        "avg_speed": round(avg_spd, 1),
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "sections": [{
            "routeNm": t["routeNm"],
            "routeWay": t["routeWay"],
            "startNodeNm": t["startNodeNm"],
            "endNodeNm": t["endNodeNm"],
            "spd": t["spd"],
            "congGrade": t["congGrade"],
            "congLabel": CONG_LABEL.get(t["congGrade"], "알수없음"),
            "congColor": CONG_COLOR.get(t["congGrade"], "secondary"),
        } for t in yp[:20]],
    }
