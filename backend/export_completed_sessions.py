import sqlite3
import json
import csv
from pathlib import Path

DB_PATH = Path("interview_platform.db")
EXPORT_DIR = Path("exports/completed_sessions")

EXPORT_DIR.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

cursor = conn.cursor()

cursor.execute("""
    SELECT *
    FROM interview_sessions
    WHERE LOWER(status) = 'completed'
    ORDER BY updated_at DESC
""")

sessions = cursor.fetchall()

all_sessions = []
summary_rows = []

for session in sessions:
    record = dict(session)

    try:
        record["state_data"] = json.loads(record["state_data"])
    except (json.JSONDecodeError, TypeError):
        print(f"Invalid JSON: {record['id']}")

    all_sessions.append(record)

    file_path = EXPORT_DIR / f"{record['id']}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=4, ensure_ascii=False)

    summary_rows.append({
        "session_id": record["id"],
        "candidate_name": record["candidate_name"],
        "status": record["status"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"]
    })

with open(EXPORT_DIR / "all_completed_sessions.json", "w", encoding="utf-8") as f:
    json.dump(all_sessions, f, indent=4, ensure_ascii=False)

with open(EXPORT_DIR / "completed_sessions_summary.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=summary_rows[0].keys() if summary_rows else [
        "session_id", "candidate_name", "status", "created_at", "updated_at"
    ])
    writer.writeheader()
    writer.writerows(summary_rows)

conn.close()

print("\nExport completed!")
print(f"Total completed sessions: {len(sessions)}")
print(f"Export location: {EXPORT_DIR.resolve()}")
