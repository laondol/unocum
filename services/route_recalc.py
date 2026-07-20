# route_recalc: 경로 재계산 공유 모듈 (핸들러/백그라운드 워커 공유)
import os
import json
import calendar
import requests
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import or_
from models import db, User, TongBotSchedule
from services.directions import plan_segment, format_itinerary, format_memo_compact
from services.transit import haversine_km


# route_recalc: 반복 발생일 확장 헬퍼 (핸들러/워커 공유 모듈)
import json
import calendar
from datetime import datetime, timedelta


def _is_occurrence(base, target):
    # O(1) check whether `target` (date) is an occurrence of recurring `base`
    start = getattr(base, 'event_date', None)
    if not start:
        return False
    start_d = start.date() if hasattr(start, 'date') else start
    if target == start_d:
        return True
    if target < start_d:
        return False
    if not getattr(base, 'is_recurring', False):
        return False
    if getattr(base, 'repeat_infinite', False):
        end_d = datetime(2999, 12, 31).date()
    else:
        end_dt = getattr(base, 'repeat_end_date', None)
        if not end_dt:
            return False
        end_d = end_dt.date() if hasattr(end_dt, 'date') else end_dt
    if target > end_d:
        return False
    rt = getattr(base, 'repeat_type', '') or ''
    interval = getattr(base, 'repeat_interval', 1) or 1
    wd_mask = getattr(base, 'repeat_weekdays', 0) or 0
    moy = getattr(base, 'repeat_month_of_year', 0) or 0
    wom = getattr(base, 'repeat_week_of_month', 0) or 0
    exc = set()
    try:
        exc = set(json.loads(getattr(base, 'repeat_exceptions', '') or '[]'))
    except Exception:
        exc = set()
    if target.strftime('%Y-%m-%d') in exc:
        return False
    if wd_mask:
        wd = target.weekday()
        if not (wd_mask & (1 << wd)):
            return False
        if moy and target.month != moy:
            return False
        if wom:
            d = 1
            while datetime(target.year, target.month, d).weekday() != wd:
                d += 1
            d += (wom - 1) * 7
            if d > calendar.monthrange(target.year, target.month)[1]:
                return False
            if target.day != d:
                return False
        return True
    if rt == 'daily':
        return (target - start_d).days % interval == 0
    if rt == 'weekly':
        if target.weekday() != start_d.weekday():
            return False
        return ((target - start_d).days // 7) % interval == 0
    if rt == 'monthly':
        if target.day != start_d.day:
            return False
        months = (target.year - start_d.year) * 12 + (target.month - start_d.month)
        return months % interval == 0
    if rt == 'yearly':
        if target.month != start_d.month or target.day != start_d.day:
            return False
        return (target.year - start_d.year) % interval == 0
    return False

def _gen_occurrences(base):
    # Return list of occurrence date objects (start+1 .. end), capped at 120, mirroring GET expansion
    import calendar as _cal
    start = getattr(base, 'event_date', None)
    if not start:
        return []
    start_d = start.date() if hasattr(start, 'date') else start
    if getattr(base, 'repeat_infinite', False):
        end_d = datetime(2999, 12, 31).date()
    else:
        end_dt = getattr(base, 'repeat_end_date', None)
        if not end_dt:
            return []
        end_d = end_dt.date() if hasattr(end_dt, 'date') else end_dt
    rt = getattr(base, 'repeat_type', '') or ''
    interval = getattr(base, 'repeat_interval', 1) or 1
    wd_mask = getattr(base, 'repeat_weekdays', 0) or 0
    moy = getattr(base, 'repeat_month_of_year', 0) or 0
    wom = getattr(base, 'repeat_week_of_month', 0) or 0
    exc = set()
    try:
        exc = set(json.loads(getattr(base, 'repeat_exceptions', '') or '[]'))
    except Exception:
        exc = set()

    def _add_months(dt, n):
        y, m = dt.year, dt.month + n
        while m > 12:
            m -= 12
            y += 1
        last = _cal.monthrange(y, m)[1]
        return dt.replace(year=y, month=m, day=min(dt.day, last))

    def _nth_weekday_day(y, m, wd, n):
        d = 1
        while datetime(y, m, d).weekday() != wd:
            d += 1
        d += (n - 1) * 7
        if d > _cal.monthrange(y, m)[1]:
            return -1
        return d

    out = []
    emitted = 1
    cur = start_d + timedelta(days=1)
    guard = 0
    while cur <= end_d and emitted < 120 and guard < 600000:
        guard += 1
        do_emit = False
        nxt = cur + timedelta(days=1)
        if wd_mask:
            wd = cur.weekday()
            if wd_mask & (1 << wd):
                ok = True
                if moy and cur.month != moy:
                    ok = False
                elif wom and cur.day != _nth_weekday_day(cur.year, cur.month, wd, wom):
                    ok = False
                if ok:
                    do_emit = True
        elif rt == 'daily':
            if (cur - start_d).days % interval == 0:
                do_emit = True
        elif rt == 'weekly':
            if cur.weekday() == start_d.weekday() and ((cur - start_d).days // 7) % interval == 0:
                do_emit = True
        elif rt == 'monthly':
            if cur.day == start_d.day:
                months = (cur.year - start_d.year) * 12 + (cur.month - start_d.month)
                if months % interval == 0:
                    do_emit = True
                nxt = _add_months(cur, 1)
            else:
                nxt = cur + timedelta(days=1)
        elif rt == 'yearly':
            if cur.month == start_d.month and cur.day == start_d.day:
                if (cur.year - start_d.year) % interval == 0:
                    do_emit = True
                nxt = _add_months(cur, 12)
            else:
                nxt = cur + timedelta(days=1)
        if do_emit and cur.strftime('%Y-%m-%d') not in exc:
            emitted += 1
            out.append(cur)
        cur = nxt
    return out

from .geo import _geocode_location

def _ensure_day_routes(uid, evt_date, exclude_ids=None):
    """Recalculate all 이동/귀가 routes for a given day based on current non-이동/귀가 events."""
    user = User.query.get(uid)
    if not user: return []
    home_addr = f"{user.town or ''} {user.village or ''}".strip()
    if user.curr_address: home_addr = user.curr_address
    home_lat = user.curr_latitude or user.reg_latitude
    home_lng = user.curr_longitude or user.reg_longitude
    day_start = evt_date.replace(hour=0, minute=0, second=0)
    day_end = evt_date.replace(hour=23, minute=59, second=59)
    # 앵커(이동 생성 제외 기준점): 집 + 회사 + (임시숙소 기간 중) 임시숙소
    anchors = []
    if home_lat and home_lng:
        anchors.append((home_lat, home_lng, home_addr))
    if user.office_latitude and user.office_longitude:
        anchors.append((user.office_latitude, user.office_longitude, user.office_address or '회사'))
    temp_active = False
    if user.temp_address and user.temp_latitude and user.temp_longitude and user.temp_start_date and user.temp_end_date:
        if user.temp_start_date <= evt_date <= user.temp_end_date:
            temp_active = True
            home_addr = f"[임시] {user.temp_address}"
            home_lat = user.temp_latitude
            home_lng = user.temp_longitude
            anchors.append((user.temp_latitude, user.temp_longitude, f"[임시] {user.temp_address}"))
    SKIP_KM = 0.5
    def _near_anchor(lat, lng):
        for a in anchors:
            if haversine_km(a[0], a[1], lat, lng) <= SKIP_KM:
                return True
        return False
    naver_id = current_app.config.get('NAVER_CLIENT_ID', os.getenv('NAVER_CLIENT_ID', ''))
    naver_secret = current_app.config.get('NAVER_CLIENT_SECRET', os.getenv('NAVER_CLIENT_SECRET', ''))
    odsay_key = os.getenv('ODSAY_API_KEY', current_app.config.get('ODSAY_API_KEY', ''))
    google_key = os.getenv('GOOGLE_MAPS_API_KEY', current_app.config.get('GOOGLE_MAPS_API_KEY', ''))
    from services.directions import plan_segment, format_itinerary, format_memo_compact
    from services.transit import haversine_km
    # Remove existing 이동/귀가 for this day
    q = TongBotSchedule.query.filter(
        TongBotSchedule.user_id == uid,
        TongBotSchedule.event_date >= day_start,
        TongBotSchedule.event_date <= day_end,
        or_(TongBotSchedule.title.like('%이동%'), TongBotSchedule.title.like('%귀가%'))
    )
    if exclude_ids:
        q = q.filter(TongBotSchedule.id.notin_(exclude_ids))
    for m in q.all():
        db.session.delete(m)
    db.session.flush()
    # Get non-이동/귀가 events with locations, sorted (include all-day for 귀가 logic)
    if not (home_lat and home_lng):
        # no home coordinates -> cannot compute routes
        return []
    all_day_events = TongBotSchedule.query.filter(
        TongBotSchedule.user_id == uid,
        TongBotSchedule.event_date >= day_start,
        TongBotSchedule.event_date <= day_end,
        ~TongBotSchedule.title.like('%이동%'),
        ~TongBotSchedule.title.like('%귀가%'),
        TongBotSchedule.location != None,
        TongBotSchedule.location != '',
        TongBotSchedule.is_allday == True
    ).order_by(TongBotSchedule.event_date.asc()).all()
    events = TongBotSchedule.query.filter(
        TongBotSchedule.user_id == uid,
        TongBotSchedule.event_date >= day_start,
        TongBotSchedule.event_date <= day_end,
        ~TongBotSchedule.title.like('%이동%'),
        ~TongBotSchedule.title.like('%귀가%'),
        TongBotSchedule.location != None,
        TongBotSchedule.location != '',
        TongBotSchedule.is_allday != True
    ).order_by(TongBotSchedule.event_date.asc()).all()
    # Virtual-expand recurring occurrences that fall on this day (day 2+)
    try:
        from types import SimpleNamespace
        rec_bases = TongBotSchedule.query.filter(
            TongBotSchedule.user_id == uid,
            TongBotSchedule.is_recurring == True,
            TongBotSchedule.event_date <= day_end,
            or_(TongBotSchedule.repeat_end_date >= day_start, TongBotSchedule.repeat_infinite == True),
            ~TongBotSchedule.title.like('%이동%'),
            ~TongBotSchedule.title.like('%귀가%'),
        ).all()
        for base in rec_bases:
            b_date = base.event_date
            if not b_date:
                continue
            if b_date.date() == evt_date.date():
                continue
            if not _is_occurrence(base, evt_date.date()):
                continue
            occ_dt = datetime(evt_date.year, evt_date.month, evt_date.day, b_date.hour, b_date.minute)
            occ_end = None
            if base.end_date:
                occ_end = datetime(evt_date.year, evt_date.month, evt_date.day, base.end_date.hour, base.end_date.minute)
            vevt = SimpleNamespace(id="rec-%s-%s" % (base.id, evt_date.date()), title=base.title,
                                   location=base.location, event_date=occ_dt, end_date=occ_end,
                                   is_allday=base.is_allday)
            if base.is_allday:
                all_day_events.append(vevt)
            else:
                events.append(vevt)
    except Exception:
        pass


    if not events and not all_day_events: return []
    auto_created = []
    prev_location = None
    prev_lat = prev_lng = None
    prev_end_dt = None
    # 이동: only for non-all-day events
    for idx, evt in enumerate(events):
        loc_lat, loc_lng = _geocode_location(evt.location) or (None, None)
        if not (loc_lat and loc_lng): continue
        if not (home_lat and home_lng): pass
        elif _near_anchor(loc_lat, loc_lng): continue
        evt_start = evt.event_date
        # 이동 from previous location to this event
        arr_dt = evt_start - timedelta(minutes=10)
        if idx > 0 and prev_end_dt and prev_end_dt > arr_dt:
            arr_dt = prev_end_dt
        if idx == 0:
            from_time = home_addr
            from_lat, from_lng = home_lat, home_lng
        else:
            from_time = prev_location
            from_lat, from_lng = prev_lat, prev_lng
        plan_to = plan_segment(from_time, from_lat, from_lng, evt.location, loc_lat, loc_lng,
            arr_dt.strftime("%H:%M"), home_town=user.town or '', home_village=user.village or '',
            naver_id=naver_id, naver_secret=naver_secret, odsay_key=odsay_key, google_key=google_key)
        plan_to.update({"from_lat":from_lat,"from_lng":from_lng,"to_lat":loc_lat,"to_lng":loc_lng})
        dep_dt = arr_dt - timedelta(minutes=plan_to['total_min'])
        _compact = format_memo_compact(plan_to)
        plan_to["compact"] = _compact
        move = TongBotSchedule(user_id=uid, title=f"{evt.title} 이동",
            description=format_itinerary(plan_to),
            content=json.dumps(plan_to, ensure_ascii=False),
            event_date=dep_dt, end_date=arr_dt, location=evt.location,
            memo=_compact, departure_location=from_time, return_location=evt.location)
        db.session.add(move)
        db.session.flush()
        auto_created.append({"id":move.id,"title":move.title,"type":"move","arrival":arr_dt.strftime("%H:%M"),"departure":dep_dt.strftime("%H:%M"),"from":from_time})
        prev_location = evt.location
        prev_lat, prev_lng = loc_lat, loc_lng
        prev_end_dt = evt.end_date or (evt_start + timedelta(hours=1))
    # 귀가: 이동 일정이 하나라도 만들어졌을 때만 생성
    if auto_created:
        all_events = sorted(events + all_day_events, key=lambda e: e.event_date)
        if all_events:
            last_evt = all_events[-1]
            last_loc = last_evt.location
            last_lat, last_lng = _geocode_location(last_loc) or (None, None)
            if not (last_lat and last_lng) and prev_lat and prev_lng:
                last_loc = prev_location or last_loc
                last_lat, last_lng = prev_lat, prev_lng
            skip_return = False
            return_title = "집으로 이동"
            return_dest = home_addr
            return_lat, return_lng = home_lat, home_lng
            if user.temp_address and user.temp_latitude and user.temp_longitude and user.temp_start_date and user.temp_end_date:
                if user.temp_start_date <= evt_date <= user.temp_end_date:
                    if last_loc.strip() == user.temp_address.strip():
                        skip_return = True
                    else:
                        return_title = "임시숙소로 이동"
                        return_dest = f"[임시] {user.temp_address}"
                        return_lat, return_lng = user.temp_latitude, user.temp_longitude
            if not skip_return and last_lat and last_lng and return_lat and return_lng:
                target_arrival = "22:00"
                plan_home = plan_segment(last_loc, last_lat, last_lng, return_dest, return_lat, return_lng, target_arrival,
                    home_town=user.town or '', home_village=user.village or '',
                    naver_id=naver_id, naver_secret=naver_secret, odsay_key=odsay_key, google_key=google_key)
                plan_home.update({"from_lat":last_lat,"from_lng":last_lng,"to_lat":return_lat,"to_lng":return_lng})
                _compact_home = format_memo_compact(plan_home)
                plan_home["compact"] = _compact_home
                dep_raw = plan_home.get('departure') or ''
                try:
                    _hh, _mm = dep_raw.split(':')[:2]
                    _hh = int(_hh); _mm = int(_mm)
                    if not (0 <= _hh < 24 and 0 <= _mm < 60):
                        raise ValueError
                    ret_dep = datetime(evt_date.year, evt_date.month, evt_date.day, _hh, _mm)
                except (ValueError, TypeError, AttributeError, IndexError):
                    ret_dep = None
                if ret_dep:
                    last_end = last_evt.end_date
                    if last_end and last_end.date() != evt_date.date():
                        last_end = None
                    if not last_end:
                        last_end = last_evt.event_date + timedelta(hours=1)
                    if ret_dep < last_end:
                        ret_dep = last_end + timedelta(minutes=5)
                    ret_arr = ret_dep + timedelta(minutes=plan_home['total_min'])
                    home_return = TongBotSchedule(user_id=uid, title=return_title,
                        description=format_itinerary(plan_home),
                        content=json.dumps(plan_home, ensure_ascii=False),
                        event_date=ret_dep, end_date=ret_arr, location=return_dest,
                        memo=_compact_home, departure_location=last_loc, return_location=return_dest)
                    db.session.add(home_return)
                    db.session.flush()
                    auto_created.append({"id":home_return.id,"title":return_title,"type":"return","departure":ret_dep.strftime("%H:%M"),"arrival":ret_arr.strftime("%H:%M")})
    return auto_created


def recalc_user_routes(uid, commit=True):
    """사용자의 모든 이동/귀가 경로를 현재 일정 기준으로 재계산·저장.
    핸들러 / 백그라운드 워커가 공유하는 단일 엔트리 포인트.
    commit=False 이면 세션만 flush 하고 커밋하지 않음(검증/트랜잭션 제어용)."""
    sources = TongBotSchedule.query.filter(
        TongBotSchedule.user_id == uid,
        TongBotSchedule.location != None,
        TongBotSchedule.location != '',
        ~TongBotSchedule.title.like('%이동%'),
        ~TongBotSchedule.title.like('%귀가%'),
        or_(TongBotSchedule.kind == None,
            TongBotSchedule.kind == 'base',
            TongBotSchedule.kind == 'occurrence')
    ).all()
    days = set()
    for s in sources:
        if not s.event_date:
            continue
        days.add(s.event_date.date())
        for occ in _gen_occurrences(s):
            days.add(occ if hasattr(occ,'year') and not hasattr(occ,'hour') else occ.date())
    # 기존 이동/귀가 전체 삭제 후 재생성 (정합성 보장)
    TongBotSchedule.query.filter(
        TongBotSchedule.user_id == uid,
        TongBotSchedule.kind == None,
        or_(TongBotSchedule.title.like('%이동%'), TongBotSchedule.title.like('%귀가%'))
    ).delete(synchronize_session=False)
    db.session.flush()
    for d in sorted(days):
        _ensure_day_routes(uid, datetime(d.year, d.month, d.day))
    if commit:
        db.session.commit()
    return len(days)
