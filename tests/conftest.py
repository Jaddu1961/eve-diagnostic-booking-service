import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["PAYMENT_WEBHOOK_SECRET"] = "test-webhook-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app import seed  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    seed.run()
    with TestClient(app) as c:
        yield c


def signup_login(client, email="user@example.com", password="Passw0rd123"):
    client.post("/auth/signup", json={"email": email, "full_name": "Test User", "password": password})
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
