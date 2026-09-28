import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.models.db import SessionLocal
from app.models.schema import StateHub

db = SessionLocal()
hub = db.query(StateHub).filter(StateHub.id == 11).first()
print(f"Hub status: '{hub.status}'")
