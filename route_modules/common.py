from flask import session
from models import User


def has_page_access(page):
    """특정 페이지 접근 권한 확인
    - leader: 모든 권한 (단 마을은 체크 필요)
    - managed_pages에 포함된 페이지에만 접근 가능
    """
    role = session.get('role', '')
    uid = session.get('user_id')
    # 마을 관리 권한은 leader만 체크 필요
    if page == 'village' or page.startswith('vi_'):
        if uid:
            user = User.query.get(uid)
            if user and user.managed_pages:
                pages = user.managed_pages.split(',')
                if page in pages or 'village' in pages:
                    return True
                for p in pages:
                    if p.startswith('vi_'):
                        return True
        return False
    # 마을 외 페이지: leader는 전체 권한
    if role == 'leader':
        return True
    if uid:
        user = User.query.get(uid)
        if user and user.managed_pages:
            pages = user.managed_pages.split(',')
            if page in pages:
                return True
    return False
