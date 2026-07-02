import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import create_app
app = create_app()
from models import db
with app.app_context():
    from sqlalchemy import inspect
    insp = inspect(db.engine)
    cols = [c['name'] for c in insp.get_columns('user')]
    print('jin_verified_at:', 'jin_verified_at' in cols)
    print('photo_path:', 'photo_path' in cols)
    lp_cols = [c['name'] for c in insp.get_columns('legal_post')]
    print('legal.ai_score:', 'ai_score' in lp_cols)
    print('legal.labor_approved:', 'labor_approved' in lp_cols)
