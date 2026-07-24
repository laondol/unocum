import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ['DB_MODE'] = 'postgresql'

from flask import Flask
from config import Config
from models import db
from sqlalchemy import text, Boolean as SaBoolean
import sqlalchemy as sa

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def migrate():
    pg_uri = Config.SQLALCHEMY_DATABASE_URI
    print(f"[MIGRATE] 대상: {pg_uri}")
    with app.app_context():
        from sqlalchemy import create_engine
        from config import BASE_DIR

        # 슈퍼유저 연결 (yp_dev는 superuser이므로 그대로 사용)
        su_uri = pg_uri
        su_engine = create_engine(su_uri)
        su_conn = su_engine.connect()
        su_conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        su_conn.execute(text("CREATE SCHEMA public"))
        pg_user = pg_uri.split('://')[1].split(':')[0]
        su_conn.execute(text(f"GRANT ALL ON SCHEMA public TO {pg_user}"))
        su_conn.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {pg_user}"))
        su_conn.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {pg_user}"))
        su_conn.commit()

        # 테이블 생성
        db.metadata.create_all(bind=su_engine)
        print("[MIGRATE] 테이블 생성 완료")

        # 모든 FK 제약조건 조회 및 삭제
        fk_sql = text("""
            SELECT conname, conrelid::regclass AS tbl,
                   pg_get_constraintdef(oid) AS def
            FROM pg_constraint
            WHERE contype = 'f' AND connamespace = 'public'::regnamespace
        """)
        fk_rows = su_conn.execute(fk_sql).fetchall()
        fk_map = {}
        for row in fk_rows:
            name, tbl, defn = row
            fk_map[name] = (tbl, defn)
            su_conn.execute(text(f"ALTER TABLE {tbl} DROP CONSTRAINT {name}"))
            print(f"  FK 삭제: {tbl}.{name}")
        su_conn.commit()

        # SQLite 데이터 읽기
        sqlite_path = os.path.join(BASE_DIR, 'instance', 'yangpyeong_v10.db')
        sqlite_engine = create_engine(f'sqlite:///{sqlite_path}')
        sqlite_conn = sqlite_engine.connect()

        # yp_user로 데이터 복사
        engine = create_engine(pg_uri)
        with engine.connect() as conn:
            trans = conn.begin()
            tables = list(db.metadata.tables.keys())
            # SQLite에 실제로 존재하는 컬럼 목록 조회
            sqlite_cols = {}
            for table_name in tables:
                try:
                    pragma_rows = sqlite_conn.execute(text(f'PRAGMA table_info("{table_name}")')).fetchall()
                    sqlite_cols[table_name] = {r[1] for r in pragma_rows}
                except:
                    sqlite_cols[table_name] = set()
            for table_name in tables:
                table = db.metadata.tables[table_name]
                if table_name not in sqlite_cols or not sqlite_cols[table_name]:
                    print(f"[MIGRATE] {table_name}: SQLite에 없는 테이블, 생성만 함")
                    continue
                rows = sqlite_conn.execute(text(f'SELECT * FROM "{table_name}"')).fetchall()
                if not rows:
                    print(f"[MIGRATE] {table_name}: 0건 (빈 테이블)")
                    continue
                model_cols = [c.name for c in table.columns]
                # SQLite와 모델에 모두 존재하는 컬럼만
                common_cols = [c for c in model_cols if c in sqlite_cols[table_name]]
                if not common_cols:
                    print(f"[MIGRATE] {table_name}: 공통 컬럼 없음, 건너뜀")
                    continue
                bool_cols = {c.name for c in table.columns if isinstance(c.type, SaBoolean)}
                def convert_row(r, cols):
                    d = {}
                    for col in cols:
                        try:
                            val = getattr(r, col)
                        except:
                            continue
                        if col in bool_cols and isinstance(val, str):
                            d[col] = val.lower() in ('1', 'true', 'yes', 'on')
                        else:
                            d[col] = val
                    return d
                data = [convert_row(r, common_cols) for r in rows]
                stmt = table.insert().values(data)
                conn.execute(stmt)
                print(f"[MIGRATE] {table_name}: {len(rows)}건 복사 (컬럼 {len(common_cols)})")
            trans.commit()

        # FK 복원 (각각 독립 트랜잭션)
        su_conn2 = su_engine.connect()
        for name, (tbl, defn) in fk_map.items():
            try:
                su_conn2.execute(text(f"ALTER TABLE {tbl} ADD CONSTRAINT {name} {defn}"))
                su_conn2.commit()
                print(f"  FK 복원: {tbl}.{name}")
            except Exception as e:
                su_conn2.rollback()
                print(f"  FK 복원 실패 (skip): {tbl}.{name} - {e}")
        su_conn2.close()

        sqlite_conn.close()
        engine.dispose()
        su_conn.close()
        su_engine.dispose()
        print("[MIGRATE] 마이그레이션 완료!")

if __name__ == '__main__':
    migrate()
