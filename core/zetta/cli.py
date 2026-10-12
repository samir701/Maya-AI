"""ZETTA CLI Entry Point."""

import json
import os
import sys
import time
from pathlib import Path

# Ensure project root directory is on sys.path dynamically regardless of execution CWD
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.zetta.health import check_health
from core.zetta.ai.brain import get_ai_brain
from core.zetta.interaction.chat import ChatShell
from core.zetta.interaction.commands import CommandProcessor
from core.zetta.memory import get_memory_manager
from core.zetta.utils.logging import get_logger
from shared.types import AIProviderType, MemorySource, MemoryType

logger = get_logger("cli")


def print_help() -> None:
    print("""
==================================================
ZETTA AI EMPLOYEE — COMMAND LINE INTERFACE (CLI)
==================================================

Usage:
  python3 core/zetta/cli.py [command] [options]

Available Commands:
  (no args)             Run system foundation, AI core & memory health check.
  ui [--port=8000]     Launch the ZETTA Desktop Operating Console UI.
  chat [--real]        Launch interactive shell session (default: deterministic fake).
  task create <desc>   Create a new system task.
  task list            List registered tasks.
  task get <task_id>   Fetch task details by ID.
  task cancel <id>     Cancel a task by ID.
  ai-test [--real]     Run AI brain inference test (default: deterministic fake).
  memory list          List stored memories in SQLite repository.
  memory add <text>    Add a new long-term user memory.
  memory get <id>      Fetch memory details by ID.
  memory delete <id>   Delete a memory by ID.
  memory search <q>    Search/retrieve relevant memories matching query text.
  memory clear-session <sess_id>  Clear ephemeral short-term session memories.
  browser status [--fake]         Show browser status and installed drivers.
  browser launch [--fake]         Launch a browser session.
  browser navigate <url> [--fake] Navigate to web address.
  browser page [--fake]           Show active webpage information.
  browser elements [--fake]       Detect clickable elements on current page.
  browser click <target> [--fake] Click element by ID, selector, or text.
  browser type <target> <text>    Type text into input field.
  browser scroll <dir> [--fake]   Scroll page (up, down, top, bottom).
  browser history <action>        Navigate history (back, forward, reload).
  browser screenshot [--fake]     Capture visual screenshot of webpage.
  browser close [--fake]          Close active browser session.
  voice status [--fake]           Show audio devices and STT/TTS availability.
  voice test-input [--fake]       Record test audio clip from microphone.
  voice test-output [--fake]      Play test tone through speaker.
  voice stt <audio_file> [--fake] Transcribe audio file to text.
  voice tts <text> [--fake]       Synthesize text to speech.
  voice listen [--fake]           Single-turn listen and transcribe.
  voice turn [--fake]             Full conversational voice turn with tool execution.
  agent list                      List registered autonomous agents in fleet.
  agent status <name_or_id>       Inspect agent status and capabilities.
  agent run <name> <task>         Dispatch a task directly to an agent.
  agent cancel <name_or_id>       Cancel a running agent.
  plan create <goal>              Decompose goal into structured DAG plan.
  plan inspect <goal>             Inspect task graph and dependency order.
  skill list                      List registered reusable skills.
  skill inspect <name>            View inputs/outputs schema for skill.
  persona list                    List available personas (default, professional, creative).
  persona switch <type>           Switch active persona.
  workflow run <goal>             Execute goal through Unified Autonomous Workflow.
  bgjob list                      List background jobs and progress.
  bgjob cancel <job_id>           Cancel a background job.
  phone status                    Inspect Desktop-Mobile phone link status.
  phone pair <pairing_code>       Pair with mobile device.
  phone disconnect                Disconnect paired device.
  phone ping                      Ping paired mobile device.
  --help, -h           Show this help message.
""")



def run_ai_test(use_real: bool = False) -> None:
    print("==================================================")
    print("RUNNING ZETTA AI CORE TEST COMMAND")
    print("==================================================")
    from core.zetta.config import get_settings
    settings = get_settings()
    configured_provider = settings.ai.default_provider.lower()
    if use_real:
        try:
            provider_type = AIProviderType(configured_provider)
        except ValueError:
            provider_type = AIProviderType.GROQ if getattr(settings.ai, "groq_api_key", None) else AIProviderType.OPENAI
    else:
        provider_type = AIProviderType.FAKE
    print(f"Using Provider Mode: {'REAL (' + provider_type.value.upper() + ')' if use_real else 'DETERMINISTIC FAKE (Offline)'}")

    try:
        brain = get_ai_brain()
        response = brain.think(
            prompt="Hello ZETTA! Confirm AI core initialization.",
            provider_type=provider_type,
        )
        print("--------------------------------------------------")
        print(f"Provider: {response.provider.value}")
        print(f"Model: {response.model}")
        print(f"Tokens: {response.usage.total_tokens}")
        print(f"Duration: {response.usage.duration_ms:.2f}ms")
        print(f"AI Response Text: {response.text}")
        print("--------------------------------------------------")
        print("AI Core test executed successfully!")
    except Exception as e:
        print(f"AI Core test failed: {e}")
        sys.exit(1)


def handle_memory_cli(args: list) -> None:
    """Handle memory management CLI commands."""
    mem_mgr = get_memory_manager()
    subcommand = args[0] if args else "list"

    if subcommand in ["--help", "-h"]:
        print("""
Memory CLI Usage:
  python3 core/zetta/cli.py memory list
  python3 core/zetta/cli.py memory add <content>
  python3 core/zetta/cli.py memory get <memory_id>
  python3 core/zetta/cli.py memory delete <memory_id>
  python3 core/zetta/cli.py memory search <query_text>
  python3 core/zetta/cli.py memory clear-session <session_id>
""")
        return

    if subcommand == "list":
        memories = mem_mgr.list_memories()
        print(f"Stored Memories Count: {len(memories)}")
        for m in memories:
            print(f" - [{m.id[:8]}] ({m.memory_type.value.upper()}) (Source: {m.source.value}): {m.content}")

    elif subcommand == "add" and len(args) > 1:
        content = " ".join(args[1:])
        mem = mem_mgr.add_memory(content, memory_type=MemoryType.LONG_TERM, source=MemorySource.USER_EXPLICIT)
        print(f"Added Long-Term Memory [ID: {mem.id}]: '{mem.content}'")

    elif subcommand == "get" and len(args) > 1:
        mem_id = args[1]
        mem = mem_mgr.repo.get(mem_id)
        if mem:
            print(json.dumps(mem.to_dict(), indent=2))
        else:
            print(f"Memory with ID '{mem_id}' not found.")

    elif subcommand == "delete" and len(args) > 1:
        mem_id = args[1]
        success = mem_mgr.delete_memory(mem_id)
        print(f"Deleted Memory '{mem_id}': {success}")

    elif subcommand == "search" and len(args) > 1:
        query_text = " ".join(args[1:])
        results = mem_mgr.retrieve_relevant(query_text)
        print(f"Retrieved {len(results)} relevant memories for query '{query_text}':")
        for r in results:
            print(f" - [{r.memory.id[:8]}] (Score: {r.score:.3f}) {r.memory.content}")
            print(f"   Breakdown: {r.breakdown}")

    elif subcommand == "clear-session" and len(args) > 1:
        session_id = args[1]
        cleared = mem_mgr.short_term.clear_session(session_id)
        print(f"Cleared {cleared} short-term memories for session '{session_id}'")

def handle_tools_cli(args: list) -> None:
    """Handle tool inspection and execution CLI commands."""
    from core.zetta.tools import get_tool_registry
    registry = get_tool_registry()

    subcommand = args[0] if args else "list"

    if subcommand in ["--help", "-h"]:
        print("""
Tools CLI Usage:
  python core/zetta/cli.py tools list
  python core/zetta/cli.py tools info <tool_name>
  python core/zetta/cli.py tools run <tool_name> [--key val ... | json_str]
""")
        return

    if subcommand == "list":
        tools = registry.list_tools()
        print(f"Registered Tools ({len(tools)}):")
        for t in tools:
            print(f" - {t['name']:<24} [{t['required_permission']:<8}] ({t.get('category', 'general')}) {t['description']}")

    elif subcommand == "info" and len(args) > 1:
        name = args[1]
        try:
            tool = registry.get(name)
            print(json.dumps(tool.get_metadata(), indent=2))
        except Exception as e:
            print(f"Error: {e}")

    elif subcommand == "run" and len(args) > 1:
        name = args[1]
        input_data = {}
        remaining = args[2:]

        if len(remaining) == 1 and remaining[0].startswith("{"):
            try:
                input_data = json.loads(remaining[0])
            except Exception:
                pass
        else:
            i = 0
            while i < len(remaining):
                arg = remaining[i]
                if arg.startswith("--") and i + 1 < len(remaining):
                    key = arg[2:]
                    val = remaining[i + 1]
                    if val.isdigit():
                        val = int(val)
                    elif val.lower() == "true":
                        val = True
                    elif val.lower() == "false":
                        val = False
                    input_data[key] = val
                    i += 2
                else:
                    i += 1

        try:
            def cli_confirm(msg: str) -> bool:
                ans = input(f"[CONFIRMATION REQUIRED] {msg} [y/N]: ").strip().lower()
                return ans in ["y", "yes"]

            result = registry.execute(name, input_data, confirmation_callback=cli_confirm)
            print("==================================================")
            print(f"Tool Execution Result: {result.tool_name}")
            print(f"Success: {result.success}")
            print(f"Duration: {result.execution_time_ms:.2f}ms")
            print("Data:")
            print(json.dumps(result.data, indent=2) if isinstance(result.data, (dict, list)) else result.data)
            if result.error:
                print(f"Error: {result.error.message}")
            print("==================================================")
        except Exception as e:
            print(f"Tool Execution Error: {e}")
            sys.exit(1)
    else:
        print("Usage: python core/zetta/cli.py tools <list|info|run> [args]")


def handle_vision_cli(args: list) -> None:
    """Handle vision CLI commands."""
    from core.zetta.vision.manager import VisionManager, get_vision_manager
    from core.zetta.vision.screen.capture import ScreenCaptureError

    use_fake = "--fake" in args
    clean_args = [a for a in args if a != "--fake"]

    if use_fake:
        vm = VisionManager(use_fake=True)
    else:
        vm = get_vision_manager()

    subcommand = clean_args[0] if clean_args else "info"

    if subcommand in ["--help", "-h", "help"]:
        print("""
Vision CLI Usage:
  python core/zetta/cli.py vision info [--fake]          # Show display info
  python core/zetta/cli.py vision capture [--fake]       # Capture screenshot
  python core/zetta/cli.py vision ocr [--fake]           # Perform OCR on screen
  python core/zetta/cli.py vision detect [--fake]        # Detect UI elements
  python core/zetta/cli.py vision analyze [--fake]       # Full screen analysis
""")
        return

    try:
        if subcommand == "info":
            info = vm.get_screen_info()
            print(f"Primary Display: {info.display_name} ({info.width}x{info.height})")
            all_displays = vm.get_all_displays()
            print(f"Total Displays: {len(all_displays)}")
            for d in all_displays:
                print(f"  - {d.name}: {d.width}x{d.height} @ ({d.x},{d.y}) {'[PRIMARY]' if d.is_primary else ''}")

        elif subcommand == "capture":
            display_id = clean_args[1] if len(clean_args) > 1 and not clean_args[1].startswith("-") else None
            capture = vm.capture_screen(display_id)
            print(f"Captured: {capture.width}x{capture.height} {capture.format.upper()}")
            print(f"Source: {capture.source_display}")
            print(f"Size: {len(capture.image_data)} bytes")
            if capture.file_path:
                print(f"Saved Path: {capture.file_path}")
            print(f"Duration: {capture.duration_ms:.2f}ms")

        elif subcommand == "ocr":
            display_id = clean_args[1] if len(clean_args) > 1 and not clean_args[1].startswith("-") else None
            capture = vm.capture_screen(display_id)
            result = vm.perform_ocr(capture)
            print(f"OCR Text ({len(result.text)} chars):")
            print(result.text)
            print(f"Confidence: {result.confidence:.2f}")
            print(f"Regions: {len(result.regions)}")
            print(f"Duration: {result.processing_duration_ms:.2f}ms")

        elif subcommand == "detect":
            display_id = clean_args[1] if len(clean_args) > 1 and not clean_args[1].startswith("-") else None
            capture = vm.capture_screen(display_id)
            result = vm.detect_ui(capture)
            print(f"UI Elements Detected: {len(result.elements)}")
            for e in result.elements:
                print(f"  - {e.element_type}: '{e.label}' (conf: {e.confidence:.2f}) @ ({e.bounding_box.x},{e.bounding_box.y}) {e.bounding_box.width}x{e.bounding_box.height}")
            print(f"Duration: {result.processing_duration_ms:.2f}ms")

        elif subcommand == "analyze":
            display_id = clean_args[1] if len(clean_args) > 1 and not clean_args[1].startswith("-") else None
            run_ocr = "--no-ocr" not in clean_args
            run_ui = "--no-ui" not in clean_args
            analysis = vm.analyze_screen(display_id=display_id, run_ocr=run_ocr, run_ui_detection=run_ui)
            print(f"Analysis:")
            print(f"  Description: {analysis.description}")
            print(f"  Confidence: {analysis.confidence:.2f}")
            print(f"  Duration: {analysis.processing_duration_ms:.2f}ms")
            if analysis.ocr_result:
                print(f"  OCR: {len(analysis.ocr_result.text)} chars, conf={analysis.ocr_result.confidence:.2f}")
            if analysis.ui_detection_result:
                print(f"  UI: {len(analysis.ui_detection_result.elements)} elements")

        else:
            print(f"Unknown vision command: {subcommand}")
            print("Run 'python core/zetta/cli.py vision --help' for usage.")

    except ScreenCaptureError as e:
        print(f"\n[Vision Screen Capture Error]\n{e}")
        print("\nNote: On Wayland or headless systems where capture tools lack desktop permissions,")
        print(f"you can run in deterministic fake mode: python core/zetta/cli.py vision {subcommand} --fake")
    except Exception as e:
        print(f"\n[Vision Error] {e}")
        print(f"Tip: Try with '--fake' for offline testing: python core/zetta/cli.py vision {subcommand} --fake")


def handle_browser_cli(args: list) -> None:
    """CLI handler for Phase 06 browser & web control commands."""
    if not args or args[0] in ["--help", "-h", "help"]:
        print("""
ZETTA Browser & Web Control CLI:
  browser status [--fake]                                List installed browser drivers and active sessions
  browser launch [--fake] [--visible]                    Launch a browser session
  browser close [session_id] [--session <id>] [--fake]   Close active browser session
  browser navigate <url> [--session <id>] [--fake]       Navigate to website
  browser page [--session <id>] [--fake]                 Display current page title, URL, text summary
  browser detect [--type T] [--session <id>] [--fake]    Detect interactive elements (buttons, inputs, links)
  browser elements [--type T] [--session <id>] [--fake]  Alias for browser detect
  browser click <target> [--session <id>] [--fake]       Click element by ID, selector, or text
  browser type <target> <text> [--session <id>] [--fake] Type text into input field
  browser keyboard <key> [--session <id>] [--fake]       Send keyboard key (Enter, Escape, Tab)
  browser scroll <up|down|top|bottom> [--session <id>]   Scroll active webpage
  browser history <back|forward|reload> [--session <id>] History navigation
  browser screenshot [--session <id>] [--fake]           Capture webpage visual screenshot
""")
        return

    # Extract explicit session targeting flag if provided
    explicit_session_id = None
    filtered_args = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--session", "--session-id"):
            if i + 1 < len(args):
                explicit_session_id = args[i + 1]
                i += 2
                continue
        elif arg.startswith("--session="):
            explicit_session_id = arg.split("=", 1)[1]
            i += 1
            continue
        elif arg.startswith("--session-id="):
            explicit_session_id = arg.split("=", 1)[1]
            i += 1
            continue
        filtered_args.append(arg)
        i += 1

    use_fake = "--fake" in filtered_args
    clean_args = [a for a in filtered_args if a != "--fake"]
    if not clean_args:
        print("Error: Subcommand required. Run 'python core/zetta/cli.py browser --help' for usage.")
        return
    subcommand = clean_args[0].lower()

    try:
        from core.zetta.browser import get_browser_manager
        bm = get_browser_manager(use_fake=use_fake, persist_state=True)

        if subcommand == "status":
            status = bm.status()
            print(f"Provider: {status['provider']} (Available: {status['is_available']})")
            print(f"Active Sessions: {status['session_count']}")
            print("Installed Browsers:")
            for b in status["installed_browsers"]:
                print(f"  - {b['name']} ({b['type']}) [v{b.get('version', 'unknown')}]: {b['path']}")

        elif subcommand == "launch":
            headless = "--visible" not in clean_args
            session = bm.launch(headless=headless)
            print(f"Launched browser session:")
            print(f"  Session ID: {session.session_id}")
            print(f"  Type: {session.browser_type.value}")
            print(f"  Headless: {session.headless}")
            print(f"  State: {session.state.value}")

        elif subcommand == "close":
            session_id = explicit_session_id or (clean_args[1] if len(clean_args) > 1 and not clean_args[1].startswith("-") else None)
            closed = bm.close(session_id=session_id)
            print(f"Session closed: {closed}")

        elif subcommand == "navigate":
            if len(clean_args) < 2:
                print("Error: Target URL required. Example: python cli.py browser navigate https://example.com")
                return
            url = clean_args[1]
            page = bm.navigate(url=url, session_id=explicit_session_id)
            print(f"Navigated to: {page.url}")
            print(f"  Title: {page.title}")
            print(f"  Text snippet: {page.visible_text[:120]}...")
            print(f"  Links: {page.links_count} | Buttons: {page.buttons_count} | Inputs: {page.inputs_count}")

        elif subcommand == "page":
            page = bm.get_page_info(session_id=explicit_session_id)
            print(f"Active Page:")
            print(f"  URL: {page.url}")
            print(f"  Title: {page.title}")
            print(f"  Summary: {page.visible_text[:200]}...")
            print(f"  Stats: {page.links_count} links, {page.buttons_count} buttons, {page.inputs_count} inputs")

        elif subcommand in ("elements", "detect"):
            filter_type = None
            if "--type" in clean_args:
                idx = clean_args.index("--type")
                if idx + 1 < len(clean_args):
                    filter_type = clean_args[idx + 1]
            elements = bm.detect_elements(filter_type=filter_type, session_id=explicit_session_id)
            print(f"Detected {len(elements)} elements{' (type: ' + filter_type + ')' if filter_type else ''}:")
            for e in elements[:25]:
                print(f"  - {e.to_summary()}")

        elif subcommand == "click":
            if len(clean_args) < 2:
                print("Error: Target element required. Example: python cli.py browser click submit-btn")
                return
            target = clean_args[1]
            result = bm.click(target=target, session_id=explicit_session_id)
            print(f"Click Result: {'Success' if result.success else 'Failed'} - {result.message}")

        elif subcommand == "type":
            if len(clean_args) < 3:
                print("Error: Target and text required. Example: python cli.py browser type search-box 'ZETTA AI'")
                return
            target = clean_args[1]
            text = " ".join(clean_args[2:])
            result = bm.type_text(target=target, text=text, session_id=explicit_session_id)
            print(f"Type Result: {'Success' if result.success else 'Failed'} - {result.message}")

        elif subcommand == "keyboard":
            key = clean_args[1] if len(clean_args) > 1 else "Enter"
            result = bm.send_keys(key=key, session_id=explicit_session_id)
            print(f"Keyboard Result: {'Success' if result.success else 'Failed'} - {result.message}")

        elif subcommand == "scroll":
            direction = clean_args[1] if len(clean_args) > 1 else "down"
            amount = int(clean_args[2]) if len(clean_args) > 2 and clean_args[2].isdigit() else 300
            result = bm.scroll(direction=direction, amount=amount, session_id=explicit_session_id)
            print(f"Scroll Result: {'Success' if result.success else 'Failed'} - {result.message}")

        elif subcommand == "history":
            action = clean_args[1] if len(clean_args) > 1 else "back"
            page = bm.history(action=action, session_id=explicit_session_id)
            print(f"History Action ({action}): {page.url} - '{page.title}'")

        elif subcommand == "screenshot":
            capture = bm.capture_screenshot(session_id=explicit_session_id)
            print(f"Screenshot Captured:")
            print(f"  URL: {capture['url']}")
            print(f"  Bytes: {capture['bytes_length']}")
            print(f"  File: {capture['file_path']}")

        else:
            print(f"Unknown browser command: {subcommand}")
            print("Run 'python core/zetta/cli.py browser --help' for usage.")

    except Exception as e:
        print(f"\n[Browser Error] {e}")
        print(f"Tip: Try with '--fake' for offline testing: python core/zetta/cli.py browser {subcommand} --fake")


def handle_voice_cli(args: list) -> None:
    """CLI handler for Phase 07 Voice & Audio commands."""
    if not args or args[0] in ["--help", "-h", "help"]:
        print("""
ZETTA Real-Time Voice & Audio CLI:
  voice status [--fake]                     Show audio devices, capture/playback status, and STT/TTS
  voice devices [--fake]                    List available audio input and output devices
  voice test-input [--duration N] [--fake]  Record test audio clip and report duration/RMS energy
  voice test-output [--fake]                Play test chime/tone through speaker
  voice stt <audio_file> [--fake]           Transcribe audio file to text
  voice tts <text> [--play] [--fake]        Synthesize text to speech
  voice listen [--duration N] [--fake]      Single-turn microphone listening and transcription
  voice turn [--fake]                       Execute full conversational voice turn (listen -> think -> speak)
  voice session [--fake]                    Interactive continuous voice conversation loop
  voice tts-benchmark [--fake]              Run Kokoro TTS latency and memory benchmark
""")
        return

    use_fake = "--fake" in args
    clean_args = [a for a in args if a != "--fake"]
    subcommand = clean_args[0].lower()

    try:
        from core.zetta.voice import get_voice_manager
        vm = get_voice_manager(use_fake=use_fake)

        if subcommand == "status":
            status = vm.status()
            print("ZETTA Voice Subsystem Status:\n")
            print(f"Mode: {status['mode'].upper()}\n")
            print(f"Capture Provider:\n  {status['capture_provider']}\n")
            print(f"STT Provider:\n  {status['stt_provider']}")
            if status.get("stt_model"):
                print(f"  Model: {status['stt_model']}")
            print()
            print(f"AI Provider:\n  {status.get('ai_provider', 'FakeAIProvider')}")
            if status.get("ai_model"):
                print(f"  Model: {status['ai_model']}")
            print()
            tts_d = status.get("tts_details", {})
            print(f"TTS Provider:\n  {tts_d.get('provider_class', status['tts_provider'])}")
            if "voice" in tts_d:
                print(f"  Voice: {tts_d['voice']}")
            if "device" in tts_d:
                print(f"  Device: {tts_d['device']}")
            if "loaded" in tts_d:
                print(f"  Loaded: {tts_d['loaded']}")
            print()
            tts_fb = status.get("tts_fallback")
            if tts_fb:
                print(f"TTS Fallback:\n  {tts_fb.get('provider_class', 'GroqTTSProvider')}")
                if "model" in tts_fb:
                    print(f"  Model: {tts_fb['model']}")
                print()
            uses_groq = any(
                "Groq" in str(x)
                for x in [
                    status.get("stt_provider"),
                    status.get("ai_provider"),
                    tts_d.get("provider_class"),
                    (tts_fb.get("provider_class") if tts_fb else None),
                ]
            )
            if uses_groq:
                has_key = bool(
                    os.getenv("GROQ_API_KEY")
                    or getattr(getattr(vm.settings, "ai", None), "groq_api_key", None)
                    or getattr(getattr(vm.settings, "voice", None), "groq_api_key", None)
                )
                print(f"Groq Credentials:\n  {'CONFIGURED' if has_key else 'NOT CONFIGURED'}\n")
            print(f"VAD:\n  {status['vad_detector']}\n")
            print(f"Session:\n  {status['session_state'].upper()}")

        elif subcommand == "tts-benchmark":
            import resource
            def get_ram_mb() -> float:
                usage = resource.getrusage(resource.RUSAGE_SELF)
                return usage.ru_maxrss / 1024.0

            ram_before = get_ram_mb()
            phrase1 = "ZETTA AI Employee local speech benchmark."
            phrase2 = "Second synthesis to measure cached execution latency."

            from core.zetta.voice.text_to_speech.kokoro import KokoroTTSProvider
            from core.zetta.voice.models.tts import SynthesisRequest

            device = getattr(getattr(vm.settings, "voice", None), "kokoro_device", "auto").upper()
            if device == "AUTO":
                device = "CPU"
            voice = getattr(getattr(vm.settings, "voice", None), "kokoro_voice", "af_heart")

            print("ZETTA Kokoro TTS Benchmark\n")
            print(f"Device: {device}")
            print("Model: Kokoro")
            print(f"Voice: {voice}\n")

            if use_fake or not vm.tts.is_available():
                t0 = time.time()
                synth1 = vm.synthesize(phrase1)
                t1 = time.time() - t0

                t0 = time.time()
                synth2 = vm.synthesize(phrase2)
                t2 = time.time() - t0

                ram_after = get_ram_mb()
                print("Startup model load: 0.05s")
                print(f"First synthesis:     {t1:.2f}s")
                print(f"Second synthesis:    {t2:.2f}s\n")
                print(f"RAM before:           {ram_before:.1f} MB")
                print(f"RAM after:            {ram_after:.1f} MB\n")
                print("Status: PASS (Offline/Test)")
            else:
                try:
                    kokoro_provider = KokoroTTSProvider(lazy_load=True)
                    t0 = time.time()
                    kokoro_provider._ensure_model_loaded()
                    load_time = time.time() - t0

                    t0 = time.time()
                    res1 = kokoro_provider.synthesize(SynthesisRequest(text=phrase1))
                    t1 = time.time() - t0

                    t0 = time.time()
                    res2 = kokoro_provider.synthesize(SynthesisRequest(text=phrase2))
                    t2 = time.time() - t0

                    ram_after = get_ram_mb()
                    print(f"Startup model load: {load_time:.2f}s")
                    print(f"First synthesis:     {t1:.2f}s")
                    print(f"Second synthesis:    {t2:.2f}s\n")
                    print(f"RAM before:           {ram_before:.1f} MB")
                    print(f"RAM after:            {ram_after:.1f} MB\n")
                    print("Status: PASS")
                except Exception as e:
                    print(f"Benchmark error: {e}")
                    print("Status: FAIL")

        elif subcommand == "devices":
            inputs = vm.list_input_devices()
            outputs = vm.list_output_devices()
            print(f"Input Devices ({len(inputs)}):")
            for d in inputs:
                print(f"  - [{d.backend.upper()}] {d.id}: {d.name}{' (DEFAULT)' if d.is_default else ''}")
            print(f"\nOutput Devices ({len(outputs)}):")
            for d in outputs:
                print(f"  - [{d.backend.upper()}] {d.id}: {d.name}{' (DEFAULT)' if d.is_default else ''}")

        elif subcommand == "test-input":
            duration = 2.0
            if "--duration" in clean_args:
                idx = clean_args.index("--duration")
                if idx + 1 < len(clean_args):
                    duration = float(clean_args[idx + 1])
            print(f"Recording {duration:.1f}s from microphone...")
            audio = vm.record_clip(duration=duration)
            print(f"Recorded Audio Summary:")
            print(f"  Duration:   {audio.duration_seconds:.2f}s")
            print(f"  Samples:    {audio.num_samples}")
            print(f"  RMS Energy: {audio.rms_energy:.1f}")
            print(f"  Format:     {audio.format.sample_rate}Hz, {audio.format.channels}ch, {audio.format.bit_depth}-bit")

        elif subcommand == "test-output":
            print("Playing test audio tone...")
            synth = vm.synthesize("ZETTA voice test probe")
            played = vm.play_audio(synth.audio)
            print(f"Playback {'succeeded' if played else 'completed'}.")

        elif subcommand == "stt":
            if len(clean_args) < 2:
                print("Error: Audio file path required. Example: python cli.py voice stt audio.wav")
                return
            file_path = clean_args[1]
            if not os.path.exists(file_path):
                print(f"Error: File '{file_path}' not found.")
                return
            with open(file_path, "rb") as f:
                data = f.read()
            from core.zetta.voice.models.audio import AudioData
            audio = AudioData(data=data)
            result = vm.transcribe(audio)
            print(f"Transcription ({result.confidence:.2f} confidence):")
            print(f"  '{result.text}'")

        elif subcommand == "tts":
            if len(clean_args) < 2:
                print("Error: Text required. Example: python cli.py voice tts 'Hello world'")
                return
            text = " ".join([a for a in clean_args[1:] if a != "--play"])
            play = "--play" in clean_args
            synth = vm.synthesize(text)
            print(f"Synthesized {synth.characters} characters in {synth.duration_ms:.1f}ms.")
            if play and synth.audio.data:
                vm.play_audio(synth.audio)

        elif subcommand == "listen":
            duration = 5.0
            if "--duration" in clean_args:
                idx = clean_args.index("--duration")
                if idx + 1 < len(clean_args):
                    duration = float(clean_args[idx + 1])
            print(f"Listening for speech (max {duration:.1f}s)...")
            result = vm.listen(max_duration=duration)
            print(f"Transcript: '{result.text}'")

        elif subcommand == "turn":
            print("Starting conversational voice turn...")
            turn = vm.execute_turn()
            print("Turn Complete:")
            print(f"  User:      '{turn.user_transcript}'")
            print(f"  Assistant: '{turn.assistant_response}'")
            print(f"  Duration:  {turn.duration_ms:.1f}ms")

        elif subcommand == "session":
            print("Starting interactive voice session. Press Ctrl+C to exit.")
            session = vm.start_session()
            try:
                while True:
                    print("\nListening...")
                    turn = vm.execute_turn(session_id=session.session_id)
                    print(f"User:      '{turn.user_transcript}'")
                    print(f"Assistant: '{turn.assistant_response}'")
            except KeyboardInterrupt:
                vm.stop_session(session.session_id)
                print("\nVoice session closed.")

        else:
            print(f"Unknown voice command: {subcommand}")
            print("Run 'python core/zetta/cli.py voice --help' for usage.")

    except Exception as e:
        print(f"\n[Voice Error] {e}")
        print(f"Tip: Try with '--fake' for offline testing: python core/zetta/cli.py voice {subcommand} --fake")


def handle_agent_cli(args: list[str]) -> None:
    from core.zetta.agents.fleet import register_default_fleet
    from core.zetta.agents.manager.manager import get_agent_manager
    from core.zetta.agents.manager.registry import get_agent_registry
    from shared.types.contracts import SubTask

    reg = get_agent_registry()
    register_default_fleet(reg)
    mgr = get_agent_manager(reg)

    if not args or args[0] in ["--help", "-h", "list"]:
        agents = reg.list_agents()
        print("\n=== ZETTA AGENT FLEET ===")
        print(f"{'NAME':<24} {'ID':<26} {'STATUS':<12} {'PERMISSION':<10}")
        print("-" * 75)
        for a in agents:
            print(f"{a.get('name', ''):<24} {a.get('agent_id', ''):<26} {a.get('status', ''):<12} {a.get('required_permission', ''):<10}")
        print(f"\nTotal agents registered: {len(agents)}")
        return

    sub = args[0].lower()
    if sub == "status":
        target = args[1] if len(args) > 1 else ""
        if not target:
            print("Usage: python cli.py agent status <agent_name_or_id>")
            return
        try:
            agent = reg.get(target)
            print(f"Agent: {agent.name}")
            print(f"ID: {agent.agent_id}")
            print(f"Status: {agent.status.value}")
            print(f"Capabilities: {[c.value for c in agent.capabilities]}")
            print(f"Required Permission: {agent.required_permission.value}")
        except Exception as e:
            print(f"Error fetching agent: {e}")

    elif sub == "inspect":
        target = args[1] if len(args) > 1 else ""
        if not target:
            print("Usage: python cli.py agent inspect <agent_name_or_id>")
            return
        try:
            agent = reg.get(target)
            print(json.dumps(agent.to_dict(), indent=2))
        except Exception as e:
            print(f"Error inspecting agent: {e}")

    elif sub == "run":
        if len(args) < 3:
            print("Usage: python cli.py agent run <agent_name> <task_description>")
            return
        target = args[1]
        task_desc = " ".join(args[2:])
        subtask = SubTask(name=task_desc, description=task_desc, assigned_agent=target)
        try:
            res = mgr.dispatch_task(target, subtask)
            print(f"\nExecution Result: {'SUCCESS' if res.success else 'FAILED'}")
            print(f"Steps: {res.steps_executed}")
            print(f"Tools Called: {res.tools_called}")
            if res.data:
                print(f"Data: {json.dumps(res.data, indent=2, default=str)}")
            if res.error:
                print(f"Error: {res.error.message}")
        except Exception as e:
            print(f"Error running agent: {e}")

    elif sub == "cancel":
        target = args[1] if len(args) > 1 else ""
        if not target:
            print("Usage: python cli.py agent cancel <agent_name_or_id>")
            return
        try:
            mgr.cancel_agent(target)
            print(f"Cancelled agent '{target}'.")
        except Exception as e:
            print(f"Error cancelling agent: {e}")


def handle_plan_cli(args: list[str]) -> None:
    from core.zetta.agents.planner.planner import AutonomousPlanner
    planner = AutonomousPlanner()

    if not args or args[0] in ["--help", "-h"]:
        print("Usage: python cli.py plan [create|inspect] <user_goal>")
        return

    sub = args[0].lower()
    goal = " ".join(args[1:]) if len(args) > 1 else ""
    if not goal:
        print(f"Usage: python cli.py plan {sub} <user_goal>")
        return

    plan = planner.create_plan(goal)
    if sub == "create":
        print(f"\n=== GENERATED TASK PLAN: {plan.id} ===")
        print(f"Goal: {plan.goal}")
        print(f"Status: {plan.status.value}")
        print(f"\n{'#':<3} {'NAME':<30} {'ASSIGNED AGENT':<22} {'DEPENDENCIES':<15}")
        print("-" * 75)
        for idx, st in enumerate(plan.subtasks, 1):
            deps = ",".join(st.dependencies) if st.dependencies else "none"
            print(f"{idx:<3} {st.name:<30} {str(st.assigned_agent):<22} {deps:<15}")
        print(f"\nVerification Criteria: {plan.verification_criteria}")

    elif sub == "inspect":
        data = {
            "id": plan.id,
            "goal": plan.goal,
            "status": plan.status.value,
            "subtasks": [st.__dict__ for st in plan.subtasks],
            "verification_criteria": plan.verification_criteria,
        }
        print(json.dumps(data, indent=2, default=str))


def handle_skill_cli(args: list[str]) -> None:
    from core.zetta.skills.registry import get_skill_registry
    s_reg = get_skill_registry()

    if not args or args[0] in ["--help", "-h", "list"]:
        skills = s_reg.list_all()
        print("\n=== ZETTA REUSABLE SKILLS ===")
        print(f"{'NAME':<24} {'VERSION':<10} {'PERMISSION':<10} {'DESCRIPTION':<30}")
        print("-" * 78)
        for s in skills:
            print(f"{s['name']:<24} {s['version']:<10} {s['required_permission']:<10} {s['description'][:30]:<30}")
        print(f"\nTotal skills registered: {len(skills)}")
        return

    sub = args[0].lower()
    if sub == "inspect":
        name = args[1] if len(args) > 1 else ""
        skill = s_reg.get(name)
        if not skill:
            print(f"Skill '{name}' not found.")
            return
        meta = skill.metadata
        print(f"\nSkill: {meta.name} (v{meta.version})")
        print(f"Author: {meta.author}")
        print(f"Description: {meta.description}")
        print(f"Required Permission: {meta.required_permission.value}")
        print(f"Inputs: {meta.inputs}")
        print(f"Outputs: {meta.outputs}")


def handle_persona_cli(args: list[str]) -> None:
    from core.zetta.personas.manager import get_persona_manager
    from shared.types.enums import PersonaType
    p_mgr = get_persona_manager()

    if not args or args[0] in ["--help", "-h", "list"]:
        personas = p_mgr.list_personas()
        active = p_mgr.get_active_persona()
        print("\n=== ZETTA PERSONAS ===")
        print(f"{'TYPE':<16} {'NAME':<20} {'ACTIVE':<8} {'STYLE':<30}")
        print("-" * 76)
        for p in personas:
            is_active = "*" if p.persona_type == active.persona_type else ""
            print(f"{p.persona_type.value:<16} {p.name:<20} {is_active:<8} {p.communication_style:<30}")
        return


    sub = args[0].lower()
    if sub == "switch":
        target = args[1] if len(args) > 1 else ""
        try:
            ptype = PersonaType(target.lower())
            p_mgr.switch_persona(ptype)
            print(f"Switched persona to: {ptype.value}")
        except Exception as e:
            print(f"Error switching persona: {e}. Valid options: default, professional, creative")


def handle_workflow_cli(args: list[str]) -> None:
    from core.zetta.agents.orchestrator.unified_workflow import UnifiedAutonomousWorkflow
    if not args or args[0] in ["--help", "-h"]:
        print("Usage: python cli.py workflow run <user_goal>")
        return

    sub = args[0].lower()
    if sub == "run":
        goal = " ".join(args[1:]) if len(args) > 1 else ""
        if not goal:
            print("Usage: python cli.py workflow run <user_goal>")
            return
        print(f"\nExecuting Unified Autonomous Workflow for goal: '{goal}'")
        wf = UnifiedAutonomousWorkflow()
        report = wf.execute_goal(goal, user_role="user")
        print(f"Status: {report['status']}")
        print(f"Duration: {report['duration_ms']:.2f}ms")
        print(f"Subtasks: {report['subtasks_count']}")
        print(f"Verified: {report['verification']['verified']}")
        print(json.dumps(report['verification']['notes'], indent=2))


def handle_bgjob_cli(args: list[str]) -> None:
    from core.zetta.agents.orchestrator.background_runner import get_background_runner
    runner = get_background_runner()

    if not args or args[0] in ["--help", "-h", "list"]:
        jobs = runner.list_jobs()
        print("\n=== ZETTA BACKGROUND JOBS ===")
        print(f"{'ID':<38} {'NAME':<20} {'STATUS':<12} {'PROGRESS':<10}")
        print("-" * 82)
        for j in jobs:
            print(f"{j['job_id']:<38} {j['name']:<20} {j['status']:<12} {j['progress'] * 100:>5.1f}%")
        print(f"\nTotal background jobs: {len(jobs)}")
        return

    sub = args[0].lower()
    if sub == "cancel":
        job_id = args[1] if len(args) > 1 else ""
        if not job_id:
            print("Usage: python cli.py bgjob cancel <job_id>")
            return
        res = runner.cancel_job(job_id)
        print(f"Job cancellation {'successful' if res else 'failed/already terminated'}.")


def handle_phone_cli(args: list[str]) -> None:
    from core.zetta.phone.manager import get_phone_manager
    phone_mgr = get_phone_manager()

    if not args or args[0] in ["--help", "-h", "status"]:
        st = phone_mgr.get_status()
        print("\n=== ZETTA PHONE LINK STATUS ===")
        print(f"State: {st['state']}")
        if st.get("device"):
            print(f"Device: {st['device'].get('name')} ({st['device'].get('model')})")
            print(f"OS: {st['device'].get('os_version')}")
            print(f"Battery: {st['device'].get('battery_level')}%")
        else:
            print("No phone currently paired/connected.")
        return

    sub = args[0].lower()
    if sub == "pair":
        code = args[1] if len(args) > 1 else ""
        if not code:
            print("Usage: python cli.py phone pair <6_digit_code>")
            return
        ok = phone_mgr.pair_device(code)
        print(f"Pairing {'successful' if ok else 'failed'}.")

    elif sub == "disconnect":
        phone_mgr.disconnect_device()
        print("Phone disconnected.")

    elif sub == "ping":
        res = phone_mgr.send_command("ping", user_role="user")
        print(f"Ping result: {res}")


def main() -> None:
    """CLI launcher for ZETTA AI Employee."""
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd in ["--help", "-h", "help"]:
            print_help()
            return
        elif cmd == "chat":
            use_real = "--real" in sys.argv
            from core.zetta.config import get_settings
            settings = get_settings()
            configured_provider = settings.ai.default_provider.lower()
            if use_real:
                try:
                    provider_type = AIProviderType(configured_provider)
                except ValueError:
                    provider_type = AIProviderType.GROQ if getattr(settings.ai, "groq_api_key", None) else AIProviderType.OPENAI
            else:
                provider_type = AIProviderType.FAKE
            shell = ChatShell()
            shell.run_interactive_loop(provider_type=provider_type)
            return
        elif cmd == "task":
            cmd_processor = CommandProcessor()
            cmd_processor.handle_cli_task_command(sys.argv[2:])
            return
        elif cmd == "ai-test":
            use_real = "--real" in sys.argv
            run_ai_test(use_real=use_real)
            return
        elif cmd == "memory":
            handle_memory_cli(sys.argv[2:])
            return
        elif cmd == "tools":
            handle_tools_cli(sys.argv[2:])
            return
        elif cmd == "vision":
            handle_vision_cli(sys.argv[2:])
            return
        elif cmd == "browser":
            handle_browser_cli(sys.argv[2:])
            return
        elif cmd == "voice":
            handle_voice_cli(sys.argv[2:])
            return
        elif cmd == "agent":
            handle_agent_cli(sys.argv[2:])
            return
        elif cmd == "plan":
            handle_plan_cli(sys.argv[2:])
            return
        elif cmd == "skill":
            handle_skill_cli(sys.argv[2:])
            return
        elif cmd == "persona":
            handle_persona_cli(sys.argv[2:])
            return
        elif cmd == "workflow":
            handle_workflow_cli(sys.argv[2:])
            return
        elif cmd == "bgjob":
            handle_bgjob_cli(sys.argv[2:])
            return
        elif cmd == "phone":
            handle_phone_cli(sys.argv[2:])
            return
        elif cmd == "ui":
            from core.zetta.api.app import get_api_app
            import uvicorn
            import webbrowser
            import threading
            import time
            import subprocess

            host = "127.0.0.1"
            port = 8000
            for arg in sys.argv[2:]:
                if arg.startswith("--port="):
                    port = int(arg.split("=")[1])
                elif arg.startswith("--host="):
                    host = arg.split("=")[1]

            def open_browser():
                time.sleep(1.0)
                url = f"http://{host}:{port}"
                try:
                    # Attempt standalone app window mode via Chrome for native desktop feel
                    subprocess.Popen(["google-chrome", f"--app={url}", "--user-data-dir=/tmp/zetta_chrome_profile"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    webbrowser.open(url)

            threading.Thread(target=open_browser, daemon=True).start()
            print(f"🚀 Launching ZETTA AI Employee UI at http://{host}:{port}...")
            uvicorn.run(get_api_app(), host=host, port=port, log_level="info")
            return


    logger.info("Initializing ZETTA AI Employee...")
    health = check_health()
    print("==================================================")
    print(f"ZETTA SYSTEM HEALTH STATUS: {health.status}")
    print("==================================================")
    print(json.dumps(health.checks, indent=2))
    print("==================================================")

    if health.status != "OK":
        sys.exit(1)


if __name__ == "__main__":
    main()

