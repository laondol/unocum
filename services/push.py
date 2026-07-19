# services/push.py - WebPush 전송 헬퍼
import os
import json
import base64
from pywebpush import webpush, WebPushException

VAPID_PRIVATE = os.getenv('VAPID_PRIVATE_KEY', '')
VAPID_PUBLIC = os.getenv('VAPID_PUBLIC_KEY', '')
VAPID_SUBJECT = os.getenv('VAPID_SUBJECT', 'mailto:admin@unocum.kr')


def _vapid_private_key_arg():
    """pywebpush는 vapid_private_key에 base64(DER) 또는 PEM을 기대.
    env에 base64 DER를 저장했으므로 그대로 반환(clean)."""
    if not VAPID_PRIVATE:
        return None
    if 'BEGIN PRIVATE KEY' in VAPID_PRIVATE:
        return VAPID_PRIVATE
    clean = ''.join(ch for ch in VAPID_PRIVATE if ch.isalnum() or ch in '+/=')
    return clean


def send_push(sub, title, body, url=None):
    priv = _vapid_private_key_arg()
    if not priv:
        print('[PUSH] VAPID_PRIVATE not set')
        return False
    payload = json.dumps({
        'title': title or '알림',
        'body': body or '',
        'url': url or '/schedule'
    })
    try:
        webpush(
            subscription_info={
                'endpoint': sub.endpoint,
                'keys': {'p256dh': sub.p256dh, 'auth': sub.auth}
            },
            data=payload,
            vapid_private_key=priv,
            vapid_claims={'sub': VAPID_SUBJECT},
        )
        return True
    except WebPushException as e:
        status = e.response.status_code if e.response is not None else None
        if status in (404, 410):
            print('[PUSH] subscription expired (status %s), will remove' % status)
            return False
        print('[PUSH] WebPushException status %s: %s' % (status, (e.response.text if e.response is not None else repr(e))))
        return False
    except Exception as e:
        print('[PUSH] Exception: %r' % e)
        return False
