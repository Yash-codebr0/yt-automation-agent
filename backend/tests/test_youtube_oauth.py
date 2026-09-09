import os
import json
import pytest
from unittest.mock import patch, MagicMock
from backend.app.core.config import settings

@pytest.fixture
def auth_header(client):
    # Register and login to get auth header
    client.post(
        "/api/v1/auth/register",
        json={"email": "oauth_test@example.com", "password": "testpassword"}
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "oauth_test@example.com", "password": "testpassword"}
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_youtube_oauth_flow(client, auth_header):
    # Mock settings.MEDIA_DIR to a temporary location or use current settings
    state_file_path = os.path.join(settings.MEDIA_DIR, "youtube_oauth_state.txt")
    if os.path.exists(state_file_path):
        os.remove(state_file_path)

    dummy_url = "https://accounts.google.com/o/oauth2/auth?client_id=123"
    dummy_verifier = "xyz_verifier_code_challenge_pkce"

    with patch("backend.app.services.youtube_service.YouTubeService.get_authorization_url") as mock_get_url:
        mock_get_url.return_value = (dummy_url, dummy_verifier)

        # 1. Start OAuth Flow
        response = client.get("/api/v1/youtube/oauth/start", headers=auth_header)
        assert response.status_code == 200
        data = response.json()
        assert data["authorization_url"] == dummy_url
        mock_get_url.assert_called_once()

        # Check state file exists and has correct json format
        assert os.path.exists(state_file_path)
        with open(state_file_path, "r") as f:
            saved_data = json.load(f)
            assert "state" in saved_data
            assert saved_data["code_verifier"] == dummy_verifier
            assert saved_data["user_id"]
            state_val = saved_data["state"]

    # 2. Callback OAuth Flow
    with patch("backend.app.services.youtube_service.YouTubeService.save_callback_credentials") as mock_save_creds:
        callback_url = f"/api/v1/youtube/oauth/callback?state={state_val}&code=4/0AdQt8qg..."
        
        # We need to pass the full request URL string including protocol/host to mock, but the mock will receive it
        response = client.get(callback_url, follow_redirects=False)
        assert response.status_code == 307  # Redirect response
        assert "http://localhost:3000?youtube=connected" in response.headers["location"]
        
        # Verify save_callback_credentials was called with correct state and verifier
        mock_save_creds.assert_called_once()
        args, kwargs = mock_save_creds.call_args
        # The first arg is authorization_response (url)
        assert state_val in args[0] or state_val in kwargs.get("authorization_response", "")
        # The second arg should be the state
        assert args[1] == state_val or kwargs.get("state") == state_val
        # The third arg should be the code_verifier
        assert args[2] == dummy_verifier or kwargs.get("code_verifier") == dummy_verifier

    # Clean up state file
    if os.path.exists(state_file_path):
        os.remove(state_file_path)


def test_youtube_oauth_callback_fallback_old_format(client, auth_header):
    state_file_path = os.path.join(settings.MEDIA_DIR, "youtube_oauth_state.txt")
    if os.path.exists(state_file_path):
        os.remove(state_file_path)

    # Write old plain-text format state
    old_state = "legacy_oauth_state_12345"
    os.makedirs(settings.MEDIA_DIR, exist_ok=True)
    with open(state_file_path, "w") as f:
        f.write(old_state)

    # Callback OAuth Flow with legacy state
    with patch("backend.app.services.youtube_service.YouTubeService.save_callback_credentials") as mock_save_creds:
        callback_url = f"/api/v1/youtube/oauth/callback?state={old_state}&code=4/0AdQt8qg..."
        
        response = client.get(callback_url, follow_redirects=False)
        assert response.status_code == 307
        assert "http://localhost:3000?youtube=connected" in response.headers["location"]
        
        # Verify save_callback_credentials was called with the old state and empty/None code_verifier
        mock_save_creds.assert_called_once()
        args, kwargs = mock_save_creds.call_args
        assert args[1] == old_state or kwargs.get("state") == old_state
        assert args[2] is None or args[2] == "" or kwargs.get("code_verifier") == ""

    # Clean up state file
    if os.path.exists(state_file_path):
        os.remove(state_file_path)
