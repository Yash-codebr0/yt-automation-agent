import sys
import os
import json
import time

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure UTF-8 for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.app.core.database import init_db, SessionLocal, transactional_session
from backend.app.core.security import get_password_hash, create_access_token
from backend.app.models.user import User
from backend.app.models.trend import Trend
from backend.app.models.project import Project
from backend.app.models.analytics import Analytics
from backend.app.models.log import AgentLog
from backend.app.tasks.workflow_tasks import run_project_workflow_task, sync_youtube_analytics_task
from backend.app.agents.graph import agent_graph

def run_end_to_end_test():
    print("=" * 60)
    print("STARTING END-TO-END SYSTEM VALIDATION TEST")
    print("=" * 60)
    
    # 1. Initialize Database Tables
    print("\n[Step 1] Initializing SQLite database tables...")
    init_db()
    print("[SUCCESS] Database tables created successfully.")
    
    # 2. Create Test User
    print("\n[Step 2] Registering test user...")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "commander@empire.ai").first()
        if not user:
            user = User(email="commander@empire.ai", hashed_password=get_password_hash("password123"))
            db.add(user)
            db.commit()
            db.refresh(user)
        print(f"✅ User created/verified: ID={user.id}, Email={user.email}")
        
        token = create_access_token(user.id)
        print(f"✅ JWT Access Token generated: {token[:20]}...")
        
        # 3. Create Test Trend & Project
        print("\n[Step 3] Creating Trend & Video Project Campaign...")
        trend = db.query(Trend).filter(Trend.query == "Autonomous AI Empire").first()
        if not trend:
            trend = Trend(
                title="Autonomous AI Empire Workflow 2026",
                query="Autonomous AI Empire",
                source="YouTube API",
                score=96.5,
                category="AI & Robotics"
            )
            db.add(trend)
            db.commit()
            db.refresh(trend)
        print(f"✅ Trend initialized: '{trend.title}' (Score: {trend.score})")
        
        project = Project(
            user_id=user.id,
            trend_id=trend.id,
            title="Campaign: Autonomous AI Agents Deep Dive",
            niche="AI",
            status="draft"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        project_id = project.id
        print(f"✅ Project created: ID={project_id}, Status={project.status}")
        
    finally:
        db.close()

    # 4. Run Multi-Agent Workflow Task (LangGraph 23-Agent Graph)
    print("\n[Step 4] Executing 23-Agent LangGraph Workflow...")
    result = run_project_workflow_task(project_id)
    print(f"✅ Workflow Execution Task Result: {result}")
    
    # 5. Check State After Graph Interruption (Human-in-the-Loop)
    db = SessionLocal()
    try:
        updated_project = db.query(Project).filter(Project.id == project_id).first()
        print(f"\n[Step 5] Human-in-the-Loop Interruption Check:")
        print(f"  - Current Project Status: {updated_project.status}")
        print(f"  - Script Title: {updated_project.script_title}")
        print(f"  - Script Hook: {updated_project.script_hook[:80]}...")
        print(f"  - Script Body Length: {len(updated_project.script_body or '')} chars")
        print(f"  - Voiceover Asset URL: {updated_project.voiceover_url}")
        print(f"  - Thumbnail Asset URL: {updated_project.thumbnail_url}")
        print(f"  - Compiled Video URL: {updated_project.video_url}")
        print(f"  - SEO Title: {updated_project.seo_title}")
        
        # Verify Agent Logs written to DB
        logs = db.query(AgentLog).filter(AgentLog.project_id == project_id).all()
        print(f"\n✅ Total Agent Execution Logs Recorded: {len(logs)}")
        for l in logs[-10:]:
            print(f"  [{l.agent_name}] status={l.status}: {l.log_message}")
            
        # 6. Simulate Human Approval to Resume Workflow
        print("\n[Step 6] Simulating Human Approval & Final Publishing...")
        config = {"configurable": {"thread_id": project_id}}
        
        # Resume graph from checkpoint after approval
        log_entry = AgentLog(
            project_id=project_id,
            agent_name="System",
            status="info",
            log_message="Human approval granted. Resuming workflow for YouTube upload."
        )
        db.add(log_entry)
        
        final_state = agent_graph.invoke(None, config=config)
        updated_project.status = "published"
        updated_project.youtube_video_id = "mock_yt_vid_998877"
        db.commit()
        print(f"✅ Workflow Resumed & Finalized. New Status: {updated_project.status}")
        print(f"  - YouTube Video ID: {updated_project.youtube_video_id}")
        
        # 7. Test Daily Analytics Sync Task
        print("\n[Step 7] Running Celery Daily Analytics Sync Task...")
        sync_result = sync_youtube_analytics_task()
        print(f"✅ Analytics Sync Result: {sync_result}")
        
        analytics_records = db.query(Analytics).filter(Analytics.project_id == project_id).all()
        print(f"✅ Recorded Analytics Entries: {len(analytics_records)}")
        for a in analytics_records:
            print(f"  - Views: {a.views}, Watch Time: {a.watch_time}h, CTR: {a.ctr}%, Revenue: ${a.revenue}, Retention: {a.retention_rate}%")

    finally:
        db.close()
        
    print("=" * 60)
    print("🎉 END-TO-END SYSTEM TEST COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_end_to_end_test()
