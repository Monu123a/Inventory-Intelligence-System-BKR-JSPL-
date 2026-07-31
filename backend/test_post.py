from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.schema import User
from app.api.dependencies import create_access_token
import requests

engine = create_engine('sqlite:///inventory.db')
Session = sessionmaker(bind=engine)
db = Session()
user = db.query(User).first()
token = create_access_token(user)

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = {
  "from_company_id": 1,
  "to_company_id": 2,
  "items": [{"product_id": 1, "requested_qty": 50}]
}
r_post = requests.post("http://localhost:8000/api/transfers/create", json=payload, headers=headers)
print("Status:", r_post.status_code)
print("Response:", r_post.text)
