import os
import secrets
from pydantic_settings import BaseSettings

def get_or_create_secret_key() -> str:
    env_file = ".env"
    key_name = "SECRET_KEY"
    
    # 1. Check environment variable
    secret = os.getenv(key_name)
    if secret:
        return secret
        
    # 2. Parse .env if it exists
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                if line.startswith(f"{key_name}="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        return val
                        
    # 3. Generate new random secret and persist to .env
    new_secret = secrets.token_urlsafe(32)
    try:
        mode = "a" if os.path.exists(env_file) else "w"
        prefix = "\n" if mode == "a" else ""
        with open(env_file, mode) as f:
            f.write(f"{prefix}{key_name}={new_secret}\n")
        print(f"Generated a new {key_name} and saved to {env_file}")
    except Exception as e:
        print(f"Failed to save generated secret key: {e}")
        
    return new_secret

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI YouTube Empire"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = get_or_create_secret_key()
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # DB & Cache
    DATABASE_URL: str = "sqlite:///./youtube_empire.db"  # Default fallback
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Third Party APIs
    OPENAI_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice default
    YOUTUBE_API_KEY: str = ""
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REDIRECT_URI: str = "http://localhost:8000/api/v1/youtube/oauth/callback"
    YOUTUBE_TOKEN_FILE: str = "media/youtube_token.json"
    YOUTUBE_PRIVACY_STATUS: str = "private"
    
    # Media Storage
    MEDIA_DIR: str = "media"
    
    # S3 / MinIO Storage Config
    S3_BUCKET: str = ""
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

    
    # Mock Settings (toggle mock mode if no api keys)
    @property
    def is_openai_mock(self) -> bool:
        return not self.OPENAI_API_KEY
        
    @property
    def is_elevenlabs_mock(self) -> bool:
        return not self.ELEVENLABS_API_KEY
        
    @property
    def is_youtube_mock(self) -> bool:
        return not self.YOUTUBE_API_KEY

    @property
    def is_youtube_upload_configured(self) -> bool:
        return bool(self.YOUTUBE_CLIENT_ID and self.YOUTUBE_CLIENT_SECRET)

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()

# Ensure media directory exists
os.makedirs(settings.MEDIA_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_DIR, "voiceovers"), exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_DIR, "thumbnails"), exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_DIR, "videos"), exist_ok=True)
os.makedirs(os.path.join(settings.MEDIA_DIR, "yt_tokens"), exist_ok=True)
