"""Wayland ScreenCast and PipeWire Desktop Portal Provider for ZETTA.

Implements clean provider architecture for:
- org.freedesktop.portal.ScreenCast (native OS authorization flow)
- PipeWire node stream negotiation via GStreamer 1.0 pipewiresrc

Guarantees:
1. Native user permission dialog is strictly obeyed.
2. If the portal request is denied or cancelled, it remains DENIED.
3. Absolutely NO silent fallback to unauthorized screenshots upon denial.
4. No fake PipeWire or mock streaming data.
"""

from dataclasses import dataclass, field
from enum import Enum
import os
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

from core.zetta.security.screen_access import (
    ScreenAccessDeniedError,
    ScreenAccessScope,
    get_screen_access_manager,
)
from core.zetta.utils.logging import get_logger

logger = get_logger("portal_screencast")


class ScreenCastSessionState(str, Enum):
    INITIALIZING = "INITIALIZING"
    PROMPTING_USER = "PROMPTING_USER"
    ACTIVE = "ACTIVE"
    DENIED = "DENIED"
    CLOSED = "CLOSED"


@dataclass
class ScreenCastStreamInfo:
    """PipeWire stream metadata returned by desktop portal."""
    node_id: int
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreenCastSession:
    """Active or pending Wayland ScreenCast session."""
    session_handle: str
    state: ScreenCastSessionState = ScreenCastSessionState.INITIALIZING
    streams: List[ScreenCastStreamInfo] = field(default_factory=list)
    restore_token: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    _gst_pipeline: Optional[Any] = None

    @property
    def is_active(self) -> bool:
        return self.state == ScreenCastSessionState.ACTIVE and len(self.streams) > 0

    @property
    def primary_node_id(self) -> Optional[int]:
        if self.streams:
            return self.streams[0].node_id
        return None


class WaylandPortalScreenCastProvider:
    """Production Wayland ScreenCast Provider integrating with XDG Desktop Portal and PipeWire."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_session: Optional[ScreenCastSession] = None
        self._has_gio, self._has_gst = self._detect_subsystems()

    def _detect_subsystems(self) -> tuple[bool, bool]:
        """Verify presence of required GLib/Gio and GStreamer PipeWire elements."""
        has_gio = False
        has_gst = False
        try:
            import gi
            gi.require_version("Gio", "2.0")
            from gi.repository import Gio
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            has_gio = bus is not None
        except Exception as e:
            logger.debug(f"Gio D-Bus unavailable: {e}")

        try:
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst
            Gst.init(None)
            factory = Gst.ElementFactory.find("pipewiresrc")
            has_gst = factory is not None
        except Exception as e:
            logger.debug(f"GStreamer pipewiresrc unavailable: {e}")

        return has_gio, has_gst

    def is_available(self) -> bool:
        """Check if native Wayland portal screen sharing is available in this environment."""
        is_wayland = os.environ.get("XDG_SESSION_TYPE") == "wayland" or "WAYLAND_DISPLAY" in os.environ
        return is_wayland and self._has_gio and self._has_gst

    def get_capabilities(self) -> Dict[str, Any]:
        """Report truthful diagnostic capabilities of the portal/PipeWire stack."""
        return {
            "portal_available": self._has_gio,
            "pipewiresrc_available": self._has_gst,
            "is_wayland": os.environ.get("XDG_SESSION_TYPE") == "wayland" or "WAYLAND_DISPLAY" in os.environ,
            "session_active": self._active_session.is_active if self._active_session else False,
            "active_node_id": self._active_session.primary_node_id if self._active_session else None,
        }

    def request_screencast_session(
        self,
        cursor_mode: int = 2,  # 1=Hidden, 2=Embedded, 4=Metadata
        persist_mode: int = 1, # 0=None, 1=Transient, 2=Persistent
        parent_window: str = "",
        timeout_seconds: float = 30.0,
    ) -> ScreenCastSession:
        """Initiate native OS permission dialog via org.freedesktop.portal.ScreenCast.

        Raises:
            ScreenAccessDeniedError: If the user cancels or denies screen access in the dialog.
            RuntimeError: If D-Bus or portal subsystems fail.
        """
        if not self._has_gio:
            raise RuntimeError("Cannot request ScreenCast: Gio D-Bus subsystem is not available.")

        with self._lock:
            # If an active valid session exists, return it
            if self._active_session and self._active_session.is_active:
                return self._active_session

            session_id = f"zetta_session_{int(time.time() * 1000)}"
            request_token = f"zetta_req_{int(time.time() * 1000)}"

            # Call portal helper script via separate python subprocess to guarantee clean GLib MainLoop isolation
            script = f"""
import sys
import json
import gi
gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gio, GLib

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
loop = GLib.MainLoop()
output = {{"status": "ERROR", "streams": [], "restore_token": None}}

session_handle = None

def on_session_created(conn, sender, obj_path, iface, signal, params, user_data):
    global session_handle
    code, results = params.unpack()
    if code != 0 or "session_handle" not in results:
        output["status"] = "DENIED"
        loop.quit()
        return
    session_handle = results["session_handle"]

    # Step 2: SelectSources
    select_opts = {{
        "types": GLib.Variant("u", 1 | 2), # Monitor or Window
        "multiple": GLib.Variant("b", False),
        "cursor_mode": GLib.Variant("u", {cursor_mode}),
        "persist_mode": GLib.Variant("u", {persist_mode}),
        "handle_token": GLib.Variant("s", "{request_token}_sources")
    }}
    bus.call_sync(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.ScreenCast",
        "SelectSources",
        GLib.Variant("(oa{{sv}})", (session_handle, select_opts)),
        GLib.VariantType("(o)"),
        Gio.DBusCallFlags.NONE,
        -1,
        None
    )

    # Step 3: Start
    start_opts = {{
        "handle_token": GLib.Variant("s", "{request_token}_start")
    }}
    start_res = bus.call_sync(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.ScreenCast",
        "Start",
        GLib.Variant("(osa{{sv}})", (session_handle, "{parent_window}", start_opts)),
        GLib.VariantType("(o)"),
        Gio.DBusCallFlags.NONE,
        -1,
        None
    )
    start_req_path = start_res.unpack()[0]
    bus.signal_subscribe(
        "org.freedesktop.portal.Desktop",
        "org.freedesktop.portal.Request",
        "Response",
        start_req_path,
        None,
        Gio.DBusSignalFlags.NONE,
        on_start_response,
        None
    )

def on_start_response(conn, sender, obj_path, iface, signal, params, user_data):
    code, results = params.unpack()
    if code == 0 and "streams" in results:
        output["status"] = "ACTIVE"
        output["session_handle"] = session_handle
        output["restore_token"] = results.get("restore_token")
        for stream in results["streams"]:
            node_id = stream[0]
            props = stream[1]
            output["streams"].append({{"node_id": node_id, "properties": dict(props)}})
    else:
        output["status"] = "DENIED"
    loop.quit()

try:
    # Step 1: CreateSession
    create_opts = {{
        "session_handle_token": GLib.Variant("s", "{session_id}"),
        "handle_token": GLib.Variant("s", "{request_token}_create")
    }}
    create_res = bus.call_sync(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.ScreenCast",
        "CreateSession",
        GLib.Variant("(a{{sv}})", (create_opts,)),
        GLib.VariantType("(o)"),
        Gio.DBusCallFlags.NONE,
        -1,
        None
    )
    req_path = create_res.unpack()[0]
    bus.signal_subscribe(
        "org.freedesktop.portal.Desktop",
        "org.freedesktop.portal.Request",
        "Response",
        req_path,
        None,
        Gio.DBusSignalFlags.NONE,
        on_session_created,
        None
    )
    GLib.timeout_add_seconds(int({timeout_seconds}), loop.quit)
    loop.run()
except Exception as exc:
    output["status"] = "ERROR"
    output["error"] = str(exc)

print(json.dumps(output))
"""
            try:
                proc = subprocess.run(
                    ["python3", "-c", script],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds + 5,
                )
            except subprocess.TimeoutExpired:
                # Portal prompt timed out or user did not respond
                sam = get_screen_access_manager()
                sam.revoke_access(reason="Portal prompt timed out")
                raise ScreenAccessDeniedError("ScreenCast portal request timed out waiting for user permission.")

            if proc.returncode != 0:
                logger.error(f"Portal helper process failed: {proc.stderr.strip()}")
                raise RuntimeError(f"Portal helper execution error: {proc.stderr.strip()}")

            import json
            try:
                data = json.loads(proc.stdout.strip())
            except Exception as e:
                raise RuntimeError(f"Failed to parse portal helper output: {proc.stdout} ({e})")

            status = data.get("status")
            if status == "ACTIVE":
                streams = [
                    ScreenCastStreamInfo(node_id=s["node_id"], properties=s.get("properties", {}))
                    for s in data.get("streams", [])
                ]
                session = ScreenCastSession(
                    session_handle=data.get("session_handle", ""),
                    state=ScreenCastSessionState.ACTIVE,
                    streams=streams,
                    restore_token=data.get("restore_token"),
                )
                self._active_session = session

                # Grant ScreenAccessManager session scope
                sam = get_screen_access_manager()
                sam.grant_access(
                    scope=ScreenAccessScope.ALLOW_SESSION,
                    reason="User approved Wayland Desktop Portal ScreenCast",
                )
                logger.info(f"ScreenCast session active with PipeWire Node ID: {session.primary_node_id}")
                return session

            elif status == "DENIED":
                sam = get_screen_access_manager()
                sam.revoke_access(reason="User rejected Wayland ScreenCast portal prompt")
                # GUARANTEE: Denied portal request must remain denied; NO silent fallback!
                raise ScreenAccessDeniedError("ScreenCast permission denied by user via native desktop portal.")
            else:
                err = data.get("error", "Unknown portal error")
                raise RuntimeError(f"ScreenCast portal error: {err}")

    def consume_latest_frame(self, session: Optional[ScreenCastSession] = None, timeout_seconds: float = 2.0) -> Optional[bytes]:
        """Pull the latest frame from the PipeWire stream using GStreamer appsink.

        Returns:
            PNG bytes of the latest frame if available.
        Raises:
            ScreenAccessDeniedError: If screen access is not authorized.
            RuntimeError: If session is inactive or stream negotiation fails.
        """
        sam = get_screen_access_manager()
        sam.require_access()

        target_session = session or self._active_session
        if not target_session or not target_session.is_active or not target_session.primary_node_id:
            raise RuntimeError("No active ScreenCast session available to consume frames from.")

        node_id = target_session.primary_node_id

        # Use GStreamer pipeline to capture one frame from PipeWire
        # pipewiresrc path=<node_id> ! videoconvert ! pngenc ! fdsink
        gst_cmd = [
            "gst-launch-1.0",
            "-q",
            "pipewiresrc",
            f"path={node_id}",
            "num-buffers=1",
            "!",
            "videoconvert",
            "!",
            "pngenc",
            "!",
            "fdsink",
        ]
        try:
            res = subprocess.run(gst_cmd, capture_output=True, timeout=timeout_seconds)
            if res.returncode == 0 and res.stdout and len(res.stdout) > 8 and res.stdout.startswith(b"\x89PNG"):
                return res.stdout
            else:
                stderr = res.stderr.decode("utf-8", errors="replace").strip()
                logger.warning(f"GStreamer PipeWire capture failed: {stderr}")
                return None
        except subprocess.TimeoutExpired:
            logger.warning("GStreamer PipeWire frame extraction timed out.")
            return None
        except Exception as e:
            logger.error(f"GStreamer error during PipeWire frame capture: {e}")
            return None

    def close_session(self, session: Optional[ScreenCastSession] = None) -> None:
        """Close the portal session handle and release PipeWire resources."""
        with self._lock:
            target = session or self._active_session
            if not target:
                return

            if target.session_handle and self._has_gio:
                try:
                    import gi
                    gi.require_version("Gio", "2.0")
                    from gi.repository import Gio, GLib
                    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
                    bus.call_sync(
                        "org.freedesktop.portal.Desktop",
                        target.session_handle,
                        "org.freedesktop.portal.Session",
                        "Close",
                        None,
                        None,
                        Gio.DBusCallFlags.NONE,
                        1000,
                        None,
                    )
                except Exception as e:
                    logger.debug(f"Error closing portal session: {e}")

            target.state = ScreenCastSessionState.CLOSED
            if target == self._active_session:
                self._active_session = None

            logger.info("ScreenCast session closed.")


_portal_screencast_provider: Optional[WaylandPortalScreenCastProvider] = None


def get_portal_screencast_provider() -> WaylandPortalScreenCastProvider:
    """Singleton getter for WaylandPortalScreenCastProvider."""
    global _portal_screencast_provider
    if _portal_screencast_provider is None:
        _portal_screencast_provider = WaylandPortalScreenCastProvider()
    return _portal_screencast_provider
