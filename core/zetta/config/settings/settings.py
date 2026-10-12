"""ZETTA Centralized Settings Dataclass Structure."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env variables automatically
load_dotenv()


@dataclass
class AppSettings:
    name: str = "ZETTA AI EMPLOYEE"
    env: str = field(default_factory=lambda: os.getenv("ZETTA_ENV", "development"))
    version: str = "0.1.0"
    debug: bool = field(default_factory=lambda: os.getenv("ZETTA_DEBUG", "true").lower() == "true")


@dataclass
class AIProviderSettings:
    default_provider: str = field(default_factory=lambda: os.getenv("AI_PROVIDER") or os.getenv("ZETTA_AI_DEFAULT_PROVIDER", "fake"))
    default_model: str = field(default_factory=lambda: os.getenv("GROQ_LLM_MODEL") if (os.getenv("AI_PROVIDER") == "groq" or os.getenv("ZETTA_AI_DEFAULT_PROVIDER") == "groq") else os.getenv("ZETTA_AI_MODEL", "gpt-4o"))
    api_base_url: str = field(default_factory=lambda: os.getenv("ZETTA_AI_BASE_URL", "https://api.openai.com/v1"))
    api_key: str = field(default_factory=lambda: os.getenv("ZETTA_AI_API_KEY", ""))
    timeout: float = field(default_factory=lambda: float(os.getenv("ZETTA_AI_TIMEOUT", "30.0")))
    temperature: float = field(default_factory=lambda: float(os.getenv("ZETTA_AI_TEMPERATURE", "0.7")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("ZETTA_AI_MAX_TOKENS", "2048")))
    streaming: bool = field(default_factory=lambda: os.getenv("ZETTA_AI_STREAMING", "false").lower() == "true")
    max_retries: int = field(default_factory=lambda: int(os.getenv("ZETTA_AI_MAX_RETRIES", "3")))
    # Groq-specific AI settings
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_llm_model: str = field(default_factory=lambda: os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-20b"))

    def __repr__(self) -> str:
        masked_groq = "****" if self.groq_api_key else ""
        masked_openai = "****" if self.api_key else ""
        return (
            f"<AIProviderSettings provider='{self.default_provider}' "
            f"model='{self.default_model}' groq_api_key='{masked_groq}' "
            f"api_key='{masked_openai}'>"
        )


@dataclass
class MemorySettings:
    memory_enabled: bool = field(default_factory=lambda: os.getenv("ZETTA_MEMORY_ENABLED", "true").lower() == "true")
    short_term_limit: int = field(default_factory=lambda: int(os.getenv("ZETTA_SHORT_TERM_LIMIT", "50")))
    short_term_expiration_hours: float = field(default_factory=lambda: float(os.getenv("ZETTA_SHORT_TERM_EXPIRATION_HOURS", "24.0")))
    long_term_enabled: bool = field(default_factory=lambda: os.getenv("ZETTA_LONG_TERM_ENABLED", "true").lower() == "true")
    semantic_memory_enabled: bool = field(default_factory=lambda: os.getenv("ZETTA_SEMANTIC_MEMORY_ENABLED", "true").lower() == "true")
    embedding_provider: str = field(default_factory=lambda: os.getenv("ZETTA_EMBEDDING_PROVIDER", "fake"))
    embedding_model: str = field(default_factory=lambda: os.getenv("ZETTA_EMBEDDING_MODEL", "fake-embed-v1"))
    retrieval_limit: int = field(default_factory=lambda: int(os.getenv("ZETTA_RETRIEVAL_LIMIT", "10")))
    similarity_threshold: float = field(default_factory=lambda: float(os.getenv("ZETTA_SIMILARITY_THRESHOLD", "0.3")))
    min_similarity_threshold: float = field(default_factory=lambda: float(os.getenv("ZETTA_MIN_SIMILARITY_THRESHOLD", "0.2")))

    # Configurable Ranking Weights
    similarity_weight: float = field(default_factory=lambda: float(os.getenv("ZETTA_SIMILARITY_WEIGHT", "0.4")))
    importance_weight: float = field(default_factory=lambda: float(os.getenv("ZETTA_IMPORTANCE_WEIGHT", "0.25")))
    recency_weight: float = field(default_factory=lambda: float(os.getenv("ZETTA_RECENCY_WEIGHT", "0.15")))
    confidence_weight: float = field(default_factory=lambda: float(os.getenv("ZETTA_CONFIDENCE_WEIGHT", "0.1")))
    source_trust_weight: float = field(default_factory=lambda: float(os.getenv("ZETTA_SOURCE_TRUST_WEIGHT", "0.1")))

    automatic_consolidation: bool = field(default_factory=lambda: os.getenv("ZETTA_AUTOMATIC_CONSOLIDATION", "true").lower() == "true")
    max_context_memory_tokens: int = field(default_factory=lambda: int(os.getenv("ZETTA_MAX_CONTEXT_MEMORY_TOKENS", "1024")))
    max_context_memories: int = field(default_factory=lambda: int(os.getenv("ZETTA_MAX_CONTEXT_MEMORIES", "5")))


@dataclass
class InteractionSettings:
    max_session_history: int = field(default_factory=lambda: int(os.getenv("ZETTA_MAX_SESSION_HISTORY", "20")))
    streaming_enabled: bool = field(default_factory=lambda: os.getenv("ZETTA_STREAMING_ENABLED", "true").lower() == "true")


@dataclass
class DatabaseSettings:
    db_path: str = field(default_factory=lambda: os.getenv("ZETTA_DB_PATH", "data/database/zetta.db"))

    def get_absolute_db_path(self, root_dir: Path) -> Path:
        p = Path(self.db_path)
        if p.is_absolute():
            return p
        return root_dir / p


@dataclass
class LoggingSettings:
    log_level: str = field(default_factory=lambda: os.getenv("ZETTA_LOG_LEVEL", "INFO"))
    log_dir: str = field(default_factory=lambda: os.getenv("ZETTA_LOG_DIR", "data/logs"))


@dataclass
class SecuritySettings:
    sandbox_enabled: bool = field(default_factory=lambda: os.getenv("ZETTA_SANDBOX_ENABLED", "true").lower() == "true")
    confirmation_threshold: str = field(default_factory=lambda: os.getenv("ZETTA_CONFIRMATION_THRESHOLD", "HIGH"))


@dataclass
class BrowserSettings:
    headless: bool = field(default_factory=lambda: os.getenv("ZETTA_BROWSER_HEADLESS", "true").lower() == "true")


@dataclass
class AutomationSettings:
    max_steps: int = field(default_factory=lambda: int(os.getenv("ZETTA_MAX_STEPS", "50")))


@dataclass
class DesktopSettings:
    os_type: str = field(default_factory=lambda: os.getenv("ZETTA_OS_TYPE", "linux"))


@dataclass
class AndroidSettings:
    enabled: bool = field(default_factory=lambda: os.getenv("ZETTA_ANDROID_ENABLED", "false").lower() == "true")


@dataclass
class VoiceSettings:
    enabled: bool = field(default_factory=lambda: os.getenv("ZETTA_VOICE_ENABLED", "true").lower() == "true")
    input_device: str = field(default_factory=lambda: os.getenv("ZETTA_AUDIO_INPUT_DEVICE", "default"))
    output_device: str = field(default_factory=lambda: os.getenv("ZETTA_AUDIO_OUTPUT_DEVICE", "default"))
    sample_rate: int = field(default_factory=lambda: int(os.getenv("ZETTA_AUDIO_SAMPLE_RATE", "16000")))
    channels: int = field(default_factory=lambda: int(os.getenv("ZETTA_AUDIO_CHANNELS", "1")))
    stt_provider: str = field(default_factory=lambda: os.getenv("STT_PROVIDER") or os.getenv("ZETTA_VOICE_STT_PROVIDER", "fake"))
    tts_provider: str = field(default_factory=lambda: os.getenv("TTS_PROVIDER") or os.getenv("ZETTA_VOICE_TTS_PROVIDER", "fake"))
    vad_energy_threshold: float = field(default_factory=lambda: float(os.getenv("ZETTA_VOICE_VAD_THRESHOLD", "500.0")))
    vad_silence_duration_sec: float = field(default_factory=lambda: float(os.getenv("ZETTA_VOICE_VAD_SILENCE_SEC", "0.6")))
    persist_audio: bool = field(default_factory=lambda: (os.getenv("PERSIST_AUDIO") or os.getenv("ZETTA_VOICE_PERSIST_AUDIO", "false")).lower() == "true")
    max_record_seconds: float = field(default_factory=lambda: float(os.getenv("ZETTA_VOICE_MAX_RECORD_SEC", "15.0")))
    # Groq Voice settings
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_stt_model: str = field(default_factory=lambda: os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo"))
    groq_tts_model: str = field(default_factory=lambda: os.getenv("GROQ_TTS_MODEL", "canopylabs/orpheus-v1-english"))
    # Kokoro Voice settings
    kokoro_enabled: bool = field(default_factory=lambda: os.getenv("KOKORO_ENABLED", "true").lower() == "true")
    kokoro_device: str = field(default_factory=lambda: os.getenv("KOKORO_DEVICE", "cpu"))
    kokoro_lazy_load: bool = field(default_factory=lambda: os.getenv("KOKORO_LAZY_LOAD", "true").lower() == "true")
    kokoro_max_concurrent_jobs: int = field(default_factory=lambda: int(os.getenv("KOKORO_MAX_CONCURRENT_JOBS", "1")))
    kokoro_timeout_seconds: float = field(default_factory=lambda: float(os.getenv("KOKORO_TIMEOUT_SECONDS", "30.0")))
    kokoro_max_text_chars: int = field(default_factory=lambda: int(os.getenv("KOKORO_MAX_TEXT_CHARS", "200")))
    kokoro_voice: str = field(default_factory=lambda: os.getenv("KOKORO_VOICE", "af_heart"))
    # TTS routing & fallback
    tts_fallback_enabled: bool = field(default_factory=lambda: os.getenv("TTS_FALLBACK_ENABLED", "true").lower() == "true")
    tts_fallback_provider: str = field(default_factory=lambda: os.getenv("TTS_FALLBACK_PROVIDER", "groq"))

    def __repr__(self) -> str:
        masked_groq = "****" if self.groq_api_key else ""
        return (
            f"<VoiceSettings enabled={self.enabled} stt='{self.stt_provider}' "
            f"tts='{self.tts_provider}' kokoro_device='{self.kokoro_device}' "
            f"groq_api_key='{masked_groq}'>"
        )


@dataclass
class Settings:
    root_path: Path = field(default_factory=lambda: Path(__file__).resolve().parents[4])
    app: AppSettings = field(default_factory=AppSettings)
    ai: AIProviderSettings = field(default_factory=AIProviderSettings)
    memory: MemorySettings = field(default_factory=MemorySettings)
    interaction: InteractionSettings = field(default_factory=InteractionSettings)
    db: DatabaseSettings = field(default_factory=DatabaseSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    browser: BrowserSettings = field(default_factory=BrowserSettings)
    voice: VoiceSettings = field(default_factory=VoiceSettings)
    automation: AutomationSettings = field(default_factory=AutomationSettings)
    desktop: DesktopSettings = field(default_factory=DesktopSettings)
    android: AndroidSettings = field(default_factory=AndroidSettings)


_settings_instance: Optional[Settings] = None


def get_settings(reload: bool = False) -> Settings:
    global _settings_instance
    if _settings_instance is None or reload:
        _settings_instance = Settings()
    return _settings_instance
