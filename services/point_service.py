from datetime import datetime
from models import db, PointHistory


def add_points(user_id, amount, reason, description='', ref_id=None):
    try:
        ph = PointHistory(
            user_id=user_id,
            points=amount,
            reason=reason,
            description=description or '',
            ref_id=ref_id,
            created_at=datetime.now()
        )
        db.session.add(ph)
        from models import User
        user = User.query.get(user_id)
        if user:
            user.points = (user.points or 0) + amount
    except Exception:
        pass
