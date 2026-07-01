from sqlalchemy import create_engine, text
e = create_engine('postgresql://yp_dev:yp_dev_pass_2026@localhost:5432/yp_local')
conn = e.connect()
for tbl in ['legal_post', 'psycho_post']:
    conn.execute(text(f'ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS ai_score INTEGER DEFAULT 0'))
    conn.execute(text(f'ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS ai_reason TEXT'))
    conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending'"))
conn.commit()
conn.close()
e.dispose()
print('OK - columns added')
