import requests
import json
from math import radians, sin, cos, sqrt, atan2

def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

def reverse_geocode(lat, lng, kakao_key):
    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    headers = {"Authorization": f"KakaoAK {kakao_key}"}
    try:
        r = requests.get(url, headers=headers, params={"x": lng, "y": lat}, timeout=10)
        if r.status_code == 200:
            docs = r.json().get("documents", [])
            if docs:
                addr = docs[0].get("road_address") or docs[0].get("address")
                if addr:
                    return {"lat": lat, "lng": lng, "address": addr.get("address_name", "")}
    except:
        pass
    return None

def geocode_address(address, kakao_key):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {kakao_key}"}
    try:
        r = requests.get(url, headers=headers, params={"query": address}, timeout=10)
        if r.status_code == 200:
            docs = r.json().get("documents", [])
            if docs:
                return {"lat": float(docs[0]["y"]), "lng": float(docs[0]["x"]), "address": docs[0]["address_name"]}
    except:
        pass
    return None

def get_naver_transit(from_lat, from_lng, to_lat, to_lng, client_id, client_secret):
    url = "https://naveropenapi.apigw.ntruss.com/map-direction-15/v1/publicTransit"
    headers = {"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret}
    params = {"startX": from_lng, "startY": from_lat, "endX": to_lng, "endY": to_lat, "count": 3}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            routes = []
            for route in data.get("route", []):
                total_min = route.get("totalTime", 0)
                fare = route.get("totalFare", 0)
                transfers = route.get("transferCount", 0)
                first_dep = route.get("firstStartTime", "")
                last_dep = route.get("lastEndTime", "")
                legs = []
                for sub in route.get("path", []):
                    ttype = sub.get("trafficType", "")
                    st_name = sub.get("startName", "")
                    en_name = sub.get("endName", "")
                    sec_min = sub.get("sectionTime", 0)
                    dist_m = sub.get("distance", 0)
                    line_info = ""
                    if ttype in ("BUS", "SUBWAY"):
                        lanes = sub.get("lanes", [])
                        if lanes:
                            line_info = lanes[0].get("name", "") or lanes[0].get("busNo", "")
                    legs.append({"type": ttype, "line": line_info, "from": st_name, "to": en_name, "time": sec_min, "distance": dist_m})
                routes.append({"total_min": total_min, "fare": fare, "transfers": transfers, "first_dep": first_dep, "last_dep": last_dep, "legs": legs})
            return routes
        elif r.status_code == 401:
            return None
    except:
        pass
    return None

def estimate_transit_time_rough(from_lat, from_lng, to_lat, to_lng):
    km = haversine_km(from_lat, from_lng, to_lat, to_lng)
    est_min = int(km * 3 + 15)
    return est_min
