import requests
import math
from flask import current_app

YANGPYEONG_BOUNDS = {
    '양평읍': {'lat_min': 37.45, 'lat_max': 37.52, 'lon_min': 127.48, 'lon_max': 127.60},
    '강상면': {'lat_min': 37.44, 'lat_max': 37.50, 'lon_min': 127.45, 'lon_max': 127.55},
    '강하면': {'lat_min': 37.46, 'lat_max': 37.53, 'lon_min': 127.38, 'lon_max': 127.48},
    '양서면': {'lat_min': 37.50, 'lat_max': 37.58, 'lon_min': 127.30, 'lon_max': 127.42},
    '옥천면': {'lat_min': 37.48, 'lat_max': 37.55, 'lon_min': 127.55, 'lon_max': 127.65},
    '서종면': {'lat_min': 37.55, 'lat_max': 37.65, 'lon_min': 127.35, 'lon_max': 127.48},
    '단월면': {'lat_min': 37.52, 'lat_max': 37.60, 'lon_min': 127.60, 'lon_max': 127.72},
    '청운면': {'lat_min': 37.50, 'lat_max': 37.58, 'lon_min': 127.68, 'lon_max': 127.75},
    '양동면': {'lat_min': 37.38, 'lat_max': 37.46, 'lon_min': 127.60, 'lon_max': 127.72},
    '지평면': {'lat_min': 37.40, 'lat_max': 37.48, 'lon_min': 127.55, 'lon_max': 127.68},
    '용문면': {'lat_min': 37.42, 'lat_max': 37.50, 'lon_min': 127.50, 'lon_max': 127.62},
    '개군면': {'lat_min': 37.35, 'lat_max': 37.44, 'lon_min': 127.48, 'lon_max': 127.62},
}

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

def generate_town_geojson():
    features = []
    for town, bounds in YANGPYEONG_BOUNDS.items():
        feature = {
            "type": "Feature",
            "properties": {"name": town, "type": "town"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [bounds['lon_min'], bounds['lat_min']],
                    [bounds['lon_max'], bounds['lat_min']],
                    [bounds['lon_max'], bounds['lat_max']],
                    [bounds['lon_min'], bounds['lat_max']],
                    [bounds['lon_min'], bounds['lat_min']]
                ]]
            }
        }
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}

def generate_village_geojson():
    features = []
    for town, villages in YANGPYEONG_VILLAGES.items():
        bounds = YANGPYEONG_BOUNDS[town]
        lon_step = (bounds['lon_max'] - bounds['lon_min']) / max(len(villages), 1)
        lat_step = (bounds['lat_max'] - bounds['lat_min']) / max(len(villages), 1)
        for i, village in enumerate(villages):
            lat_min = bounds['lat_min'] + (i % max(len(villages)//2+1, 1)) * lat_step * 2
            lat_max = min(lat_min + lat_step * 2, bounds['lat_max'])
            lon_min = bounds['lon_min'] + ((i // max(len(villages)//2+1, 1)) % 2) * lon_step * (len(villages)//2)
            lon_max = min(lon_min + lon_step * (len(villages)//2), bounds['lon_max'])
            feature = {
                "type": "Feature",
                "properties": {"name": village, "town": town, "type": "village"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [lon_min, lat_min],
                        [lon_max, lat_min],
                        [lon_max, lat_max],
                        [lon_min, lat_max],
                        [lon_min, lat_min]
                    ]]
                }
            }
            features.append(feature)
    return {"type": "FeatureCollection", "features": features}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def gps_to_town_village(lat, lon, kakao_key=None):
    # 1) 행정안전부 주소기반산업지원서비스 API (좌표→주소)
    try:
        juso_key = current_app.config.get('JUSO_API_KEY', '')
    except RuntimeError:
        juso_key = ''
    if juso_key:
        try:
            url = 'https://business.juso.go.kr/addrlink/coordAddrApi.do'
            params = {'confmKey': juso_key, 'entX': lon, 'entY': lat, 'resultType': 'json'}
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                results = data.get('results', {})
                juso = results.get('juso', [])
                if juso:
                    addr = juso[0]
                    # 법정동명에서 읍면/리 추출
                    full = addr.get('emdNm', '') or addr.get('lnmAdres', '')
                    if full:
                        parts = full.split()
                        for t in YANGPYEONG_BOUNDS:
                            if t in full:
                                for v in YANGPYEONG_VILLAGES.get(t, []):
                                    if v in full:
                                        return t, v
                                return t, ''
            print(f"[Geocode] JUSO API status: {res.status_code}")
        except Exception as e:
            print(f"[Geocode] JUSO API exception: {e}")

    # 2) Kakao API fallback
    if kakao_key is None:
        try:
            kakao_key = current_app.config.get('KAKAO_REST_API_KEY', '')
        except RuntimeError:
            kakao_key = ''
    if kakao_key:
        try:
            url = f'https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?x={lon}&y={lat}'
            headers = {'Authorization': f'KakaoAK {kakao_key}'}
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                town, village = '', ''
                for doc in data.get('documents', []):
                    rt = doc.get('region_type', '')
                    r3 = doc.get('region_3depth_name', '')
                    r4 = doc.get('region_4depth_name', '')
                    if rt == 'B' and r3:
                        town, village = r3, r4 or village
                    elif rt == 'H' and r3 and not town:
                        town = r3
                if town:
                    return town, village or ''
            print(f"[Geocode] Kakao API error: {res.status_code}")
        except Exception as e:
            print(f"[Geocode] Kakao API exception: {e}")

    # 3) 최종 폴백: 양평군 bounds lookup
    return _fallback_lookup(lat, lon)

def _fallback_lookup(lat, lon):
    best_town = None
    best_village = ''
    for town, bounds in YANGPYEONG_BOUNDS.items():
        if bounds['lat_min'] <= lat <= bounds['lat_max'] and bounds['lon_min'] <= lon <= bounds['lon_max']:
            best_town = town
            break
    if not best_town:
        min_dist = float('inf')
        for town, bounds in YANGPYEONG_BOUNDS.items():
            center_lat = (bounds['lat_min'] + bounds['lat_max']) / 2
            center_lon = (bounds['lon_min'] + bounds['lon_max']) / 2
            dist = haversine(lat, lon, center_lat, center_lon)
            if dist < min_dist:
                min_dist = dist
                best_town = town
    return best_town, ''

def get_nearby_reports(reports, user_lat, user_lon, max_count=12, max_km=20):
    scored = []
    for r in reports:
        if r.latitude and r.longitude:
            dist = haversine(user_lat, user_lon, r.latitude, r.longitude)
            if dist <= max_km:
                scored.append((r, round(dist, 1)))
    scored.sort(key=lambda x: x[1])
    return scored[:max_count]

def is_in_yangpyeong(lat, lon):
    return 37.35 <= lat <= 37.65 and 127.30 <= lon <= 127.75

# 양수리 지역 GPS 보정값 (현장实测 기반)
_YANGSU_OFFSET_LAT = -0.00013000
_YANGSU_OFFSET_LON = -0.00013000

def calibrate_gps(lat, lon):
    """양수리(양서면) 지역에 한해 GPS 보정 적용"""
    bounds = YANGPYEONG_BOUNDS.get('양서면')
    if bounds and bounds['lat_min'] <= lat <= bounds['lat_max'] and bounds['lon_min'] <= lon <= bounds['lon_max']:
        return lat + _YANGSU_OFFSET_LAT, lon + _YANGSU_OFFSET_LON
    return lat, lon
