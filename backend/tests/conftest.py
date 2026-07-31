import os
import pytest
import hashlib
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-suite-123456")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app as fastapi_app
from app.api.dependencies import create_access_token
from app.models.db import Base, get_db
from app.models.schema import Company, CompanyUser, User

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session():
    db = TestingSessionLocal()
    # Reset tables per function for isolation
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def seeded_company_context(db_session):
    company = Company(name="Test Company", code="TST", status="Active")
    user = User(username="tester", password_hash=hashlib.sha256("password".encode()).hexdigest(), role="Admin")
    db_session.add_all([company, user])
    db_session.flush()

    access = CompanyUser(user_id=user.id, company_id=company.id, role="Admin")
    db_session.add(access)
    db_session.commit()
    db_session.refresh(company)
    db_session.refresh(user)

    return {
        "company": company,
        "user": user,
        "headers": {
            "Authorization": f"Bearer {create_access_token(user)}",
            "X-Company-Id": str(company.id),
        }
    }

@pytest.fixture(scope="function")
def client(db_session, seeded_company_context):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as c:
        c.headers.update(seeded_company_context["headers"])
        yield c
    fastapi_app.dependency_overrides.clear()
