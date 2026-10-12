"""Lightweight Chrome DevTools Protocol (CDP) Client using Python Standard Library.

Provides WebSocket-based automation for local Chrome/Chromium sessions over
Chrome's remote debugging port without third-party dependencies.
"""

import base64
import json
import os
import socket
import struct
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from core.zetta.utils.errors.exceptions import ToolError
from core.zetta.utils.logging import get_logger

logger = get_logger("cdp_client")


class CDPClient:
    """Communicates with Chrome via Chrome DevTools Protocol over WebSocket."""

    def __init__(self, port: int, host: str = "127.0.0.1", timeout: float = 10.0) -> None:
        self.port = port
        self.host = host
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._msg_id: int = 0
        self._target_id: Optional[str] = None
        self._ws_url: Optional[str] = None

    @classmethod
    def is_port_responding(cls, port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
        """Check if Chrome's HTTP debugging endpoint responds."""
        url = f"http://{host}:{port}/json/version"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ZETTA-Agent"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            return False

    def discover_page_target(self) -> Dict[str, Any]:
        """Query /json/list to find the active browser page target."""
        url = f"http://{self.host}:{self.port}/json/list"
        data: List[Dict[str, Any]] = []
        last_error = None
        for attempt in range(5):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "ZETTA-Agent"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except Exception as e:
                last_error = e
                time.sleep(0.15)
        else:
            raise ToolError(f"Failed to query Chrome targets on port {self.port}: {last_error}")

        # Prioritize page targets
        page_targets = [t for t in data if t.get("type") == "page"]
        if not page_targets:
            # If no page target exists, try to create one or use first available
            new_tab_url = f"http://{self.host}:{self.port}/json/new?about:blank"
            try:
                new_req = urllib.request.Request(new_tab_url, headers={"User-Agent": "ZETTA-Agent"}, method="PUT")
                with urllib.request.urlopen(new_req, timeout=self.timeout) as resp:
                    target = json.loads(resp.read().decode("utf-8"))
                    return target
            except Exception:
                if data:
                    return data[0]
                raise ToolError(f"No active page targets available on Chrome port {self.port}.")

        # If we previously had a target_id and it is still a valid page target, keep target affinity
        if self._target_id:
            for t in page_targets:
                if t.get("id") == self._target_id:
                    return t

        # Return the active page target (first page target)
        return page_targets[0]

    def connect(self) -> None:
        """Connect WebSocket to the active Chrome page target."""
        if self._sock:
            return

        target = self.discover_page_target()
        self._target_id = target.get("id")
        ws_url = target.get("webSocketDebuggerUrl")
        if not ws_url:
            raise ToolError(f"Target '{self._target_id}' has no webSocketDebuggerUrl.")

        self._ws_url = ws_url
        parts = ws_url.split("/", 3)
        path = "/" + parts[3] if len(parts) > 3 else "/devtools/page/" + str(self._target_id)

        try:
            self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            key = base64.b64encode(os.urandom(16)).decode("ascii")
            handshake = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {self.host}:{self.port}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n\r\n"
            )
            self._sock.sendall(handshake.encode("ascii"))

            # Read handshake response
            resp = bytearray()
            while b"\r\n\r\n" not in resp:
                chunk = self._sock.recv(1024)
                if not chunk:
                    raise ToolError("Chrome closed connection during WebSocket handshake.")
                resp.extend(chunk)

            headers_text = resp.decode("latin1", errors="replace")
            status_line = headers_text.split("\r\n")[0]
            if "101" not in status_line:
                raise ToolError(f"WebSocket handshake failed: {status_line}")

        except Exception as e:
            self.close()
            raise ToolError(f"Failed to connect to Chrome session on port {self.port}: {e}")

    def reconnect(self) -> None:
        """Close existing connection and reconnect to the active page target."""
        self.close()
        self.connect()

    def send_command(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        allow_retry: bool = True,
    ) -> Any:
        """Send a CDP command and wait for the correlated response, auto-recovering on target navigation."""
        if not self._sock:
            self.connect()

        self._msg_id += 1
        mid = self._msg_id
        payload = json.dumps({"id": mid, "method": method, "params": params or {}})

        try:
            self._send_frame(payload)
        except Exception as e:
            if allow_retry:
                logger.info(f"Socket error sending '{method}': {e}. Reconnecting...")
                self.reconnect()
                return self.send_command(method, params, timeout=timeout, allow_retry=False)
            raise ToolError(f"Failed to send CDP command '{method}': {e}")

        cmd_timeout = timeout or self.timeout
        deadline = time.time() + cmd_timeout

        while time.time() < deadline:
            remaining = max(0.1, deadline - time.time())
            assert self._sock is not None
            self._sock.settimeout(remaining)
            try:
                frame = self._recv_frame()
            except socket.timeout:
                raise ToolError(f"CDP command '{method}' timed out after {cmd_timeout}s.")
            except Exception as e:
                self.close()
                if allow_retry:
                    logger.info(f"Socket error receiving '{method}': {e}. Reconnecting...")
                    self.reconnect()
                    return self.send_command(method, params, timeout=timeout, allow_retry=False)
                raise ToolError(f"CDP connection error during '{method}': {e}")

            if not frame:
                self.close()
                if allow_retry:
                    logger.info(f"Target closed during '{method}'. Reconnecting to active target...")
                    time.sleep(0.3)
                    self.reconnect()
                    return self.send_command(method, params, timeout=timeout, allow_retry=False)
                raise ToolError(f"Chrome disconnected while executing '{method}'.")

            try:
                msg = json.loads(frame)
            except Exception:
                continue

            if msg.get("id") == mid:
                if "error" in msg:
                    err_info = msg["error"]
                    msg_text = err_info.get("message", str(err_info)) if isinstance(err_info, dict) else str(err_info)
                    if allow_retry and "inspected target navigated or closed" in msg_text.lower():
                        logger.info(f"Target navigated or closed during '{method}'. Refreshing target connection...")
                        time.sleep(0.5)
                        self.reconnect()
                        return self.send_command(method, params, timeout=timeout, allow_retry=False)
                    raise ToolError(f"CDP command '{method}' error: {msg_text}")
                return msg.get("result", {})

        raise ToolError(f"CDP command '{method}' timed out waiting for response.")

    def _send_frame(self, payload_str: str) -> None:
        """Encode and send an RFC 6455 masked text WebSocket frame."""
        if not self._sock:
            raise ToolError("Cannot send frame: socket not connected.")

        payload = payload_str.encode("utf-8")
        mask = os.urandom(4)
        length = len(payload)

        if length < 126:
            header = bytes([0x81, 0x80 | length]) + mask
        elif length < 65536:
            header = bytes([0x81, 0x80 | 126]) + struct.pack(">H", length) + mask
        else:
            header = bytes([0x81, 0x80 | 127]) + struct.pack(">Q", length) + mask

        masked_payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self._sock.sendall(header + masked_payload)

    def _recv_frame(self) -> Optional[str]:
        """Receive and decode a WebSocket frame."""
        if not self._sock:
            return None

        head = self._sock.recv(2)
        if not head or len(head) < 2:
            return None

        b1, b2 = head[0], head[1]
        opcode = b1 & 0x0F
        masked = bool(b2 & 0x80)
        length = b2 & 0x7F

        if length == 126:
            len_bytes = self._sock.recv(2)
            if len(len_bytes) < 2:
                return None
            length = struct.unpack(">H", len_bytes)[0]
        elif length == 127:
            len_bytes = self._sock.recv(8)
            if len(len_bytes) < 8:
                return None
            length = struct.unpack(">Q", len_bytes)[0]

        mask = self._sock.recv(4) if masked else None

        data = bytearray()
        while len(data) < length:
            chunk = self._sock.recv(min(8192, length - len(data)))
            if not chunk:
                break
            data.extend(chunk)

        if mask:
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))

        # Handle ping frames by sending pong
        if opcode == 0x9:
            pong_header = bytes([0x8A, 0x80 | len(data)]) + os.urandom(4)
            self._sock.sendall(pong_header + data)
            return self._recv_frame()
        elif opcode == 0x8:  # Close frame
            return None

        return data.decode("utf-8", errors="replace")

    def _wait_for_settle(self, max_wait: float = 3.0) -> None:
        """Wait for document.readyState to become complete or interactive."""
        deadline = time.time() + max_wait
        while time.time() < deadline:
            try:
                state = self.evaluate("document.readyState")
                if state in ("complete", "interactive"):
                    break
            except Exception:
                pass
            time.sleep(0.1)

    def navigate(self, url: str) -> None:
        """Navigate active page to target URL and wait for load."""
        self.send_command("Page.enable")
        self.send_command("Page.navigate", {"url": url})
        time.sleep(0.6)
        self.reconnect()
        self._wait_for_settle()

    def history_navigate(self, action: str) -> None:
        """Execute history navigation (back, forward, reload) and refresh active target."""
        self.send_command("Page.enable")
        if action == "reload":
            self.send_command("Page.reload", {"ignoreCache": True})
        elif action in ("back", "forward"):
            try:
                history = self.send_command("Page.getNavigationHistory")
                curr_idx = history.get("currentIndex", 0)
                entries = history.get("entries", [])
                target_idx = curr_idx - 1 if action == "back" else curr_idx + 1
                if 0 <= target_idx < len(entries):
                    target_id = entries[target_idx]["id"]
                    self.send_command("Page.navigateToHistoryEntry", {"entryId": target_id})
                else:
                    # At boundary or no entries
                    js_cmd = "window.history.back()" if action == "back" else "window.history.forward()"
                    try:
                        self.evaluate(js_cmd)
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Error executing history command via CDP: {e}")
                js_cmd = "window.history.back()" if action == "back" else "window.history.forward()"
                try:
                    self.evaluate(js_cmd)
                except Exception:
                    pass

        # Wait for navigation to settle and reconnect to fresh target
        time.sleep(0.6)
        self.reconnect()
        self._wait_for_settle()

    def get_page_details(self) -> Dict[str, Any]:
        """Extract live page details: URL, title, visible text, and outerHTML."""
        js_code = """
        (() => {
            return {
                url: window.location.href,
                title: document.title || "",
                text: (document.body ? document.body.innerText : "") || "",
                html: document.documentElement ? document.documentElement.outerHTML : ""
            };
        })()
        """
        result = self.send_command("Runtime.evaluate", {"expression": js_code, "returnByValue": True})
        val = result.get("result", {}).get("value", {})
        if not isinstance(val, dict):
            val = {}
        return {
            "url": val.get("url", "about:blank"),
            "title": val.get("title", ""),
            "text": val.get("text", ""),
            "html": val.get("html", ""),
        }

    def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript expression on active page."""
        result = self.send_command("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        return result.get("result", {}).get("value")

    def capture_screenshot(self) -> bytes:
        """Capture viewport screenshot as PNG bytes."""
        self.send_command("Page.enable")
        res = self.send_command("Page.captureScreenshot", {"format": "png"})
        b64_data = res.get("data", "")
        if not b64_data:
            raise ToolError("Failed to capture screenshot data from Chrome.")
        return base64.b64decode(b64_data)

    def close(self) -> None:
        """Close WebSocket connection."""
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
