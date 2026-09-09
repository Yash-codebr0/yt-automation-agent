# AI YouTube Empire Agent System

A production-ready, fully-automated multi-agent YouTube creation engine. It uses **FastAPI**, **LangGraph**, **Celery**, **PostgreSQL**, **Redis**, and a high-fidelity **React Dashboard** to discover trends, analyze niches, draft scripts, generate voiceovers, render videos, optimize SEO copy, and schedule uploads automatically.

---

## Technical Stack & Architecture

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery (asynchronous task runners).
- **Multi-Agent Engine**: LangGraph (coordinates stateful workflows through 9 specialized agents).
- **Frontend**: React, Vite, Recharts (analytics lines/bars), Lucide Icons, Vanilla CSS (Premium dark glassmorphism).
- **Video Assembly Engine**: MoviePy & FFmpeg CLI fallback.
- **APIs Integrated (with automatic mock fallbacks)**:
  - **OpenAI**: Script writing, Niche Opportunity Scoring, and DALL-E Thumbnail creation.
  - **ElevenLabs**: High-fidelity narration.
  - **YouTube Data API**: Real trending queries and automated video uploading/scheduling.
  - **Google Trends**: Real-time keyword scraping (via pytrends).

---

## Project Structure

```text
youtube_empire_agent/
├── docker-compose.yml              # Production multi-container orchestration
├── prometheus.yml                  # Prometheus metric scraping config
├── requirements.txt                # Python backend dependencies
├── backend/
│   ├── main.py                     # FastAPI app + Prometheus + WebSocket + Static Media
│   ├── alembic.ini                 # DB migration config
│   ├── alembic/                    # DB migration environment & version scripts
│   └── app/
│       ├── core/
│       │   ├── config.py           # Settings + Auto-generated SECRET_KEY + S3 configs
│       │   ├── database.py         # SQLAlchemy engine + transactional_session helper
│       │   ├── celery_app.py       # Celery configuration + Beat daily schedules
│       │   ├── redis_lock.py       # Redis distributed lock implementation
│       │   ├── logging_config.py   # Structured JSON logging setup
│       │   ├── security.py         # Password hashing & JWT token decode/encode
│       │   └── websocket_manager.py # Real-time per-project WebSocket Connection Manager
│       ├── agents/
│       │   └── graph.py            # 23-node stateful LangGraph workflow with checkpoints
│       ├── models/                 # DB models (User, Project, Trend, Analytics, Log)
│       ├── schemas/                # Strict Pydantic validation schemas
│       ├── services/
│       │   ├── openai_service.py   # 13 AI Agent LLM implementations + tenacity retries
│       │   ├── elevenlabs_service.py# TTS voice generation + tenacity retries
│       │   ├── youtube_service.py  # YouTube API upload & analytics fetch + retries
│       │   └── storage_service.py  # MinIO / S3 storage wrapper with local fallback
│       ├── tasks/
│       │   └── workflow_tasks.py   # Celery tasks (project workflow & daily analytics sync)
│       └── api/
│           ├── api.py              # Central FastAPI router
│           ├── auth.py             # User register/login routes
│           ├── projects.py         # Project CRUD + Workflow Trigger + Approval/Rejection
│           ├── trends.py           # Trend harvesting routes
│           ├── analytics.py        # Dashboard stats + Chart data endpoints
│           ├── health.py           # Deep service health check (/api/v1/health)
│           └── ws.py               # WebSocket real-time log stream endpoint
└── frontend/                       # Vite + React Dashboard UI
    ├── src/
    │   ├── App.jsx                 # 23-Agent matrix, WebSocket logs, Approval banner, Charts
    │   └── index.css               # Glassmorphism dark-mode UI design system
    └── Dockerfile                  # Frontend container definition
```

---

## Quick Start (Docker Compose)

### 1. Configure the Environment
Create a `.env` file in the project root folder. If left empty, the application will **automatically run in Mock Mode** with simulated voice synthesis, text-thumbnail generation, and virtual publishing.

```env
OPENAI_API_KEY=your_openai_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
YOUTUBE_API_KEY=your_youtube_api_key
```

### 2. Launch Container Services
Compile and run the stack using Docker Compose:

```bash
docker-compose up --build
```

- **Vite React UI**: [http://localhost:3000](http://localhost:3000)
- **FastAPI OpenAPI Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database Port**: `5432`
- **Redis Cache/Broker Port**: `6379`

---

## Multi-Agent Execution Nodes

When you select a project and click **Deploy Automation Pipeline**, a Celery background worker launches the compiled LangGraph workflow:

1. **Trend Hunter Agent**: Pulls queries from Google Trends and YouTube, ranking popularity.
2. **Niche Analyzer Agent**: Evaluates niche competition, views potential, and content difficulty.
3. **Script Writer Agent**: Generates hook, script body, video title, and call-to-action (CTA).
4. **Voice Agent**: Integrates ElevenLabs to create natural MP3 voice narration.
5. **Thumbnail Agent**: Invokes DALL-E to generate vibrant backgrounds.
6. **Video Generator Agent**: Combines voiceover audio, images, and slides into a final MP4 using MoviePy.
7. **SEO Agent**: Autogenerates keyword-optimized descriptions, tags, and hashtags.
8. **Publishing Agent**: Stages, uploads, and schedules video to YouTube.
9. **Analytics Agent**: Computes CTR and views progression, outputting improvement logs.

---

## REST API Documentation

### Authentication
- `POST /api/v1/auth/register` - Create creator account.
- `POST /api/v1/auth/login` - Obtain JWT session token.
- `GET /api/v1/auth/me` - Fetch authenticated user profile details.

### Trend Discovery
- `GET /api/v1/trends/` - List all trends sorted by popularity.
- `POST /api/v1/trends/hunt` - Trigger background harvested trends worker.

### Video Projects
- `GET /api/v1/projects/` - List all user projects.
- `POST /api/v1/projects/` - Create a custom project campaign.
- `GET /api/v1/projects/{project_id}` - View assets & metadata of a project.
- `PUT /api/v1/projects/{project_id}` - Edit hook, title, and body copy.
- `POST /api/v1/projects/{project_id}/run` - Deploy LangGraph pipeline for the project.
- `GET /api/v1/projects/{project_id}/logs` - Stream execution logs.

---

## Running Automated Tests

To run the Pytest backend checks locally (using isolated SQLite in-memory tables):

1. Install requirements locally:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute the test suite:
   ```bash
   pytest backend/tests/
   ```
