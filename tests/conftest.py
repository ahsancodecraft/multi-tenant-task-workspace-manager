import os
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base, get_db
from app.main import app

load_dotenv()

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:admin123@localhost:5433/task_manager_test",
)

test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture()
def auth_headers_factory(client):
    def _create_user_headers(
        email: str, password: str = "StrongPassword123!"
    ) -> dict[str, str]:
        client.post("/api/auth/register", json={"email": email, "password": password})
        login_res = client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        token = login_res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _create_user_headers