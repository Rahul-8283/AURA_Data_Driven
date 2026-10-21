"""Live check of the chat Ask endpoint against the real store, Neo4j, LLM and Redis limiter.

It posts to POST /api/v1/chat/ask in-process as a throwaway user, so it needs the Supabase schema
applied and some harvested literature. One check spends a single LLM request. The user's daily
counter key is deleted at the end. Usage (from backend/):
    uv run python -m app.scripts.verify_chat_ask
"""
import sys
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.v1.endpoints.chat import NO_EVIDENCE_ANSWER
from app.core.config import settings
from app.core.security import get_current_user
from app.db.literature_store import get_literature_store
from app.services.rate_limit import daily_limiter
from main import app

failures = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"  [{'ok' if condition else 'FAIL'}] {label}" + (f"  ({detail})" if detail and not condition else ""))
    if not condition:
        failures.append(label)


def main() -> int:
    user_id = f"verify-{uuid.uuid4().hex[:8]}"
    counter_key = daily_limiter.key(user_id)
    client = TestClient(app)
    chunks = get_literature_store().count()
    print(f"Store holds {chunks} literature chunks")
    if chunks == 0:
        print("Nothing harvested yet: run a harvest from the Evidence tab first.")
        return 1

    try:
        print("1. Authentication")
        anonymous = client.post("/api/v1/chat/ask", json={"question": "What is LFP?"})
        check("anonymous request is rejected", anonymous.status_code in (401, 403), str(anonymous.status_code))

        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)

        print("2. A question the literature can answer")
        answered = client.post("/api/v1/chat/ask", json={"question": "What do the papers say about LFP cathode cycle life?"})
        body = answered.json()
        check("request succeeds", answered.status_code == 200, f"{answered.status_code} {body.get('detail', '')}")
        if answered.status_code == 200:
            check("answer is grounded", body["grounded"] is True)
            check("answer has text", len(body["answer"]) > 20)
            check("sources are returned", len(body["sources"]) >= 1)
            check("every source is within the relevance cutoff", all(s["distance"] <= settings.ASK_MAX_DISTANCE for s in body["sources"]))
            check("sources carry a title and a link or DOI", all(s["title"] and (s["url"] or s["doi"]) for s in body["sources"]))
            check("source ids are S1, S2, ...", [s["id"] for s in body["sources"]] == [f"S{i}" for i in range(1, len(body["sources"]) + 1)])
            check("remaining count reflects one use", body["remaining_today"] == settings.ASK_DAILY_LIMIT - 1)
            print("     answer:", body["answer"][:160].replace("\n", " "))
            print("     sources:", [(s["id"], s["source"], s["title"][:45]) for s in body["sources"]])

        print("3. An off-topic question")
        before = int(daily_limiter.client.get(counter_key) or 0)
        off = client.post("/api/v1/chat/ask", json={"question": "What is the best pizza in Chennai?"})
        off_body = off.json()
        check("request succeeds", off.status_code == 200, str(off.status_code))
        check("reply is ungrounded with the standard message", off_body.get("grounded") is False and off_body.get("answer") == NO_EVIDENCE_ANSWER)
        check("no sources are shown", off_body.get("sources") == [] and off_body.get("graph_rules") == [])
        check("no quota was spent on it", int(daily_limiter.client.get(counter_key) or 0) == before)

        print("4. The daily limit")
        with patch.object(settings, "ASK_DAILY_LIMIT", 1):
            limited = client.post("/api/v1/chat/ask", json={"question": "What do the papers say about LFP cathode cycle life?"})
        check("a second answer past the limit is refused", limited.status_code == 429, str(limited.status_code))

        print("5. Validation")
        check("too-short question is rejected", client.post("/api/v1/chat/ask", json={"question": "hi"}).status_code == 422)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        try:
            daily_limiter.client.delete(counter_key)
        except Exception:
            pass

    print("\nFAILED: " + ", ".join(failures) if failures else "\nAll Ask checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
