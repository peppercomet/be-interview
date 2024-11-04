from pathlib import Path
from typing import Generator
from unittest.mock import patch
from uuid import uuid4
from fastapi import status
import alembic.command
import alembic.config
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.db import get_database_session
from app.main import app
from app.models import Organisation

_ALEMBIC_INI_PATH = Path(__file__).parent.parent / "alembic.ini"

@pytest.fixture()
def test_client() -> TestClient:
    return TestClient(app)

@pytest.fixture(autouse=True)
def apply_alembic_migrations() -> Generator[None, None, None]:
    # Creates test database per test function
    test_db_file_name = f"test_{uuid4()}.db"
    database_path = Path(test_db_file_name)
    try:
        test_db_url = f"sqlite:///{test_db_file_name}"
        alembic_cfg = alembic.config.Config(_ALEMBIC_INI_PATH)
        alembic_cfg.attributes["sqlalchemy_url"] = test_db_url
        alembic.command.upgrade(alembic_cfg, "head")
        test_engine = create_engine(test_db_url, echo=True)
        with patch("app.db.get_engine") as mock_engine:
            mock_engine.return_value = test_engine
            yield
    finally:
        database_path.unlink(missing_ok=True)


def test_organisation_endpoints(test_client: TestClient) -> None:
    list_of_organisation_names_to_create = ["organisation_a", "organisation_b", "organisation_c"]

    with get_database_session() as database_session:
        organisations_before = database_session.query(Organisation).all()
        database_session.expunge_all()
    assert len(organisations_before) == 0

    for organisation_name in list_of_organisation_names_to_create:
        response = test_client.post("/api/organisations/create", json={"name": organisation_name})
        assert response.status_code == status.HTTP_200_OK

    with get_database_session() as database_session:
        organisations_after = database_session.query(Organisation).all()
        database_session.expunge_all()
    created_organisation_names = set(organisation.name for organisation in organisations_after)
    assert created_organisation_names == set(list_of_organisation_names_to_create)

    response = test_client.get("/api/organisations")
    organisations = set(organisation["name"] for organisation in response.json())
    assert  set(organisations) == created_organisation_names


def test_get_organisations(test_client: TestClient) -> None:
    response = test_client.get("/api/organisations/")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


def test_get_organisation(test_client: TestClient) -> None:
    response = test_client.post("/api/organisations/create", json={"name": "Test Organisation"})
    organisation_id = response.json()["id"]
    
    response = test_client.get(f"/api/organisations/{organisation_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == organisation_id


def test_get_organisation_not_found(test_client: TestClient) -> None:
    response = test_client.get("/api/organisations/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_location(test_client: TestClient) -> None:
    response = test_client.post("/api/organisations/create", json={"name": "Organisation for Location"})
    organisation_id = response.json()["id"]
    location_data = {"location_name": "Test Location", "longitude": 10.0, "latitude": 10.0, "organisation_id": organisation_id}
    response = test_client.post("/api/organisations/create/locations", json=location_data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["location"]["location_name"] == "Test Location"


def test_get_organisation_locations(test_client: TestClient) -> None:
    response = test_client.post("/api/organisations/create", json={"name": "Organisation for Locations"})
    organisation_id = response.json()["id"]
    location_data = {"location_name": "Location 1", "longitude": 10.0, "latitude": 10.0, "organisation_id": organisation_id}
    test_client.post("/api/organisations/create/locations", json=location_data)
    response = test_client.get(f"/api/organisations/{organisation_id}/locations")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0


def test_get_organisation_locations_with_bounding_box(test_client: TestClient) -> None:
    response = test_client.post("/api/organisations/create", json={"name": "Bounding Box Org"})
    organisation_id = response.json()["id"]
    location_data = {"location_name": "Location A", "longitude": 5.0, "latitude": 5.0, "organisation_id": organisation_id}
    test_client.post("/api/organisations/create/locations", json=location_data)
    response = test_client.get(f"/api/organisations/{organisation_id}/locations?bounding_box=0.0,0.0,10.0,10.0")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0


def test_get_organisation_locations_empty(test_client: TestClient) -> None:
    response = test_client.post("/api/organisations/create", json={"name": "Empty Locations Org"})
    organisation_id = response.json()["id"]
    response = test_client.get(f"/api/organisations/{organisation_id}/locations?bounding_box=50.0,50.0,60.0,60.0")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_create_location_not_implemented(test_client: TestClient) -> None:
    location_data = {
        "location_name": "Test Location",
        "longitude": 10.0,
        "latitude": 20.0,
        "organisation_id": 0
    }
    response = test_client.post("/api/organisations/create/locations", json=location_data)
    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED


def test_get_organisation_locations_with_bounding_box(test_client: TestClient) -> None:

    response = test_client.post("/api/organisations/create", json={"name": "Bounding Box Org"})
    organisation_id = response.json()["id"]

    location_data = {
        "location_name": "Location A",
        "longitude": 5.0,
        "latitude": 5.0,
        "organisation_id": organisation_id
    }
    test_client.post("/api/organisations/create/locations", json=location_data)

    response = test_client.get(f"/api/organisations/{organisation_id}/locations?bounding_box=0.0,0.0,10.0,10.0")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0  # Expected location to be within the bounding box


def test_get_organisation_locations_empty_bounding_box(test_client: TestClient) -> None:
  
    response = test_client.post("/api/organisations/create", json={"name": "Empty Locations Org"})
    organisation_id = response.json()["id"]

    response = test_client.get(f"/api/organisations/{organisation_id}/locations?bounding_box=50.0,50.0,60.0,60.0")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_create_location_via_get(test_client: TestClient) -> None:

    response = test_client.get("/api/organisations/create/location")
    assert response.status_code == status.HTTP_200_OK
    assert "Location created" in response.json()["message"]
    assert response.json()["location"]["location_name"] == "Default Name"
    assert response.json()["location"]["longitude"] == 0.0
    assert response.json()["location"]["latitude"] == 0.0