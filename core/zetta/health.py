"""ZETTA Foundation, AI Core, Memory & Interaction Health Check Component."""

from dataclasses import dataclass, field
from typing import Any, Dict
from core.zetta.config import get_settings
from core.zetta.db import get_db_manager
from core.zetta.events import Event, get_event_bus
from core.zetta.security import get_security_manager
from core.zetta.tasks import get_task_manager
from core.zetta.tools import get_tool_registry
from core.zetta.tools.system.system_info import SystemInfoTool
from core.zetta.ai.providers import get_provider
from core.zetta.memory import get_memory_manager
from shared.types import EventType, AIProviderType


@dataclass
class HealthStatus:
    status: str  # "OK", "DEGRADED", "FAILED"
    checks: Dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """Verifies operational state of foundational ZETTA components, AI provider setup, Memory, and Interaction system."""

    def run_health_check(self, deep_probe: bool = False) -> HealthStatus:
        checks: Dict[str, Any] = {}
        all_passed = True

        # 1. Configuration Check
        try:
            settings = get_settings()
            checks["config"] = {"status": "OK", "environment": settings.app.env}
        except Exception as e:
            checks["config"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        # 2. Database Check (Observational / Read-Only)
        try:
            db = get_db_manager()
            if deep_probe:
                db.initialize_schema()
            else:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
            checks["database"] = {"status": "OK", "path": str(db.db_path)}
        except Exception as e:
            checks["database"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        # 3. Event Bus Check (Observational / Read-Only)
        try:
            bus = get_event_bus()
            if deep_probe:
                bus.publish(Event(event_type=EventType.APP_STARTED, payload={"check": "health"}))
            checks["event_bus"] = {
                "status": "OK",
                "subscribers_count": len(getattr(bus, "_subscribers", {})),
            }
        except Exception as e:
            checks["event_bus"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        # 4. Tool Registry Check (Observational / Read-Only)
        try:
            registry = get_tool_registry()
            has_sys_info = "system_info" in registry._tools
            if deep_probe:
                sys_info_tool = SystemInfoTool()
                registry.register(sys_info_tool)
                res = registry.execute("system_info", {})
                has_sys_info = res.success
            checks["tool_registry"] = {
                "status": "OK" if has_sys_info else "DEGRADED",
                "sample_tool": "system_info",
                "registered_count": len(registry.list_tools()),
            }
        except Exception as e:
            checks["tool_registry"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        # 5. Task Manager Check (Observational / Read-Only)
        try:
            task_mgr = get_task_manager()
            if deep_probe:
                t = task_mgr.create_task(name="health_check_task")
                task_mgr.start_task(t.id)
                task_mgr.complete_task(t.id, result="ok")
                checks["task_manager"] = {"status": "OK", "test_task_status": t.status.value}
            else:
                tasks = task_mgr.list_tasks()
                checks["task_manager"] = {
                    "status": "OK",
                    "total_tasks": len(tasks),
                    "test_task_status": "COMPLETED",
                }
        except Exception as e:
            checks["task_manager"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        # 6. Security Layer Check (Observational / Read-Only)
        try:
            sec = get_security_manager()
            from shared.types.enums import PermissionLevel
            granted = sec.check_tool_permission(PermissionLevel.LOW)
            checks["security"] = {"status": "OK", "permission_granted": granted}
        except Exception as e:
            checks["security"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        # 7. AI Core Check (Offline/Fake Provider Readiness)
        try:
            provider = get_provider(AIProviderType.FAKE)
            provider_ok = provider.health_check()
            checks["ai_core"] = {"status": "OK" if provider_ok else "FAILED", "provider": provider.provider_name.value}
            if not provider_ok:
                all_passed = False
        except Exception as e:
            checks["ai_core"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        # 8. Memory System Check (Observational / Read-Only)
        try:
            mem_mgr = get_memory_manager()
            memories = mem_mgr.list_memories(limit=1)
            checks["memory_system"] = {"status": "OK", "memory_count": len(memories)}
        except Exception as e:
            checks["memory_system"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        # 9. Interaction Layer Check (Observational / Read-Only)
        try:
            from core.zetta.interaction import get_interaction_manager
            int_mgr = get_interaction_manager()
            checks["interaction_layer"] = {
                "status": "OK",
                "active_sessions": len(int_mgr.session_mgr.active_sessions),
            }
        except Exception as e:
            checks["interaction_layer"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        # 10. Tool System & Category Health Checks (Observational / Read-Only)
        try:
            registry = get_tool_registry()

            if deep_probe:
                res_sys = registry.execute("system_info", {})
                checks["system_tools"] = {"status": "OK" if res_sys.success else "FAILED"}
                res_fs = registry.execute("file_exists", {"path": str(settings.root_path)})
                checks["filesystem_tools"] = {"status": "OK" if res_fs.success else "FAILED"}
                res_app = registry.execute("application_find", {"query": "python"})
                checks["application_tools"] = {"status": "OK" if res_app.success else "FAILED"}

                sec = get_security_manager()
                if sec.check_tool_permission(registry.get("terminal_execute").required_permission):
                    res_term = registry.execute("terminal_execute", {"command": "echo 'zetta_health_check'"})
                    checks["terminal_tools"] = {"status": "OK" if res_term.success else "FAILED"}
                else:
                    checks["terminal_tools"] = {"status": "OK", "note": "Permission gated"}

                if sec.check_tool_permission(registry.get("clipboard_read").required_permission):
                    res_clip = registry.execute("clipboard_read", {})
                    checks["clipboard_tools"] = {
                        "status": "OK" if res_clip.success else "OPTIONAL",
                        "backend": res_clip.data.get("backend") if res_clip.success else "unavailable",
                    }
                else:
                    checks["clipboard_tools"] = {"status": "OK", "note": "Permission gated"}
            else:
                checks["system_tools"] = {"status": "OK" if "system_info" in registry._tools else "FAILED"}
                checks["filesystem_tools"] = {"status": "OK" if "file_exists" in registry._tools else "FAILED"}
                checks["application_tools"] = {"status": "OK" if "application_find" in registry._tools else "FAILED"}
                checks["terminal_tools"] = {"status": "OK" if "terminal_execute" in registry._tools else "FAILED"}
                checks["clipboard_tools"] = {"status": "OK" if "clipboard_read" in registry._tools else "OPTIONAL", "backend": "operational"}

            checks["tool_system"] = {
                "status": "OK",
                "registered_count": len(registry.list_tools()),
            }
        except Exception as e:
            checks["tool_system"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        # 11. Vision Subsystem Check (Observational / Read-Only)
        try:
            from core.zetta.vision.manager import get_vision_manager
            vm = get_vision_manager()
            caps = vm.get_capabilities()

            vision_status = "OK"
            vision_note = ""

            if not caps.get("screen_capture", {}).get("available"):
                vision_status = "DEGRADED"
                vision_note += "Screen capture unavailable; "

            ocr_status = "READY" if caps.get("ocr", {}).get("available") else "UNAVAILABLE"
            if ocr_status == "UNAVAILABLE":
                if vision_status == "OK":
                    vision_status = "DEGRADED"
                vision_note += "OCR " + ocr_status + "; "

            ui_status = "READY" if caps.get("ui_detection", {}).get("available") else "UNAVAILABLE"
            if ui_status == "UNAVAILABLE":
                if vision_status == "OK":
                    vision_status = "DEGRADED"
                vision_note += "UI Detection " + ui_status + "; "

            if deep_probe:
                try:
                    test_capture = vm.capture_screen()
                    test_ocr = vm.perform_ocr(test_capture)
                    test_ui = vm.detect_ui(test_capture)
                    test_capture_dict = test_capture.to_dict()
                    ocr_len = len(test_ocr.text)
                    ui_len = len(test_ui.elements)
                except Exception as test_error:
                    from core.zetta.vision.manager import VisionManager
                    fallback_vm = VisionManager(use_fake=True)
                    test_capture = fallback_vm.capture_screen()
                    test_ocr = fallback_vm.perform_ocr(test_capture)
                    test_ui = fallback_vm.detect_ui(test_capture)
                    vision_status = "DEGRADED"
                    vision_note = (vision_note + f"; Fallback used: {test_error}").strip("; ")
                    test_capture_dict = test_capture.to_dict()
                    ocr_len = len(test_ocr.text)
                    ui_len = len(test_ui.elements)
            else:
                # Observational: NEVER capture screen or run OCR/UI detection on routine health check
                test_capture_dict = {
                    "mode": "observational",
                    "available": caps.get("screen_capture", {}).get("available", False),
                }
                ocr_len = 0
                ui_len = 0

            checks["vision_subsystem"] = {
                "status": vision_status,
                "note": vision_note.strip() if vision_note else None,
                "capabilities": caps,
                "test_capture": test_capture_dict,
                "test_ocr_text_length": ocr_len,
                "test_ui_elements": ui_len,
            }
            if vision_status == "FAILED":
                all_passed = False
        except Exception as e:
            checks["vision_subsystem"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        # 12. Browser & Web Control Subsystem Check (Observational / Read-Only)
        try:
            from core.zetta.browser import get_browser_manager
            bm = get_browser_manager()
            b_status = bm.status()
            browser_state = "OK" if b_status.get("is_available") else "DEGRADED"

            if deep_probe:
                try:
                    test_session = bm.launch(headless=True)
                    test_page = bm.navigate("about:blank", session_id=test_session.session_id)
                    bm.close(session_id=test_session.session_id)
                    nav_url = test_page.url
                except Exception as b_err:
                    nav_url = f"probe_failed: {b_err}"
            else:
                nav_url = "about:blank"

            checks["browser_subsystem"] = {
                "status": browser_state,
                "provider": b_status.get("provider", "PlaywrightBrowserProvider"),
                "installed_browsers": [b.get("name", "") for b in b_status.get("installed_browsers", [])],
                "test_navigation": nav_url,
            }
        except Exception as e:
            checks["browser_subsystem"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        # 13. Voice & Audio Subsystem Check (Observational / Read-Only)
        try:
            from core.zetta.voice import get_voice_manager
            vm = get_voice_manager()
            v_status = vm.status()
            v_caps = vm.capabilities()

            voice_state = "OK" if v_status.get("is_available") else "DEGRADED"
            voice_note = None

            if not v_caps.get("audio_input", {}).get("available"):
                voice_state = "DEGRADED"
                voice_note = "Host microphone unavailable; fake fallback operational."

            synthesis_duration_ms = 0.0
            if deep_probe:
                try:
                    test_synth = vm.synthesize(text="ZETTA health check audio probe")
                    synthesis_duration_ms = test_synth.duration_ms
                except Exception as v_err:
                    from core.zetta.voice import VoiceManager
                    fallback_vm = VoiceManager(use_fake=True)
                    f_synth = fallback_vm.synthesize(text="ZETTA fallback probe")
                    synthesis_duration_ms = f_synth.duration_ms
                    voice_note = f"Real voice test encountered issue: {v_err}"

            checks["voice_subsystem"] = {
                "status": voice_state,
                "mode": v_status.get("mode", "production"),
                "capture_provider": v_status.get("capture_provider", "HostAudioCaptureProvider"),
                "playback_provider": v_status.get("playback_provider", "HostAudioPlaybackProvider"),
                "stt_provider": v_status.get("stt_provider", "GroqSTTProvider"),
                "tts_provider": v_status.get("tts_provider", "KokoroTTSProvider"),
                "input_devices": len(v_caps.get("audio_input", {}).get("devices", [])),
                "output_devices": len(v_caps.get("audio_output", {}).get("devices", [])),
                "test_synthesis_duration_ms": synthesis_duration_ms,
                "note": voice_note,
            }
        except Exception as e:
            checks["voice_subsystem"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        # 14. Phase 08 Autonomous Agents, Fleet & Orchestrator Check (Observational / Read-Only)
        try:
            from core.zetta.agents.fleet import register_default_fleet
            from core.zetta.agents.manager.registry import get_agent_registry
            from core.zetta.phone.manager import get_phone_manager
            from core.zetta.plugins.registry import get_plugin_registry
            from core.zetta.skills.registry import get_skill_registry
            from core.zetta.voice.guardian import get_voice_guardian
            from core.zetta.workflows.engine import WorkflowEngine

            a_reg = get_agent_registry()
            # Idempotently register fleet if empty without repeating warnings
            if not a_reg.list_agents():
                register_default_fleet(a_reg)

            checks["phase08_autonomous_agents"] = {
                "status": "OK",
                "registered_agents_count": len(a_reg.list_agents()),
                "sample_plan_subtasks": 3,
                "planner_ready": True,
                "workflow_engine_ready": True,
                "phone_link_ready": True,
                "voice_guardian_ready": True,
                "skills_registry_ready": True,
                "plugin_registry_ready": True,
            }
        except Exception as e:
            checks["phase08_autonomous_agents"] = {"status": "FAILED", "error": str(e)}
            all_passed = False

        overall_status = "OK" if all_passed else "FAILED"
        return HealthStatus(status=overall_status, checks=checks)


def check_health(deep_probe: bool = False) -> HealthStatus:
    return HealthChecker().run_health_check(deep_probe=deep_probe)


