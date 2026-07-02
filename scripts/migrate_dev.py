import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import create_app
app = create_app()
from models import db
with app.app_context():
    from sqlalchemy import inspect
    insp = inspect(db.engine)
    cols = [c['name'] for c in insp.get_columns('user')]
    for col in ['jin_verified_at','photo_path']:
        if col not in cols:
            db.session.execute(db.text('ALTER TABLE user ADD COLUMN {} {}'.format(col, 'DATETIME' if col=='jin_verified_at' else 'VARCHAR(300)')))
            db.session.commit()
            print('Added', col)
    # legal_post columns
    lp_cols = [c['name'] for c in insp.get_columns('legal_post')]
    for col, ctype in [('ai_score','INTEGER DEFAULT 0'),('ai_reason','TEXT'),('status',"VARCHAR(20) DEFAULT 'pending'"),('labor_approved','BOOLEAN DEFAULT 0')]:
        if col not in lp_cols:
            db.session.execute(db.text('ALTER TABLE legal_post ADD COLUMN {} {}'.format(col, ctype)))
            db.session.commit()
            print('Added legal_post.'+col)
    print('Done')
