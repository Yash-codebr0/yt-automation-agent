"""
Migration: Add youtube_accounts table and youtube_account_id to projects.
Run from the project root: python scripts/migrate_youtube_accounts.py
"""
import sys
import os
import sqlite3

# Resolve DB path from .env or default
db_path = "youtube_empire.db"
if os.path.exists(".env"):
    for line in open(".env"):
        if line.startswith("DATABASE_URL="):
            val = line.split("=", 1)[1].strip().replace("sqlite:///", "").replace("./", "")
            if val:
                db_path = val
            break

print(f"Migrating database: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Create youtube_accounts table
cursor.execute("""
CREATE TABLE IF NOT EXISTS youtube_accounts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    nickname TEXT NOT NULL DEFAULT 'My Channel',
    channel_id TEXT,
    channel_title TEXT,
    channel_thumbnail TEXT,
    token_file TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0,
    connected_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
print("  [OK] youtube_accounts table created (or already exists).")

# 2. Add youtube_account_id column to projects if missing
cursor.execute("PRAGMA table_info(projects)")
cols = [row[1] for row in cursor.fetchall()]
if "youtube_account_id" not in cols:
    cursor.execute("""
        ALTER TABLE projects ADD COLUMN youtube_account_id TEXT REFERENCES youtube_accounts(id)
    """)
    print("  [OK] Added youtube_account_id column to projects.")
else:
    print("  [OK] youtube_account_id already exists in projects.")

# 3. Migrate existing youtube_token.json into a youtube_accounts row
legacy_token = os.path.join("media", "youtube_token.json")
if os.path.exists(legacy_token):
    cursor.execute("SELECT id FROM users LIMIT 1")
    row = cursor.fetchone()
    if row:
        user_id = row[0]
        cursor.execute("SELECT id FROM youtube_accounts WHERE token_file = ?", (legacy_token,))
        if not cursor.fetchone():
            import uuid, shutil
            acc_id = str(uuid.uuid4())
            new_token_path = os.path.join("media", "yt_tokens", f"acc_{acc_id}.json")
            os.makedirs(os.path.join("media", "yt_tokens"), exist_ok=True)
            shutil.copy2(legacy_token, new_token_path)
            cursor.execute("""
                INSERT INTO youtube_accounts (id, user_id, nickname, token_file, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (acc_id, user_id, "Primary Channel", new_token_path))
            print(f"  [OK] Migrated youtube_token.json -> Primary Channel (active).")
        else:
            print("  [OK] Legacy token already migrated.")
    else:
        print("  [WARN] No users in DB -- skipping legacy token migration.")
else:
    print("  [INFO] No legacy youtube_token.json found -- skipping.")

conn.commit()
conn.close()
print("\nMigration complete.")
