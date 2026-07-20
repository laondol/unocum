import os
import re
import time
import requests
from flask import current_app

_GEO_CACHE = {}
_GEO_CACHE_TTL = 3600


def _geo_cache_key(loc):
    return loc.strip().lower()


def _geo_cache_get(loc):
    key = _geo_cache_key(loc)
    hit = _GEO_CACHE.get(key)
    if hit and (hit[0] + _GEO_CACHE_TTL) > time.time():
        return hit[1]
    return None


def _geo_cache_set(loc, result):
    _GEO_CACHE[_geo_cache_key(loc)] = (time.time(), result)


def _clean_query(q):
    q = re.sub(r'[\(\)\[\]\{\}「」【】〈〉《》"'']', ' ', q)
    q = re.sub(r'\s+', ' ', q).strip()
    return q


def _kakao_geocode(query, kakao_key):
    try:
        resp = requests.get('https://dapi.kakao.com/v2/local/search/keyword.json',
                            params={'query': query, 'size': 1},
                            headers={'Authorization': f'KakaoAK {kakao_key}'}, timeout=2)
        if resp.status_code == 200:
            docs = resp.json().get('documents', [])
            if docs:
                return float(docs[0].get('y', 0)), float(docs[0].get('x', 0))
        resp = requests.get('https://dapi.kakao.com/v2/local/search/address.json',
                            params={'query': query},
                            headers={'Authorization': f'KakaoAK {kakao_key}'}, timeout=2)
        if resp.status_code == 200:
            docs = resp.json().get('documents', [])
            if docs:
                return float(docs[0].get('y', 0)), float(docs[0].get('x', 0))
    except Exception:
        pass
    return None


def _naver_geocode(query, client_id, client_secret):
    if not client_id or not client_secret:
        return None
    try:
        resp = requests.get('https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode',
                            params={'query': query},
                            headers={
                                'x-ncp-apigw-api-key-id': client_id,
                                'x-ncp-apigw-api-key': client_secret,
                            }, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            addrs = (data.get('addresses') or [])
            if addrs:
                return float(addrs[0].get('y', 0)), float(addrs[0].get('x', 0))
    except Exception:
        pass
    return None


def _all_partial_queries(loc_name):
    """Generate progressively shorter queries from a location name."""
    yield loc_name
    cleaned = _clean_query(loc_name)
    if cleaned != loc_name:
        yield cleaned
    tokens = cleaned.split()
    for i in range(1, len(tokens)):
        yield ' '.join(tokens[:-i])


def _geocode_location(loc_name):
    """location name -> (lat,lng); Kakao -> Naver fallback with progressive trimming."""
    if not loc_name:
        return None, None
    cached = _geo_cache_get(loc_name)
    if cached:
        return cached if cached != (None, None) else (None, None)
    try:
        kakao_key = current_app.config.get('KAKAO_REST_API_KEY', '')
        naver_id = current_app.config.get('NAVER_CLIENT_ID',
                    os.getenv('NAVER_CLIENT_ID', ''))
        naver_secret = current_app.config.get('NAVER_CLIENT_SECRET',
                        os.getenv('NAVER_CLIENT_SECRET', ''))

        queries = list(_all_partial_queries(loc_name))

        for q in queries:
            res = _kakao_geocode(q, kakao_key)
            if res:
                _geo_cache_set(loc_name, res)
                return res

        if naver_id and naver_secret:
            for q in queries:
                res = _naver_geocode(q, naver_id, naver_secret)
                if res:
                    _geo_cache_set(loc_name, res)
                    return res

    except Exception:
        pass
    _geo_cache_set(loc_name, (None, None))
    return None, None
