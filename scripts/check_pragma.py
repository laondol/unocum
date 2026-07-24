import sqlite3
conn = sqlite3.connect('instance/yangpyeong_v10.db')
c = conn.cursor()
for tbl in ['legal_post','post','share_report','tong_bot']:
    c.execute(f'PRAGMA table_info("{tbl}")')
    cols = c.fetchall()
    for col in cols:
        print(f'{tbl}.{col[1]}  type={col[2]}')
    print()
