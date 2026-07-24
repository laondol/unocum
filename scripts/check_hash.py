import sqlite3
conn = sqlite3.connect('instance/yangpyeong_v10.db')
c = conn.cursor()
c.execute('SELECT password FROM user WHERE email="eou@kakao.com"')
row = c.fetchone()
print('SQLite hash:', repr(row[0]))
print('Length:', len(row[0]))
from werkzeug.security import check_password_hash
print('Verify:', check_password_hash(row[0], 'pw1234'))

# Check PG
print('---')
import os
os.environ['DEV_MODE'] = '1'
os.environ['DB_MODE'] = 'postgresql'
os.environ['DATABASE_URL'] = 'postgresql://yp_dev:yp_dev_2026@127.0.0.1:5432/yp_dev_db'
import sys; sys.path.insert(0, '.')
from run import app
with app.app_context():
    from models import db, User
    u = User.query.filter_by(email='eou@kakao.com').first()
    if u:
        print('PG hash:', repr(u.password))
        print('PG Length:', len(u.password))
        print('PG Verify:', check_password_hash(u.password, 'pw1234'))
        print('Role:', u.role)
