import os
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.project import Project
from backend.app.agents.graph import (
    trend_hunter_node,
    competitor_research_node,
    keyword_research_node,
    audience_research_node,
    analytics_feedback_node,
    memory_agent_node,
    idea_generator_node,
    script_writer_node,
    voice_agent_node,
    thumbnail_agent_node,
    video_generator_node,
    seo_agent_node
)

def test_multi_agent_graph_nodes(db):
    # Setup test user and project
    user = User(email="agent_test@example.com", hashed_password="pw")
    db.add(user)
    db.commit()
    db.refresh(user)
    
    project = Project(title="Agent Test", niche="Startups", user_id=user.id, status="draft")
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # 1. Test state initialization
    state = {
        "project_id": project.id,
        "niche": project.niche,
        "trend_title": "",
        "script": {},
        "voiceover_path": "",
        "thumbnail_path": "",
        "video_path": "",
        "seo": {},
        "youtube_video_id": "",
        "errors": [],
        "current_step": "init"
    }
    
    # 2. Run Trend Hunter node
    state = trend_hunter_node(state)
    assert state["trend_title"] != ""
    assert state["current_step"] == "Trend Hunter"
    
    # 3. Run Competitor Research node
    state = competitor_research_node(state)
    assert state["competitor_research_summary"] != ""
    assert state["current_step"] == "Competitor Research"

    # 4. Run Keyword Research node
    state = keyword_research_node(state)
    assert isinstance(state["keyword_research_tags"], list)
    assert state["current_step"] == "Keyword Research"

    # 5. Run Audience Research node
    state = audience_research_node(state)
    assert state["audience_research_demographics"] != ""
    assert state["current_step"] == "Audience Research"

    # 6. Run Analytics Feedback node
    state = analytics_feedback_node(state)
    assert state["analytics_advice"] != ""
    assert state["current_step"] == "Analytics Feedback"

    # 7. Run Memory Agent node
    state = memory_agent_node(state)
    assert state["memory_context"] != ""
    assert state["current_step"] == "Memory Agent"

    # 8. Run Idea Generator node
    state = idea_generator_node(state)
    assert state["idea_pitch"] != ""
    assert state["current_step"] == "Idea Generator"
    
    # 9. Run Script Writer node
    state = script_writer_node(state)
    assert "title" in state["script"]
    assert "body" in state["script"]
    assert state["current_step"] == "Script Writer"
    
    # 10. Run Voice Agent node
    state = voice_agent_node(state)
    assert state["voiceover_path"] != ""
    assert os.path.exists(state["voiceover_path"])
    assert state["current_step"] == "Voice Agent"
    
    # 11. Run Thumbnail Agent node
    state = thumbnail_agent_node(state)
    assert state["thumbnail_path"] != ""
    assert os.path.exists(state["thumbnail_path"])
    assert state["current_step"] == "Thumbnail Agent"

    # 12. Run Video Generator node
    state = video_generator_node(state)
    assert state["video_path"] != ""
    assert os.path.exists(state["video_path"])
    assert state["current_step"] == "Video Generator"

    # 13. Run SEO Agent node
    state = seo_agent_node(state)
    assert "title" in state["seo"]
    assert "description" in state["seo"]
    assert state["current_step"] == "SEO Agent"
    
    # Clean up generated files
    for path in [state.get("voiceover_path"), state.get("thumbnail_path"), state.get("video_path")]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"Cleanup warning: failed to delete {path}: {e}")


def test_custom_video_graph_nodes(db):
    user = User(email="custom_user@example.com", hashed_password="pw")
    db.add(user)
    db.commit()
    db.refresh(user)

    custom_title = "My Own Custom Porsche 911 Edit"
    project = Project(
        title=custom_title,
        niche="car edit",
        user_id=user.id,
        is_custom=True,
        custom_title=custom_title,
        status="draft"
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    from backend.app.agents.graph import custom_input_node, route_entry

    # Initial state for custom project
    state = {
        "project_id": project.id,
        "niche": project.niche,
        "trend_title": custom_title,
        "is_custom": True,
        "custom_title": custom_title,
        "script": {},
        "voiceover_path": "",
        "thumbnail_path": "",
        "video_path": "",
        "seo": {},
        "youtube_video_id": "",
        "errors": [],
        "current_step": "init"
    }

    # Route entry should go to custom_input
    next_node = route_entry(state)
    assert next_node == "custom_input"

    # Run custom_input_node
    state = custom_input_node(state)
    assert state["trend_title"] == custom_title
    assert state["current_step"] == "Custom Input"

    # Idea generator should preserve custom title
    state = idea_generator_node(state)
    assert state["idea_pitch"] == custom_title
    assert state["trend_title"] == custom_title

    # Script writer should retain custom title
    state = script_writer_node(state)
    assert state["script"]["title"] == custom_title


def test_video_service_niche_themes_and_storyboard():
    from backend.app.services.video_service import VideoService, THEMES

    # 1. Test Niche Theme resolution
    ai_theme = VideoService.get_niche_theme("AI Automation")
    assert ai_theme["name"] == "Cyber Intelligence"

    car_theme = VideoService.get_niche_theme("Automotive Car Edit")
    assert car_theme["name"] == "Apex Motorsport"

    finance_theme = VideoService.get_niche_theme("Crypto Finance")
    assert finance_theme["name"] == "Gold & Capital"

    # 2. Test Storyboard Generation
    mock_script = {
        "title": "Autonomous Coding Breakthrough",
        "hook": "Stop coding manually in 2026!",
        "body": "Autonomous agents write, debug, and ship production software. This revolutionizes engineering workflows.",
        "cta": "Hit subscribe for the next AI secret!"
    }
    scenes = VideoService.build_storyboard_scenes(mock_script, "Autonomous Coding", "AI")
    assert len(scenes) == 4
    assert scenes[0]["phase"] == "⚡ HOOK"
    assert scenes[0]["headline"] == "Stop coding manually in 2026!"
    assert scenes[3]["phase"] == "🎯 NEXT ACTION"
    assert sum(s["weight"] for s in scenes) == 1.0


def test_video_generator_node_full_rendering():
    import uuid as _uuid
    from backend.app.core.database import SessionLocal
    _run_id = str(_uuid.uuid4())[:8]
    _user_email = f"video_test_{_run_id}@example.com"

    setup_db = SessionLocal()
    user_id = None
    project_id = None
    try:
        user = User(email=_user_email, hashed_password="pw")
        setup_db.add(user)
        setup_db.commit()
        setup_db.refresh(user)
        user_id = user.id

        project = Project(
            title="Cinematic Porsche GT3 RS Edit",
            niche="car edit",
            user_id=user.id,
            status="draft"
        )
        setup_db.add(project)
        setup_db.commit()
        setup_db.refresh(project)
        project_id = project.id
    finally:
        setup_db.close()

    from backend.app.services.openai_service import OpenAIService
    from backend.app.services.video_service import VideoService

    # 1. Create mock thumbnail
    thumb_path = os.path.join(settings.MEDIA_DIR, "thumbnails", f"thumb_{project_id}.jpg")
    OpenAIService._generate_mock_thumbnail("Cinematic Porsche GT3 RS Edit", thumb_path)
    assert os.path.exists(thumb_path)

    # 2. Setup state
    state = {
        "project_id": project_id,
        "niche": "car edit",
        "trend_title": "Cinematic Porsche GT3 RS Edit",
        "is_custom": True,
        "custom_title": "Cinematic Porsche GT3 RS Edit",
        "script": {
            "title": "Cinematic Porsche GT3 RS Edit",
            "hook": "Hear that flat-six roar!",
            "body": "Pure naturally aspirated perfection. 9,000 RPM track weapon engineered for speed.",
            "cta": "Follow for the next cinematic supercar edit!"
        },
        "shorts_script": {
            "title": "GT3 RS Cold Start! 🔥",
            "hook": "Is this the best sounding car ever?",
            "body": "518 horsepower of pure aerodynamic track dominance.",
            "cta": "Drop a like if you love Porsche!"
        },
        "voiceover_path": "",
        "thumbnail_path": thumb_path,
        "video_path": "",
        "seo": {},
        "youtube_video_id": "",
        "errors": [],
        "current_step": "init"
    }

    # 3. Execute video_generator_node
    from backend.app.agents.graph import video_generator_node
    result_state = video_generator_node(state)

    # 4. Assert video files were created and exist
    video_path = result_state["video_path"]
    assert video_path != ""
    assert os.path.exists(video_path)
    assert os.path.getsize(video_path) > 0

    shorts_path = os.path.join(settings.MEDIA_DIR, "videos", f"shorts_{project_id}.mp4")
    assert os.path.exists(shorts_path)
    assert os.path.getsize(shorts_path) > 0

    # 5. Verify database record
    from backend.app.core.database import SessionLocal
    verify_db = SessionLocal()
    try:
        db_project = verify_db.query(Project).filter(Project.id == project_id).first()
        assert db_project.video_url is not None
        assert "/media/videos/" in db_project.video_url
        assert db_project.shorts_video_url is not None
        assert "/media/videos/" in db_project.shorts_video_url
        assert db_project.status == "waiting_for_approval"
    finally:
        verify_db.close()

    # 6. Cleanup
    for path in [thumb_path, video_path, shorts_path]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
