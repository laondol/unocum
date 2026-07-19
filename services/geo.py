import os
import requests
from flask import current_app


def _geocode_location(loc_name):
    """location name -> (lat,lng); keyword->address->trim-trailing-token fallback"""
    if not loc_name:
        return None, None
    try:
        kakao_key = current_app.config.get('KAKAO_REST_API_KEY', '')
        if not kakao_key:
            return None, None

        def _one(query):
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

        res = _one(loc_name)
        if res:
            return res
        tokens = loc_name.split()
        for i in range(1, min(len(tokens), 3)):
            res = _one(' '.join(tokens[:-i]))
            if res:
                return res
    except Exception:
        pass
    return None, None
