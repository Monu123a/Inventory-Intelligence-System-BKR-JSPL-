import sys
import os
sys.path.append(os.path.abspath('backend'))
from sqlalchemy import create_engine, text

RENDER_POSTGRES_URL = 'postgresql://inventory_db_r7fg_user:q03CgWQKPynzBfBiyvZxJ1RnO0vC2gfz@dpg-da2ju97qj5pc73fvjbc0-a.oregon-postgres.render.com/inventory_db_r7fg'
engine = create_engine(RENDER_POSTGRES_URL, isolation_level="AUTOCOMMIT")

with engine.connect() as conn:
    print("Finding blocking queries...")
    res = conn.execute(text("""
        SELECT pid, state, query 
        FROM pg_stat_activity 
        WHERE state != 'idle' AND pid != pg_backend_pid();
    """))
    for r in res:
        print(f"PID {r[0]} | State: {r[1]} | Query: {r[2][:100]}")
        print(f"Killing PID {r[0]}")
        conn.execute(text(f"SELECT pg_terminate_backend({r[0]})"))
        
print("Done killing locks.")
