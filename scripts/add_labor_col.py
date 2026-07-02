from sqlalchemy import create_engine, text
e = create_engine('postgresql://yp_dev:yp_dev_pass_2026@localhost:5432/yp_local')
conn = e.connect()
conn.execute(text('ALTER TABLE legal_post ADD COLUMN IF NOT EXISTS labor_approved BOOLEAN DEFAULT FALSE'))
conn.commit()
conn.close()
e.dispose()
print('OK')
