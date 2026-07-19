from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, current_app, send_file
from datetime import datetime, timedelta
from urllib.parse import quote
from sqlalchemy import or_
from models import db, ConstructionNotice, StoreInfo, VillageAlert, HeritageStamp, User, Message, ShareReport, VillageCache, PublicFacility
from services.construction import sync_construction_notices, sync_traffic_incidents, sync_congestion_info, sync_building_permits
from services.transit import haversine_km
from config import Config

construction_bp = Blueprint('construction', __name__)

@construction_bp.route('/construction')
def construction():
    six_months_ago = datetime.now() - timedelta(days=180)
    notices = ConstructionNotice.query.filter(
        ConstructionNotice.is_active == True,
        db.or_(
            ConstructionNotice.start_date >= six_months_ago,
            ConstructionNotice.start_date == None
        )
    ).all()
    # 사용자 집 기준 거리순 정렬
    uid = session.get('user_id')
    if uid:
        user = User.query.get(uid)
        if user and (user.curr_latitude or user.reg_latitude):
            from services.transit import haversine_km
            home_lat = user.curr_latitude or user.reg_latitude
            home_lng = user.curr_longitude or user.reg_longitude
            def dist_key(n):
                if n.latitude and n.longitude:
                    return haversine_km(home_lat, home_lng, n.latitude, n.longitude)
                return 999
            notices = sorted(notices, key=dist_key)
        else:
            notices = sorted(notices, key=lambda n: n.created_at or datetime.min, reverse=True)
    else:
        notices = sorted(notices, key=lambda n: n.created_at or datetime.min, reverse=True)
    alerts = VillageAlert.query.filter_by(is_active=True).order_by(VillageAlert.created_at.desc()).limit(20).all()
    from config import Config
    dg_key = getattr(Config, 'DATA_GO_KR_API_KEY', '')
    gg_key = getattr(Config, 'GG_TRAFFIC_API_KEY', '')
    return render_template('construction.html', notices=notices, alerts=alerts, api_key_configured=bool(dg_key), traffic_key_configured=bool(gg_key))

@construction_bp.route('/construction/heritage')
def construction_heritage():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    if not lat or not lng:
        return jsonify([])
    from services.local_sources import get_nearby_heritage
    from services.transit import haversine_km
    items = get_nearby_heritage(lat, lng, max_km=5)
    uid = session.get('user_id')
    home_lat = home_lng = None
    home_label = ''
    stamped_names = set()
    if uid:
        user = User.query.get(uid)
        if user and user.curr_town and user.curr_village:
            from services.transit import lookup_village_coords
            hc = lookup_village_coords(user.curr_town, user.curr_village)
            if hc:
                home_lat, home_lng = hc
        stamps = HeritageStamp.query.filter_by(user_id=uid).all()
        stamped_names = {s.heritage_name for s in stamps}
    for h in items:
        h['stamped'] = h['name'] in stamped_names
        if home_lat and home_lng:
            d_home = round(haversine_km(h['lat'], h['lng'], home_lat, home_lng), 1)
            h['dist_from_home'] = d_home
            h['near_home'] = d_home <= 5
        else:
            h['near_home'] = False
    return jsonify(items)

@construction_bp.route('/construction/heritage/stamp', methods=['POST'])
def heritage_stamp():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    data = request.get_json()
    name = data.get('name', '').strip()
    lat = data.get('lat', type=float)
    lng = data.get('lng', type=float)
    gps_lat = data.get('gps_lat', type=float)
    gps_lng = data.get('gps_lng', type=float)
    if not name or not lat or not lng:
        return jsonify({"success": False, "error": "정보가 부족합니다."})
    from services.transit import haversine_km
    if gps_lat and gps_lng:
        dist = haversine_km(gps_lat, gps_lng, lat, lng)
        if dist > 0.2:
            return jsonify({"success": False, "error": f"현장에서만 찍을 수 있어요! 약 {round(dist*1000)}m 떨어져 있습니다. 가까이 가서 다시 시도해 주세요.", "distance_m": round(dist*1000)})
    existing = HeritageStamp.query.filter_by(user_id=uid, heritage_name=name).first()
    if existing:
        return jsonify({"success": False, "error": "이미 방문 완료한 국가유산입니다."})
    stamp = HeritageStamp(user_id=uid, heritage_name=name, heritage_lat=lat, heritage_lng=lng)
    db.session.add(stamp)
    db.session.commit()
    return jsonify({"success": True, "message": "⭐ 스탬프가 찍혔습니다!"})

@construction_bp.route('/construction/transit')
def construction_transit():
    from_lat = request.args.get('from_lat', type=float)
    from_lng = request.args.get('from_lng', type=float)
    if not from_lat or not from_lng:
        return jsonify({"error": "출발 위치가 필요합니다."}), 400
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    from models import User
    user = User.query.get(user_id)
    if not user or (not user.village and not user.curr_village):
        return jsonify({"error": "등록된 주소가 없습니다. 마이페이지에서 설정해 주세요."}), 400
    home_town = user.town or user.curr_town or ''
    home_village = user.village or user.curr_village or ''
    # 보정된 위치가 있으면 그걸 집 주소로
    if user.curr_address and user.curr_latitude and user.curr_longitude:
        to_address = user.curr_address
        dest = {"lat": user.curr_latitude, "lng": user.curr_longitude, "address": to_address}
    else:
        to_address = f"경기 양평군 {home_town} {home_village}".strip()
        dest = None
    from config import Config
    kakao_key = Config.KAKAO_REST_API_KEY
    naver_id = Config.NAVER_SEARCH_CLIENT_ID or Config.NAVER_CLIENT_ID
    naver_secret = Config.NAVER_SEARCH_CLIENT_SECRET or Config.NAVER_CLIENT_SECRET
    from services.transit import reverse_geocode, geocode_address, estimate_transit_time_rough, haversine_km, lookup_village_coords
    dep = reverse_geocode(from_lat, from_lng, kakao_key, naver_id, naver_secret)
    if not dest:
        dest = geocode_address(to_address, kakao_key, naver_id, naver_secret)
    if not dest or not dest.get("lat"):
        lc = lookup_village_coords(user.curr_town, user.curr_village)
        if lc:
            dest = {"lat": lc[0], "lng": lc[1], "address": to_address}
    result = {
        "departure": dep or {"lat": from_lat, "lng": from_lng, "address": f"{from_lat:.5f}, {from_lng:.5f}"},
        "destination": dest or {"lat": 0, "lng": 0, "address": to_address},
        "distance_km": 0,
    }
    if dest and dest["lat"]:
        from services.transit import haversine_km
        result["distance_km"] = round(haversine_km(from_lat, from_lng, dest["lat"], dest["lng"]), 1)
    if not result.get("transit_routes"):
        from services.transit import estimate_transit_time_rough
        rough_min = estimate_transit_time_rough(from_lat, from_lng, (dest or {}).get("lat") or from_lat, (dest or {}).get("lng") or from_lng)
        result["rough_estimate_min"] = rough_min
    # 대중교통 막차 정보 (추정)
    if dest and dest.get("lat"):
        from services.transit import estimate_last_transit
        last_info = estimate_last_transit(from_lat, from_lng, dest["lat"], dest["lng"])
        if last_info:
            result["last_transit"] = [last_info]
    if dest and dest.get("lng"):
        dep_addr = quote(dep["address"] if dep else f"{from_lat},{from_lng}")
        dest_addr = quote(dest["address"])
        result["deep_links"] = {
            "kakao": f"https://map.kakao.com/?sX={from_lng}&sY={from_lat}&sName={dep_addr}&eX={dest['lng']}&eY={dest['lat']}&eName={dest_addr}",
            "naver": f"https://map.naver.com/index.nhn?slat={from_lat}&slng={from_lng}&stitle={dep_addr}&elat={dest['lat']}&elng={dest['lng']}&etitle={dest_addr}&pathType=1"
        }
    else:
        dep_addr = quote(dep["address"] if dep else f"{from_lat},{from_lng}")
        dest_addr = quote(to_address)
        result["deep_links"] = {
            "kakao": f"https://map.kakao.com/?sName={dep_addr}&eName={dest_addr}",
            "naver": f"https://map.naver.com/index.nhn?stitle={dep_addr}&etitle={dest_addr}&pathType=1"
        }
    return jsonify(result)

@construction_bp.route('/construction/transit/suggest')
def construction_transit_suggest():
    from_lat = request.args.get('from_lat', type=float)
    from_lng = request.args.get('from_lng', type=float)
    if not from_lat or not from_lng:
        return jsonify({"error": "출발 위치가 필요합니다."}), 400
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    from models import User
    user = User.query.get(uid)
    if not user or (not user.village and not user.curr_village):
        return jsonify({"error": "등록된 주소가 없습니다."}), 400
    home_town = user.town or user.curr_town or ''
    home_village = user.village or user.curr_village or ''
    # 보정 오프셋 적용: 학습된 GPS 오차 보정
    corrected_lat = from_lat + (user.curr_offset_lat or 0)
    corrected_lng = from_lng + (user.curr_offset_lng or 0)
    from services.transit import suggest_optimal_departure, lookup_village_coords, haversine_km
    from services.geocode import gps_to_town_village
    gps_result = gps_to_town_village(corrected_lat, corrected_lng)
    gps_town = gps_result[0] if gps_result else ""
    gps_village = gps_result[1] if gps_result else ""
    same_village = bool(gps_town and gps_town == home_town and gps_village == home_village)
    # 집 판정: 보정좌표와 등록좌표 거리 1km 이내면 집
    user_home_lat = user.curr_latitude or user.reg_latitude or 0
    user_home_lng = user.curr_longitude or user.reg_longitude or 0
    is_home = False
    if user_home_lat and user_home_lng:
        d = haversine_km(corrected_lat, corrected_lng, user_home_lat, user_home_lng)
        is_home = d <= 0.2
    if not is_home:
        same_village = bool(gps_town and gps_town == home_town and gps_village == home_village)
        is_home = same_village
    if is_home:
        home_addr = user.curr_address or f"{home_town} {home_village}"
        return jsonify({
            "already_home": True,
            "message": f"🏠 집입니다! 현재 위치가 {home_addr} 근처입니다.",
            "home_address": home_addr,
        })
    suggestion = suggest_optimal_departure(from_lat, from_lng, home_town, home_village)
    if not suggestion:
        return jsonify({"error": "경로를 찾을 수 없습니다."}), 404
    # 보정된 위치가 있으면 그걸로 집 좌표+주소 사용
    if user.curr_latitude and user.curr_longitude:
        home_coords = {"lat": user.curr_latitude, "lng": user.curr_longitude}
    else:
        home_coords = lookup_village_coords(home_town, home_village)
        if home_coords:
            home_coords = {"lat": home_coords[0], "lng": home_coords[1]}
    if home_coords:
        suggestion["home_coords"] = home_coords
        suggestion["home_distance_km"] = round(haversine_km(
            suggestion["station_coords"]["lat"], suggestion["station_coords"]["lng"],
            home_coords["lat"], home_coords["lng"]
        ), 1)
    suggestion["home_town"] = user.curr_town
    suggestion["home_village"] = user.curr_village
    suggestion["home_address"] = user.curr_address or user.address or ''
    suggestion["already_home"] = False
    suggestion["corrected"] = bool(user.curr_offset_lat or user.curr_offset_lng)
    suggestion["corrected_lat"] = corrected_lat
    suggestion["corrected_lng"] = corrected_lng
    from urllib.parse import quote
    sc = suggestion["station_coords"]
    sname = quote(suggestion["transfer_station"])
    suggestion["deep_links"] = {
        "kakao": f"https://map.kakao.com/?sX={from_lng}&sY={from_lat}&eX={sc['lng']}&eY={sc['lat']}&eName={sname}",
        "naver": f"https://map.naver.com/index.nhn?slat={from_lat}&slng={from_lng}&elat={sc['lat']}&elng={sc['lng']}&etitle={sname}&pathType=1"
    }
    return jsonify(suggestion)

@construction_bp.route('/construction/traffic/gg')
def construction_traffic_gg():
    import json
    # 캐시 우선 조회
    cache = VillageCache.query.filter_by(data_type='traffic').order_by(VillageCache.updated_at.desc()).first()
    if cache and cache.updated_at and (datetime.now() - cache.updated_at).seconds < 600:
        data = json.loads(cache.data_json or '[]')
        return jsonify({"available":True,"yangpyeong":cache.data_count,"incidents":data,"cached":True})
    from services.utic_traffic import traffic_summary as utic_summary
    return jsonify(utic_summary())

def _resolve_canonical_store_name(report):
    """네이버 역지오코딩으로 건물명 조회 (Smartplace 대체), 실패시 카카오"""
    if not report.latitude or not report.longitude:
        return
    try:
        import requests
        best_name = None
        best_source = None
        smartplace = None

        # 1) 네이버 Reverse Geocoding: 좌표 → 건물명
        ncp_id = current_app.config.get('NAVER_SEARCH_CLIENT_ID','')
        ncp_secret = current_app.config.get('NAVER_SEARCH_CLIENT_SECRET','')
        if ncp_id and ncp_secret:
            resp = requests.get('https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc', params={
                'coords': f'{report.longitude},{report.latitude}',
                'orders': 'roadaddr',
                'output': 'json'
            }, headers={
                'x-ncp-apigw-api-key-id': ncp_id,
                'x-ncp-apigw-api-key': ncp_secret,
            }, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                for r in data.get('results', []):
                    if r.get('name') == 'roadaddr':
                        land = r.get('land', {})
                        bldg = next((a.get('value','') for a in [land.get('addition0',{}), land.get('addition1',{}), land.get('addition2',{}), land.get('addition3',{}), land.get('addition4',{})] if a.get('type') == 'building'), '')
                        if bldg:
                            best_name = bldg
                            best_source = 'naver'
                        # 네이버 지도 링크 생성
                        smartplace = f'https://map.naver.com/p?c={report.longitude},{report.latitude},16,0,0,0,dh'
                        break

        # 2) 카카오 키워드 검색 (fallback)
        if not best_name:
            kakao_key = current_app.config.get('KAKAO_REST_API_KEY','')
            if kakao_key:
                resp = requests.get('https://dapi.kakao.com/v2/local/search/keyword.json', params={
                    'query': (report.title or '').strip()[:30],
                    'x': str(report.longitude),
                    'y': str(report.latitude),
                    'radius': 1000,
                    'size': 1
                }, headers={'Authorization': f'KakaoAK {kakao_key}'}, timeout=3)
                if resp.status_code == 200:
                    docs = resp.json().get('documents', [])
                    if docs:
                        from services.transit import haversine_km
                        p = docs[0]
                        d = haversine_km(report.latitude, report.longitude, float(p.get('y',0)), float(p.get('x',0)))
                        if d <= 1.0:
                            best_name = p.get('place_name','')
                            best_source = 'kakao'
                            smartplace = p.get('place_url','') or f'https://map.naver.com/p?c={report.longitude},{report.latitude},16,0,0,0,dh'

        if best_name:
            report.canonical_name = best_name
            report.canonical_source = best_source
        if smartplace:
            report.smartplace_url = smartplace
    except:
        pass

def _normalize_store_name(title):
    """이름 정규화: 공백+특수문자 제거, 앞20자"""
    import re
    return re.sub(r'[\s\-_.,·]+', '', (title or '제목없음'))[:20]

@construction_bp.route('/construction/local-stores')
def construction_local_stores():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    user = User.query.get(uid)
    if not user or (not user.town and not user.curr_town):
        return jsonify({"error": "등록된 주소가 없습니다."}), 400
    town = user.town or user.curr_town
    village = user.village or user.curr_village
    stores = ShareReport.query.filter_by(
        town=town, village=village, status='approved'
    ).order_by(ShareReport.created_at.desc()).limit(50).all()
    # 그룹화: 100m 이내 같은 위치 → 하나의 가게
    from services.transit import haversine_km
    grouped = {}
    for s in stores:
        slat = s.latitude or 0
        slng = s.longitude or 0
        matched_key = None
        for gk, gv in grouped.items():
            if slat and slng and gv["lat"] and gv["lng"]:
                d = haversine_km(float(gv["lat"]), float(gv["lng"]), slat, slng)
                if d <= 0.1:
                    matched_key = gk
                    break
        if matched_key:
            g = grouped[matched_key]
            g["posts"].append({
                "id": s.id, "title": s.title, "desc": (s.description or "")[:100],
                "user": s.author_name or "익명", "image": s.image_path,
                "date": s.created_at.strftime("%m/%d") if s.created_at else ""
            })
            if s.image_path and not g["image"]:
                g["image"] = s.image_path
        else:
            key = f"{round(slat,4)}|{round(slng,4)}"
            grouped[key] = {
                "name": s.title or "제목없음",
                "posts": [{
                    "id": s.id, "title": s.title, "desc": (s.description or "")[:100],
                    "user": s.author_name or "익명", "image": s.image_path,
                    "date": s.created_at.strftime("%m/%d") if s.created_at else ""
                }],
                "image": s.image_path,
                "lat": s.latitude, "lng": s.longitude,
            }
    # StoreInfo 매칭: 각 그룹 좌표와 가장 가까운 StoreInfo(100m 이내) 찾기
    store_infos = StoreInfo.query.filter_by(town=town, village=village).all()
    for gk, gv in grouped.items():
        for si in store_infos:
            if si.latitude and si.longitude and gv["lat"] and gv["lng"]:
                d = haversine_km(si.latitude, si.longitude, float(gv["lat"]), float(gv["lng"]))
                if d <= 0.1:
                    gv["name"] = si.name
                    gv["store_link"] = si.our_link or si.store_homepage or si.smartplace or None
                    gv["link_label"] = "🏠 가게소개" if si.our_link else ("🌐 홈페이지" if si.store_homepage else ("📍 스마트플레이스" if si.smartplace else None))
                    break
    result = {
        "town": town, "village": village,
        "stores": list(grouped.values())[:20],
    }
    return jsonify(result)

@construction_bp.route('/construction/store/<string:store_name>')
def construction_store_detail(store_name):
    uid = session.get('user_id')
    user = User.query.get(uid) if uid else None
    town = request.args.get('town','')
    village = request.args.get('village','')
    target_lat = request.args.get('lat','0')
    target_lng = request.args.get('lng','0')
    stores = ShareReport.query.filter_by(
        town=town, village=village, status='approved'
    ).order_by(ShareReport.created_at.desc()).all()
    from services.transit import haversine_km
    target_lat_f = float(target_lat)
    target_lng_f = float(target_lng)
    grouped = []
    for s in stores:
        if s.latitude and s.longitude and target_lat_f and target_lng_f:
            d = haversine_km(target_lat_f, target_lng_f, s.latitude, s.longitude)
            if d <= 0.1:
                grouped.append(s)
    if not grouped:
        from urllib.parse import unquote
        name = _normalize_store_name(unquote(store_name))
        grouped = [s for s in stores if _normalize_store_name(s.canonical_name or s.title) == name]
    if not grouped:
        return "가게를 찾을 수 없습니다.", 404

    # StoreInfo 매칭
    store_link = None
    link_label = None
    display_name = store_name
    if target_lat_f and target_lng_f:
        sis = StoreInfo.query.filter_by(town=town, village=village).all()
        for si in sis:
            if si.latitude and si.longitude:
                if haversine_km(si.latitude, si.longitude, target_lat_f, target_lng_f) <= 0.1:
                    display_name = si.name
                    store_link = si.our_link or si.store_homepage or si.smartplace or None
                    link_label = "🏠 가게소개" if si.our_link else ("🌐 홈페이지" if si.store_homepage else ("📍 스마트플레이스" if si.smartplace else None))
                    break

    naver_map = f'https://map.naver.com/p?c={target_lng},{target_lat},16,0,0,0,dh' if target_lat_f and target_lng_f else None
    # 갤러리 이미지 수집
    gallery = []
    for p in grouped:
        if p.image_path and p.image_path not in gallery:
            gallery.append(p.image_path)
    # 주소: 공유글 address → location → GPS 역지오코딩
    store_address = ''
    if grouped:
        store_address = grouped[0].address or grouped[0].location or ''
    if not store_address and target_lat_f and target_lng_f:
        from services.transit import reverse_geocode
        from config import Config
        geo = reverse_geocode(target_lat_f, target_lng_f,
            kakao_key=Config.KAKAO_REST_API_KEY,
            naver_id=Config.NAVER_CLIENT_ID or Config.NAVER_SEARCH_CLIENT_ID,
            naver_secret=Config.NAVER_CLIENT_SECRET or Config.NAVER_SEARCH_CLIENT_SECRET)
        if geo and geo.get('address'):
            store_address = geo['address']
    if not store_address:
        store_address = f'{town} {village}'
    return render_template('store_detail.html', store_name=display_name, posts=grouped, town=town, village=village, store_link=store_link, link_label=link_label, naver_map=naver_map, gallery=gallery, store_address=store_address)

@construction_bp.route('/construction/local-scenery')
def construction_local_scenery():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    user = User.query.get(uid)
    if not user or not user.curr_town or not user.curr_village:
        return jsonify({"error": "등록된 주소(리)가 없습니다."}), 400
    now = datetime.now()
    cur_month = now.month
    season_months = {1,2,12} if cur_month in (1,2,12) else {3,4,5} if cur_month in (3,4,5) else {6,7,8} if cur_month in (6,7,8) else {9,10,11}
    season_name = '겨울' if cur_month in (1,2,12) else '봄' if cur_month in (3,4,5) else '여름' if cur_month in (6,7,8) else '가을'
    all_approved = ShareReport.query.filter_by(
        town=user.curr_town,
        village=user.curr_village,
        status='approved'
    ).order_by(ShareReport.created_at.desc()).all()
    scenery = []
    for s in all_approved:
        if not s.image_path:
            continue
        if s.created_at and s.created_at.month in season_months and s.id:
            # 같은 게시물이 scenery와 stores에 모두 나오는 것 방지: 
            # ai_category가 'store'/'가게'면 건너뛰기
            cat = (s.ai_category or '').lower()
            if cat in ('store','가게','상점','마트','음식점','식당','카페'):
                continue
            scenery.append(s)
    return jsonify({
        "town": user.curr_town,
        "village": user.curr_village,
        "season": season_name,
        "sceneries": [{
            "id": s.id,
            "title": s.title or "제목없음",
            "image_path": s.image_path,
            "description": (s.description or "")[:100],
            "created_at": s.created_at.strftime("%Y-%m-%d") if s.created_at else "",
        } for s in scenery[:30]],
    })

# ---- 동네가게 관리 (Admin) ----
@construction_bp.route('/admin/stores')
def admin_stores():
    if session.get('role') not in ('admin','leader'):
        return "권한 없음", 403
    stores = StoreInfo.query.order_by(StoreInfo.town, StoreInfo.name).all()
    return render_template('admin_stores.html', stores=stores)

@construction_bp.route('/admin/stores/new', methods=['GET','POST'])
def admin_stores_new():
    if session.get('role') not in ('admin','leader'):
        return "권한 없음", 403
    if request.method == 'POST':
        s = StoreInfo(
            name=request.form.get('name','').strip(),
            latitude=float(request.form.get('latitude',0) or 0),
            longitude=float(request.form.get('longitude',0) or 0),
            town=request.form.get('town','').strip(),
            village=request.form.get('village','').strip(),
            our_link=request.form.get('our_link','').strip(),
            store_homepage=request.form.get('store_homepage','').strip(),
            smartplace=request.form.get('smartplace','').strip(),
        )
        db.session.add(s)
        db.session.commit()
        return redirect('/admin/stores')
    return render_template('admin_store_edit.html', store=None)

@construction_bp.route('/admin/stores/edit/<int:store_id>', methods=['GET','POST'])
def admin_stores_edit(store_id):
    if session.get('role') not in ('admin','leader'):
        return "권한 없음", 403
    s = StoreInfo.query.get_or_404(store_id)
    if request.method == 'POST':
        s.name = request.form.get('name','').strip()
        s.latitude = float(request.form.get('latitude',0) or 0)
        s.longitude = float(request.form.get('longitude',0) or 0)
        s.town = request.form.get('town','').strip()
        s.village = request.form.get('village','').strip()
        s.our_link = request.form.get('our_link','').strip()
        s.store_homepage = request.form.get('store_homepage','').strip()
        s.smartplace = request.form.get('smartplace','').strip()
        db.session.commit()
        return redirect('/admin/stores')
    return render_template('admin_store_edit.html', store=s)

@construction_bp.route('/admin/stores/delete/<int:store_id>', methods=['POST'])
def admin_stores_delete(store_id):
    if session.get('role') not in ('admin','leader'):
        return jsonify({"status":"error"}), 403
    s = StoreInfo.query.get_or_404(store_id)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"status":"success"})

@construction_bp.route('/admin/alerts')
def admin_alerts():
    if session.get('role') not in ('admin', 'leader', 'village_leader'):
        return "권한 없음", 403
    role = session.get('role')
    user_town = session.get('town', '')
    user_village = session.get('village', '')
    if role == 'admin':
        alerts = VillageAlert.query.order_by(VillageAlert.created_at.desc()).all()
    elif role == 'leader':
        alerts = VillageAlert.query.filter_by(town=user_town).order_by(VillageAlert.created_at.desc()).all()
    else:
        alerts = VillageAlert.query.filter_by(town=user_town, village=user_village).order_by(VillageAlert.created_at.desc()).all()
    return render_template('admin_alerts.html', alerts=alerts, role=role, town=user_town, village=user_village)

@construction_bp.route('/admin/alerts/new', methods=['GET', 'POST'])
def admin_alerts_new():
    if session.get('role') not in ('admin', 'leader', 'village_leader'):
        return "권한 없음", 403
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        alert_type = request.form.get('alert_type', 'general')
        urgency = request.form.get('urgency', 'normal')
        town = request.form.get('town', '').strip()
        village = request.form.get('village', '').strip()
        if not title:
            return "<script>alert('제목을 입력하세요.'); history.back();</script>"
        alert = VillageAlert(
            title=title, content=content, alert_type=alert_type, urgency=urgency,
            town=town, village=village,
            author_id=session.get('user_id'),
            author_name=session.get('username', '')
        )
        db.session.add(alert)
        db.session.flush()
        # 마을주민 자동 쪽지
        if town:
            recipients = User.query.filter(User.village_notify != False, User.town == town)
            if village:
                recipients = recipients.filter(User.village == village)
            for r in recipients.all():
                db.session.add(Message(sender_id=session.get('user_id'), sender_name=session.get('username','관리자'),
                    receiver_id=r.id, subject=f'🚨 마을소식: {title}',
                    content=f'[{town} {village}] {title}\n\n{content}\n\n자세한 내용은 위치기반안내 > 알림에서 확인하세요.',
                    sender_role=session.get('role','admin')))
        db.session.commit()
        return redirect('/admin/alerts')
    user_town = session.get('town', '')
    user_village = session.get('village', '')
    towns = db.session.query(VillageAlert.town).distinct().all() if session.get('role') == 'admin' else [(user_town,)]
    return render_template('admin_alerts_new.html', town=user_town, village=user_village, role=session.get('role'), towns=[t[0] for t in towns if t[0]])

@construction_bp.route('/admin/alerts/edit/<int:alert_id>', methods=['GET', 'POST'])
def admin_alerts_edit(alert_id):
    if session.get('role') not in ('admin', 'leader', 'village_leader'):
        return "권한 없음", 403
    alert = VillageAlert.query.get_or_404(alert_id)
    if request.method == 'POST':
        alert.title = request.form.get('title', '').strip()
        alert.content = request.form.get('content', '').strip()
        alert.alert_type = request.form.get('alert_type', 'general')
        alert.urgency = request.form.get('urgency', 'normal')
        alert.is_active = request.form.get('is_active') == '1'
        if session.get('role') == 'admin':
            alert.town = request.form.get('town', '').strip()
            alert.village = request.form.get('village', '').strip()
        alert.updated_at = datetime.now()
        db.session.commit()
        return redirect('/admin/alerts')
    return render_template('admin_alerts_edit.html', alert=alert, role=session.get('role'))

@construction_bp.route('/admin/alerts/delete/<int:alert_id>', methods=['POST'])
def admin_alerts_delete(alert_id):
    if session.get('role') not in ('admin', 'leader', 'village_leader'):
        return "권한 없음", 403
    alert = VillageAlert.query.get_or_404(alert_id)
    db.session.delete(alert)
    db.session.commit()
    return redirect('/admin/alerts')

@construction_bp.route('/api/user/unread')
def api_user_unread():
    uid = session.get('user_id')
    if not uid: return jsonify({"count": 0})
    count = Message.query.filter_by(receiver_id=uid, is_read=False).count()
    return jsonify({"count": count})

@construction_bp.route('/api/construction/unread')
def api_construction_unread():
    uid = session.get('user_id')
    user = User.query.get(uid) if uid else None
    alerts = 0
    if user and user.town:
        alerts = VillageAlert.query.filter_by(is_active=True, town=user.town).count()
    return jsonify({"alerts": alerts, "heritage": 0, "scenery": 0})

@construction_bp.route('/construction/safetydata')
def construction_safetydata():
    from services.safetydata import get_yangpyeong_safety, TYPE_NAMES
    data = get_yangpyeong_safety()
    total = sum(len(v) for v in data.values())
    return jsonify({"available": True, "total": total, "types": {k: {"name": TYPE_NAMES.get(k,k), "items": v[:10]} for k, v in data.items() if v}}) 

@construction_bp.route('/api/user/location', methods=['GET','POST'])
def api_user_location():
    if request.method == 'POST':
        uid = session.get('user_id')
        if not uid: return jsonify({"status":"error","msg":"login"})
        user = User.query.get(uid)
        loc = request.get_json().get('manual_loc','')
        if not loc: return jsonify({"status":"error","msg":"need location"})
        parts = loc.strip().split()
        if len(parts) >= 2:
            user.curr_town = parts[0]
            user.curr_village = parts[1]
            user.location_updated_at = datetime.now()
            db.session.commit()
            return jsonify({"status":"success","msg":"ok"})
        return jsonify({"status":"error","msg":"format"})
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "login"}), 401
    from models import User
    user = User.query.get(uid)
    if not user:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"town": user.curr_town or "", "village": user.curr_village or "", "address": user.curr_address or ""})

@construction_bp.route('/construction/refresh')
def construction_refresh():
    if session.get('role') not in ('admin', 'leader'):
        return "권한 없음", 403
    from flask import current_app
    from config import Config
    dg_key = getattr(Config, 'DATA_GO_KR_API_KEY', '')
    gg_key = getattr(Config, 'GG_TRAFFIC_API_KEY', '')
    build_key = getattr(Config, 'GG_BUILDING_API_KEY', '')
    arch_hub_key = getattr(Config, 'ARCH_HUB_API_KEY', '')
    if not dg_key and not gg_key and not build_key and not arch_hub_key:
        return "<script>alert('API 키가 설정되지 않았습니다. config.py를 확인하세요.'); history.back();</script>"
    import threading
    if dg_key:
        threading.Thread(target=sync_construction_notices, args=(current_app._get_current_object(), dg_key)).start()
    if gg_key:
        threading.Thread(target=sync_traffic_incidents, args=(current_app._get_current_object(), gg_key)).start()
        threading.Thread(target=sync_congestion_info, args=(current_app._get_current_object(), gg_key)).start()
    if build_key:
        from services.construction import sync_building_permits
        threading.Thread(target=sync_building_permits, args=(current_app._get_current_object(), build_key)).start()
    if arch_hub_key:
        from services.construction import sync_architecture_hub
        threading.Thread(target=sync_architecture_hub, args=(current_app._get_current_object(), arch_hub_key)).start()
    return "<script>alert('정보 갱신이 시작되었습니다.'); location.href='/construction';</script>"

# --- [상시 서비스 3종] ---


@construction_bp.route('/api/construction/notices')
def api_construction_notices():
    six_months_ago = datetime.now() - timedelta(days=180)
    notices = ConstructionNotice.query.filter(
        ConstructionNotice.is_active == True,
        db.or_(
            ConstructionNotice.start_date >= six_months_ago,
            ConstructionNotice.start_date == None
        )
    ).all()
    # GPS 우선, 없으면 집/회사 위치
    gps_lat = request.args.get('lat', type=float)
    gps_lng = request.args.get('lng', type=float)
    ref_lat = ref_lng = None
    town = village = ''
    if gps_lat and gps_lng:
        ref_lat, ref_lng = gps_lat, gps_lng
        try:
            from services.geocode import gps_to_town_village
            t, v = gps_to_town_village(gps_lat, gps_lng)
            town, village = t or '', v or ''
        except Exception:
            pass
    else:
        uid = session.get('user_id')
        if uid:
            user = User.query.get(uid)
            if user and (user.curr_latitude or user.reg_latitude):
                ref_lat = user.curr_latitude or user.reg_latitude
                ref_lng = user.curr_longitude or user.reg_longitude
                town = user.curr_town or ''
                village = user.curr_village or ''
    out = []
    for n in notices:
        d = None
        if ref_lat and n.latitude and n.longitude:
            d = round(haversine_km(ref_lat, ref_lng, n.latitude, n.longitude), 1)
        out.append({
            "id": n.id, "title": n.title, "description": n.description,
            "location": n.location, "latitude": n.latitude, "longitude": n.longitude,
            "notice_type": n.notice_type, "source": n.source,
            "start_date": n.start_date.strftime('%Y-%m-%d') if n.start_date else None,
            "end_date": n.end_date.strftime('%Y-%m-%d') if n.end_date else None,
            "distance_km": d,
        })
    if ref_lat:
        out.sort(key=lambda x: x['distance_km'] if x['distance_km'] is not None else 999)
    return jsonify({"notices": out, "town": town, "village": village,
                    "based_on": "gps" if (gps_lat and gps_lng) else "home"})

@construction_bp.route('/api/construction/alerts')
def api_construction_alerts():
    alerts = VillageAlert.query.filter_by(is_active=True).order_by(VillageAlert.created_at.desc()).limit(20).all()
    out = [{
        "id": a.id, "title": a.title, "content": a.content,
        "alert_type": a.alert_type, "urgency": a.urgency,
        "town": a.town, "village": a.village,
        "created_at": a.created_at.strftime('%Y-%m-%d %H:%M') if a.created_at else None,
    } for a in alerts]
    return jsonify({"alerts": out})

@construction_bp.route('/api/facilities')
def api_facilities():
    ftype = request.args.get('type', 'toilet')
    facs = PublicFacility.query.filter_by(facility_type=ftype, is_active=True).all()
    uid = session.get('user_id')
    home_lat = home_lng = None
    if uid:
        user = User.query.get(uid)
        if user and (user.curr_latitude or user.reg_latitude):
            home_lat = user.curr_latitude or user.reg_latitude
            home_lng = user.curr_longitude or user.reg_longitude
    out = []
    for f in facs:
        d = None
        if home_lat and f.latitude and f.longitude:
            d = round(haversine_km(home_lat, home_lng, f.latitude, f.longitude), 1)
        out.append({
            "id": f.id, "name": f.name, "address": f.address,
            "latitude": f.latitude, "longitude": f.longitude,
            "open_hr": f.open_hr, "tel": f.tel, "manager": f.manager,
            "emergency_bell": f.emergency_bell, "cctv": f.cctv,
            "facility_type": f.facility_type, "distance_km": d,
        })
    if home_lat:
        out.sort(key=lambda x: x['distance_km'] if x['distance_km'] is not None else 999)
    return jsonify({"facilities": out, "type": ftype})

@construction_bp.route('/construction/refresh-facilities', methods=['POST'])
def refresh_facilities():
    if session.get('role') not in ('admin', 'leader'):
        return jsonify({"error": "권한 없음"}), 403
    from config import Config
    key = getattr(Config, 'SAFEMAP_API_KEY', '')
    if not key:
        return jsonify({"error": "SAFEMAP_API_KEY 미설정"}), 400
    from services.construction import sync_public_facilities
    sync_public_facilities(current_app._get_current_object(), key)
    return jsonify({"status": "success", "msg": "편의시설 동기화 완료"})
