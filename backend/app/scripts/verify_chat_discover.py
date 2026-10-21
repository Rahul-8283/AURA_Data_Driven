"""Live check of the Discover path: POST /api/v1/research/start against the real database.

A real user id is read from Supabase so the ResearchTasks foreign key is satisfied. Queueing is
replaced, so no worker runs and no LLM quota is spent; the row it creates is deleted at the end.
The pipeline itself is exercised by simulate_discovery_run. Usage (from backend/):
    uv run python -m app.scripts.verify_chat_discover
"""
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import psycopg2
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.db.supabase import supabase_client
from main import app

load_dotenv(".env")
failures = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"  [{'ok' if condition else 'FAIL'}] {label}" + (f"  ({detail})" if detail and not condition else ""))
    if not condition:
        failures.append(label)


def main() -> int:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"), connect_timeout=10)
    cur = conn.cursor()
    cur.execute("select id from auth.users order by created_at limit 1")
    row = cur.fetchone()
    if not row:
        print("No user exists in Supabase auth: sign up once, then rerun.")
        return 1
    user_id = str(row[0])
    task_id = None
    prompt = "Verify run: find a cobalt-free cathode with more than 250 mAh/g"
    queued = MagicMock(side_effect=lambda args, task_id: SimpleNamespace(id=task_id))

    try:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)
        client = TestClient(app)

        print("1. Starting a discovery")
        with patch("app.api.v1.endpoints.research.run_discovery_loop.apply_async", queued):
            response = client.post("/api/v1/research/start", json={"prompt": prompt})
        body = response.json()
        task_id = body.get("task_id")
        check("accepted with 202", response.status_code == 202, str(response.status_code))
        check("a task id is returned", bool(task_id))
        check("the task was queued once with prompt, id and user", queued.call_count == 1
              and queued.call_args.kwargs["args"] == [prompt, task_id, user_id])

        print("2. The run is recorded for the user")
        cur.execute('select status, user_id::text, prompt from "ResearchTasks" where id = %s', (task_id,))
        saved = cur.fetchone()
        check("a ResearchTasks row exists", saved is not None)
        if saved:
            check("it is in processing state", saved[0] == "processing")
            check("it belongs to the requesting user", saved[1] == user_id)
            check("it stores the prompt", saved[2] == prompt)

        print("3. Status endpoint")
        status = client.get(f"/api/v1/research/status/{task_id}")
        check("status is readable", status.status_code == 200 and "status" in status.json())

        print("4. Authentication and validation")
        app.dependency_overrides.pop(get_current_user, None)
        check("anonymous start is rejected", client.post("/api/v1/research/start", json={"prompt": prompt}).status_code in (401, 403))
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        if task_id:
            supabase_client.table("ResearchTasks").delete().eq("id", task_id).execute()
        conn.close()

    print("\nFAILED: " + ", ".join(failures) if failures else "\nAll Discover checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
