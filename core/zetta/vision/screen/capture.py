"""Screen Capture Abstraction for ZETTA Phase 05."""

import time
from abc import ABC, abstractmethod
from typing import List, Optional
from core.zetta.vision.models.results import ScreenInfo, ScreenCapture


class ScreenCaptureProvider(ABC):
    """Abstract base for screen capture providers."""

    @abstractmethod
    def get_displays(self) -> List[ScreenInfo]:
        """Get list of available displays/monitors."""
        pass

    @abstractmethod
    def capture_screen(self, display_id: Optional[str] = None, save_to_disk: bool = False) -> ScreenCapture:
        """Capture screen. If display_id is None, capture primary display."""
        pass

    @abstractmethod
    def get_primary_display(self) -> Optional[ScreenInfo]:
        """Get primary display info."""
        pass


class ScreenCaptureError(Exception):
    """Exception for screen capture failures."""
    pass


class LinuxScreenCaptureProvider(ScreenCaptureProvider):
    """Linux screen capture supporting Wayland Portal, native CLI tools, and Python mss."""

    def __init__(self):
        self._available_tools = self._detect_tools()

    def _detect_tools(self) -> List[str]:
        """Detect available screenshot tools/backends on Linux."""
        import shutil
        tools = []

        # Desktop Portal via DBus is available on modern Wayland/Linux desktops
        tools.append("portal")

        for tool in ["grim", "gnome-screenshot", "spectacle", "flameshot", "maim", "import", "scrot"]:
            if shutil.which(tool):
                tools.append(tool)

        try:
            import mss
            tools.append("mss")
        except ImportError:
            pass

        return tools

    def _is_black_image(self, image_bytes: bytes) -> bool:
        """Check if captured image consists entirely of black pixels (X11/Wayland restriction)."""
        try:
            import io
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))
            extrema = img.getextrema()
            if isinstance(extrema, (list, tuple)) and len(extrema) >= 3:
                r_max = extrema[0][1] if isinstance(extrema[0], tuple) else extrema[0]
                g_max = extrema[1][1] if isinstance(extrema[1], tuple) else extrema[1]
                b_max = extrema[2][1] if isinstance(extrema[2], tuple) else extrema[2]
                if r_max == 0 and g_max == 0 and b_max == 0:
                    return True
        except Exception:
            pass
        return False

    def get_displays(self) -> List[ScreenInfo]:
        """Get display information using mss, xrandr, or xdpyinfo."""
        displays = []

        try:
            import mss
            mss_cls = getattr(mss, "MSS", mss.mss)
            with mss_cls() as sct:
                for i, monitor in enumerate(sct.monitors):
                    if i == 0:
                        continue
                    output_name = monitor.get("output", f"display-{i}")
                    displays.append(ScreenInfo(
                        name=output_name,
                        display_name=output_name,
                        width=monitor["width"],
                        height=monitor["height"],
                        x=monitor["left"],
                        y=monitor["top"],
                        is_primary=monitor.get("is_primary", i == 1),
                    ))
        except Exception:
            pass

        if not displays:
            try:
                import subprocess
                result = subprocess.run(
                    ["xrandr", "--query"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    displays = self._parse_xrandr(result.stdout)
            except Exception:
                pass

        if not displays:
            try:
                import subprocess
                result = subprocess.run(
                    ["xdpyinfo"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    displays = self._parse_xdpyinfo(result.stdout)
            except Exception:
                pass

        if not displays:
            displays = [ScreenInfo(
                name="primary",
                display_name="Primary Display",
                width=1920,
                height=1080,
                is_primary=True,
            )]

        return displays

    def _parse_xrandr(self, output: str) -> List[ScreenInfo]:
        """Parse xrandr output for display info."""
        displays = []
        lines = output.strip().split('\n')
        for i, line in enumerate(lines):
            if ' connected' in line:
                parts = line.split()
                name = parts[0]
                is_primary = 'primary' in parts
                
                width, height = 1920, 1080
                x, y = 0, 0
                
                for j in range(i + 1, min(i + 10, len(lines))):
                    if 'x' in lines[j] and '+' in lines[j]:
                        res_part = lines[j].strip().split()[0]
                        if 'x' in res_part and '+' in res_part:
                            res_xy = res_part.split('+')
                            wh = res_xy[0].split('x')
                            if len(wh) == 2:
                                width = int(wh[0])
                                height = int(wh[1])
                            if len(res_xy) >= 3:
                                x = int(res_xy[1])
                                y = int(res_xy[2])
                        break
                
                displays.append(ScreenInfo(
                    name=name,
                    display_name=name,
                    width=width,
                    height=height,
                    x=x,
                    y=y,
                    is_primary=is_primary,
                ))
        return displays

    def _parse_xdpyinfo(self, output: str) -> List[ScreenInfo]:
        """Parse xdpyinfo output for screen dimensions."""
        import re
        displays = []
        
        dim_match = re.search(r'dimensions:\s+(\d+)x(\d+)', output)
        if dim_match:
            width = int(dim_match.group(1))
            height = int(dim_match.group(2))
            displays.append(ScreenInfo(
                name="screen0",
                display_name="X Screen 0",
                width=width,
                height=height,
                is_primary=True,
            ))
        
        return displays

    def get_primary_display(self) -> Optional[ScreenInfo]:
        """Get primary display."""
        displays = self.get_displays()
        for d in displays:
            if d.is_primary:
                return d
        return displays[0] if displays else None

    def capture_screen(self, display_id: Optional[str] = None, save_to_disk: bool = False) -> ScreenCapture:
        """Capture screen using best available tool with detailed error handling."""
        start_time = time.perf_counter()
        
        if not self._available_tools:
            raise ScreenCaptureError(
                "No screenshot tools available. Install mss (pip install mss), grim, gnome-screenshot, spectacle, maim, or scrot."
            )

        display = None
        if display_id:
            for d in self.get_displays():
                if d.name == display_id or d.id == display_id or d.display_name == display_id:
                    display = d
                    break
        else:
            display = self.get_primary_display()

        if not display:
            raise ScreenCaptureError(f"No display found matching '{display_id}' to capture")

        backend_errors = {}
        for tool in self._available_tools:
            try:
                image_data = self._capture_with_tool(tool, display)
                if image_data and len(image_data) > 0:
                    if self._is_black_image(image_data):
                        backend_errors[tool] = "Captured 100% black image (X11 / Wayland window permission restriction)"
                        continue

                    saved_path_str = None
                    if save_to_disk:
                        import os
                        from pathlib import Path

                        try:
                            from core.zetta.config import get_settings
                            root_path = get_settings().root_path
                        except Exception:
                            root_path = Path(__file__).resolve().parents[4]

                        runtime_dir = (root_path / "runtime" / "captures").resolve()
                        runtime_dir.mkdir(parents=True, exist_ok=True)

                        display_clean = (display.name or "display").replace("/", "_")
                        filename = f"capture_{int(time.time() * 1000)}_{display_clean}.png"
                        saved_path = runtime_dir / filename
                        with open(saved_path, "wb") as f:
                            f.write(image_data)

                        saved_path_str = str(saved_path)

                    duration_ms = (time.perf_counter() - start_time) * 1000
                    return ScreenCapture(
                        image_data=image_data,
                        width=display.width,
                        height=display.height,
                        format="png",
                        source_display=display.name,
                        file_path=saved_path_str,
                        duration_ms=duration_ms,
                    )

                else:
                    backend_errors[tool] = "Captured 0 bytes (empty output file or silent failure)"
            except Exception as e:
                backend_errors[tool] = str(e)

        error_details = "\n".join(f"  - {backend}: {err}" for backend, err in backend_errors.items())
        raise ScreenCaptureError(f"All capture backends failed:\n{error_details}")

    def _capture_with_tool(self, tool: str, display: ScreenInfo) -> Optional[bytes]:
        """Capture using specific backend tool."""
        if tool == "portal":
            return self._capture_via_portal()

        if tool == "mss":
            import mss
            import mss.tools
            mss_cls = getattr(mss, "MSS", mss.mss)
            with mss_cls() as sct:
                target_mon = None
                for i, mon in enumerate(sct.monitors):
                    if i == 0:
                        continue
                    if mon.get("output") == display.name or mon.get("output") == display.display_name:
                        target_mon = mon
                        break
                if not target_mon and len(sct.monitors) > 1:
                    target_mon = sct.monitors[1]
                elif not target_mon:
                    target_mon = sct.monitors[0]

                sct_img = sct.grab(target_mon)
                png_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
                return png_bytes

        import subprocess
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            if tool == "grim":
                cmd = ["grim", tmp_path]
            elif tool == "gnome-screenshot":
                cmd = ["gnome-screenshot", "-f", tmp_path]
            elif tool == "spectacle":
                cmd = ["spectacle", "-b", "-n", "-o", tmp_path]
            elif tool == "scrot":
                cmd = ["scrot", "-z", tmp_path]
            elif tool == "import":
                cmd = ["import", "-window", "root", tmp_path]
            elif tool == "maim":
                cmd = ["maim", tmp_path]
            elif tool == "flameshot":
                cmd = ["flameshot", "full", "-r"]
            else:
                raise ValueError(f"Unsupported tool: {tool}")

            if tool == "flameshot":
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                if result.returncode != 0:
                    stderr = result.stderr.decode().strip() if result.stderr else ""
                    raise RuntimeError(f"Exit code {result.returncode}. Stderr: {stderr}")
                return result.stdout

            result = subprocess.run(cmd, capture_output=True, timeout=10)
            if result.returncode != 0:
                stderr = result.stderr.decode().strip() if result.stderr else ""
                raise RuntimeError(f"Exit code {result.returncode}. Stderr: {stderr}")

            if os.path.exists(tmp_path):
                file_size = os.path.getsize(tmp_path)
                if file_size == 0:
                    raise RuntimeError("Output file was created but is 0 bytes (empty)")
                with open(tmp_path, "rb") as f:
                    data = f.read()
                return data
            else:
                raise RuntimeError("Output file was not created by screenshot tool")

        finally:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass

    def _capture_via_portal(self) -> Optional[bytes]:
        """Capture screen via org.freedesktop.portal.Screenshot DBus Desktop Portal."""
        import subprocess
        import urllib.parse
        import os

        script = """
import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib
import urllib.parse, os

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
captured_path = []

def on_signal(connection, sender_name, object_path, interface_name, signal_name, parameters, user_data):
    response_code, results = parameters.unpack()
    if response_code == 0 and "uri" in results:
        uri = results["uri"]
        path = urllib.parse.unquote(urllib.parse.urlparse(uri).path)
        captured_path.append(path)
    loop.quit()

try:
    call_res = bus.call_sync(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.Screenshot",
        "Screenshot",
        GLib.Variant("(sa{sv})", ("", {"interactive": GLib.Variant("b", False)})),
        GLib.VariantType("(o)"),
        Gio.DBusCallFlags.NONE,
        -1,
        None
    )
    request_path = call_res.unpack()[0]
    bus.signal_subscribe(
        "org.freedesktop.portal.Desktop",
        "org.freedesktop.portal.Request",
        "Response",
        request_path,
        None,
        Gio.DBusSignalFlags.NONE,
        on_signal,
        None
    )
    loop = GLib.MainLoop()
    GLib.timeout_add_seconds(5, loop.quit)
    loop.run()

    if captured_path:
        print(captured_path[0])
except Exception as e:
    pass
"""
        res = subprocess.run(["python3", "-c", script], capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            img_path = res.stdout.strip()
            if os.path.exists(img_path):
                try:
                    with open(img_path, "rb") as f:
                        data = f.read()
                    return data
                finally:
                    try:
                        os.unlink(img_path)
                    except Exception:
                        pass
        return None



class FakeScreenCaptureProvider(ScreenCaptureProvider):
    """Deterministic fake screen capture for testing."""

    def __init__(self, fake_displays: Optional[List[ScreenInfo]] = None):
        self._fake_displays = fake_displays or [
            ScreenInfo(
                name="fake-primary",
                display_name="Fake Primary Display",
                width=1920,
                height=1080,
                x=0,
                y=0,
                is_primary=True,
                scale_factor=1.0,
                refresh_rate=60,
            ),
            ScreenInfo(
                name="fake-secondary",
                display_name="Fake Secondary Display",
                width=1920,
                height=1080,
                x=1920,
                y=0,
                is_primary=False,
                scale_factor=1.0,
                refresh_rate=60,
            ),
        ]
        self._capture_count = 0

    def get_displays(self) -> List[ScreenInfo]:
        return self._fake_displays.copy()

    def get_primary_display(self) -> Optional[ScreenInfo]:
        for d in self._fake_displays:
            if d.is_primary:
                return d
        return self._fake_displays[0] if self._fake_displays else None

    def capture_screen(self, display_id: Optional[str] = None, save_to_disk: bool = False) -> ScreenCapture:
        """Return a deterministic fake screenshot."""
        self._capture_count += 1
        
        display = None
        if display_id:
            for d in self._fake_displays:
                if d.name == display_id or d.id == display_id:
                    display = d
                    break
        else:
            display = self.get_primary_display()

        if not display:
            display = self._fake_displays[0]

        fake_png = self._generate_fake_png(display.width, display.height, self._capture_count)
        
        file_path = "runtime/captures/fake_capture.png" if save_to_disk else None

        return ScreenCapture(
            image_data=fake_png,
            width=display.width,
            height=display.height,
            format="png",
            source_display=display.name,
            file_path=file_path,
            duration_ms=1.5,
            metadata={"capture_count": self._capture_count, "fake": True},
        )

    def _generate_fake_png(self, width: int, height: int, seed: int) -> bytes:
        """Generate a deterministic fake PNG."""
        import zlib
        
        png = b'\x89PNG\r\n\x1a\n'
        
        ihdr_data = (
            width.to_bytes(4, 'big') +
            height.to_bytes(4, 'big') +
            b'\x08\x02\x00\x00\x00'
        )
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
        png += len(ihdr_data).to_bytes(4, 'big') + b'IHDR' + ihdr_data + ihdr_crc.to_bytes(4, 'big')
        
        raw_data = bytearray()
        for y in range(height):
            raw_data.append(0)
            for x in range(width):
                r = (x * 255) // width
                g = (y * 255) // height
                b = (seed * 50 + x + y) % 256
                raw_data.extend([r, g, b])
        
        compressed = zlib.compress(bytes(raw_data), level=1)
        idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
        png += len(compressed).to_bytes(4, 'big') + b'IDAT' + compressed + idat_crc.to_bytes(4, 'big')
        
        iend_crc = zlib.crc32(b'IEND') & 0xffffffff
        png += b'\x00\x00\x00\x00IEND' + iend_crc.to_bytes(4, 'big')
        
        return png


def get_screen_capture_provider(use_fake: bool = False) -> ScreenCaptureProvider:
    """Factory function to get appropriate screen capture provider."""
    if use_fake:
        return FakeScreenCaptureProvider()
    return LinuxScreenCaptureProvider()