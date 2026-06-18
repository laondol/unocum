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

TRANSIT_HUBS = [
    {"name": "양평역", "lat": 37.4918, "lng": 127.4913, "type": "train", "line": "경의중앙선",
     "last_toward_seoul": "23:10", "last_toward_jipyeong": "00:10",
     "towns": {"양평읍", "강상면", "강하면", "개군면"}},
    {"name": "용문역", "lat": 37.4815, "lng": 127.5946, "type": "train", "line": "경의중앙선",
     "last_toward_seoul": "22:50", "last_toward_jipyeong": "00:20",
     "towns": {"용문면", "단월면", "청운면", "양동면"}},
    {"name": "옥천역", "lat": 37.5180, "lng": 127.5083, "type": "train", "line": "경의중앙선",
     "last_toward_seoul": "23:30", "last_toward_jipyeong": "00:00",
     "towns": {"옥천면", "양서면", "서종면"}},
    {"name": "지평역", "lat": 37.4460, "lng": 127.6210, "type": "train", "line": "경의중앙선",
     "last_toward_seoul": "22:40", "last_toward_jipyeong": "00:25",
     "towns": {"지평면"}},
    {"name": "원덕역", "lat": 37.4900, "lng": 127.5050, "type": "train", "line": "경의중앙선",
     "last_toward_seoul": "23:15", "last_toward_jipyeong": "00:14",
     "towns": set()},
    {"name": "아신역", "lat": 37.5134, "lng": 127.5105, "type": "train", "line": "경의중앙선",
     "last_toward_seoul": "23:25", "last_toward_jipyeong": "00:05",
     "towns": set()},
]

def _hm_to_min(t):
    h, m = int(t.split(":")[0]), int(t.split(":")[1])
    if h < 6:
        h += 24
    return h * 60 + m

def find_best_hubs(from_lat, from_lng, home_town):
    serving = [h for h in TRANSIT_HUBS if home_town in h["towns"]]
    if not serving:
        serving = sorted(TRANSIT_HUBS, key=lambda h: haversine_km(from_lat, from_lng, h["lat"], h["lng"]))[:3]
    results = []
    for hub in serving:
        dist = haversine_km(from_lat, from_lng, hub["lat"], hub["lng"])
        time_min = int(dist * 3 + 15)
        home_coords = YANGPYEONG_CENTERS.get(home_town)
        if home_coords and home_coords[1] >= hub["lng"]:
            last_dep = hub["last_toward_jipyeong"]
            direction = "용문/지평 방면"
        else:
            last_dep = hub["last_toward_seoul"]
            direction = "서울/덕소 방면"
        results.append({
            "station": hub["name"], "lat": hub["lat"], "lng": hub["lng"],
            "type": hub["type"], "line": hub["line"],
            "distance_km": round(dist, 1), "time_to_station_min": time_min,
            "last_transit_dep": last_dep, "direction": direction,
            "last_transit_total_min": _hm_to_min(last_dep),
        })
    results.sort(key=lambda r: r["distance_km"])
    return results

def suggest_optimal_departure(from_lat, from_lng, home_town, home_village):
    hubs = find_best_hubs(from_lat, from_lng, home_town)
    if not hubs:
        return None
    best = hubs[0]
    last_min = best["last_transit_total_min"]
    time_to_station = best["time_to_station_min"]
    buffer_min = 10
    optimal_dep_min = last_min - time_to_station - buffer_min
    optimal_hour = optimal_dep_min // 60
    optimal_min = optimal_dep_min % 60
    return {
        "transfer_station": best["station"],
        "station_coords": {"lat": best["lat"], "lng": best["lng"]},
        "station_type": best["type"], "line": best["line"],
        "distance_to_station_km": best["distance_km"],
        "time_to_station_min": time_to_station,
        "last_transit_from_station": best["last_transit_dep"],
        "direction": best["direction"],
        "buffer_min": buffer_min,
        "optimal_departure": f"{optimal_hour:02d}:{optimal_min:02d}",
        "estimate": True,
        "all_options": hubs,
    }
