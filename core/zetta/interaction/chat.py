"""ZETTA Interactive Chat Terminal Shell."""

import sys
from typing import Optional
from core.zetta.config import get_settings
from core.zetta.interaction.commands import CommandProcessor
from core.zetta.interaction.formatting import format_banner, format_error, normalize_user_input
from core.zetta.interaction.manager import InteractionManager, get_interaction_manager
from core.zetta.utils.logging import get_logger
from shared.types import AIProviderType

logger = get_logger("chat_shell")


class ChatShell:
    """Interactive CLI terminal shell for ZETTA AI Employee."""

    def __init__(
        self,
        interaction_manager: Optional[InteractionManager] = None,
    ) -> None:
        self.int_mgr = interaction_manager or get_interaction_manager()
        self.cmd_processor = CommandProcessor()

    def run_interactive_loop(
        self,
        session_id: Optional[str] = None,
        provider_type: Optional[AIProviderType] = None,
        use_stream: bool = True,
    ) -> None:
        """Run the interactive chat loop in terminal."""
        settings = get_settings()

        session = self.int_mgr.session_mgr.load_or_create(session_id)
        effective_provider = provider_type or AIProviderType(settings.ai.default_provider)
        active_provider_obj = self.int_mgr.brain.get_active_provider(effective_provider)

        banner = format_banner(
            session_id=session.session_id,
            provider_name=active_provider_obj.provider_name.value,
            model_name=active_provider_obj.model,
        )
        print(banner)

        while True:
            try:
                raw_input = input("\nYou > ")
                user_input = normalize_user_input(raw_input)
                if not user_input:
                    continue

                # Check for slash command
                if self.cmd_processor.is_slash_command(user_input):
                    should_exit, output_msg = self.cmd_processor.process_slash_command(
                        command_str=user_input,
                        session_id=session.session_id,
                        provider_name=active_provider_obj.provider_name.value,
                        model_name=active_provider_obj.model,
                    )
                    if output_msg:
                        print(f"\n{output_msg}")
                    if should_exit:
                        break
                    continue

                # Normal User Chat Input
                print("\nZetta > ", end="", flush=True)

                if use_stream and settings.interaction.streaming_enabled:
                    full_response = ""
                    try:
                        for chunk in self.int_mgr.stream_user_message(
                            session_id=session.session_id,
                            user_input=user_input,
                            provider_type=effective_provider,
                        ):
                            sys.stdout.write(chunk)
                            sys.stdout.flush()
                            full_response += chunk
                        print()  # New line after stream completion
                    except Exception as e:
                        logger.warning(f"Streaming error encountered: {e}. Falling back to non-stream mode.")
                        response_text = self.int_mgr.process_user_message(
                            session_id=session.session_id,
                            user_input=user_input,
                            provider_type=effective_provider,
                        )
                        print(response_text)
                else:
                    response_text = self.int_mgr.process_user_message(
                        session_id=session.session_id,
                        user_input=user_input,
                        provider_type=effective_provider,
                    )
                    print(response_text)

            except (KeyboardInterrupt, EOFError):
                print("\n\nSession terminated cleanly by user.")
                self.int_mgr.session_mgr.close_session(session.session_id)
                break
            except Exception as e:
                print(f"\n{format_error(str(e))}")
                logger.error(f"Error in chat loop: {e}")
