import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run import create_app
app = create_app()
from models import db
with app.app_context():
    from sqlalchemy import inspect
    insp = inspect(db.engine)
    cols = [c['name'] for c in insp.get_columns('message')]
    if 'attachment' not in cols:
        db.session.execute(db.text('ALTER TABLE message ADD COLUMN attachment VARCHAR(500)'))
        db.session.commit()
        print('Added message.attachment')
    else:
        print('Already exists')
