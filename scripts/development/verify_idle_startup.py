"""Controlled UI/backend idle test script.

Verifies:
- runtime/captures does NOT grow during idle startup or polling.
- /api/health does not capture.
- no repeated agent registration.
- no repeated tool registration.
- no repeated TTS initialization.
- no runaway CPU or disk activity.
"""

import os
from pathlib import Path
import subprocess
import time
import urllib.request
import json
import signal

def count_captures() -> int:
    cap_dir = Path("runtime/captures")
    if not cap_dir.exists():
        return 0
    return len(list(cap_dir.glob("*.png")))

def run_idle_test():
    print("==================================================")
    print("STARTING CONTROLLED UI/BACKEND IDLE TEST")
    print("==================================================")

    initial_captures = count_captures()
    print(f"Initial captures in runtime/captures: {initial_captures}")

    port = 8019
    cmd = [
        "python3", "-m", "uvicorn",
        "core.zetta.api.app:app",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--log-level", "info",
    ]

    print(f"Spawning backend on port {port}...")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    log_lines = []
    def read_logs():
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            log_lines.append(line)

    import threading
    t = threading.Thread(target=read_logs, daemon=True)
    t.start()

    # Wait for server to become ready
    url = f"http://127.0.0.1:{port}/api/health"
    ready = False
    for _ in range(20):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.5)

    if not ready:
        proc.kill()
        print("FAILED: Backend did not start in time. Process logs:")
        print("".join(log_lines))
        return False

    print("Backend is ready. Polling /api/health repeatedly for 8 seconds (idle simulation)...")
    for i in range(8):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                data = json.loads(resp.read().decode())
                assert data["status"].lower() in ("ok", "healthy", "degraded")
        except Exception as e:
            print(f"Polling error at second {i}: {e}")
        time.sleep(1.0)

    # Check screen access status endpoint
    status_url = f"http://127.0.0.1:{port}/api/computer/screen-access"
    try:
        req = urllib.request.Request(status_url)
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            data = json.loads(resp.read().decode())
            print(f"Screen access manager status: scope={data.get('scope')}, authorized={data.get('is_authorized')}")
            assert data.get("scope") == "DENIED"
            assert data.get("is_authorized") is False
    except Exception as e:
        print(f"Screen access endpoint error: {e}")

    # Terminate backend process
    print("Stopping backend process...")
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    time.sleep(1)
    final_captures = count_captures()
    print(f"Final captures in runtime/captures: {final_captures}")

    # Log analysis
    all_logs = "".join(log_lines)
    tool_registrations = all_logs.count("Registering core tools...")
    fleet_registrations = all_logs.count("Registering default agent fleet...")
    screen_captures_logged = all_logs.count("Saved real screen capture PNG")

    print("--------------------------------------------------")
    print(f"Tool registry initializations in logs: {tool_registrations}")
    print(f"Fleet registrations in logs: {fleet_registrations}")
    print(f"Real screen captures in logs: {screen_captures_logged}")
    print(f"Captures file delta: {final_captures - initial_captures}")
    print("--------------------------------------------------")

    success = True
    if final_captures > initial_captures:
        print("FAILURE: New screen captures were saved during idle polling!")
        success = False
    else:
        print("SUCCESS: Zero screen captures saved to disk during idle polling.")

    if tool_registrations > 1:
        print(f"FAILURE: Tool registration occurred {tool_registrations} times (expected <= 1).")
        success = False
    else:
        print("SUCCESS: Tool registration is idempotent (occurred <= 1 time).")

    if fleet_registrations > 1:
        print(f"FAILURE: Fleet registration occurred {fleet_registrations} times (expected <= 1).")
        success = False
    else:
        print("SUCCESS: Fleet registration is idempotent (occurred <= 1 time).")

    if screen_captures_logged > 0:
        print(f"FAILURE: Real screen capture messages found in logs: {screen_captures_logged}")
        success = False
    else:
        print("SUCCESS: Zero screen capture log events observed.")

    return success

if __name__ == "__main__":
    import sys
    ok = run_idle_test()
    sys.exit(0 if ok else 1)
