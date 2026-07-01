from run import create_app
app = create_app()
from models import db
with app.app_context():
    try:
        db.session.execute(db.text("ALTER TABLE \"user\" ADD COLUMN jin_verified_at TIMESTAMP"))
        db.session.commit()
        print("jin_verified_at column added")
    except Exception as e:
        print(str(e)[:150])
