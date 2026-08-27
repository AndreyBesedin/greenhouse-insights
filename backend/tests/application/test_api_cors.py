from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from application.api.dependencies import get_engine
from application.api.main import app
from application.bootstrap import bootstrap_greenhouses


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    bootstrap_greenhouses(engine)
    app.dependency_overrides[get_engine] = lambda: engine
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_frontend_dev_origin_is_allowed_to_call_the_api(client: TestClient) -> None:
    response = client.get("/greenhouses", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
