"""Comprehensive Import & Static Module Resolution Verifier."""

import importlib
import sys
from pathlib import Path

# Add project root to sys.path if not present
root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

modules_to_test = [
    "pydantic",
    "dotenv",
    "pytest",
    "sqlite3",
    "json",
    "logging",
    "dataclasses",
    "shared",
    "shared.types",
    "shared.types.enums",
    "shared.types.contracts",
    "shared.schemas",
    "shared.schemas.models",
    "core",
    "core.zetta",
    "core.zetta.config",
    "core.zetta.config.settings",
    "core.zetta.utils",
    "core.zetta.utils.errors",
    "core.zetta.utils.logging",
    "core.zetta.events",
    "core.zetta.events.event",
    "core.zetta.events.bus",
    "core.zetta.tools",
    "core.zetta.tools.base",
    "core.zetta.tools.registry",
    "core.zetta.tools.system",
    "core.zetta.tasks",
    "core.zetta.tasks.queue",
    "core.zetta.tasks.history",
    "core.zetta.tasks.manager",
    "core.zetta.security",
    "core.zetta.security.permissions",
    "core.zetta.security.confirmation",
    "core.zetta.security.audit",
    "core.zetta.security.sandbox",
    "core.zetta.security.secrets",
    "core.zetta.security.manager",
    "core.zetta.db",
    "core.zetta.db.database",
    "core.zetta.ai",
    "core.zetta.ai.brain",
    "core.zetta.ai.providers",
    "core.zetta.ai.providers.demo_provider",
    "core.zetta.ai.prompts",
    "core.zetta.ai.responses",
    "core.zetta.ai.context",
    "core.zetta.memory",
    "core.zetta.memory.repository",
    "core.zetta.memory.short_term",
    "core.zetta.memory.long_term",
    "core.zetta.memory.episodic",
    "core.zetta.memory.embeddings",
    "core.zetta.memory.retrieval",
    "core.zetta.memory.dedup",
    "core.zetta.memory.expiration",
    "core.zetta.memory.forgetting",
    "core.zetta.memory.consolidation",
    "core.zetta.memory.manager",
    "core.zetta.interaction",
    "core.zetta.interaction.session",
    "core.zetta.interaction.manager",
    "core.zetta.interaction.chat",
    "core.zetta.interaction.commands",
    "core.zetta.interaction.formatting",
    "core.zetta.interaction.confirmation",
    "core.zetta.health",
    "core.zetta.vision",
    "core.zetta.vision.models",
    "core.zetta.vision.models.results",
    "core.zetta.vision.screen",
    "core.zetta.vision.screen.capture",
    "core.zetta.vision.screen.display",
    "core.zetta.vision.ocr",
    "core.zetta.vision.ocr.base",
    "core.zetta.vision.ocr.fake",
    "core.zetta.vision.ocr.local",
    "core.zetta.vision.ui_detection",
    "core.zetta.vision.ui_detection.detector",
    "core.zetta.vision.ui_detection.fake",
    "core.zetta.vision.ui_detection.models",
    "core.zetta.vision.analysis",
    "core.zetta.vision.analysis.analyzer",
    "core.zetta.vision.manager",
    "core.zetta.tools.vision",
    "core.zetta.tools.vision.vision_tools",
    # Phase 06: Browser & Web Control
    "core.zetta.browser",
    "core.zetta.browser.models",
    "core.zetta.browser.models.session",
    "core.zetta.browser.models.page",
    "core.zetta.browser.models.elements",
    "core.zetta.browser.models.actions",
    "core.zetta.browser.providers",
    "core.zetta.browser.providers.base",
    "core.zetta.browser.providers.fake",
    "core.zetta.browser.providers.local",
    "core.zetta.browser.controller",
    "core.zetta.browser.manager",
    "core.zetta.tools.browser",
    "core.zetta.tools.browser.browser_tools",
    # Phase 07: Real-Time Voice & Audio
    "core.zetta.voice",
    "core.zetta.voice.models",
    "core.zetta.voice.models.audio",
    "core.zetta.voice.models.vad",
    "core.zetta.voice.models.stt",
    "core.zetta.voice.models.tts",
    "core.zetta.voice.models.session",
    "core.zetta.voice.audio",
    "core.zetta.voice.audio.base",
    "core.zetta.voice.audio.fake",
    "core.zetta.voice.audio.linux",
    "core.zetta.voice.audio.device",
    "core.zetta.voice.vad",
    "core.zetta.voice.vad.detector",
    "core.zetta.voice.vad.fake",
    "core.zetta.voice.speech_to_text",
    "core.zetta.voice.speech_to_text.base",
    "core.zetta.voice.speech_to_text.fake",
    "core.zetta.voice.speech_to_text.local",
    "core.zetta.voice.text_to_speech",
    "core.zetta.voice.text_to_speech.base",
    "core.zetta.voice.text_to_speech.fake",
    "core.zetta.voice.text_to_speech.local",
    "core.zetta.voice.controller",
    "core.zetta.voice.manager",
    "core.zetta.tools.voice",
    "core.zetta.tools.voice.voice_tools",
]


def main():
    print("=" * 60)
    print("VERIFYING MODULE RESOLUTION & IMPORTABILITY")
    print(f"Python Executable: {sys.executable}")
    print("=" * 60)
    passed = 0
    failed = 0
    missing_pkgs = []

    for mod_name in modules_to_test:
        try:
            mod = importlib.import_module(mod_name)
            location = getattr(mod, "__file__", "built-in")
            print(f"[OK] {mod_name:<40} -> {location}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {mod_name:<38} -> Error: {e}")
            missing_pkgs.append(mod_name)
            failed += 1

    print("=" * 60)
    print(f"Import Summary: {passed} passed, {failed} failed.")
    print("=" * 60)

    if missing_pkgs:
        print("Missing / Unresolved Modules:", missing_pkgs)
        sys.exit(1)
    else:
        print("ALL MODULES SUCCESSFULLY RESOLVED AND IMPORTED!")


if __name__ == "__main__":
    main()
