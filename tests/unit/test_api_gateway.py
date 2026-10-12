"""Unit tests for ZETTA Desktop API Gateway."""

import pytest
from fastapi.testclient import TestClient
from core.zetta.api.app import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_system_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "subsystems" in data


def test_system_status(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "active_agent" in data
    assert "agents_count" in data


def test_agents_fleet_and_specialized(client):
    response = client.get("/api/agents")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "fleet" in data
    assert "specialized" in data
    assert data["fleet_count"] >= 6
    # Ensure base fleet names are present
    fleet_names = [a["name"] for a in data["fleet"]]
    assert "GeneralAssistantAgent" in fleet_names
    assert "BrowserAgent" in fleet_names
    assert "VisionAgent" in fleet_names
    assert "VoiceAgent" in fleet_names
    assert "ResearchAgent" in fleet_names
    assert "DocumentAgent" in fleet_names


def test_chat_interaction(client):
    # Test session list
    resp_sess = client.get("/api/chat/sessions")
    assert resp_sess.status_code == 200

    # Test sending a chat message
    resp_msg = client.post("/api/chat/message", json={"message": "Hello ZETTA", "session_id": "test-session"})
    assert resp_msg.status_code == 200
    data = resp_msg.json()
    assert data["status"] == "success"
    assert "response" in data
    assert len(data["response"]) > 0


def test_tasks_list(client):
    response = client.get("/api/tasks")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "tasks" in data


def test_computer_status(client):
    response = client.get("/api/computer/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "active_window" in data


def test_browser_status(client):
    response = client.get("/api/browser/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "is_open" in data


def test_vision_status(client):
    response = client.get("/api/vision/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "displays" in data


def test_voice_status(client):
    response = client.get("/api/voice/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_memory_crud(client):
    # Add memory
    add_resp = client.post(
        "/api/memory",
        json={
            "content": "User prefers dark mode and python.",
            "memory_type": "LONG_TERM",
            "tags": ["ui_test", "preferences"],
        },
    )
    assert add_resp.status_code == 200
    mem = add_resp.json()["memory"]
    mem_id = mem["id"]

    # List memory
    list_resp = client.get("/api/memory/list?tag=ui_test")
    assert list_resp.status_code == 200
    assert any(m["id"] == mem_id for m in list_resp.json()["memories"])

    # Search memory
    search_resp = client.get("/api/memory/search?query=dark%20mode")
    assert search_resp.status_code == 200

    # Delete memory
    del_resp = client.delete(f"/api/memory/{mem_id}")
    assert del_resp.status_code == 200


def test_skills_and_plugins(client):
    resp_skills = client.get("/api/skills")
    assert resp_skills.status_code == 200
    assert "skills" in resp_skills.json()

    resp_plugins = client.get("/api/plugins")
    assert resp_plugins.status_code == 200
    assert "plugins" in resp_plugins.json()


def test_confirmations_flow(client):
    # List confirmations
    resp = client.get("/api/confirmations")
    assert resp.status_code == 200

    # Create confirmation
    create_resp = client.post(
        "/api/confirmations/request",
        json={
            "action": "system_shutdown",
            "description": "ZETTA wants to restart service",
            "required_permission": "HIGH",
        },
    )
    assert create_resp.status_code == 200
    cid = create_resp.json()["confirmation"]["id"]

    # Resolve confirmation
    res_resp = client.post(f"/api/confirmations/{cid}/resolve", json={"approved": True, "reason": "User approved in test"})
    assert res_resp.status_code == 200
    assert res_resp.json()["resolution"] == "APPROVED"


def test_settings_and_personas(client):
    # Get settings
    settings_resp = client.get("/api/settings")
    assert settings_resp.status_code == 200
    data = settings_resp.json()
    assert "active_persona" in data
    # Sensitive keys must never be exposed raw
    if data["ai"]["has_openai_key"]:
        assert data["ai"]["openai_key_masked"].startswith("sk-") or "..." in data["ai"]["openai_key_masked"]

    # List personas
    personas_resp = client.get("/api/personas")
    assert personas_resp.status_code == 200
    assert len(personas_resp.json()["personas"]) >= 3

    # Switch persona
    switch_resp = client.post("/api/settings/persona", json={"persona_type": "PROFESSIONAL"})
    assert switch_resp.status_code == 200
    assert switch_resp.json()["active_persona"]["type"].lower() == "professional"


def test_ui_static_serving(client):
    # Verify index HTML
    index_resp = client.get("/")
    assert index_resp.status_code == 200
    assert "ZETTA" in index_resp.text
    assert "AI EMPLOYEE" in index_resp.text

    # Verify CSS stylesheet
    css_resp = client.get("/css/style.css")
    assert css_resp.status_code == 200
    assert "--bg-base" in css_resp.text

    # Verify core JS modules
    app_js = client.get("/js/app.js")
    assert app_js.status_code == 200
    assert "initApp" in app_js.text

    api_js = client.get("/js/api.js")
    assert api_js.status_code == 200
    assert "getSystemStatus" in api_js.text

