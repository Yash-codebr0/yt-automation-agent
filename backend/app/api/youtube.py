import json
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.api.deps import get_current_user
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.models.youtube_account import YouTubeAccount
from backend.app.services.youtube_service import YouTubeService

router = APIRouter()

STATE_FILE = os.path.join(settings.MEDIA_DIR, "youtube_oauth_state.txt")


# ---------------------------------------------------------------------------
# State helpers (PKCE + pending nickname)
# ---------------------------------------------------------------------------

def _save_state(state: str, code_verifier: str, nickname: str = "My Channel", user_id: str = "") -> None:
    os.makedirs(settings.MEDIA_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(
            {
                "state": state,
                "code_verifier": code_verifier,
                "nickname": nickname,
                "user_id": user_id,
            },
            f,
        )


def _load_state() -> tuple[str, str, str, str]:
    """Returns (state, code_verifier, nickname, user_id)."""
    if not os.path.exists(STATE_FILE):
        return "", "", "My Channel", ""
    try:
        with open(STATE_FILE, "r") as f:
            content = f.read().strip()
        if not content:
            return "", "", "My Channel", ""
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return (
                    data.get("state", ""),
                    data.get("code_verifier", ""),
                    data.get("nickname", "My Channel"),
                    data.get("user_id", ""),
                )
        except json.JSONDecodeError:
            # Legacy plain-text state
            return content, "", "My Channel", ""
    except Exception:
        return "", "", "My Channel", ""
    return "", "", "My Channel", ""


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/status")
def youtube_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return connection status + active account info."""
    active = (
        db.query(YouTubeAccount)
        .filter(YouTubeAccount.user_id == current_user.id, YouTubeAccount.is_active == True)
        .first()
    )
    connected = bool(active and YouTubeService.has_upload_connection(active.token_file))
    return {
        "configured": settings.is_youtube_upload_configured,
        "connected": connected,
        "redirect_uri": settings.YOUTUBE_REDIRECT_URI,
        "privacy_status": settings.YOUTUBE_PRIVACY_STATUS,
        "active_account": {
            "id": active.id,
            "nickname": active.nickname,
            "channel_title": active.channel_title,
            "channel_id": active.channel_id,
            "channel_thumbnail": active.channel_thumbnail,
        } if active else None,
    }


# ---------------------------------------------------------------------------
# List accounts
# ---------------------------------------------------------------------------

@router.get("/accounts")
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all connected YouTube accounts for the current user."""
    accounts = (
        db.query(YouTubeAccount)
        .filter(YouTubeAccount.user_id == current_user.id)
        .order_by(YouTubeAccount.connected_at.desc())
        .all()
    )
    return [
        {
            "id": acc.id,
            "nickname": acc.nickname,
            "channel_id": acc.channel_id,
            "channel_title": acc.channel_title,
            "channel_thumbnail": acc.channel_thumbnail,
            "is_active": acc.is_active,
            "connected": YouTubeService.has_upload_connection(acc.token_file),
            "connected_at": acc.connected_at.isoformat() if acc.connected_at else None,
        }
        for acc in accounts
    ]


# ---------------------------------------------------------------------------
# Connect a new account (OAuth start)
# ---------------------------------------------------------------------------

@router.get("/oauth/start")
def start_youtube_oauth(
    nickname: Optional[str] = Query("My Channel", description="Friendly name for this channel"),
    current_user: User = Depends(get_current_user),
):
    """Begin OAuth flow to connect a new YouTube channel."""
    try:
        state = secrets.token_urlsafe(32)
        authorization_url, code_verifier = YouTubeService.get_authorization_url(state)
        _save_state(state, code_verifier, nickname or "My Channel", current_user.id)
        return {"authorization_url": authorization_url}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# OAuth callback — saves new account to DB
# ---------------------------------------------------------------------------

@router.get("/oauth/callback")
def youtube_oauth_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth redirect and save the new account."""
    state = request.query_params.get("state", "")
    expected_state, code_verifier, nickname, state_user_id = _load_state()

    if not expected_state or state != expected_state:
        raise HTTPException(status_code=400, detail="Invalid YouTube OAuth state.")

    # Build a unique token file path for this account
    import uuid as _uuid
    acc_id = str(_uuid.uuid4())
    token_file = os.path.join(settings.MEDIA_DIR, "yt_tokens", f"acc_{acc_id}.json")

    try:
        YouTubeService.save_callback_credentials(
            str(request.url), state, code_verifier, token_file=token_file
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"YouTube OAuth failed: {exc}") from exc

    # Fetch channel metadata from the YouTube API
    channel_info = YouTubeService.get_channel_info(token_file)

    # Determine user_id from the state file owner — we peek at the DB for the most recent user
    # In a real multi-user app we'd embed user_id in the state. Here we take the first user
    # as this is a single-user tool. If you need multi-user, embed user_id in the OAuth state.
    if state_user_id:
        user = db.query(User).filter(User.id == state_user_id).first()
    else:
        # Legacy state files did not store the user. Keep old manual/test flows working.
        from sqlalchemy import text
        row = db.execute(text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")).fetchone()
        user = db.query(User).filter(User.id == row[0]).first() if row else None
    if not user:
        raise HTTPException(status_code=400, detail="No user found. Register first.")
    user_id = user.id

    # Deactivate all existing accounts for this user before setting the new one active
    db.query(YouTubeAccount).filter(
        YouTubeAccount.user_id == user_id
    ).update({"is_active": False})

    account = YouTubeAccount(
        id=acc_id,
        user_id=user_id,
        nickname=nickname,
        channel_id=channel_info["channel_id"],
        channel_title=channel_info["channel_title"],
        channel_thumbnail=channel_info["channel_thumbnail"],
        token_file=token_file,
        is_active=True,
    )
    db.add(account)
    db.commit()

    return RedirectResponse(f"http://localhost:3000?youtube=connected&channel={channel_info['channel_title'] or nickname}")


# ---------------------------------------------------------------------------
# Activate an account
# ---------------------------------------------------------------------------

@router.post("/accounts/{account_id}/activate")
def activate_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set the specified account as the active one for uploads."""
    account = (
        db.query(YouTubeAccount)
        .filter(YouTubeAccount.id == account_id, YouTubeAccount.user_id == current_user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    # Deactivate all others
    db.query(YouTubeAccount).filter(YouTubeAccount.user_id == current_user.id).update({"is_active": False})
    account.is_active = True
    db.commit()
    return {"status": "activated", "account_id": account_id, "nickname": account.nickname}


# ---------------------------------------------------------------------------
# Update nickname
# ---------------------------------------------------------------------------

@router.patch("/accounts/{account_id}")
def update_account_nickname(
    account_id: str,
    nickname: str = Query(..., description="New nickname"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rename a connected account."""
    account = (
        db.query(YouTubeAccount)
        .filter(YouTubeAccount.id == account_id, YouTubeAccount.user_id == current_user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")
    account.nickname = nickname
    db.commit()
    return {"status": "updated", "nickname": nickname}


# ---------------------------------------------------------------------------
# Disconnect / delete an account
# ---------------------------------------------------------------------------

@router.delete("/accounts/{account_id}")
def delete_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect a YouTube account and delete its token file."""
    account = (
        db.query(YouTubeAccount)
        .filter(YouTubeAccount.id == account_id, YouTubeAccount.user_id == current_user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    was_active = account.is_active

    # Delete token file
    if account.token_file and os.path.exists(account.token_file):
        try:
            os.remove(account.token_file)
        except Exception as e:
            print(f"Could not delete token file {account.token_file}: {e}")

    db.delete(account)
    db.commit()

    # If deleted account was active, activate the most recent remaining one
    if was_active:
        remaining = (
            db.query(YouTubeAccount)
            .filter(YouTubeAccount.user_id == current_user.id)
            .order_by(YouTubeAccount.connected_at.desc())
            .first()
        )
        if remaining:
            remaining.is_active = True
            db.commit()

    return {"status": "disconnected", "account_id": account_id}
