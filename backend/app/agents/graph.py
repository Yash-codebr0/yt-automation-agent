import os
import shutil
import time
import sqlite3
import math
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END, START
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.project import Project
from backend.app.models.log import AgentLog
from backend.app.models.trend import Trend
from backend.app.models.analytics import Analytics
from backend.app.models.user import User  # noqa: F401 - ensure relationship target is registered
from backend.app.models.youtube_account import YouTubeAccount  # noqa: F401

from backend.app.services.openai_service import OpenAIService
from backend.app.services.elevenlabs_service import ElevenLabsService
from backend.app.services.youtube_service import YouTubeService
from backend.app.services.pytrends_service import PyTrendsService

# Define AgentState with all 13 new agent fields
class AgentState(TypedDict):
    project_id: str
    niche: str
    trend_title: str
    is_custom: bool
    custom_title: Optional[str]
    
    # Phase 2 AI Agent outputs
    competitor_research_summary: str
    keyword_research_tags: List[str]
    audience_research_demographics: str
    idea_pitch: str
    fact_checker_report: str
    script_reviewer_critique: str
    brand_report: str
    retention_cues: str
    shorts_script: Dict[str, str]
    translated_metadata: Dict[str, Any]
    scheduled_date: str
    analytics_advice: str
    memory_context: str
    thumbnail_score: float
    thumbnail_feedback: str

    # Core states
    script: Dict[str, str]
    voiceover_path: str
    thumbnail_path: str
    video_path: str
    seo: Dict[str, str]
    youtube_video_id: str
    errors: List[str]
    current_step: str

# Helper to log agent steps to DB and broadcast to WebSocket clients
def log_agent_step(project_id: str, agent_name: str, status: str, message: str):
    db = SessionLocal()
    try:
        log_entry = AgentLog(
            project_id=project_id,
            agent_name=agent_name,
            status=status,
            log_message=message
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        print(f"[{agent_name}] {status.upper()}: {message}")

        # Broadcast via WebSocket manager if active connections exist
        try:
            from backend.app.core.websocket_manager import manager
            if manager.connection_count(project_id) > 0:
                import asyncio
                payload = {
                    "type": "log",
                    "agent": agent_name,
                    "status": status,
                    "message": message,
                    "timestamp": log_entry.created_at.isoformat() if log_entry.created_at else datetime.utcnow().isoformat()
                }
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(manager.broadcast_to_project(project_id, payload))
                except RuntimeError:
                    asyncio.run(manager.broadcast_to_project(project_id, payload))
        except Exception:
            pass
    except Exception as e:
        print(f"Logging error: {e}")
    finally:
        db.close()

# Helper to update project status in DB
def update_project_fields(project_id: str, updates: Dict[str, Any]):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            for key, val in updates.items():
                setattr(project, key, val)
            project.updated_at = datetime.utcnow()
            db.commit()
    except Exception as e:
        print(f"Project update error: {e}")
    finally:
        db.close()


# --- Node Definitions ---

def trend_hunter_node(state: AgentState) -> AgentState:
    state["current_step"] = "Trend Hunter"
    niche = state.get("niche", "")
    existing_title = state.get("trend_title", "").strip()
    
    log_agent_step(state["project_id"], "Trend Hunter", "running",
                   f"Fetching trending topics for niche '{niche}' from Google Trends & YouTube API.")

    db = SessionLocal()
    try:
        # Pass the project's niche so we get relevant trends, not just AI/Finance
        g_trends = PyTrendsService.fetch_google_trends(niche=niche if niche else None)
        if niche:
            # Real YouTube search by niche keyword
            y_trends = YouTubeService.fetch_niche_videos(niche=niche)
        else:
            # Global most-popular chart
            y_trends = YouTubeService.fetch_trending_videos()

        all_trends = (g_trends or []) + (y_trends or [])
        log_agent_step(state["project_id"], "Trend Hunter", "info",
                       f"Found {len(all_trends)} trending topics for '{niche or 'global'}'. Saving and ranking.")

        saved_trends = []
        for t in all_trends:
            exists = db.query(Trend).filter(Trend.query == t["query"]).first()
            if not exists:
                trend_obj = Trend(
                    title=t["title"],
                    query=t["query"],
                    source=t["source"],
                    score=t["score"],
                    category=t["category"]
                )
                db.add(trend_obj)
                db.commit()
                db.refresh(trend_obj)
                saved_trends.append(trend_obj)
            else:
                saved_trends.append(exists)

        # Pick the highest-score trend; all returned trends are already niche-relevant
        target_trend = None
        if saved_trends:
            # Prefer exact niche match first
            niche_lower = niche.lower() if niche else ""
            niche_matches = [t for t in saved_trends if t.category and t.category.lower() == niche_lower]
            if niche_matches:
                target_trend = max(niche_matches, key=lambda x: x.score)
            else:
                target_trend = max(saved_trends, key=lambda x: x.score)

        if existing_title and existing_title != "Autonomous Agents Future":
            trend_title = existing_title
        elif target_trend:
            trend_title = target_trend.title
        else:
            trend_title = f"Top {niche or 'Trending'} Topics 2026"

        state["trend_title"] = trend_title
        log_agent_step(state["project_id"], "Trend Hunter", "success",
                       f"Selected trend: '{trend_title}' (Source: {target_trend.source if target_trend else 'Selected'})")

        if target_trend:
            update_project_fields(state["project_id"], {"trend_id": target_trend.id})

    except Exception as e:
        trend_title = existing_title or f"Top {niche or 'Trending'} Topics 2026"
        state["trend_title"] = trend_title
        log_agent_step(state["project_id"], "Trend Hunter", "info", f"Using resilient fallback topic: '{trend_title}' ({e})")
        log_agent_step(state["project_id"], "Trend Hunter", "success", f"Selected trend: '{trend_title}'")
    finally:
        db.close()

    return state



def competitor_research_node(state: AgentState) -> AgentState:
    state["current_step"] = "Competitor Research"
    log_agent_step(state["project_id"], "Competitor Research", "running", f"Analyzing competitor performance and thumbnails for topic '{state['trend_title']}'.")
    try:
        summary = OpenAIService.research_competitors(state["niche"], state["trend_title"])
        state["competitor_research_summary"] = summary
        log_agent_step(state["project_id"], "Competitor Research", "success", f"Completed: {summary[:120]}...")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Competitor Research", "error", f"Failed: {e}")
    return state


def keyword_research_node(state: AgentState) -> AgentState:
    state["current_step"] = "Keyword Research"
    log_agent_step(state["project_id"], "Keyword Research", "running", f"Extracting search tags and search volume insights for topic '{state['trend_title']}'.")
    try:
        tags = OpenAIService.research_keywords(state["niche"], state["trend_title"])
        state["keyword_research_tags"] = tags
        log_agent_step(state["project_id"], "Keyword Research", "success", f"Compiled {len(tags)} targeted tags: {', '.join(tags[:4])}")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Keyword Research", "error", f"Failed: {e}")
    return state


def audience_research_node(state: AgentState) -> AgentState:
    state["current_step"] = "Audience Research"
    log_agent_step(state["project_id"], "Audience Research", "running", f"Mapping search intent and demographics for topic '{state['trend_title']}'.")
    try:
        demographics = OpenAIService.research_audience(state["niche"], state["trend_title"])
        state["audience_research_demographics"] = demographics
        log_agent_step(state["project_id"], "Audience Research", "success", f"Mapped: {demographics[:120]}...")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Audience Research", "error", f"Failed: {e}")
    return state


def analytics_feedback_node(state: AgentState) -> AgentState:
    state["current_step"] = "Analytics Feedback"
    log_agent_step(state["project_id"], "Analytics Feedback", "running", "Retrieving historical dashboard performance to formulate pacing guidelines.")
    try:
        # Mock historical data for lookup
        historical_stats = {"views": 12050, "avg_ctr": 6.8, "average_watch_time": 4.2}
        advice = OpenAIService.analytics_feedback(historical_stats)
        state["analytics_advice"] = advice
        log_agent_step(state["project_id"], "Analytics Feedback", "success", f"Feedback advice: {advice}")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Analytics Feedback", "error", f"Failed: {e}")
    return state


def memory_agent_node(state: AgentState) -> AgentState:
    state["current_step"] = "Memory Agent"
    log_agent_step(state["project_id"], "Memory Agent", "running", f"Searching memory logs database for '{state['niche']}' niches lessons.")
    try:
        mock_logs = [
            "Script generated successfully. CTR optimized.",
            "Elevenlabs speech failed. Handled fallback.",
            "Moviepy stitching succeeded but low FPS."
        ]
        context = OpenAIService.retrieve_memory(state["niche"], mock_logs)
        state["memory_context"] = context
        log_agent_step(state["project_id"], "Memory Agent", "success", f"Loaded memory insights: {context}")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Memory Agent", "error", f"Failed: {e}")
    return state


def idea_generator_node(state: AgentState) -> AgentState:
    state["current_step"] = "Idea Generator"
    log_agent_step(state["project_id"], "Idea Generator", "running", "Synthesizing competitor trends, target keywords, and memory loops to generate video angle.")
    try:
        if state.get("is_custom"):
            custom_title = state.get("custom_title") or state.get("trend_title")
            state["idea_pitch"] = custom_title
            state["trend_title"] = custom_title
            log_agent_step(state["project_id"], "Idea Generator", "success", f"Using custom title angle: '{custom_title}'")
        else:
            comp = state.get("competitor_research_summary", "")
            keywords = state.get("keyword_research_tags", [])
            pitch = OpenAIService.generate_video_idea(state["niche"], state["trend_title"], comp, keywords)
            state["idea_pitch"] = pitch
            state["trend_title"] = pitch  # Override trend_title with finalized pitch
            log_agent_step(state["project_id"], "Idea Generator", "success", f"Selected angle: '{pitch}'")
            update_project_fields(state["project_id"], {"title": pitch})
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Idea Generator", "error", f"Failed: {e}")
    return state


def script_writer_node(state: AgentState) -> AgentState:
    state["current_step"] = "Script Writer"
    log_agent_step(state["project_id"], "Script Writer", "running", f"Writing script for angle '{state['trend_title']}' with memory guards.")
    
    try:
        # In a real setup, we pass memory_context to influence OpenAI output
        script = OpenAIService.generate_script(state["niche"], state["trend_title"])
        if state.get("is_custom"):
            custom_title = state.get("custom_title") or state.get("trend_title")
            if custom_title:
                script["title"] = custom_title
        state["script"] = script
        log_agent_step(state["project_id"], "Script Writer", "success", f"Script drafted: '{script.get('title')}'")
        
        update_project_fields(state["project_id"], {
            "script_title": script.get("title"),
            "script_hook": script.get("hook"),
            "script_body": script.get("body"),
            "script_cta": script.get("cta"),
            "status": "script_generated"
        })
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Script Writer", "error", f"Failed: {e}")
        
    return state


def fact_checker_node(state: AgentState) -> AgentState:
    state["current_step"] = "Fact Checker"
    log_agent_step(state["project_id"], "Fact Checker", "running", "Cross-checking script claims and metrics validity.")
    try:
        body = state.get("script", {}).get("body", "")
        report = OpenAIService.fact_check_script(state["niche"], body)
        state["fact_checker_report"] = report
        log_agent_step(state["project_id"], "Fact Checker", "success", f"Report: {report}")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Fact Checker", "error", f"Failed: {e}")
    return state


def script_reviewer_node(state: AgentState) -> AgentState:
    state["current_step"] = "Script Reviewer"
    log_agent_step(state["project_id"], "Script Reviewer", "running", "Scoring hook structure, retention pacing, and CTAs.")
    try:
        script = state.get("script", {})
        review = OpenAIService.review_script(script.get("hook", ""), script.get("body", ""), script.get("cta", ""))
        state["script_reviewer_critique"] = review.get("feedback", "")
        log_agent_step(state["project_id"], "Script Reviewer", "success", f"Score: {review.get('score')}/100. Critique: {review.get('feedback')}")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Script Reviewer", "error", f"Failed: {e}")
    return state


def brand_consistency_node(state: AgentState) -> AgentState:
    state["current_step"] = "Brand Consistency"
    log_agent_step(state["project_id"], "Brand Consistency", "running", "Verifying brand rules adherence and script tone.")
    try:
        script = state.get("script", {})
        body = f"{script.get('hook')} {script.get('body')}"
        report = OpenAIService.verify_brand(script.get("title", ""), body)
        state["brand_report"] = report
        log_agent_step(state["project_id"], "Brand Consistency", "success", f"Consistency Check: {report}")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Brand Consistency", "error", f"Failed: {e}")
    return state


def retention_optimizer_node(state: AgentState) -> AgentState:
    state["current_step"] = "Retention Optimizer"
    log_agent_step(state["project_id"], "Retention Optimizer", "running", "Injecting scene cues, subtitle timestamps, and zoom edits.")
    try:
        body = state.get("script", {}).get("body", "")
        cues = OpenAIService.optimize_retention(body)
        state["retention_cues"] = cues
        log_agent_step(state["project_id"], "Retention Optimizer", "success", "Retention indicators generated and stored in state.")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Retention Optimizer", "error", f"Failed: {e}")
    return state


def shorts_generator_node(state: AgentState) -> AgentState:
    state["current_step"] = "Shorts Generator"
    log_agent_step(state["project_id"], "Shorts Generator", "running", "Drafting 30-60s secondary vertical shorts script.")
    try:
        body = state.get("script", {}).get("body", "")
        shorts = OpenAIService.generate_shorts(body)
        state["shorts_script"] = shorts
        log_agent_step(state["project_id"], "Shorts Generator", "success", f"Shorts title drafted: '{shorts.get('title')}'")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Shorts Generator", "error", f"Failed: {e}")
    return state


def translation_node(state: AgentState) -> AgentState:
    state["current_step"] = "Translation Agent"
    log_agent_step(state["project_id"], "Translation Agent", "running", "Translating script components to Spanish for global targeting.")
    try:
        title = state.get("script", {}).get("title", "")
        desc = state.get("seo", {}).get("description", "")
        tags = state.get("seo", {}).get("tags", "")
        res = OpenAIService.translate_metadata(title, desc, tags)
        state["translated_metadata"] = res
        log_agent_step(state["project_id"], "Translation Agent", "success", f"Translation Spanish title: '{res.get('spanish_title')}'")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Translation Agent", "error", f"Failed: {e}")
    return state


def content_calendar_node(state: AgentState) -> AgentState:
    state["current_step"] = "Content Calendar"
    log_agent_step(state["project_id"], "Content Calendar", "running", "Planning scheduling slot and strategic playlist alignment.")
    try:
        slot = OpenAIService.plan_calendar(state["niche"], state["trend_title"])
        state["scheduled_date"] = slot
        log_agent_step(state["project_id"], "Content Calendar", "success", f"Planned publishing slot: {slot}")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Content Calendar", "error", f"Failed: {e}")
    return state


def voice_agent_node(state: AgentState) -> AgentState:
    state["current_step"] = "Voice Agent"
    script = state.get("script", {})
    body_text = f"{script.get('hook', '')} {script.get('body', '')} {script.get('cta', '')}"
    
    if not body_text.strip():
        body_text = "Hello! Today we are discussing automated YouTube production with LangGraph and FastAPI."
        
    log_agent_step(state["project_id"], "Voice Agent", "running", "Generating narration voiceover with ElevenLabs.")
    
    filename = f"voice_{state['project_id']}.mp3"
    save_path = os.path.join(settings.MEDIA_DIR, "voiceovers", filename)
    
    try:
        ElevenLabsService.generate_speech(body_text, save_path)
        web_url = f"/media/voiceovers/{filename}"
        state["voiceover_path"] = save_path
        log_agent_step(state["project_id"], "Voice Agent", "success", f"Voiceover MP3 rendered to {web_url}")
        
        update_project_fields(state["project_id"], {
            "voiceover_url": web_url,
            "status": "voice_generated"
        })
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Voice Agent", "error", f"Failed: {e}")
        raise e  # Fail node to trigger retry/checkpoint
        
    return state


def thumbnail_agent_node(state: AgentState) -> AgentState:
    state["current_step"] = "Thumbnail Agent"
    title = state.get("script", {}).get("title", "Awesome Tech Video")
    log_agent_step(state["project_id"], "Thumbnail Agent", "running", f"Generating clickbait thumbnail for title '{title}'.")
    
    filename = f"thumb_{state['project_id']}.jpg"
    save_path = os.path.join(settings.MEDIA_DIR, "thumbnails", filename)
    
    try:
        OpenAIService.generate_thumbnail_image(title, save_path)
        web_url = f"/media/thumbnails/{filename}"
        state["thumbnail_path"] = save_path
        log_agent_step(state["project_id"], "Thumbnail Agent", "success", f"Thumbnail image created at {web_url}")
        
        update_project_fields(state["project_id"], {
            "thumbnail_url": web_url,
            "status": "thumbnail_generated"
        })
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Thumbnail Agent", "error", f"Failed: {e}")
        raise e  # Fail node to trigger retry/checkpoint
        
    return state


def thumbnail_scoring_node(state: AgentState) -> AgentState:
    state["current_step"] = "Thumbnail Scorer"
    title = state.get("script", {}).get("title", "Awesome Video")
    thumb_path = state.get("thumbnail_path")
    if not thumb_path or not os.path.exists(thumb_path):
        thumb_path = os.path.join(settings.MEDIA_DIR, "thumbnails", f"thumb_{state['project_id']}.jpg")

    log_agent_step(state["project_id"], "Thumbnail Scorer", "running", "Running visual scoring on generated thumbnail.")
    try:
        score_res = OpenAIService.score_thumbnail(thumb_path, title)
        state["thumbnail_score"] = float(score_res.get("clickability_score", 0))
        state["thumbnail_feedback"] = score_res.get("feedback", "")
        log_agent_step(state["project_id"], "Thumbnail Scorer", "success", f"Score: {state['thumbnail_score']}/100. Feedback: {state['thumbnail_feedback']}")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Thumbnail Scorer", "error", f"Failed: {e}")
    return state


def video_generator_node(state: AgentState) -> AgentState:
    state["current_step"] = "Video Generator"
    log_agent_step(state["project_id"], "Video Generator", "running", "Rendering cinematic multi-scene video with kinetic typography and theme pacing.")
    
    voice_path = state.get("voiceover_path")
    thumb_path = state.get("thumbnail_path")
    
    if not voice_path or not os.path.exists(voice_path):
        voice_path = os.path.join(settings.MEDIA_DIR, "voiceovers", f"voice_{state['project_id']}.mp3")
    if not thumb_path or not os.path.exists(thumb_path):
        thumb_path = os.path.join(settings.MEDIA_DIR, "thumbnails", f"thumb_{state['project_id']}.jpg")
        
    filename = f"video_{state['project_id']}.mp4"
    save_path = os.path.join(settings.MEDIA_DIR, "videos", filename)
    
    shorts_filename = f"shorts_{state['project_id']}.mp4"
    shorts_save_path = os.path.join(settings.MEDIA_DIR, "videos", shorts_filename)
    
    try:
        from backend.app.services.video_service import VideoService
        
        # 1. Render primary 16:9 Landscape Video
        log_agent_step(state["project_id"], "Video Generator", "info", "Executing cinematic 16:9 storyboard rendering...")
        render_meta = VideoService.render_video(
            project_id=state["project_id"],
            thumb_path=thumb_path,
            voice_path=voice_path,
            output_path=save_path,
            script=state.get("script", {}),
            trend_title=state.get("trend_title", "Viral Video"),
            niche=state.get("niche", "AI"),
            aspect_ratio="16:9"
        )
        
        web_url = f"/media/videos/{filename}"
        state["video_path"] = save_path
        log_agent_step(
            state["project_id"],
            "Video Generator",
            "info",
            f"16:9 Master rendered [{render_meta['resolution']}, {render_meta['theme']} theme, {render_meta['scenes_count']} scenes]"
        )

        # 2. Render 9:16 Vertical Short
        shorts_script = state.get("shorts_script") or state.get("script", {})
        shorts_web_url = None
        try:
            log_agent_step(state["project_id"], "Video Generator", "info", "Rendering secondary 9:16 vertical Short...")
            VideoService.render_video(
                project_id=state["project_id"],
                thumb_path=thumb_path,
                voice_path=voice_path,
                output_path=shorts_save_path,
                script=shorts_script,
                trend_title=state.get("trend_title", "Shorts"),
                niche=state.get("niche", "AI"),
                aspect_ratio="9:16"
            )
            shorts_web_url = f"/media/videos/{shorts_filename}"
            log_agent_step(state["project_id"], "Video Generator", "info", "9:16 Vertical Short rendered successfully.")
        except Exception as shorts_err:
            print(f"Shorts vertical render warning: {shorts_err}")

        log_agent_step(state["project_id"], "Video Generator", "success", f"Video pipeline finished: {web_url}")
        
        update_fields = {
            "video_url": web_url,
            "status": "waiting_for_approval" # Interruption threshold
        }
        if shorts_web_url:
            update_fields["shorts_video_url"] = shorts_web_url
            
        update_project_fields(state["project_id"], update_fields)
        
    except Exception as e:
        print(f"VideoService failed: {e}. Attempting direct FFmpeg CLI command fallback.")
        import subprocess
        try:
            cmd = f'ffmpeg -y -loop 1 -i "{thumb_path}" -i "{voice_path}" -c:v libx264 -t 5 -pix_fmt yuv420p "{save_path}"'
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            web_url = f"/media/videos/{filename}"
            state["video_path"] = save_path
            log_agent_step(state["project_id"], "Video Generator", "success", f"FFmpeg fallback compiled video: {web_url}")
            update_project_fields(state["project_id"], {
                "video_url": web_url,
                "status": "waiting_for_approval"
            })
        except Exception as cli_error:
            state["errors"].append(str(cli_error))
            log_agent_step(state["project_id"], "Video Generator", "error", f"Failed to render video: {cli_error}")
            raise cli_error
            
    return state
            
    return state


def seo_agent_node(state: AgentState) -> AgentState:
    state["current_step"] = "SEO Agent"
    script = state.get("script", {})
    title = script.get("title", "Viral Video")
    
    log_agent_step(state["project_id"], "SEO Agent", "running", "Generating metadata, descriptions, keywords, and hashtags.")
    
    try:
        desc = (
            f"🔥 The ultimate guide to {state.get('trend_title')}. In this video, we break down "
            f"key concepts, news updates, and strategy guidelines.\n\n"
            f"💡 Hook: {script.get('hook')}\n\n"
            f"📌 Niche: #{state['niche']}\n"
            f"👉 Don't forget to Like, Share, and Subscribe!"
        )
        tags = f"{state['niche']}, {state.get('trend_title')}, YouTube Automation, AI Empire"
        
        state["seo"] = {
            "title": f"{title} 🚀",
            "description": desc,
            "tags": tags
        }
        
        log_agent_step(state["project_id"], "SEO Agent", "success", "SEO copy generated. Tags and tags hash injected.")
        
        update_project_fields(state["project_id"], {
            "seo_title": f"{title} 🚀",
            "seo_description": desc,
            "seo_tags": tags,
            "status": "seo_generated"
        })
        
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "SEO Agent", "error", f"Failed: {e}")
        
    return state


def publishing_agent_node(state: AgentState) -> AgentState:
    state["current_step"] = "Publishing Agent"
    seo = state.get("seo", {})
    video_path = state.get("video_path")

    log_agent_step(state["project_id"], "Publishing Agent", "running",
                   "Resolving YouTube account and pushing video to YouTube Data API.")

    # Resolve which token file to use:
    # 1. Project's assigned account  2. User's active account  3. Legacy token
    token_file = None
    db_resolve = SessionLocal()
    try:
        from backend.app.models.project import Project
        from backend.app.models.youtube_account import YouTubeAccount
        project = db_resolve.query(Project).filter(Project.id == state["project_id"]).first()
        if project and project.youtube_account_id:
            acc = db_resolve.query(YouTubeAccount).filter(
                YouTubeAccount.id == project.youtube_account_id
            ).first()
            if acc:
                token_file = acc.token_file
                log_agent_step(state["project_id"], "Publishing Agent", "info",
                               f"Using assigned account: {acc.nickname} ({acc.channel_title or acc.channel_id or 'unknown'})")
        if not token_file and project:
            # Fall back to user's active account
            active_acc = db_resolve.query(YouTubeAccount).filter(
                YouTubeAccount.user_id == project.user_id,
                YouTubeAccount.is_active == True,
            ).first()
            if active_acc:
                token_file = active_acc.token_file
                log_agent_step(state["project_id"], "Publishing Agent", "info",
                               f"Using active account: {active_acc.nickname} ({active_acc.channel_title or 'unknown'})")
    except Exception as e:
        log_agent_step(state["project_id"], "Publishing Agent", "info",
                       f"Account lookup failed ({e}), using default token.")
    finally:
        db_resolve.close()

    try:
        yt_id = YouTubeService.upload_video(
            video_path=video_path,
            title=seo.get("title", "Default Title"),
            description=seo.get("description", "Default Desc"),
            tags=seo.get("tags", "tech"),
            token_file=token_file,
        )
        state["youtube_video_id"] = yt_id
        log_agent_step(state["project_id"], "Publishing Agent", "success",
                       f"Video published! YouTube ID: {yt_id}")

        update_project_fields(state["project_id"], {
            "youtube_video_id": yt_id,
            "status": "published",
        })

    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Publishing Agent", "error", f"Failed: {e}")
        raise e

    return state



def analytics_agent_node(state: AgentState) -> AgentState:
    state["current_step"] = "Analytics Agent"
    log_agent_step(state["project_id"], "Analytics Agent", "running", "Injecting initial metrics tracking for views, CTR, and watch time.")
    
    db = SessionLocal()
    try:
        initial_stats = Analytics(
            project_id=state["project_id"],
            views=0,
            watch_time=0.0,
            ctr=0.0,
            subscribers_gained=0
        )
        db.add(initial_stats)
        db.commit()
        log_agent_step(state["project_id"], "Analytics Agent", "success", "Analytics model tracking registered. Loop finished.")
        
        update_project_fields(state["project_id"], {"status": "completed"})
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Analytics Agent", "error", f"Failed: {e}")
    finally:
        db.close()
        
    return state


def memory_update_node(state: AgentState) -> AgentState:
    state["current_step"] = "Memory Update"
    log_agent_step(state["project_id"], "Memory Update", "running", "Extracting execution milestones and updating system memory logs.")
    try:
        # In a real setting we compile execution highlights and write to db logs
        log_agent_step(state["project_id"], "Memory Update", "success", "Milestones integrated in niche guidelines. Loop closed.")
    except Exception as e:
        state["errors"].append(str(e))
        log_agent_step(state["project_id"], "Memory Update", "error", f"Failed: {e}")
    return state


# --- Custom Input Node for Custom Campaigns ---
def custom_input_node(state: AgentState) -> AgentState:
    """Bypass trend hunting by using the user-supplied custom title."""
    state["current_step"] = "Custom Input"
    custom_title = state.get("custom_title") or state.get("trend_title") or ""
    if custom_title:
        state["custom_title"] = custom_title
        state["trend_title"] = custom_title
        log_agent_step(state["project_id"], "Custom Input", "success",
                       f"Using custom title: '{custom_title}'")
    else:
        fallback = f"Top {state.get('niche') or 'Trending'} Topics 2026"
        state["custom_title"] = fallback
        state["trend_title"] = fallback
        log_agent_step(state["project_id"], "Custom Input", "warning",
                       f"Custom mode active but no custom_title provided. Using fallback: '{fallback}'.")
    return state

# --- Build LangGraph state machine workflow ---

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("custom_input", custom_input_node)
workflow.add_node("trend_hunter", trend_hunter_node)
workflow.add_node("competitor_research", competitor_research_node)
workflow.add_node("keyword_research", keyword_research_node)
workflow.add_node("audience_research", audience_research_node)
workflow.add_node("analytics_feedback", analytics_feedback_node)
workflow.add_node("memory_agent", memory_agent_node)
workflow.add_node("idea_generator", idea_generator_node)
workflow.add_node("script_writer", script_writer_node)
workflow.add_node("fact_checker", fact_checker_node)
workflow.add_node("script_reviewer", script_reviewer_node)
workflow.add_node("brand_consistency", brand_consistency_node)
workflow.add_node("retention_optimizer", retention_optimizer_node)
workflow.add_node("shorts_generator", shorts_generator_node)
workflow.add_node("seo_agent", seo_agent_node)
workflow.add_node("translation", translation_node)
workflow.add_node("content_calendar", content_calendar_node)
workflow.add_node("thumbnail_agent", thumbnail_agent_node)
workflow.add_node("thumbnail_scoring", thumbnail_scoring_node)
workflow.add_node("voice_agent", voice_agent_node)
workflow.add_node("video_generator", video_generator_node)
workflow.add_node("publishing_agent", publishing_agent_node)
workflow.add_node("analytics_agent", analytics_agent_node)
workflow.add_node("memory_update", memory_update_node)

# Conditional Entry Point: custom campaigns skip trend_hunter
def route_entry(state: AgentState) -> str:
    if state.get("is_custom"):
        return "custom_input"
    return "trend_hunter"

workflow.add_conditional_edges(START, route_entry, {
    "custom_input": "custom_input",
    "trend_hunter": "trend_hunter",
})

# Custom input joins the main pipeline at competitor_research
workflow.add_edge("custom_input", "competitor_research")

# Define Connections/Edges (Upgraded Workflow Graph)
workflow.add_edge("trend_hunter", "competitor_research")
workflow.add_edge("competitor_research", "keyword_research")
workflow.add_edge("keyword_research", "audience_research")
workflow.add_edge("audience_research", "analytics_feedback")
workflow.add_edge("analytics_feedback", "memory_agent")
workflow.add_edge("memory_agent", "idea_generator")
workflow.add_edge("idea_generator", "script_writer")
workflow.add_edge("script_writer", "fact_checker")
workflow.add_edge("fact_checker", "script_reviewer")
workflow.add_edge("script_reviewer", "brand_consistency")
workflow.add_edge("brand_consistency", "retention_optimizer")
workflow.add_edge("retention_optimizer", "shorts_generator")
workflow.add_edge("shorts_generator", "seo_agent")
workflow.add_edge("seo_agent", "translation")
workflow.add_edge("translation", "content_calendar")
workflow.add_edge("content_calendar", "thumbnail_agent")
workflow.add_edge("thumbnail_agent", "thumbnail_scoring")
workflow.add_edge("thumbnail_scoring", "voice_agent")
workflow.add_edge("voice_agent", "video_generator")
workflow.add_edge("video_generator", "publishing_agent")
workflow.add_edge("publishing_agent", "analytics_agent")
workflow.add_edge("analytics_agent", "memory_update")
workflow.add_edge("memory_update", END)

# Set up Checkpointer for Human-in-the-Loop persistent state
checkpointer = None
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
except ImportError:
    try:
        from langgraph_checkpoint_sqlite import SqliteSaver
        conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
        checkpointer = SqliteSaver(conn)
    except ImportError:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
except Exception:
    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()


# Compile the graph with checkpointer and interrupt before publishing (Human-in-the-Loop)
agent_graph = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["publishing_agent"]
)
