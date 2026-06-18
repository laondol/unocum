import requests
from math import radians, sin, cos, sqrt, atan2

def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

def estimate_last_transit(from_lat, from_lng, to_lat, to_lng):
    km = haversine_km(from_lat, from_lng, to_lat, to_lng)
    total_min = int(km * 3 + 15)
    if km > 30:
        last_dep_hour, last_dep_min = 21, 0
    elif km > 15:
        last_dep_hour, last_dep_min = 21, 30
    else:
        last_dep_hour, last_dep_min = 22, 0
    return {"total_min": total_min, "last_dep": f"{last_dep_hour:02d}:{last_dep_min:02d}", "estimate": True}

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

YANGPYEONG_VILLAGES = {
    '양평읍': ['양근리', '오빈리', '신애리', '덕평리', '봉성리', '원덕리', '도곡리', '백안리', '송학리', '대흥리', '회현리', '공흥리', '사송리'],
    '강상면': ['병산리', '교평리', '세월리', '운심리', '신화리', '송학리', '화양리', '대석리', '강하리'],
    '강하면': ['전수리', '왕창리', '운심리', '성덕리', '동오리', '공세리', '항금리'],
    '양서면': ['양수리', '용담리', '대심리', '신원리', '목왕리', '증동리', '가동리', '도곡리', '부평리', '삼회리'],
    '옥천면': ['옥천리', '용천리', '신복리', '아신리', '삼합리', '후곡리'],
    '서종면': ['서후리', '문호리', '정배리', '수능리', '도장리', '금사리', '내수리', '노문리'],
    '단월면': ['봉상리', '향양리', '보룡리', '부안리', '석산리', '명성리', '삼가리', '덕수리'],
    '청운면': ['용두리', '가현리', '여물리', '도원리', '갈운리', '비룡리', '신론리', '삼성리'],
    '양동면': ['쌍학리', '매월리', '석정리', '금왕리', '고송리', '계정리'],
    '지평면': ['지평리', '월산리', '송현리', '무왕리', '대평리', '수곡리', '일신리'],
    '용문면': ['용문리', '마룡리', '금곡리', '망미리', '삼성리', '화전리', '다문리', '조현리', '오촌리', '연수리', '덕촌리', '중원리'],
    '개군면': ['주읍리', '내리', '석장리', '하자포리', '부리', '공세리', '양동리', '구미리', '향리', '계전리'],
}
YANGPYEONG_CENTERS = {
    '양평읍': (37.485, 127.54), '강상면': (37.47, 127.50), '강하면': (37.495, 127.43),
    '양서면': (37.54, 127.36), '옥천면': (37.515, 127.60), '서종면': (37.60, 127.415),
    '단월면': (37.56, 127.66), '청운면': (37.54, 127.715), '양동면': (37.42, 127.66),
    '지평면': (37.44, 127.615), '용문면': (37.46, 127.56), '개군면': (37.395, 127.55),
}

def lookup_village_coords(town, village):
    base = YANGPYEONG_CENTERS.get(town)
    if not base:
        return None
    base_lat, base_lng = base
    vilist = YANGPYEONG_VILLAGES.get(town, [])
    if village not in vilist:
        return base_lat, base_lng
    idx = vilist.index(village)
    total = len(vilist)
    offset = (idx - (total - 1) / 2) * 0.005
    return round(base_lat + offset, 6), round(base_lng + offset * 0.7, 6)
