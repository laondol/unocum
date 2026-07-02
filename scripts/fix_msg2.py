import sqlite3
conn = sqlite3.connect('/home/ubuntu/yp_project_dev/instance/yangpyeong_v10_dev.db')
try:
    conn.execute('ALTER TABLE message ADD COLUMN attachment VARCHAR(500)')
    conn.commit()
    print('Added column')
except Exception as e:
    print(str(e)[:100])
conn.close()
