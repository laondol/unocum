import requests
from math import radians, sin, cos, sqrt, atan2

def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

def reverse_geocode(lat, lng, kakao_key=None, naver_id=None, naver_secret=None):
    if naver_id and naver_secret:
        url = "https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc"
        headers = {"X-NCP-APIGW-API-KEY-ID": naver_id, "X-NCP-APIGW-API-KEY": naver_secret}
        try:
            r = requests.get(url, headers=headers, params={"coords": f"{lng},{lat}", "output": "json", "orders": "addr"}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                if results:
                    region = results[0].get("region", {})
                    area1 = region.get("area1", {}).get("name", "")
                    area2 = region.get("area2", {}).get("name", "")
                    area3 = region.get("area3", {}).get("name", "")
                    area4 = region.get("area4", {}).get("name", "")
                    addr = f"{area1} {area2} {area3} {area4}".strip()
                    if addr:
                        return {"lat": lat, "lng": lng, "address": addr}
        except:
            pass
    if kakao_key:
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
    url = "https://nominatim.openstreetmap.org/reverse"
    try:
        r = requests.get(url, params={"lat": lat, "lon": lng, "format": "json", "accept-language": "ko"},
                         headers={"User-Agent": "YangpyeongApp/1.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            addr = data.get("display_name", "")
            parts = addr.split(",")
            short = ",".join(parts[:3]) if len(parts) > 3 else addr
            return {"lat": lat, "lng": lng, "address": short.strip()}
    except:
        pass
    return None

def geocode_address(address, kakao_key=None, naver_id=None, naver_secret=None):
    if naver_id and naver_secret:
        url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
        headers = {"X-NCP-APIGW-API-KEY-ID": naver_id, "X-NCP-APIGW-API-KEY": naver_secret}
        try:
            r = requests.get(url, headers=headers, params={"query": address}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                addrs = data.get("addresses", [])
                if addrs:
                    return {"lat": float(addrs[0]["y"]), "lng": float(addrs[0]["x"]), "address": addrs[0].get("jibunAddress", addrs[0].get("roadAddress", address))}
        except:
            pass
    if kakao_key:
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
    url = "https://nominatim.openstreetmap.org/search"
    try:
        r = requests.get(url, params={"q": address, "format": "json", "limit": 1, "accept-language": "ko"},
                         headers={"User-Agent": "YangpyeongApp/1.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data:
                return {"lat": float(data[0]["lat"]), "lng": float(data[0]["lon"]), "address": data[0].get("display_name", address)}
    except:
        pass
    return None

def estimate_transit_time_rough(from_lat, from_lng, to_lat, to_lng):
    km = haversine_km(from_lat, from_lng, to_lat, to_lng)
    est_min = int(km * 3 + 15)
    return est_min
