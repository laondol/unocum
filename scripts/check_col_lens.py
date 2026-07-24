import sqlite3
conn = sqlite3.connect('instance/yangpyeong_v10.db')
c = conn.cursor()
c.execute('SELECT name FROM sqlite_master WHERE type="table" ORDER BY name')
for t in c.fetchall():
    tn = t[0]
    c2 = conn.cursor()
    c2.execute(f'SELECT COUNT(*) FROM "{tn}"')
    cnt = c2.fetchone()[0]
    if cnt == 0: continue
    c2.execute(f'PRAGMA table_info("{tn}")')
    cols = c2.fetchall()
    for col in cols:
        c3 = conn.cursor()
        try:
            c3.execute(f'SELECT MAX(LENGTH("{col[1]}")) FROM "{tn}"')
            mx = c3.fetchone()[0]
            if mx and mx > 200:
                print(f'{tn}.{col[1]}: max_len={mx}')
        except Exception as e:
            pass
