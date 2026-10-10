import pathlib
from unittest.mock import MagicMock, patch

from app.agents.nodes import planner
from app.core.config import settings

TEST_KEY = "TEST-KEY-not-real"
BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_planner_gemini_sends_key_in_header_not_url(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", TEST_KEY)
    response = MagicMock()
    response.json.return_value = {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}

    with patch.object(planner.requests, "post", return_value=response) as mock_post:
        planner.call_gemini_fallback("prompt")

    url = mock_post.call_args.args[0]
    headers = mock_post.call_args.kwargs["headers"]
    assert TEST_KEY not in url
    assert headers["x-goog-api-key"] == TEST_KEY


def test_no_service_module_puts_the_gemini_key_in_a_url():
    offenders = []
    for folder in ("app/services", "app/agents"):
        for path in (BACKEND_ROOT / folder).rglob("*.py"):
            if "?key={" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(BACKEND_ROOT)))
    assert offenders == []
