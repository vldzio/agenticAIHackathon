import datetime as dt
import json

import pytest

from app.llm.base import LLMAuthError, LLMRateLimitError
from app.llm.mock import MockLLMClient
from tests.conftest import DEVICE, OTHER_DEVICE

BASE = "/api/v1"


def create(client, profile, mode="mock", headers=None, **extra):
    return client.post(f"{BASE}/assessments", json={"profile": profile, "mode": mode}, headers={**DEVICE, **(headers or {})})


def test_health(client):
    body = client.get(f"{BASE}/health").json()
    assert body == {"status": "ok", "version": "1.0.0", "database": True, "models_loaded": True}


def test_create_and_fetch_assessment(client, profile):
    r = create(client, profile)
    assert r.status_code == 201
    a = r.json()
    assert a["status"] == "complete" and a["simulated"] is True and a["mode"] == "mock"
    assert a["fitness"]["level"] and a["injury"]["risk"] and a["safety"]["disclaimer"]
    assert all(v == "ok" for v in a["sections"].values())
    assert client.get(f"{BASE}/assessments/{a['id']}", headers=DEVICE).json()["id"] == a["id"]
    summaries = client.get(f"{BASE}/assessments", headers=DEVICE).json()
    assert [s["id"] for s in summaries] == [a["id"]] and summaries[0]["sessions_per_week"] == a["workout"][
        "workout_frequency_per_week"
    ]


def test_device_scoping(client, profile):
    a = create(client, profile).json()
    assert client.get(f"{BASE}/assessments/{a['id']}", headers=OTHER_DEVICE).status_code == 404
    assert client.get(f"{BASE}/assessments", headers=OTHER_DEVICE).json() == []
    assert client.delete(f"{BASE}/assessments/{a['id']}", headers=OTHER_DEVICE).status_code == 404
    assert client.get(f"{BASE}/assessments/{a['id']}/export.pdf", headers=OTHER_DEVICE).status_code == 404


def test_device_header_required(client, profile):
    r = client.post(f"{BASE}/assessments", json={"profile": profile})
    assert r.status_code == 400 and r.json()["error"]["code"] == "missing_device_id"
    assert client.get(f"{BASE}/assessments", headers={"X-Device-Id": "short"}).status_code == 400


def test_delete(client, profile):
    a = create(client, profile).json()
    assert client.delete(f"{BASE}/assessments/{a['id']}", headers=DEVICE).status_code == 204
    assert client.get(f"{BASE}/assessments/{a['id']}", headers=DEVICE).status_code == 404


@pytest.mark.parametrize(
    ("patch", "field"),
    [
        ({"age": 5}, "age"),
        ({"weight_kg": 1000}, "weight_kg"),
        ({"gender": "Robot"}, "gender"),
        ({"fitness_experience": ""}, "fitness_experience"),
        ({"fitness_experience": "x" * 501}, "fitness_experience"),
        ({"nope": 1}, "nope"),
    ],
)
def test_validation_errors_are_structured(client, profile, patch, field):
    r = create(client, {**profile, **patch})
    body = r.json()["error"]
    assert r.status_code == 422 and body["code"] == "validation_error" and body["request_id"]
    assert any(field in fe["field"] for fe in body["field_errors"])


def test_control_characters_are_stripped(client, profile):
    a = create(client, {**profile, "user_name": "  Al\x00ex\x07  "}).json()
    assert a["profile"]["user_name"] == "Alex"


def test_live_mode_requires_key(client, profile):
    r = create(client, profile, mode="live")
    assert r.status_code == 401 and r.json()["error"]["code"] == "llm_auth"


def test_bad_key_format_rejected_and_not_echoed(client, profile):
    r = create(client, profile, mode="live", headers={"X-Gemini-Api-Key": "bad key!!"})
    assert r.status_code == 400 and "bad key" not in r.text


class KeyChecking(MockLLMClient):
    simulated = False

    def __init__(self, key):
        if key == "A" * 30:
            raise LLMAuthError("Gemini rejected the API key.")
        self.key = key


def test_live_mode_uses_byok_header_and_persists_no_key(client, profile, monkeypatch):
    seen = {}

    def fake_build(mode, api_key=None):
        seen["key"] = api_key
        return KeyChecking(api_key)

    monkeypatch.setattr("app.api.deps.build_llm_client", fake_build)
    key = "AIza" + "x" * 35
    r = create(client, profile, mode="live", headers={"X-Gemini-Api-Key": key})
    assert r.status_code == 201 and seen["key"] == key
    a = r.json()
    assert a["mode"] == "live" and a["simulated"] is False
    assert key not in r.text and key not in client.get(f"{BASE}/assessments/{a['id']}", headers=DEVICE).text
    from app.db.models import AssessmentRow
    from app.db.session import session_factory

    with session_factory()() as db:
        assert all(key not in row.payload for row in db.query(AssessmentRow))


def test_invalid_key_maps_to_401(client, profile, monkeypatch):
    monkeypatch.setattr("app.api.deps.build_llm_client", lambda mode, api_key=None: KeyChecking(api_key))
    r = create(client, profile, mode="live", headers={"X-Gemini-Api-Key": "A" * 30})
    assert r.status_code == 401 and r.json()["error"]["code"] == "llm_auth"


def test_quota_error_maps_to_429_and_nothing_saved(client, profile, monkeypatch):
    class Quota(MockLLMClient):
        simulated = False

        def generate(self, task, prompt, schema, context):
            raise LLMRateLimitError("quota")

    monkeypatch.setattr("app.api.deps.build_llm_client", lambda mode, api_key=None: Quota())
    r = create(client, profile, mode="live", headers={"X-Gemini-Api-Key": "A" * 30})
    assert r.status_code == 429 and r.json()["error"]["code"] == "llm_rate_limited"
    assert client.get(f"{BASE}/assessments", headers=DEVICE).json() == []


def test_partial_result_is_saved_and_flagged(client, profile, monkeypatch):
    from app.llm.base import LLMUnavailableError

    class Flaky(MockLLMClient):
        simulated = False

        def generate(self, task, prompt, schema, context):
            if task == "recovery":
                raise LLMUnavailableError("down")
            return super().generate(task, prompt, schema, context)

    monkeypatch.setattr("app.api.deps.build_llm_client", lambda mode, api_key=None: Flaky())
    r = create(client, profile, mode="live", headers={"X-Gemini-Api-Key": "A" * 30})
    a = r.json()
    assert r.status_code == 201 and a["status"] == "partial" and a["sections"]["recovery"] == "failed"
    assert a["errors"][0]["node"] == "recovery_optimizer" and a["recovery"] is None and a["workout"]


def test_stream_emits_progress_then_result(client, profile):
    with client.stream("POST", f"{BASE}/assessments/stream", json={"profile": profile, "mode": "mock"}, headers=DEVICE) as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        text = "".join(r.iter_text())
    events = [line.removeprefix("event: ") for line in text.splitlines() if line.startswith("event: ")]
    assert events[0] == "start" and events[-1] == "result" and events.count("node") == 8
    result = json.loads(text.split("event: result\ndata: ")[1].split("\n\n")[0])
    assert client.get(f"{BASE}/assessments/{result['id']}", headers=DEVICE).status_code == 200


def test_stream_reports_errors_as_events(client, profile, monkeypatch):
    class Quota(MockLLMClient):
        simulated = False

        def generate(self, task, prompt, schema, context):
            raise LLMRateLimitError("quota")

    monkeypatch.setattr("app.api.deps.build_llm_client", lambda mode, api_key=None: Quota())
    with client.stream(
        "POST",
        f"{BASE}/assessments/stream",
        json={"profile": profile, "mode": "live"},
        headers={**DEVICE, "X-Gemini-Api-Key": "A" * 30},
    ) as r:
        text = "".join(r.iter_text())
    assert "event: error" in text and "llm_rate_limited" in text and "event: result" not in text


def test_exports(client, profile):
    a = create(client, profile).json()
    pdf = client.get(f"{BASE}/assessments/{a['id']}/export.pdf", headers=DEVICE)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF") and "attachment" in pdf.headers["content-disposition"]
    ics = client.get(f"{BASE}/assessments/{a['id']}/export.ics", headers=DEVICE)
    assert (
        ics.status_code == 200
        and ics.text.startswith("BEGIN:VCALENDAR")
        and ics.text.count("BEGIN:VEVENT") == a["workout"]["workout_frequency_per_week"]
    )
    assert all(len(line.encode()) <= 75 for line in ics.text.split("\r\n"))
    js = client.get(f"{BASE}/assessments/{a['id']}/export.json", headers=DEVICE)
    assert js.json()["id"] == a["id"]
    assert client.get(f"{BASE}/assessments/{a['id']}/export.docx", headers=DEVICE).status_code == 422


def test_progress_logging_and_summary(client, profile):
    a = create(client, profile).json()
    aid = a["id"]
    planned = a["workout"]["workout_frequency_per_week"]
    today = dt.date.today()
    for i in range(planned):
        assert (
            client.post(
                f"{BASE}/assessments/{aid}/logs",
                json={"kind": "session", "logged_on": str(today - dt.timedelta(days=i)), "rpe": 6, "duration_minutes": 45},
                headers=DEVICE,
            ).status_code
            == 201
        )
    w = client.post(f"{BASE}/assessments/{aid}/logs", json={"kind": "weight", "weight_kg": 68.5}, headers=DEVICE)
    assert w.status_code == 201
    s = client.get(f"{BASE}/assessments/{aid}/progress", headers=DEVICE).json()
    assert s["sessions_last_28_days"] == planned and s["adherence_pct"] == 100.0 and s["weight_change_kg"] == -1.5
    assert s["average_rpe"] == 6.0 and len(s["weekly"]) == 8 and s["deload_due"] is False
    logs = client.get(f"{BASE}/assessments/{aid}/logs", headers=DEVICE).json()
    assert len(logs) == planned + 1
    assert client.delete(f"{BASE}/assessments/{aid}/logs/{w.json()['id']}", headers=DEVICE).status_code == 204
    assert client.delete(f"{BASE}/assessments/{aid}/logs/{w.json()['id']}", headers=DEVICE).status_code == 404


def test_log_validation_and_scoping(client, profile):
    aid = create(client, profile).json()["id"]
    assert client.post(f"{BASE}/assessments/{aid}/logs", json={"kind": "weight"}, headers=DEVICE).status_code == 422
    assert client.post(f"{BASE}/assessments/{aid}/logs", json={"kind": "session", "rpe": 11}, headers=DEVICE).status_code == 422
    assert client.post(f"{BASE}/assessments/{aid}/logs", json={"kind": "session"}, headers=OTHER_DEVICE).status_code == 404


def test_replan_uses_progress_history(client, profile):
    a = create(client, {**profile, "available_hours_per_week": "5 hours"}).json()
    aid = a["id"]
    client.post(f"{BASE}/assessments/{aid}/logs", json={"kind": "weight", "weight_kg": 66.0}, headers=DEVICE)
    r = client.post(f"{BASE}/assessments/{aid}/replan", json={"mode": "mock"}, headers=DEVICE)
    b = r.json()
    assert r.status_code == 201 and b["parent_id"] == aid and b["id"] != aid
    assert b["profile"]["weight_kg"] == 66.0
    assert b["progress_context"]["adherence_pct"] == 0.0
    assert (
        b["workout"]["workout_frequency_per_week"] == a["workout"]["workout_frequency_per_week"] - 1
    )  # low adherence => easier plan
    assert client.post(f"{BASE}/assessments/{'0' * 36}/replan", json={}, headers=DEVICE).status_code == 404


def test_models_endpoints(client):
    info = client.get(f"{BASE}/models/info").json()
    assert set(info["models"]) == {"fitness_level", "injury_risk"} and info["limitations"]
    ev = client.get(f"{BASE}/models/evaluation").json()
    assert ev["models"]["fitness_level"]["accuracy"] > 0.7
    assert client.get(f"{BASE}/workflow").json()["nodes"][0]["name"] == "form_parser"


def test_request_id_and_security_headers(client):
    r = client.get(f"{BASE}/health")
    assert len(r.headers["x-request-id"]) == 16 and r.headers["x-content-type-options"] == "nosniff"
    assert client.get("/api/v1/nope").json()["error"]["code"] == "not_found"


def test_cors_preflight_allows_byok_headers(client):
    r = client.options(
        f"{BASE}/assessments",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-gemini-api-key,x-device-id,content-type",
        },
    )
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "x-gemini-api-key" in r.headers["access-control-allow-headers"].lower()
    evil = client.options(
        f"{BASE}/assessments", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"}
    )
    assert "access-control-allow-origin" not in evil.headers


def test_body_size_limit(client, profile):
    r = client.post(
        f"{BASE}/assessments", content=b"{" + b" " * 70_000 + b"}", headers={**DEVICE, "Content-Type": "application/json"}
    )
    assert r.status_code == 413 and r.json()["error"]["code"] == "payload_too_large"


def test_rate_limiting(profile, monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.db.session import reset_engine_for_tests
    from app.main import create_app

    monkeypatch.setenv("AETHERFIT_ASSESSMENT_RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    reset_engine_for_tests()
    try:
        with TestClient(create_app()) as c:
            codes = [create(c, profile).status_code for _ in range(3)]
            assert codes == [201, 201, 429]
            limited = create(c, profile)
            assert limited.headers["retry-after"].isdigit() and limited.json()["error"]["code"] == "rate_limited"
            assert c.get(f"{BASE}/health").status_code == 200  # health is never limited
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
        reset_engine_for_tests()


def test_openapi_documents_byok_and_errors(client):
    spec = client.get("/api/openapi.json").json()
    params = [p["name"] for p in spec["paths"]["/api/v1/assessments"]["post"]["parameters"]]
    assert {"x-gemini-api-key", "x-device-id"} <= set(params)
    assert "401" in spec["paths"]["/api/v1/assessments"]["post"]["responses"]
