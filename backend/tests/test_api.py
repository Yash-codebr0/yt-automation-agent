import pytest

@pytest.fixture
def auth_header(client):
    # Register and login to get auth header
    client.post(
        "/api/v1/auth/register",
        json={"email": "creator@example.com", "password": "creatorpassword"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "creator@example.com", "password": "creatorpassword"}
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_get_trends_unauthorized(client):
    response = client.get("/api/v1/trends/")
    assert response.status_code == 401

def test_get_trends_authorized(client, auth_header):
    response = client.get("/api/v1/trends/", headers=auth_header)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_project(client, auth_header):
    response = client.post(
        "/api/v1/projects/",
        headers=auth_header,
        json={"title": "Test YouTube Project", "niche": "AI"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test YouTube Project"
    assert data["niche"] == "AI"
    assert data["status"] == "draft"

def test_create_project_accepts_freeform_car_edit_niche(client, auth_header):
    response = client.post(
        "/api/v1/projects/",
        headers=auth_header,
        json={"title": "Car Edit Campaign", "niche": "car edit"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Car Edit Campaign"
    assert data["niche"] == "car edit"

def test_get_project_logs(client, auth_header):
    # Create project first
    proj_resp = client.post(
        "/api/v1/projects/",
        headers=auth_header,
        json={"title": "Logs Test Project", "niche": "Programming"}
    )
    project_id = proj_resp.json()["id"]
    
    # Fetch logs
    response = client.get(f"/api/v1/projects/{project_id}/logs", headers=auth_header)
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) > 0
    assert logs[0]["agent_name"] == "System"
