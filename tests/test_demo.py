"""Demo-mode tests: OpenAI-compatible client + the real Streamlit app (AppTest) against a stub LLM endpoint.

The stub is the only fake: the LangGraph workflow, ML models and Streamlit UI all run for real.
"""
from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

from utils import demo_guard, openai_compat_client  # noqa: E402
from utils.gemini_client import _mock_payload_for_prompt  # noqa: E402  (test data generator only)
from utils.openai_compat_client import OpenAICompatClient  # noqa: E402


class _Stub(BaseHTTPRequestHandler):
    replies: list = []  # optional queue of raw replies; empty -> well-formed payload for the prompt
    seen_auth: list = []
    seen_models: list = []
    fail_models: set = set()
    calls = 0

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
        type(self).calls += 1
        type(self).seen_auth.append(self.headers.get("authorization", ""))
        type(self).seen_models.append(body.get("model"))
        if body.get("model") in type(self).fail_models:  # e.g. a rate-limited free model
            self.send_response(429)
            self.send_header("content-length", "2")
            self.end_headers()
            self.wfile.write(b"{}")
            return
        user = next((m["content"] for m in reversed(body["messages"]) if m["role"] == "user"), "")
        content = type(self).replies.pop(0) if type(self).replies else json.dumps(_mock_payload_for_prompt(user))
        payload = {"id": "x", "object": "chat.completion", "created": 0, "model": "auto",
                   "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                   "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


@pytest.fixture()
def gateway(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), _Stub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    _Stub.replies, _Stub.seen_auth, _Stub.calls = [], [], 0
    _Stub.seen_models, _Stub.fail_models = [], set()
    openai_compat_client._cooldown_until.clear()
    monkeypatch.setenv("LLM_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("LLM_API_KEY", "gateway-key")
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("ENABLE_MOCK", raising=False)
    monkeypatch.setattr(demo_guard, "UPSTASH_URL", "")
    demo_guard._mem.clear()
    yield _Stub
    server.shutdown()


def click(at, label):
    next(b for b in at.sidebar.button if b.label == label).click().run()


def client_for(base_url, key="k"):
    return OpenAICompatClient(api_key=key, base_url=base_url)


def test_client_parses_fenced_json_and_sends_key(gateway):
    gateway.replies = ['```json\n{"a": 1}\n```']
    out = client_for(f"{__import__('os').environ['LLM_BASE_URL']}", "abc").generate_structured_json("p", ["a"])
    assert out == {"a": 1} and gateway.seen_auth[0] == "Bearer abc"


def test_client_retries_once_on_missing_fields(gateway):
    gateway.replies = ['{"b": 2}', '{"a": 1}']
    out = client_for(__import__("os").environ["LLM_BASE_URL"]).generate_structured_json("p", ["a"])
    assert out == {"a": 1} and gateway.calls == 2


def test_client_gives_up_after_retry(gateway):
    gateway.replies = ["nope", "still nope"]
    with pytest.raises(ValueError):
        client_for(__import__("os").environ["LLM_BASE_URL"]).generate_structured_json("p", ["a"])


def test_model_chain_falls_through_and_rests_a_failed_model(gateway):
    gateway.fail_models = {"fast-a"}
    client = OpenAICompatClient(api_key="k", base_url=__import__("os").environ["LLM_BASE_URL"], models=["fast-a", "slow-b@low", "auto"])
    gateway.replies = ['{"a": 1}', '{"a": 2}']
    assert client.generate_structured_json("p", ["a"]) == {"a": 1}
    assert gateway.seen_models == ["fast-a", "slow-b"]  # "@low" is the reasoning effort, not part of the name
    assert client.generate_structured_json("p", ["a"]) == {"a": 2}
    assert gateway.seen_models[2:] == ["slow-b"]  # the failed model is skipped while it cools down


def test_free_mode_uses_the_pinned_chain_but_own_key_does_not(gateway, monkeypatch):
    monkeypatch.setenv("LLM_MODELS", "pinned-1,auto")
    assert openai_compat_client.free_demo_models() == ["pinned-1", "auto"]
    assert client_for("http://x/v1").models == ["auto"]  # a visitor's own key never gets gateway model names
    at = AppTest.from_file(str(ROOT / "main.py"), default_timeout=120).run()
    click(at, "Generate Assessment")
    assert any("Assessment generated" in s.value for s in at.success), [e.value for e in at.error]
    assert set(gateway.seen_models) == {"pinned-1"}


def test_app_defaults_to_free_live_mode_and_hides_mock(gateway):
    at = AppTest.from_file(str(ROOT / "main.py"), default_timeout=60).run()
    assert not at.exception
    radio = at.sidebar.radio[0]
    assert radio.value == "Free Demo (live LLM)"
    assert "Mock Demo" not in radio.options
    assert any("live by an LLM" in i.value for i in at.info)


def test_mock_mode_only_with_dev_flag(gateway, monkeypatch):
    monkeypatch.setenv("ENABLE_MOCK", "1")
    at = AppTest.from_file(str(ROOT / "main.py"), default_timeout=60).run()
    assert "Mock Demo" in at.sidebar.radio[0].options


def test_free_mode_runs_real_workflow_through_the_gateway(gateway):
    at = AppTest.from_file(str(ROOT / "main.py"), default_timeout=120).run()
    click(at, "Generate Assessment")
    assert not at.exception
    assert any("Assessment generated" in s.value for s in at.success), [e.value for e in at.error]
    assert gateway.calls >= 4  # normaliser + workout + nutrition + recovery
    assert set(gateway.seen_auth) == {"Bearer gateway-key"}
    # real ML classifiers ran in the workflow
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Fitness Level"] != "Unknown" and metrics["Injury Risk"] != "Unknown"
    assert any("synthetic dataset" in c.value for c in at.caption)  # the UI states the model's limitation


def test_free_mode_is_rate_limited_but_byo_key_is_not(gateway, monkeypatch):
    monkeypatch.setattr(demo_guard, "PER_IP_DAILY", 4)  # exactly one assessment
    at = AppTest.from_file(str(ROOT / "main.py"), default_timeout=120).run()
    click(at, "Generate Assessment")
    assert any("Assessment generated" in s.value for s in at.success)
    click(at, "Generate Assessment")
    assert any("Daily free-demo limit" in e.value for e in at.error)
    # a visitor's own key is not subject to the shared limit (the stub stands in for their provider here)
    at.sidebar.radio[0].set_value("Use My OpenAI-Compatible Key").run()
    assert any(t.label == "API Key" for t in at.sidebar.text_input)


def test_byo_mode_requires_a_key(gateway):
    at = AppTest.from_file(str(ROOT / "main.py"), default_timeout=60).run()
    at.sidebar.radio[0].set_value("Use My Gemini API Key").run()
    click(at, "Generate Assessment")
    assert any("Gemini API key" in e.value for e in at.error)
