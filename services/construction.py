import requests
import json
from datetime import datetime
from models import db, ConstructionNotice

CALS_BASE = "http://openapi.calspia.go.kr/openapi/service"
GG_INCIDENT_URL = "https://openapigits.gg.go.kr/api/rest/getIncidentInfo"
GG_CONGEST_URL  = "https://openapigits.gg.go.kr/api/rest/getRoadLinkCongestInfo"
GG_BUILDING_URL = "https://openapi.gg.go.kr/Buildstrcontr"

def fetch_cals_road_construction(api_key):
    url = f"{CALS_BASE}/roadCstrncInfoService/getRoadCstrncList"
    params = {"serviceKey": api_key, "numOfRows": 100, "pageNo": 1, "type": "json"}
    try:
        res = requests.get(url, params=params, timeout=15)
        data = res.json()
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if isinstance(items, dict): items = [items]
        return items
    except Exception as e:
        print(f"[CALS API] error: {e}"); return []

def fetch_traffic_incidents(api_key):
    if not api_key: return []
    try:
        res = requests.get(GG_INCIDENT_URL, params={"serviceKey": api_key}, timeout=15)
        data = res.json()
        items = data.get("body", data.get("response", {}).get("body", {}).get("items", {}).get("item", []))
        if isinstance(items, dict): items = [items]
        return items
    except Exception as e:
        print(f"[TRAFFIC INCIDENT] error: {e}"); return []

def fetch_congestion_info(api_key):
    """경기도 지정체 구간정보 조회"""
    if not api_key: return []
    try:
        res = requests.get(GG_CONGEST_URL, params={"serviceKey": api_key}, timeout=15)
        data = res.json()
        items = data.get("body", data.get("response", {}).get("body", {}).get("items", {}).get("item", []))
        if isinstance(items, dict): items = [items]
        return items
    except Exception as e:
        print(f"[CONGEST API] error: {e}"); return []

def sync_traffic_incidents(app, api_key):
    if not api_key: print("[TRAFFIC] No API key. Skipping."); return
    with app.app_context():
        ConstructionNotice.query.filter_by(source="gg_traffic", notice_type="traffic_incident", is_active=True).update({"is_active": False})
        db.session.commit()
        count = 0
        for item in fetch_traffic_incidents(api_key):
            title = item.get("inciDesc", "교통 돌발")
            desc = item.get("inciDesc", "")
            place = f"{item.get('inciplace1', '')} {item.get('inciplace2', '')}".strip()
            lat = item.get("coord_y"); lon = item.get("coord_x")
            try: start = datetime.strptime(item.get("startDate", "")[:14], "%Y%m%d%H%M%S") if item.get("startDate") else None
            except: start = None
            try: end = datetime.strptime(item.get("estEndDate", "")[:14], "%Y%m%d%H%M%S") if item.get("estEndDate") else None
            except: end = None
            reg_id = item.get("regSeq", "")
            if not reg_id: continue
            exists = ConstructionNotice.query.filter_by(source="gg_traffic", source_url=reg_id).first()
            if exists: exists.is_active = True; exists.updated_at = datetime.now(); continue
            db.session.add(ConstructionNotice(title=title[:300], description=desc, location=place,
                latitude=float(lat) if lat else None, longitude=float(lon) if lon else None,
                source="gg_traffic", source_url=str(reg_id), notice_type="traffic_incident",
                start_date=start, end_date=end, is_active=True))
            count += 1
        db.session.commit()
        print(f"[TRAFFIC INCIDENT] Synced {count} new.")

def sync_congestion_info(app, api_key):
    """지정체 구간정보 동기화"""
    if not api_key: print("[CONGEST] No API key. Skipping."); return
    with app.app_context():
        ConstructionNotice.query.filter_by(source="gg_traffic", notice_type="traffic_congestion", is_active=True).update({"is_active": False})
        db.session.commit()
        count = 0
        for item in fetch_congestion_info(api_key):
            route = item.get("routeNm", "")
            start_nm = item.get("startNodeNm", "")
            end_nm = item.get("endNodeNm", "")
            spd = item.get("spd", "0")
            grade = item.get("congGrade", "0")
            title = f"{route} {start_nm}→{end_nm}"
            grade_map = {'0':'정보없음','1':'원활','2':'지체','3':'정체'}
            desc = f"속도: {spd}km/h | 혼잡도: {grade_map.get(grade, '알수없음')}"
            link_id = item.get("linkId", "")
            if not title.strip() or not link_id: continue
            link_key = f"{route}|{link_id}"
            exists = ConstructionNotice.query.filter_by(source="gg_traffic", source_url=link_key).first()
            if exists: exists.is_active = True; exists.updated_at = datetime.now(); continue
            db.session.add(ConstructionNotice(title=title[:300], description=desc, location=route,
                source="gg_traffic", source_url=link_key, notice_type="traffic_congestion", is_active=True))
            count += 1
        db.session.commit()
        print(f"[CONGEST] Synced {count} new.")

def sync_construction_notices(app, api_key):
    if not api_key: print("[CONSTRUCTION] No API key. Skipping."); return
    with app.app_context():
        count = 0
        for item in fetch_cals_road_construction(api_key):
            title = item.get("cstrncNm", item.get("roadCstrncNm", ""))
            if not title: continue
            loc = item.get("cstrncSggCd", "")
            lat = item.get("lat", item.get("latitude")); lon = item.get("lon", item.get("longitude"))
            start = item.get("cstrncBeginDe", item.get("beginDe")); end = item.get("cstrncEndDe", item.get("endDe"))
            if ConstructionNotice.query.filter_by(title=title, source="cals").first(): continue
            db.session.add(ConstructionNotice(title=title, description=item.get("cstrncCn", ""), location=loc,
                latitude=float(lat) if lat else None, longitude=float(lon) if lon else None,
                source="cals", source_url="", notice_type="road_construction",
                start_date=datetime.strptime(start, "%Y%m%d") if start and len(start)==8 else None,
                end_date=datetime.strptime(end, "%Y%m%d") if end and len(end)==8 else None, is_active=True))
            count += 1
        if count: db.session.commit()
        print(f"[CONSTRUCTION] Synced {count} new.")

def sync_building_permits(app, api_key):
    """경기데이터드림 건축착공 신고 현황 → ConstructionNotice"""
    if not api_key: print("[BUILDING] No API key. Skipping."); return
    with app.app_context():
        from models import ConstructionNotice
        import requests
        count = 0
        try:
            resp = requests.get(GG_BUILDING_URL, params={
                'Key': api_key, 'Type': 'json', 'pIndex': 1, 'pSize': 100,
                'SIGUN_NM': '양평군'
            }, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('Buildstrcontr', [])
                # items는 [{head:...}, {row:[...]}] 구조
                rows = []
                if isinstance(items, list):
                    for part in items:
                        if isinstance(part, dict) and 'row' in part:
                            rows = part['row']
                            break
                elif isinstance(items, dict):
                    rows = items.get('row', [])
                if not isinstance(rows, list):
                    rows = []
                for row in rows:
                    sigun = row.get('SIGUN_NM', '')
                    if '양평' not in sigun:
                        continue
                    lat = row.get('REFINE_WGS84_LAT')
                    lng = row.get('REFINE_WGS84_LOGT')
                    title = row.get('BIZ_REGION_INFO', '') or '건축공사'
                    stmt_date = row.get('STATMNT_DE', '')
                    builder = row.get('CNSTRCT_BIZNES_INFO', '')
                    office = row.get('ETC_SERVC_INFO', '')
                    key_str = f"{title}|{stmt_date}|{builder}"
                    if ConstructionNotice.query.filter_by(title=title, source="gg_building").first():
                        continue
                    desc_parts = []
                    if builder: desc_parts.append(f'시공사: {builder}')
                    if office: desc_parts.append(f'설계사무소: {office}')
                    if stmt_date: desc_parts.append(f'신고일: {stmt_date}')
                    db.session.add(ConstructionNotice(
                        title=title,
                        description=' | '.join(desc_parts),
                        location=sigun,
                        latitude=float(lat) if lat else None,
                        longitude=float(lng) if lng else None,
                        source='gg_building', source_url='',
                        notice_type='building_permit',
                        start_date=datetime.strptime(stmt_date, "%Y%m%d") if stmt_date and len(stmt_date)==8 else None,
                        is_active=True
                    ))
                    count += 1
            else:
                print(f"[BUILDING] API error: {resp.status_code}")
        except Exception as e:
            print(f"[BUILDING] Error: {e}")
        if count: db.session.commit()
        print(f"[BUILDING] Synced {count} new.")
