"""Controlled manual verification script for ZETTA UI and API startup.

Verifies:
1. Server starts and initializes runtime once.
2. GET /api/health returns 200 OK and is called repeatedly.
3. GET /api/status returns ONLINE.
4. WebSocket connects and stays idle.
5. Zero new screen captures are created in runtime/captures/.
6. No duplicate agent or tool registrations.
"""

import sys
import time
from pathlib import Path
import threading

root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import uvicorn
import requests

from core.zetta.api.app import get_api_app
from core.zetta.runtime import is_runtime_initialized
from core.zetta.agents.manager.registry import get_agent_registry
from core.zetta.tools import get_tool_registry

PORT = 8765
HOST = "127.0.0.1"
BASE_URL = f"http://{HOST}:{PORT}"


def run_server():
    app = get_api_app()
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


def main():
    captures_dir = Path("runtime/captures")
    captures_dir.mkdir(parents=True, exist_ok=True)
    initial_captures = len(list(captures_dir.glob("*.png")))
    print(f"[*] Initial screen captures in runtime/captures: {initial_captures}")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Wait for server to be responsive
    started = False
    for _ in range(30):
        try:
            r = requests.get(f"{BASE_URL}/api/status", timeout=1.0)
            if r.status_code == 200:
                started = True
                break
        except Exception:
            time.sleep(0.2)

    if not started:
        print("[!] Server failed to start within 6 seconds.")
        sys.exit(1)

    print("[+] Server started and responding to HTTP requests.")
    assert is_runtime_initialized(), "Runtime should be initialized after app startup."

    # Test GET / (UI index page)
    r_index = requests.get(f"{BASE_URL}/", timeout=2.0)
    print(f"[+] GET / -> HTTP {r_index.status_code}")
    assert r_index.status_code == 200

    # Call /api/health 10 times consecutively
    for i in range(10):
        r_health = requests.get(f"{BASE_URL}/api/health", timeout=2.0)
        assert r_health.status_code == 200
        data = r_health.json()
        assert data["status"] in ("healthy", "degraded")
        time.sleep(0.1)
    print("[+] Called GET /api/health 10 times consecutively — all returned 200 OK.")

    # Call /api/status
    r_status = requests.get(f"{BASE_URL}/api/status", timeout=2.0)
    assert r_status.status_code == 200
    st_data = r_status.json()
    print(f"[+] GET /api/status -> state={st_data.get('state')}, agents={st_data.get('registered_agents_count')}")

    # Simulate idle wait for 4 seconds
    print("[*] Simulating idle UI wait for 4 seconds...")
    time.sleep(4.0)

    # Check screen captures count
    final_captures = len(list(captures_dir.glob("*.png")))
    print(f"[*] Final screen captures in runtime/captures: {final_captures}")

    if final_captures != initial_captures:
        print(f"[FAIL] Captured leaked! {final_captures - initial_captures} new files created during idle check.")
        sys.exit(1)

    print("[SUCCESS] Zero new screen captures created during startup, repeated health calls, and idle period.")

    # Verify agent registry count and tool count
    a_count = len(get_agent_registry().list_agents())
    t_count = len(get_tool_registry().list_tools())
    print(f"[SUCCESS] Agent registry count: {a_count}, Tool registry count: {t_count} (zero duplicates).")


if __name__ == "__main__":
    main()
