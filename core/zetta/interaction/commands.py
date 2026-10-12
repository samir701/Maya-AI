"""ZETTA Chat Slash Commands & CLI Command Processor."""

import json
import os
import sys
from typing import Any, Dict, Optional, Tuple
from core.zetta.interaction.formatting import (
    format_capabilities,
    format_memory_summary,
    format_status_report,
    format_task_created,
)
from core.zetta.memory import get_memory_manager
from core.zetta.tasks import get_task_manager
from core.zetta.tools import get_tool_registry
from core.zetta.utils.logging import get_logger

logger = get_logger("command_processor")


class CommandProcessor:
    """Processes interactive slash commands and CLI management commands."""

    def __init__(self) -> None:
        self.mem_mgr = get_memory_manager()
        self.task_mgr = get_task_manager()
        self.tool_reg = get_tool_registry()

    def is_slash_command(self, text: str) -> bool:
        return text.strip().startswith("/")

    def process_slash_command(
        self,
        command_str: str,
        session_id: str,
        provider_name: str,
        model_name: str,
    ) -> Tuple[bool, str]:
        """Execute interactive slash command.

        Returns (should_exit: bool, output_message: str).
        """
        parts = command_str.strip().split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ("/exit", "/quit"):
            return True, "Session closed."

        elif cmd == "/help":
            help_text = """
Available Interactive Commands:
  /help                  Display this command summary.
  /status                Display complete system, provider, memory & task status.
  /session               Display current session ID and metadata.
  /memory                Display summary of stored memories.
  /memory search <q>     Search relevant memories matching query text.
  /memory clear          Clear ephemeral short-term session memories.
  /tasks                 Display task list and status.
  /clear                 Clear terminal screen.
  /exit, /quit           Exit interactive chat session.
"""
            return False, help_text.strip()

        elif cmd == "/status":
            memories = self.mem_mgr.list_memories()
            all_tasks = self.task_mgr.list_tasks()
            active_tasks = [t for t in all_tasks if t.status.value in ("CREATED", "QUEUED", "RUNNING")]

            report = format_status_report(
                session_id=session_id,
                provider=provider_name,
                model=model_name,
                ai_status="OK",
                memory_count=len(memories),
                task_count=len(all_tasks),
                active_tasks=len(active_tasks),
            )
            return False, report

        elif cmd == "/session":
            return False, f"Current Session ID: {session_id}"

        elif cmd == "/memory":
            if not args:
                mems = self.mem_mgr.list_memories(limit=20)
                return False, format_memory_summary(mems)
            sub = args[0].lower()
            if sub == "search" and len(args) > 1:
                q = " ".join(args[1:])
                results = self.mem_mgr.retrieve_relevant(q, session_id=session_id)
                if not results:
                    return False, f"No relevant memories found for query '{q}'."
                lines = [f"Retrieved {len(results)} relevant memories:"]
                for r in results:
                    lines.append(f"  - [{r.memory.id[:8]}] (Score: {r.score:.3f}): {r.memory.content}")
                return False, "\n".join(lines)
            elif sub == "clear":
                cleared = self.mem_mgr.short_term.clear_session(session_id)
                return False, f"Cleared {cleared} short-term session memories for session '{session_id}'."
            else:
                return False, "Usage: /memory [search <query> | clear]"

        elif cmd == "/tasks":
            tasks = self.task_mgr.list_tasks()
            if not tasks:
                return False, "No tasks currently registered."
            lines = ["Task List:"]
            for t in tasks:
                lines.append(f"  - [{t.id[:8]}] Status: {t.status.value:<10} Title: {t.name}")
            return False, "\n".join(lines)

        elif cmd == "/clear":
            os.system("clear" if os.name == "posix" else "cls")
            return False, ""

        else:
            return False, f"Unknown command: '{cmd}'. Type `/help` for available commands."

    def handle_cli_task_command(self, args: list) -> None:
        """Handle CLI task subcommands: task create|list|get|cancel."""
        if not args or args[0] in ("--help", "-h"):
            print("""
Task CLI Commands:
  python3 core/zetta/cli.py task create "<description>"
  python3 core/zetta/cli.py task list
  python3 core/zetta/cli.py task get <task_id>
  python3 core/zetta/cli.py task cancel <task_id>
""")
            return

        subcmd = args[0].lower()

        if subcmd == "create" and len(args) > 1:
            description = " ".join(args[1:])
            task = self.task_mgr.create_task(name=description)
            print(format_task_created(task.id, task.name, task.status))

        elif subcmd == "list":
            tasks = self.task_mgr.list_tasks()
            print(f"Total Tasks: {len(tasks)}")
            for t in tasks:
                print(f" - [{t.id[:8]}] Status: {t.status.value:<10} Title: {t.name}")

        elif subcmd == "get" and len(args) > 1:
            task_id = args[1]
            task = self.task_mgr.get_task(task_id)
            if task:
                print(json.dumps(task.to_dict(), indent=2))
            else:
                print(f"Task with ID '{task_id}' not found.")

        elif subcmd == "cancel" and len(args) > 1:
            task_id = args[1]
            try:
                task = self.task_mgr.cancel_task(task_id)
                print(f"Task '{task_id}' cancelled successfully. Status: {task.status.value}")
            except Exception as e:
                print(f"Failed to cancel task '{task_id}': {e}")

        else:
            print("Usage: python3 core/zetta/cli.py task <create|list|get|cancel> [args]")
