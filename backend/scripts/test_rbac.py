from fastapi.testclient import TestClient
from app.main import app
from app.models.db import SessionLocal
from app.models.schema import User, CompanyUser, Company
from app.api.dependencies import create_access_token

client = TestClient(app)

def test_rbac():
    db = SessionLocal()
    
    # 1. Create a mock company
    company = db.query(Company).filter(Company.name == "RBAC_TEST_COMP").first()
    if not company:
        company = Company(name="RBAC_TEST_COMP", code="RBAC", status="Active")
        db.add(company)
        db.commit()
        
    # 2. Create a mock viewer user
    viewer = db.query(User).filter(User.username == "viewer@test.com").first()
    if not viewer:
        viewer = User(username="viewer@test.com", password_hash="test", role="Viewer")
        db.add(viewer)
        db.commit()
        
    # 3. Create a mock admin user
    admin = db.query(User).filter(User.username == "admin@test.com").first()
    if not admin:
        admin = User(username="admin@test.com", password_hash="test", role="Admin")
        db.add(admin)
        db.commit()
        
    # 4. Give them access to the company
    for user, role in [(viewer, "Viewer"), (admin, "Admin")]:
        cu = db.query(CompanyUser).filter(CompanyUser.user_id == user.id, CompanyUser.company_id == company.id).first()
        if not cu:
            cu = CompanyUser(user_id=user.id, company_id=company.id, role=role)
            db.add(cu)
    db.commit()
    
    # Run tests
    viewer_token = create_access_token(viewer)
    admin_token = create_access_token(admin)
    
    print("\n--- Test Viewer ---")
    headers = {"Authorization": f"Bearer {viewer_token}", "X-Company-Id": str(company.id)}
    # Try assign user to warehouse 1
    r = client.post("/api/warehouses/1/users", json={"user_id": 1, "permission": "VIEW"}, headers=headers)
    print(f"Viewer POST /api/warehouses/1/users: {r.status_code} - {r.json()}")
    
    print("\n--- Test Admin ---")
    headers = {"Authorization": f"Bearer {admin_token}", "X-Company-Id": str(company.id)}
    # Try assign user to warehouse 1 (will be 404 if warehouse 1 doesn't exist, but that passes the 403 check)
    r = client.post("/api/warehouses/1/users", json={"user_id": 1, "permission": "VIEW"}, headers=headers)
    print(f"Admin POST /api/warehouses/1/users: {r.status_code} - {r.json()}")

if __name__ == "__main__":
    test_rbac()
