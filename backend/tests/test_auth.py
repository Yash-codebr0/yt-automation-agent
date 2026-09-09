def test_register_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "testuser@example.com", "password": "securepassword123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "testuser@example.com"
    assert "id" in data

def test_login_user(client):
    # Try to login with created user
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "securepassword123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_get_me(client):
    # Login to get token
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "securepassword123"}
    )
    token = login_resp.json()["access_token"]
    
    # Fetch profile
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testuser@example.com"
