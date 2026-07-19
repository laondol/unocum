import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from models import db, ConstructionNotice

# 양평군 중심 좌표 (위도, 경도)
YANGPYEONG_LAT = 37.49
YANGPYEONG_LON = 127.63
YANGPYEONG_RADIUS_KM = 30.0

def _haversine_km(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, asin, sqrt
    if None in (lat1, lon1, lat2, lon2): return 999.0
    dlat = radians(lat2 - lat1); dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 6371.0 * 2 * asin(sqrt(a))

def _in_yangpyeong(lat, lon, place=""):
    if "양평" in (place or ""):
        return True
    d = _haversine_km(YANGPYEONG_LAT, YANGPYEONG_LON, lat, lon)
    return d <= YANGPYEONG_RADIUS_KM

def _xml_items(text, tag="itemList"):
    try:
        root = ET.fromstring(text)
    except Exception:
        return []
    return root.findall(f".//{tag}")

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
        items = _xml_items(res.text, "itemList")
        out = []
        for it in items:
            def g(t):
                e = it.find(t)
                return e.text if e is not None else ""
            lat = g("coord_y"); lon = g("coord_x")
            try: flat = float(lat) if lat else None
            except: flat = None
            try: flon = float(lon) if lon else None
            except: flon = None
            place = f"{g('inciPlace1')} {g('inciPlace2')}".strip()
            if not _in_yangpyeong(flat, flon, place):
                continue
            out.append({
                "inciDesc": g("inciDesc"),
                "inciplace1": g("inciPlace1"),
                "inciplace2": g("inciPlace2"),
                "coord_y": lat, "coord_x": lon,
                "startDate": g("startDate"), "estEndDate": g("estEndDate"),
                "regSeq": g("regSeq"), "restrictType": g("restrictType"),
            })
        return out
    except Exception as e:
        print(f"[TRAFFIC INCIDENT] error: {e}"); return []

def fetch_congestion_info(api_key):
    """경기도 지정체 구간정보 조회 (XML)"""
    if not api_key: return []
    try:
        res = requests.get(GG_CONGEST_URL, params={"serviceKey": api_key}, timeout=15)
        items = _xml_items(res.text, "itemList")
        out = []
        for it in items:
            def g(t):
                e = it.find(t)
                return e.text if e is not None else ""
            lat = g("coord_y"); lon = g("coord_x")
            try: flat = float(lat) if lat else None
            except: flat = None
            try: flon = float(lon) if lon else None
            except: flon = None
            route = g("routeNm")
            place = route
            if not _in_yangpyeong(flat, flon, place):
                continue
            out.append({
                "routeNm": route,
                "startNodeNm": g("startNodeNm"),
                "endNodeNm": g("endNodeNm"),
                "spd": g("spd"), "congGrade": g("congGrade"),
                "linkId": g("linkId"),
                "coord_y": lat, "coord_x": lon,
            })
        return out
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


# --- [건축데이터허브(국토부) 건축인허가 기본개요] ---
ARCH_HUB_URL = "http://apis.data.go.kr/1613000/ArchPmsHubService/getApBasisOulnInfo"
YANGPYEONG_SIGUNGU_CD = "41830"  # 양평군 시군구코드 (첨부2 PDF)


def _parse_yyyymmdd(v):
    if not v or len(str(v)) != 8:
        return None
    try:
        return datetime.strptime(str(v), "%Y%m%d")
    except Exception:
        return None


def sync_architecture_hub(app, api_key):
    """건축데이터허브 건축인허가 기본개요 -> ConstructionNotice(notice_type='building_permit')"""
    if not api_key:
        print("[ARCHHUB] No API key. Skipping.")
        return
    with app.app_context():
        from models import ConstructionNotice
        count = 0
        try:
            for bjdong in range(10000, 100000, 100):
                bj = f"{bjdong:05d}"
                pIdx = 1
                while True:
                    resp = requests.get(ARCH_HUB_URL, params={
                        'serviceKey': api_key,
                        'sigunguCd': YANGPYEONG_SIGUNGU_CD,
                        'bjdongCd': bj,
                        'platGbCd': '0',
                        'numOfRows': 100,
                        'pageNo': pIdx,
                        '_type': 'json',
                    }, timeout=15)
                    if resp.status_code != 200:
                        break
                    data = resp.json()
                    body = data.get('response', {}).get('body', {})
                    items = body.get('items', {}).get('item', [])
                    if isinstance(items, dict):
                        items = [items]
                    if not items:
                        break
                    for row in items:
                        pk = row.get('mgmPmsrgstPk')
                        if not pk:
                            continue
                        if ConstructionNotice.query.filter_by(source='arch_hub', source_url=str(pk)).first():
                            continue
                        plat_plc = row.get('platPlc', '') or ''
                        bld_nm = row.get('bldNm', '') or ''
                        arch_gb = row.get('archGbCdNm', '') or ''
                        purps = row.get('mainPurpsCdNm', '') or ''
                        pms_day = _parse_yyyymmdd(row.get('archPmsDay'))
                        real_stcns = _parse_yyyymmdd(row.get('realStcnsDay'))
                        desc_parts = []
                        if arch_gb:
                            desc_parts.append(f'구분: {arch_gb}')
                        if purps:
                            desc_parts.append(f'용도: {purps}')
                        if row.get('platArea'):
                            desc_parts.append(f'대지면적: {row.get("platArea")}㎡')
                        if row.get('archArea'):
                            desc_parts.append(f'건축면적: {row.get("archArea")}㎡')
                        if row.get('totArea'):
                            desc_parts.append(f'연면적: {row.get("totArea")}㎡')
                        if row.get('bcRat'):
                            desc_parts.append(f'건폐율: {row.get("bcRat")}%')
                        if row.get('vlRat'):
                            desc_parts.append(f'용적률: {row.get("vlRat")}%')
                        if row.get('mainBldCnt') is not None:
                            desc_parts.append(f'건물수: {row.get("mainBldCnt")}')
                        if row.get('hhldCnt'):
                            desc_parts.append(f'세대수: {row.get("hhldCnt")}')
                        if row.get('archPmsDay'):
                            desc_parts.append(f'허가일: {row.get("archPmsDay")}')
                        title = (bld_nm.strip() if bld_nm.strip() else (plat_plc.strip() or '건축인허가'))
                        db.session.add(ConstructionNotice(
                            title=title,
                            description=' | '.join(desc_parts),
                            location=plat_plc.strip(),
                            latitude=None,
                            longitude=None,
                            source='arch_hub',
                            source_url=str(pk),
                            notice_type='building_permit',
                            start_date=pms_day,
                            end_date=real_stcns,
                            is_active=True,
                        ))
                        count += 1
                    total = int(body.get('totalCount', '0'))
                    if pIdx * 100 >= total:
                        break
                    pIdx += 1
                # be gentle with the API
                import time
                time.sleep(0.05)
            if count:
                db.session.commit()
            print(f"[ARCHHUB] Synced {count} new building permits.")
        except Exception as e:
            print(f"[ARCHHUB] Error: {e}")
            import traceback; traceback.print_exc()
