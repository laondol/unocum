import requests, math, json, time
from math import radians, sin, cos, sqrt, atan2

# In-process TTL cache for ODSay routing results (saves the 1,000 calls/day quota).
_ODSAY_CACHE = {}
_ODSAY_CACHE_TTL = 24 * 3600

def _odsay_cache_key(fy, fx, ty, tx):
    return (round(fy, 5), round(fx, 5), round(ty, 5), round(tx, 5))

def _odsay_cache_get(fy, fx, ty, tx):
    hit = _ODSAY_CACHE.get(_odsay_cache_key(fy, fx, ty, tx))
    if hit and (hit[0] + _ODSAY_CACHE_TTL) > time.time():
        return hit[1], hit[2], hit[3]
    return None

def _odsay_cache_set(fy, fx, ty, tx, steps, total_min, dist):
    _ODSAY_CACHE[_odsay_cache_key(fy, fx, ty, tx)] = (time.time(), steps, total_min, dist)

def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

STATIONS = [
    {"name":"양평역","lat":37.4918,"lng":127.4913,"line":"경의중앙선","toward_seoul":["05:30","23:10"],"toward_jipyeong":["05:50","00:10"]},
    {"name":"용문역","lat":37.4815,"lng":127.5946,"line":"경의중앙선","toward_seoul":["05:10","22:50"],"toward_jipyeong":["06:10","00:20"]},
    {"name":"옥천역","lat":37.5180,"lng":127.5083,"line":"경의중앙선","toward_seoul":["05:40","23:30"],"toward_jipyeong":["05:40","00:00"]},
    {"name":"지평역","lat":37.4460,"lng":127.6210,"line":"경의중앙선","toward_seoul":["05:00","22:40"],"toward_jipyeong":["06:20","00:25"]},
    {"name":"원덕역","lat":37.4900,"lng":127.5050,"line":"경의중앙선","toward_seoul":["05:35","23:15"],"toward_jipyeong":["05:55","00:14"]},
    {"name":"아신역","lat":37.5134,"lng":127.5105,"line":"경의중앙선","toward_seoul":["05:38","23:25"],"toward_jipyeong":["05:45","00:05"]},
]

YANGPYEONG_BUS_ROUTES = [
    {"name":"1번","stops":[{"name":"문호리","lat":37.583,"lng":127.405},{"name":"양수리","lat":37.545,"lng":127.325},{"name":"양평터미널","lat":37.488,"lng":127.492}]},
    {"name":"1-1번","stops":[{"name":"문호리","lat":37.583,"lng":127.405},{"name":"양수역","lat":37.555,"lng":127.342},{"name":"양평터미널","lat":37.488,"lng":127.492}]},
    {"name":"2번","stops":[{"name":"양평터미널","lat":37.488,"lng":127.492},{"name":"양평역","lat":37.4918,"lng":127.4913},{"name":"용문","lat":37.481,"lng":127.594}]},
    {"name":"2-2번","stops":[{"name":"양평터미널","lat":37.488,"lng":127.492},{"name":"옥천","lat":37.518,"lng":127.508},{"name":"용문","lat":37.481,"lng":127.594}]},
    {"name":"3번","stops":[{"name":"양평터미널","lat":37.488,"lng":127.492},{"name":"아신","lat":37.513,"lng":127.510},{"name":"서종","lat":37.583,"lng":127.415}]},
    {"name":"3-1번","stops":[{"name":"양평터미널","lat":37.488,"lng":127.492},{"name":"양서","lat":37.540,"lng":127.360},{"name":"서종","lat":37.583,"lng":127.415}]},
    {"name":"3-2번","stops":[{"name":"양평터미널","lat":37.488,"lng":127.492},{"name":"양수리","lat":37.545,"lng":127.325}]},
    {"name":"4번","stops":[{"name":"양평터미널","lat":37.488,"lng":127.492},{"name":"강상","lat":37.470,"lng":127.500},{"name":"강하","lat":37.495,"lng":127.430}]},
    {"name":"5번","stops":[{"name":"양평터미널","lat":37.488,"lng":127.492},{"name":"개군","lat":37.395,"lng":127.550}]},
    {"name":"6번","stops":[{"name":"양평터미널","lat":37.488,"lng":127.492},{"name":"지평","lat":37.440,"lng":127.615},{"name":"용문","lat":37.481,"lng":127.594}]},
    {"name":"6-1번","stops":[{"name":"양평터미널","lat":37.488,"lng":127.492},{"name":"양동","lat":37.420,"lng":127.660}]},
    {"name":"7번","stops":[{"name":"양평터미널","lat":37.488,"lng":127.492},{"name":"단월","lat":37.560,"lng":127.660}]},
    {"name":"7-1번","stops":[{"name":"양평터미널","lat":37.488,"lng":127.492},{"name":"청운","lat":37.540,"lng":127.715}]},
    {"name":"8번","stops":[{"name":"용문","lat":37.481,"lng":127.594},{"name":"지평","lat":37.440,"lng":127.615},{"name":"양동","lat":37.420,"lng":127.660}]},
    {"name":"8-1번","stops":[{"name":"용문","lat":37.481,"lng":127.594},{"name":"단월","lat":37.560,"lng":127.660}]},
    {"name":"9번","stops":[{"name":"양평터미널","lat":37.488,"lng":127.492},{"name":"양수리","lat":37.545,"lng":127.325},{"name":"서종","lat":37.583,"lng":127.415}]},
]

WALK_SPEED = 5  # km/h
BUS_SPEED = 20  # km/h

def _hm_to_min(t):
    parts = t.split(":")
    return int(parts[0]) * 60 + int(parts[1])

def _min_to_hm(m):
    h = m // 60
    if h >= 24: h -= 24
    return f"{h:02d}:{m % 60:02d}"

def find_nearest_station(lat, lng):
    best = None
    best_dist = float('inf')
    for s in STATIONS:
        d = haversine_km(lat, lng, s["lat"], s["lng"])
        if d < best_dist:
            best_dist = d
            best = s
    return best, best_dist

def find_nearest_bus_stop(lat, lng, route_name=None):
    best = None
    best_dist = float('inf')
    for route in YANGPYEONG_BUS_ROUTES:
        if route_name and route["name"] != route_name: continue
        for stop in route["stops"]:
            d = haversine_km(lat, lng, stop["lat"], stop["lng"])
            if d < best_dist:
                best_dist = d
                best = {"route": route["name"], "stop": stop["name"], "lat": stop["lat"], "lng": stop["lng"]}
    return best, best_dist

def find_bus_between(from_lat, from_lng, to_lat, to_lng):
    candidates = []
    for route in YANGPYEONG_BUS_ROUTES:
        stops = route["stops"]
        for i in range(len(stops)):
            d_from = haversine_km(from_lat, from_lng, stops[i]["lat"], stops[i]["lng"])
            for j in range(i+1, len(stops)):
                d_to = haversine_km(to_lat, to_lng, stops[j]["lat"], stops[j]["lng"])
                if d_from < 2.0 and d_to < 2.0:
                    dist_km = sum(haversine_km(stops[k]["lat"], stops[k]["lng"], stops[k+1]["lat"], stops[k+1]["lng"]) for k in range(i, j))
                    candidates.append({"route": route["name"], "from_stop": stops[i]["name"], "to_stop": stops[j]["name"], "dist_km": round(dist_km, 1), "time_min": round(dist_km / BUS_SPEED * 60 + 5)})
    candidates.sort(key=lambda c: c["time_min"])
    return candidates[:3]

def get_train_between(from_station, to_station, arrival_before_min):
    station_names = [s["name"] for s in STATIONS]
    if from_station not in station_names or to_station not in station_names:
        return None
    fi = station_names.index(from_station)
    ti = station_names.index(to_station)
    if ti > fi:
        direction = "toward_jipyeong"
    else:
        direction = "toward_seoul"
    s = STATIONS[fi]
    times = s[direction]
    first = _hm_to_min(times[0])
    last = _hm_to_min(times[1])
    dist_stops = abs(ti - fi)
    travel_min = dist_stops * 4
    dep_min = arrival_before_min - travel_min - 5
    if dep_min < first:
        dep_min = first
    if dep_min > last:
        dep_min = last
    arr_min = dep_min + travel_min
    return {
        "from": from_station, "to": to_station, "line": s["line"],
        "direction": "용문/지평 방면" if direction == "toward_jipyeong" else "서울/덕소 방면",
        "departure": _min_to_hm(dep_min),
        "arrival": _min_to_hm(arr_min),
        "travel_min": travel_min, "stops": dist_stops
    }

def naver_transit(from_lat, from_lng, to_lat, to_lng, client_id=None, client_secret=None, arrival_min=None):
    """Naver Cloud Platform 대중교통 방향 API 호출"""
    if not client_id or not client_secret:
        return None
    url = "https://maps.apigw.ntruss.com/map-direction/v1/pubtransit"
    params = {"start":f"{from_lng},{from_lat}","goal":f"{to_lng},{to_lat}","lang":"ko"}
    if arrival_min is not None:
        params["arrivalTime"] = f"20260711{arrival_min//60:02d}{arrival_min%60:02d}"
    headers = {"x-ncp-apigw-api-key-id":client_id,"x-ncp-apigw-api-key":client_secret}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("code") != 0 or not data.get("route"):
            return None
        route = data["route"]["traoptimal"][0]
        summary = route.get("summary", {})
        guides = summary.get("guide", [])
        if not guides:
            return None
        total_sec = summary.get("duration", 0)
        total_min = round(total_sec / 60)
        dep_time = summary.get("departureTime","")
        arr_time = summary.get("arrivalTime","")
        steps = []
        for g in guides:
            mode_map = {"WALK":"🚶 도보","BUS":"🚌 버스","SUBWAY":"🚄 지하철","EXPRESS_BUS":"🚌 고속버스","AIRPORT_BUS":"🚌 공항버스"}
            mode = mode_map.get(g.get("mode",""), g.get("mode",""))
            detail = f"{g.get('startName','')} → {g.get('endName','')} "
            if g.get("stationCount"):
                detail += f"({g['stationCount']}정거장) "
            dist_m = g.get("distance",0)
            dur_sec = g.get("duration",0)
            if dist_m > 0: detail += f"{round(dist_m/1000,1)}km "
            if dur_sec > 0: detail += f"{round(dur_sec/60)}분"
            if g.get("busNo"): detail = f"{g['busNo']}번 " + detail
            if g.get("subwayName"): detail = g['subwayName'] + " " + detail
            step = {"mode":mode,"from":g.get("startName",""),"to":g.get("endName",""),"detail":detail.strip(),"time_min":round(dur_sec/60) if dur_sec else 0}
            if g.get("busNo"): step["bus_no"] = f"{g['busNo']}번"
            if g.get("subwayName"): step["subway_name"] = g["subwayName"]
            steps.append(step)
        return {"steps":steps,"total_min":total_min,"departure":dep_time[-5:] if dep_time else "","arrival":arr_time[-5:] if arr_time else "","distance_km":round(summary.get("distance",0)/1000,1)}
    except:
        return None

def _estimate_plan(from_name, to_name, direct_km, arrival_min):
    """Distance-based transit estimate used when Naver is unavailable and the
    leg lies outside the Yangpyeong transit network."""
    total_min = int(direct_km * 3 + 15)
    steps = [{"mode": "🚌 대중교통(추정)", "from": from_name, "to": to_name,
              "detail": f"대중교통 약 {total_min}분 ({round(direct_km, 1)}km, 정확 경로 미제공)",
              "time_min": total_min}]
    dep_min = arrival_min - total_min
    return {"steps": steps, "total_min": total_min, "departure": _min_to_hm(dep_min),
            "arrival": _min_to_hm(arrival_min), "distance_km": round(direct_km, 1), "estimate": True}

def is_korea(lat, lng):
    """Rough bounding box for South Korea (incl. Jeju)."""
    try:
        return 33.0 <= float(lat) <= 38.7 and 124.5 <= float(lng) <= 129.7
    except (TypeError, ValueError):
        return False

def odsay_transit(from_lat, from_lng, to_lat, to_lng, api_key, arrival_min=None):
    """ODSay public transit routing (Korea). Returns plan_segment-compatible dict."""
    if not api_key:
        return None
    _cached = _odsay_cache_get(from_lat, from_lng, to_lat, to_lng)
    if _cached:
        _steps, _total, _dist = _cached
        _dep = (arrival_min - _total) if arrival_min is not None else 0
        return {"steps": _steps, "total_min": _total,
                "departure": _min_to_hm(_dep) if arrival_min is not None else "",
                "arrival": _min_to_hm(arrival_min) if arrival_min is not None else "",
                "distance_km": _dist}
    url = "https://api.odsay.com/v1/api/searchPubTransPathT"
    params = {"apiKey": api_key, "SX": from_lng, "SY": from_lat,
              "EX": to_lng, "EY": to_lat, "OPT": 0, "lang": 0}
    try:
        resp = requests.get(url, params=params, timeout=6)
        data = resp.json()
    except:
        return None
    if data.get("error"):
        return None
    paths = (data.get("result") or {}).get("path") or []
    if not paths:
        return None
    path = paths[0]
    info = path.get("info", {})
    total_min = info.get("totalTime")
    if not total_min or total_min <= 0:
        return None
    total_min = int(total_min)
    steps = []
    for sp in path.get("subPath", []):
        t = sp.get("trafficType")
        sec = sp.get("sectionTime") or 0
        dist = sp.get("distance") or 0
        if t == 3:
            steps.append({"mode": "🚶 도보", "from": "", "to": "",
                          "detail": f"도보 {sec}분 ({round(dist/1000,1)}km)", "time_min": sec})
        elif t == 1:
            lane = (sp.get("lane") or [{}])[0]
            name = lane.get("name") or ""
            start = sp.get("startName") or ""
            end = sp.get("endName") or ""
            steps.append({"mode": "🚄 지하철", "from": start, "to": end,
                          "detail": f"{name} {start}→{end} ({sec}분, {sp.get('stationCount',0)}정거장)",
                          "time_min": sec, "subway_name": name})
        elif t == 2:
            lane = (sp.get("lane") or [{}])[0]
            name = lane.get("name") or lane.get("busNo") or ""
            start = sp.get("startName") or ""
            end = sp.get("endName") or ""
            steps.append({"mode": "🚌 버스", "from": start, "to": end,
                          "detail": f"{name} {start}→{end} ({sec}분)", "time_min": sec, "bus_no": name})
        else:
            steps.append({"mode": "🚉 기타", "from": "", "to": "", "detail": f"{sec}분", "time_min": sec})
    _odsay_cache_set(from_lat, from_lng, to_lat, to_lng, steps, total_min, round(info.get("pointDistance", 0)/1000, 1))
    dep_min = (arrival_min - total_min) if arrival_min is not None else 0
    return {"steps": steps, "total_min": total_min,
            "departure": _min_to_hm(dep_min) if arrival_min is not None else "",
            "arrival": _min_to_hm(arrival_min) if arrival_min is not None else "",
            "distance_km": round(info.get("pointDistance", 0)/1000, 1)}

def google_transit(from_lat, from_lng, to_lat, to_lng, api_key, arrival_min=None):
    """Google Maps Directions (transit mode) - used for overseas legs."""
    if not api_key:
        return None
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {"origin": f"{from_lat},{from_lng}", "destination": f"{to_lat},{to_lng}",
              "mode": "transit", "language": "ko", "region": "kr",
              "key": api_key, "departure_time": "now"}
    try:
        resp = requests.get(url, params=params, timeout=6)
        data = resp.json()
    except:
        return None
    if data.get("status") != "OK":
        return None
    routes = data.get("routes") or []
    if not routes:
        return None
    leg = routes[0]["legs"][0]
    total_sec = leg.get("duration", {}).get("value", 0)
    total_min = round(total_sec / 60)
    if total_min <= 0:
        return None
    steps = []
    for s in leg.get("steps", []):
        mode = s.get("travel_mode")
        dur = round(s.get("duration", {}).get("value", 0) / 60)
        if mode == "WALKING":
            dist_m = s.get("distance", {}).get("value", 0)
            steps.append({"mode": "🚶 도보", "from": "", "to": "",
                          "detail": f"도보 {dur}분 ({round(dist_m/1000,1)}km)", "time_min": dur})
        elif mode == "TRANSIT":
            td = s.get("transit_details", {})
            line = td.get("line", {})
            veh = line.get("vehicle", {}).get("type", "")
            name = line.get("short_name") or line.get("name") or veh
            dep = td.get("departure_stop", {}).get("name", "")
            arr = td.get("arrival_stop", {}).get("name", "")
            icon = "🚄" if any(k in veh for k in ("SUBWAY", "RAIL", "METRO", "TRAIN")) else "🚌"
            steps.append({"mode": f"{icon} {veh}", "from": dep, "to": arr,
                          "detail": f"{name} {dep}→{arr} ({dur}분)", "time_min": dur,
                          "bus_no": name if icon == "🚌" else "", "subway_name": name if icon == "🚄" else ""})
        else:
            steps.append({"mode": "🚗 기타", "from": "", "to": "", "detail": f"{mode} {dur}분", "time_min": dur})
    dep_min = (arrival_min - total_min) if arrival_min is not None else 0
    return {"steps": steps, "total_min": total_min,
            "departure": _min_to_hm(dep_min) if arrival_min is not None else "",
            "arrival": _min_to_hm(arrival_min) if arrival_min is not None else "",
            "distance_km": round(leg.get("distance", {}).get("value", 0)/1000, 1)}

def plan_segment(from_name, from_lat, from_lng, to_name, to_lat, to_lng, arrival_time_str, home_town=None, home_village=None, naver_id=None, naver_secret=None, odsay_key=None, google_key=None):
    parts = arrival_time_str.split(":")
    arr_h = int(parts[0]) if parts else 9
    arr_m = int(parts[1]) if len(parts) > 1 else 0
    arrival_min = arr_h * 60 + arr_m

    # Regional routing: Korea -> ODSay, Overseas -> Google
    domestic = is_korea(from_lat, from_lng) and is_korea(to_lat, to_lng)
    if domestic:
        primary, secondary, pk, sk = odsay_transit, google_transit, odsay_key, google_key
    else:
        primary, secondary, pk, sk = google_transit, odsay_transit, google_key, odsay_key
    res = primary(from_lat, from_lng, to_lat, to_lng, pk, arrival_min)
    if not res and sk:
        res = secondary(from_lat, from_lng, to_lat, to_lng, sk, arrival_min)
    if res:
        dep_min = arrival_min - res["total_min"]
        res["departure"] = _min_to_hm(dep_min)
        res["arrival"] = arrival_time_str
        return res

    # Legacy Naver (if configured)
    naver_result = naver_transit(from_lat, from_lng, to_lat, to_lng, naver_id, naver_secret, arrival_min)
    if naver_result:
        dep_min = arrival_min - naver_result["total_min"]
        naver_result["departure"] = _min_to_hm(dep_min)
        naver_result["arrival"] = arrival_time_str
        return naver_result

    direct_km = haversine_km(from_lat, from_lng, to_lat, to_lng)
    steps = []
    total_travel_min = 0

    if direct_km < 1.0:
        walk_min = round(direct_km / WALK_SPEED * 60) + 2
        steps.append({"mode":"도보","from":from_name,"to":to_name,"detail":f"도보 {walk_min}분 ({round(direct_km,1)}km)","time_min":walk_min})
        total_travel_min = walk_min
        dep_min = arrival_min - walk_min
        return {"steps":steps,"total_min":total_travel_min,"departure":_min_to_hm(dep_min),"arrival":arrival_time_str,"distance_km":round(direct_km,1)}

    # 1. Walk to nearest bus stop or station
    near_station, dist_station = find_nearest_station(from_lat, from_lng)
    near_bus, dist_bus = find_nearest_bus_stop(from_lat, from_lng)

    # When Naver is unavailable, legs outside the Yangpyeong transit network
    # (both endpoints far from any Yangpyeong station/bus stop) would otherwise
    # produce absurd "walk to a distant Yangpyeong station" estimates. Fall back
    # to a distance-based estimate instead.
    _ns_to, _ds_to = find_nearest_station(to_lat, to_lng)
    _nb_to, _db_to = find_nearest_bus_stop(to_lat, to_lng)
    _from_far = dist_station > 5.0 or dist_bus > 5.0
    _to_far = _ds_to > 5.0 or _db_to > 5.0
    if _from_far and _to_far:
        return _estimate_plan(from_name, to_name, direct_km, arrival_min)

    use_station_first = dist_station <= dist_bus or dist_station < 3.0

    if use_station_first and near_station:
        walk_to_station = round(dist_station / WALK_SPEED * 60) + 3
        if walk_to_station > 2:
            steps.append({"mode":"도보","from":f"{from_name}","to":f"{near_station['name']}","detail":f"도보 {walk_to_station}분 ({round(dist_station,1)}km)","time_min":walk_to_station})
            total_travel_min += walk_to_station

        dest_station, _ = find_nearest_station(to_lat, to_lng)
        if dest_station and near_station["name"] != dest_station["name"]:
            train = get_train_between(near_station["name"], dest_station["name"], arrival_min - total_travel_min)
            if train:
                steps.append({"mode":"🚄 전철","from":near_station["name"],"to":dest_station["name"],"detail":f"{train['line']} {train['direction']} {train['departure']}→{train['arrival']} ({train['travel_min']}분, {train['stops']}정거장)","time_min":train["travel_min"],"subway_name":train["line"]})
                total_travel_min += train["travel_min"]

        walk_to_dest = haversine_km(dest_station["lat"], dest_station["lng"], to_lat, to_lng) if dest_station else 0
        walk_dest_min = round(walk_to_dest / WALK_SPEED * 60) + 3
        if walk_dest_min > 2:
            steps.append({"mode":"도보","from":f"{dest_station['name'] if dest_station else ''}","to":f"{to_name}","detail":f"도보 {walk_dest_min}분 ({round(walk_to_dest,1)}km)","time_min":walk_dest_min})
            total_travel_min += walk_dest_min
    else:
        if near_bus:
            walk_to_bus = round(dist_bus / WALK_SPEED * 60) + 3
            if walk_to_bus > 2:
                steps.append({"mode":"도보","from":f"{from_name}","to":f"{near_bus['stop']}({near_bus['route']})","detail":f"도보 {walk_to_bus}분 ({round(dist_bus,1)}km)","time_min":walk_to_bus})
                total_travel_min += walk_to_bus

            buses = find_bus_between(from_lat, from_lng, to_lat, to_lng)
            if buses:
                b = buses[0]
                steps.append({"mode":"🚌 버스","from":f"{b['from_stop']}({b['route']})","to":f"{b['to_stop']}({b['route']})","detail":f"{b['route']} {b['from_stop']}→{b['to_stop']} ({b['time_min']}분, {b['dist_km']}km)","time_min":b['time_min'],"bus_no":b['route']})
                total_travel_min += b['time_min']
            else:
                road_km = direct_km * 1.3
                walk_min = round(direct_km / WALK_SPEED * 60 * 1.3) + 5
                if walk_min > 20:
                    taxi_min = round(road_km / 40 * 60) + 5
                    taxi_fare = round(road_km * 1500 + 3800, -2)
                    steps.append({"mode":"🚕 택시","from":from_name,"to":to_name,"detail":f"택시 {taxi_min}분 예상 ({round(road_km,1)}km, 약 {taxi_fare:,}원)","time_min":taxi_min})
                    total_travel_min += taxi_min
                else:
                    steps.append({"mode":"🚶 도보","from":from_name,"to":to_name,"detail":f"도보 {walk_min}분 (직선 {round(direct_km,1)}km, 도로 약 {round(road_km,1)}km)","time_min":walk_min})
                    total_travel_min += walk_min

    if not steps:
        taxi_min = round(direct_km / 40 * 60) + 5
        taxi_fare = round(direct_km * 1500 + 3800, -2)
        steps.append({"mode":"🚕 택시","from":from_name,"to":to_name,"detail":f"택시 {taxi_min}분 예상 ({round(direct_km,1)}km, 약 {taxi_fare:,}원)","time_min":taxi_min})
        total_travel_min = taxi_min

    dep_min = arrival_min - total_travel_min
    return {"steps":steps,"total_min":total_travel_min,"departure":_min_to_hm(dep_min),"arrival":arrival_time_str,"distance_km":round(direct_km,1)}

def format_itinerary(plan):
    lines = [f"🚶 {plan['departure']} 출발 → {plan['arrival']} 도착 (총 {plan['total_min']}분, {plan['distance_km']}km)"]
    for s in plan["steps"]:
        lines.append(f"  {s['mode']} {s['detail']}")
    return "\n".join(lines)

def format_memo_compact(plan):
    parts = []
    cumulative_min = 0
    dep_min = _hm_to_min(plan.get("departure", "00:00"))
    for s in plan["steps"]:
        step_start_min = dep_min + cumulative_min
        step_time = s.get("time_min", 1)
        step_hm = f"{step_start_min//60:02d}:{step_start_min%60:02d}"
        mode = s["mode"]
        if "도보" in mode:
            parts.append(f"도{step_time}")
        elif "버스" in mode or "고속" in mode:
            bus_no = s.get("bus_no", "")
            stop = s.get("from", "").split("(")[0]
            parts.append(f"{bus_no}(버, {stop}, {step_hm})" if bus_no else f"버스{step_time}분")
        elif "전철" in mode or "지하철" in mode:
            line = s.get("subway_name", "")
            station = s.get("from", "")
            parts.append(f"{line}(지, {station}, {step_hm})" if line else f"전철{step_time}분")
        elif "택시" in mode:
            parts.append(f"택시{step_time}분")
        else:
            parts.append(f"{mode}{step_time}분")
        cumulative_min += step_time
    return " -> ".join(parts)
