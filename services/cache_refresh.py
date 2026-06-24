import json
from datetime import datetime, timedelta
from models import db, VillageCache

def refresh_all_caches():
    results = {}
    # 1. Safetydata refresh
    from services.safetydata import get_yangpyeong_safety, TYPE_NAMES
    try:
        sd = get_yangpyeong_safety()
        for api_type, items in sd.items():
            if items:
                for item in items:
                    town = '양평군'
                    for t in ['양평읍','강상면','강하면','양서면','옥천면','서종면','단월면','청운면','양동면','지평면','용문면','개군면']:
                        if t in item.get('addr',''):
                            town = t
                            break
                    cache = VillageCache.query.filter_by(town=town, data_type=api_type).first()
                    if cache:
                        cache.data_json = json.dumps(items[:10], ensure_ascii=False)
                        cache.data_count = len(items)
                        cache.updated_at = datetime.now()
                    else:
                        db.session.add(VillageCache(town=town, village='', data_type=api_type, data_json=json.dumps(items[:10], ensure_ascii=False), data_count=len(items)))
        results['safetydata'] = 'ok'
    except Exception as e:
        results['safetydata'] = str(e)[:50]

    # 2. UTIC traffic refresh
    from services.utic_traffic import get_yangpyeong_incidents
    try:
        inc, err = get_yangpyeong_incidents()
        if inc:
            for t in set(i.get('addr','')[:6] for i in inc):
                town = next((x for x in ['양평읍','강상면','강하면','양서면','옥천면','서종면','단월면','청운면','양동면','지평면','용문면','개군면'] if x in t), '양평군')
                cache = VillageCache.query.filter_by(town=town, data_type='traffic').first()
                if cache:
                    cache.data_json = json.dumps(inc[:10], ensure_ascii=False)
                    cache.data_count = len(inc)
                    cache.updated_at = datetime.now()
                else:
                    db.session.add(VillageCache(town=town, village='', data_type='traffic', data_json=json.dumps(inc[:10], ensure_ascii=False), data_count=len(inc)))
        results['utic'] = f'{len(inc)} items'
    except Exception as e:
        results['utic'] = str(e)[:50]

    db.session.commit()
    return results

def scheduled_refresh(app):
    with app.app_context():
        refresh_all_caches()

CACHE_INTERVALS = {
    'traffic': 300,    # 5분
    'flood': 3600,     # 1시간
    'fog': 3600,
    'bike': 3600,
    'block': 3600,
}
