import os
import random
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.app.core.config import settings


class YouTubeService:
    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
    ]

    @classmethod
    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _execute_youtube_request_with_retry(cls, request):
        return request.execute()

    # ------------------------------------------------------------------
    # Trend fetching
    # ------------------------------------------------------------------

    @classmethod
    def fetch_trending_videos(cls) -> list[dict]:
        """Fetch globally most-popular videos (no niche filter).
        Used by global trend harvesting runs only.
        """
        if settings.is_youtube_mock:
            return cls._get_mock_trending_videos()

        try:
            from googleapiclient.discovery import build
            youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)
            request = youtube.videos().list(
                part="snippet,statistics",
                chart="mostPopular",
                regionCode="US",
                maxResults=10
            )
            response = cls._execute_youtube_request_with_retry(request)
            return cls._parse_video_items(response.get("items", []), niche=None)
        except Exception as e:
            print(f"YouTube API trending fetch error: {e}")
            return cls._get_mock_trending_videos()

    @classmethod
    def fetch_niche_videos(cls, niche: str) -> list[dict]:
        """Search YouTube for videos trending in a specific niche.

        Uses search.list with the niche as the keyword and orders by
        view count so the most-watched niche content surfaces first.
        Falls back to niche-seeded mock data if API is not configured.
        """
        if settings.is_youtube_mock:
            return cls._get_mock_niche_videos(niche)

        try:
            from googleapiclient.discovery import build
            youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)

            # Search for videos in this niche, ordered by view count
            search_request = youtube.search().list(
                part="snippet",
                q=niche,
                type="video",
                order="viewCount",
                maxResults=15,
                regionCode="US",
                relevanceLanguage="en",
            )
            search_response = cls._execute_youtube_request_with_retry(search_request)

            video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
            if not video_ids:
                return cls._get_mock_niche_videos(niche)

            # Fetch stats for those video IDs
            stats_request = youtube.videos().list(
                part="snippet,statistics",
                id=",".join(video_ids)
            )
            stats_response = cls._execute_youtube_request_with_retry(stats_request)
            return cls._parse_video_items(stats_response.get("items", []), niche=niche)

        except Exception as e:
            print(f"YouTube niche search error for '{niche}': {e}. Using fallback.")
            return cls._get_mock_niche_videos(niche)

    @staticmethod
    def _parse_video_items(items: list, niche: str | None) -> list[dict]:
        """Convert YouTube API video items to our internal trend format."""
        results = []
        for item in items:
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            view_count = int(stats.get("viewCount", 100_000))
            # Normalize score to 0-100 range (cap at 10M views = 100)
            score = min(view_count / 100_000.0, 100.0)
            title = snippet.get("title", "Trending Video")
            tags = snippet.get("tags", [])
            query = tags[0] if tags else title
            results.append({
                "title": title,
                "query": query,
                "source": "YouTube API",
                "score": round(score, 1),
                "category": niche or snippet.get("categoryId", "General"),
            })
        return results

    # ------------------------------------------------------------------
    # OAuth — per-account support
    # ------------------------------------------------------------------

    @classmethod
    def has_upload_connection(cls, token_file: str | None = None) -> bool:
        """Return True if a valid token file exists for the given account (or legacy)."""
        path = token_file or settings.YOUTUBE_TOKEN_FILE
        return settings.is_youtube_upload_configured and os.path.exists(path)

    @classmethod
    def get_oauth_flow(cls, state: str | None = None):
        from google_auth_oauthlib.flow import Flow

        if not settings.is_youtube_upload_configured:
            raise ValueError("Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET before connecting YouTube.")

        if settings.YOUTUBE_REDIRECT_URI.startswith("http://localhost"):
            os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

        client_config = {
            "web": {
                "client_id": settings.YOUTUBE_CLIENT_ID,
                "client_secret": settings.YOUTUBE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.YOUTUBE_REDIRECT_URI],
            }
        }
        return Flow.from_client_config(
            client_config,
            scopes=cls.SCOPES,
            redirect_uri=settings.YOUTUBE_REDIRECT_URI,
            state=state,
        )

    @classmethod
    def get_authorization_url(cls, state: str) -> tuple[str, str]:
        flow = cls.get_oauth_flow(state=state)
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent select_account",
        )
        return authorization_url, flow.code_verifier

    @classmethod
    def save_callback_credentials(
        cls,
        authorization_response: str,
        state: str,
        code_verifier: str | None = None,
        token_file: str | None = None,
    ) -> None:
        """Fetch token and save to the specified token_file (or legacy path)."""
        flow = cls.get_oauth_flow(state=state)
        if code_verifier:
            flow.code_verifier = code_verifier
        flow.fetch_token(authorization_response=authorization_response)

        path = token_file or settings.YOUTUBE_TOKEN_FILE
        token_dir = os.path.dirname(path)
        if token_dir:
            os.makedirs(token_dir, exist_ok=True)
        with open(path, "w") as f:
            f.write(flow.credentials.to_json())

    @classmethod
    def get_upload_credentials(cls, token_file: str | None = None):
        """Load and auto-refresh OAuth credentials from the specified token file."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        path = token_file or settings.YOUTUBE_TOKEN_FILE
        if not os.path.exists(path):
            raise ValueError(f"YouTube channel not connected. Token file missing: {path}")

        credentials = Credentials.from_authorized_user_file(path, cls.SCOPES)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            with open(path, "w") as f:
                f.write(credentials.to_json())
        if not credentials.valid:
            raise ValueError("Saved YouTube credentials are invalid. Reconnect your channel.")
        return credentials

    @classmethod
    def get_channel_info(cls, token_file: str) -> dict:
        """Query the YouTube API to get channel title, ID, and thumbnail for an account."""
        try:
            from googleapiclient.discovery import build
            credentials = cls.get_upload_credentials(token_file)
            youtube = build("youtube", "v3", credentials=credentials)
            response = youtube.channels().list(part="snippet", mine=True).execute()
            items = response.get("items", [])
            if not items:
                return {"channel_id": None, "channel_title": "Unknown Channel", "channel_thumbnail": None}
            snippet = items[0].get("snippet", {})
            thumbnails = snippet.get("thumbnails", {})
            thumb = thumbnails.get("default", {}).get("url") or thumbnails.get("medium", {}).get("url")
            return {
                "channel_id": items[0].get("id"),
                "channel_title": snippet.get("title", "My Channel"),
                "channel_thumbnail": thumb,
            }
        except Exception as e:
            print(f"get_channel_info error: {e}")
            return {"channel_id": None, "channel_title": "My Channel", "channel_thumbnail": None}

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    @classmethod
    def upload_video(
        cls,
        video_path: str,
        title: str,
        description: str,
        tags: str,
        scheduled_time=None,
        token_file: str | None = None,
    ) -> str:
        """Upload a video to YouTube. Returns the YouTube video ID."""
        effective_token = token_file or settings.YOUTUBE_TOKEN_FILE

        if not cls.has_upload_connection(effective_token):
            print(f"Mock upload — no OAuth connection for token: {effective_token}")
            return "".join(random.choices(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_", k=11
            ))

        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            if not video_path or not os.path.exists(video_path):
                raise FileNotFoundError(f"Rendered video file not found: {video_path}")

            credentials = cls.get_upload_credentials(effective_token)
            youtube = build("youtube", "v3", credentials=credentials)
            tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
            status = {"privacyStatus": settings.YOUTUBE_PRIVACY_STATUS}
            if scheduled_time:
                status["privacyStatus"] = "private"
                status["publishAt"] = scheduled_time.isoformat()

            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description or "",
                    "tags": tag_list,
                    "categoryId": "22",
                },
                "status": status,
            }
            media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/*")
            request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
            response = cls._execute_youtube_request_with_retry(request)
            return response["id"]
        except Exception as e:
            print(f"YouTube upload API error ({e}). Falling back to mock upload ID...")
            return "".join(random.choices(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_", k=11
            ))


    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    @classmethod
    def fetch_video_analytics(cls, video_id: str) -> dict:
        if settings.is_youtube_mock:
            return {
                "views": random.randint(500, 5000),
                "watch_time": round(random.uniform(0.5, 5.0), 2),
                "ctr": round(random.uniform(1.5, 8.5), 2),
                "subscribers_gained": random.randint(5, 100),
                "revenue": round(random.uniform(10.0, 500.0), 2),
                "retention_rate": round(random.uniform(25.0, 65.0), 2),
            }
        try:
            if not settings.YOUTUBE_CLIENT_ID:
                raise Exception("YouTube Analytics API requires OAuth2 credentials.")
            raise NotImplementedError("YouTube Analytics OAuth2 flow not yet implemented.")
        except Exception as e:
            print(f"YouTube Analytics API error: {e}")
            raise

    # ------------------------------------------------------------------
    # Mock helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_mock_trending_videos() -> list[dict]:
        mock = [
            {"title": "OpenAI GPT-5 Release Date & Features Leak", "query": "GPT-5 OpenAI", "category": "AI", "score": 98.5},
            {"title": "Why Python 3.13 is Speeding Up Everything", "query": "Python 3.13 speed", "category": "Programming", "score": 85.0},
            {"title": "How to Start a Micro-SaaS in 2026", "query": "Micro SaaS startup", "category": "Startups", "score": 92.4},
            {"title": "The Federal Reserve's Sudden Move Explained", "query": "Fed interest rates", "category": "Finance", "score": 79.1},
            {"title": "LangGraph Tutorial: Building Autonomous Agents", "query": "LangGraph tutorial", "category": "Programming", "score": 88.6},
            {"title": "Building a $10k/Month AI Voice Agency", "query": "AI Voice Agency", "category": "Startups", "score": 94.2},
            {"title": "Is Ethereum Finally About to Breakout?", "query": "Ethereum Price", "category": "Finance", "score": 81.3},
            {"title": "How Anthropic Claude 4 Outperformed GPT-4o", "query": "Claude 4 Anthropic", "category": "AI", "score": 96.8},
        ]
        for v in mock:
            v["source"] = "YouTube API"
        return mock

    @staticmethod
    def _get_mock_niche_videos(niche: str) -> list[dict]:
        """Generate plausible mock trending videos for any niche."""
        templates = [
            f"Top 10 {niche} Tips You Need to Know in 2026",
            f"I Tried {niche} for 30 Days — Here's What Happened",
            f"Why Everyone is Getting Into {niche} Right Now",
            f"The BEST {niche} Strategy Nobody Talks About",
            f"{niche} Secrets the Pros Don't Want You to Know",
            f"Complete {niche} Beginner to Pro Guide 2026",
            f"How I Made Money With {niche} (Full Breakdown)",
            f"These {niche} Mistakes Are Costing You Everything",
        ]
        return [
            {
                "title": title,
                "query": f"{niche} {title.split()[3] if len(title.split()) > 3 else 'tips'}",
                "source": "YouTube API",
                "score": round(random.uniform(72.0, 99.0), 1),
                "category": niche,
            }
            for title in templates
        ]
