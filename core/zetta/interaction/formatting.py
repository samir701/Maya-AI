"""ZETTA Interaction Output & Terminal Formatting Utilities."""

import re
from typing import Any, Dict, List
from shared.types import Memory, MemoryType, TaskStatus

# Regex pattern for sanitizing sensitive keys/credentials from error outputs
SECRET_MASK_REGEX = re.compile(r"(sk-[a-zA-Z0-9_-]{20,}|key-[a-zA-Z0-9_-]{20,}|[a-zA-Z0-9_-]{32,})")

# Regex pattern for matching leading prompt prefixes such as "You > "
PROMPT_PREFIX_REGEX = re.compile(r"^(?:you\s*>\s*)+", re.IGNORECASE)


def normalize_user_input(raw_input: str) -> str:
    """Normalize raw user input string by stripping surrounding whitespace
    and removing any accidental leading prompt prefix like 'You > '.
    """
    if not raw_input:
        return ""
    text = raw_input.strip()
    normalized = PROMPT_PREFIX_REGEX.sub("", text).strip()
    return normalized if normalized else text


def sanitize_text(text: str) -> str:
    """Mask potential secret strings or API keys in output text."""
    if not text:
        return ""
    def mask_match(m):
        val = m.group(0)
        if len(val) > 8 and ("sk-" in val or "key-" in val or "api" in val.lower()):
            return val[:4] + "..." + val[-4:]
        return val

    return SECRET_MASK_REGEX.sub(mask_match, text)


def format_banner(session_id: str, provider_name: str, model_name: str) -> str:
    """Format interactive shell launch banner."""
    lines = [
        "==================================================",
        "ZETTA AI EMPLOYEE — INTERACTIVE MODE",
        "==================================================",
        f"Session:  {session_id}",
        f"Provider: {provider_name} ({model_name})",
        "",
        "Type `/help` for commands.",
        "Type `/exit` to leave.",
        "==================================================",
    ]
    return "\n".join(lines)


def format_capabilities(tools: List[Dict[str, Any]]) -> str:
    """Format read-only capabilities list."""
    lines = ["Available capabilities:"]
    if not tools:
        lines.append("  (None registered)")
    else:
        for t in tools:
            name = t.get("name", "unknown")
            perm = t.get("required_permission", "LOW")
            lines.append(f"  - {name:<20} [Permission: {perm}]")
    return "\n".join(lines)


def format_memory_summary(memories: List[Memory]) -> str:
    """Format memory summary listing grouped by category."""
    if not memories:
        return "No memories currently stored."

    long_term = [m for m in memories if m.memory_type == MemoryType.LONG_TERM]
    short_term = [m for m in memories if m.memory_type == MemoryType.SHORT_TERM]
    other = [m for m in memories if m.memory_type not in (MemoryType.LONG_TERM, MemoryType.SHORT_TERM)]

    lines = [f"Memory Summary ({len(memories)} entries):"]

    if long_term:
        lines.append("\nLONG_TERM")
        for m in long_term:
            src = m.source.value
            lines.append(f"  - [{m.id[:8]}] [{src}] (Importance: {m.importance:.2f}): {m.content}")

    if short_term:
        lines.append("\nSHORT_TERM / SESSION")
        for m in short_term:
            role = str(m.provenance.get("role", "unknown")).upper()
            sess = str(m.provenance.get("session_id", "global"))[:8]
            lines.append(f"  - [{m.id[:8]}] [{sess}] {role}: {m.content}")

    if other:
        lines.append("\nOTHER MEMORIES")
        for m in other:
            lines.append(f"  - [{m.id[:8]}] ({m.memory_type.value}) {m.content}")

    return "\n".join(lines)



def format_status_report(
    session_id: str,
    provider: str,
    model: str,
    ai_status: str,
    memory_count: int,
    task_count: int,
    active_tasks: int,
) -> str:
    """Format complete system status breakdown."""
    lines = [
        "--------------------------------------------------",
        "ZETTA SYSTEM STATUS",
        "--------------------------------------------------",
        f"Session ID:      {session_id}",
        f"AI Provider:     {provider} ({model})",
        f"AI System:       {ai_status}",
        f"Memory System:   OK ({memory_count} memories loaded)",
        f"Task System:     OK ({task_count} total, {active_tasks} active)",
        "--------------------------------------------------",
    ]
    return "\n".join(lines)


def format_task_created(task_id: str, title: str, status: TaskStatus) -> str:
    """Format task creation confirmation."""
    lines = [
        "Task created successfully.",
        f"  ID:     {task_id}",
        f"  Status: {status.value}",
        f"  Title:  {title}",
    ]
    return "\n".join(lines)


def format_error(error_msg: str) -> str:
    """Format sanitized user-friendly error message."""
    clean_msg = sanitize_text(str(error_msg))
    return f"[ERROR] {clean_msg}"
