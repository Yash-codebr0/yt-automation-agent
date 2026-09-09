from backend.app.core.celery_app import celery_app
from backend.app.core.database import SessionLocal
from backend.app.models.project import Project
from backend.app.models.trend import Trend
from backend.app.models.log import AgentLog
from backend.app.models.analytics import Analytics
from backend.app.agents.graph import agent_graph, log_agent_step
from backend.app.services.pytrends_service import PyTrendsService
from backend.app.services.youtube_service import YouTubeService

@celery_app.task(name="tasks.hunt_trends")
def hunt_trends_task(niche: str | None = None):
    """Celery task running trend harvesting.

    When `niche` is provided:
      - Google Trends via interest_over_time() for real search-volume data
      - YouTube via search.list(q=niche) for real niche-specific videos
    Without niche: global most-popular harvest from both sources.
    """
    db = SessionLocal()
    try:
        niche_label = f"'{niche}' niche" if niche else "global multi-niche"
        print(f"Celery Worker starting trend hunting for {niche_label}...")

        g_trends = PyTrendsService.fetch_google_trends(niche=niche)

        if niche:
            # Real YouTube search for this niche
            y_trends = YouTubeService.fetch_niche_videos(niche=niche)
        else:
            # Global most-popular chart
            y_trends = YouTubeService.fetch_trending_videos()

        all_trends = g_trends + y_trends

        saved_count = 0
        for t in all_trends:
            exists = db.query(Trend).filter(Trend.query == t["query"]).first()
            if not exists:
                trend_obj = Trend(
                    title=t["title"],
                    query=t["query"],
                    source=t["source"],
                    score=t["score"],
                    category=t["category"],
                )
                db.add(trend_obj)
                saved_count += 1

        db.commit()
        print(f"Trend hunting finished for {niche_label}. Added {saved_count} new trends.")
        return {"status": "success", "new_trends": saved_count, "niche": niche}
    except Exception as e:
        print(f"Trend hunting failed: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name="tasks.run_project_workflow")
def run_project_workflow_task(project_id: str):
    """Celery task executing the multi-agent YouTube creation graph."""
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            print(f"Workflow Task: Project {project_id} not found in database.")
            return {"status": "error", "message": "Project not found"}
            
        is_custom = bool(getattr(project, "is_custom", False) or (project.trend_id is None))
        custom_title = getattr(project, "custom_title", None) or project.title or ""
        
        # For custom campaigns, use the custom title as trend_title
        if is_custom and custom_title:
            trend_title = custom_title
        elif project.trend:
            trend_title = project.trend.title
        else:
            trend_title = project.title or "Autonomous Agents Future"
        
        print(f"Celery worker running multi-agent workflow for project {project_id}...")
        log_agent_step(project_id, "System", "running", "LangGraph multi-agent execution pipeline active.")
        
        config = {"configurable": {"thread_id": project_id}}
        
        # Check if a checkpoint exists for this thread
        state_info = agent_graph.get_state(config)
        if state_info and state_info.next:
            print(f"Resuming project {project_id} from checkpoint: {state_info.next}")
            log_agent_step(project_id, "System", "info", f"Resuming workflow from checkpoint at step: {', '.join(state_info.next)}")
            
            # Resume execution
            final_state = agent_graph.invoke(None, config=config)
        else:
            print(f"Starting project {project_id} from entrypoint.")
            # Prepare LangGraph Initial State with new agent keys
            initial_state = {
                "project_id": project_id,
                "niche": project.niche,
                "trend_title": trend_title,
                "is_custom": is_custom,
                "custom_title": custom_title,
                
                # Phase 2 AI Agent outputs placeholder defaults
                "competitor_research_summary": "",
                "keyword_research_tags": [],
                "audience_research_demographics": "",
                "idea_pitch": "",
                "fact_checker_report": "",
                "script_reviewer_critique": "",
                "brand_report": "",
                "retention_cues": "",
                "shorts_script": {},
                "translated_metadata": {},
                "scheduled_date": "",
                "analytics_advice": "",
                "memory_context": "",
                "thumbnail_score": 0.0,
                "thumbnail_feedback": "",

                "script": {
                    "title": project.script_title or "",
                    "hook": project.script_hook or "",
                    "body": project.script_body or "",
                    "cta": project.script_cta or ""
                },
                "voiceover_path": project.voiceover_url or "",
                "thumbnail_path": project.thumbnail_url or "",
                "video_path": project.video_url or "",
                "seo": {
                    "title": project.seo_title or "",
                    "description": project.seo_description or "",
                    "tags": project.seo_tags or ""
                },
                "youtube_video_id": project.youtube_video_id or "",
                "errors": [],
                "current_step": "init"
            }
            # Invoke LangGraph from scratch
            final_state = agent_graph.invoke(initial_state, config=config)
        
        # Check current state again after invocation
        current_state_info = agent_graph.get_state(config)
        if current_state_info and current_state_info.next:
            # The graph was interrupted (Human-in-the-loop approval step)
            print(f"Workflow interrupted. Next step: {current_state_info.next}")
            log_agent_step(project_id, "System", "info", f"Workflow paused. Waiting for human approval before publishing.")
            project.status = "waiting_for_approval"
        elif final_state.get("errors"):
            print(f"Workflow completed with errors: {final_state['errors']}")
            log_agent_step(project_id, "System", "error", f"Workflow execution finished with issues: {', '.join(final_state['errors'])}")
            project.status = "failed"
        else:
            print("Workflow execution succeeded.")
            log_agent_step(project_id, "System", "success", "LangGraph workflow completed successfully. Assets are ready.")
            project.status = "completed"
            
        db.commit()
        return {"status": "success", "errors": final_state.get("errors", [])}
        
    except Exception as e:
        print(f"Celery task run error: {e}")
        log_agent_step(project_id, "System", "error", f"Pipeline fatal exception: {e}")
        
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = "failed"
            db.commit()
            
        return {"status": "error", "message": str(e)}
    finally:
        from backend.app.core.redis_lock import release_project_lock
        release_project_lock(project_id)
        db.close()

@celery_app.task(name="tasks.sync_youtube_analytics")
def sync_youtube_analytics_task():
    """Celery Beat task: daily YouTube analytics sync for all published projects."""
    import datetime
    db = SessionLocal()
    synced = 0
    errors = 0
    try:
        print("Starting daily YouTube analytics sync...")
        # Fetch all published projects that have a YouTube video ID
        published_projects = (
            db.query(Project)
            .filter(Project.status == "published")
            .filter(Project.youtube_video_id.isnot(None))
            .all()
        )
        print(f"Found {len(published_projects)} published projects to sync.")

        for project in published_projects:
            try:
                metrics = YouTubeService.fetch_video_analytics(project.youtube_video_id)
                record = Analytics(
                    project_id=project.id,
                    views=metrics.get("views", 0),
                    watch_time=metrics.get("watch_time", 0.0),
                    ctr=metrics.get("ctr", 0.0),
                    subscribers_gained=metrics.get("subscribers_gained", 0),
                    revenue=metrics.get("revenue", 0.0),
                    retention_rate=metrics.get("retention_rate", 0.0),
                    recorded_at=datetime.datetime.utcnow()
                )
                db.add(record)
                synced += 1
            except Exception as project_error:
                print(f"Analytics sync failed for project {project.id}: {project_error}")
                errors += 1
                continue

        db.commit()
        print(f"Daily analytics sync complete. Synced={synced}, Errors={errors}.")
        return {"status": "success", "synced": synced, "errors": errors}
    except Exception as e:
        db.rollback()
        print(f"Daily analytics sync fatal error: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
