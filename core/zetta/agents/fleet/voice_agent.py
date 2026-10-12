"""Voice Agent in ZETTA Fleet."""

from core.zetta.agents.base.base_agent import BaseAgent
from core.zetta.tools.registry import get_tool_registry
from core.zetta.utils.logging import get_logger
from core.zetta.voice import get_voice_manager
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask
from shared.types.enums import AgentCapability, PermissionLevel

logger = get_logger("agent_voice")


class VoiceAgent(BaseAgent):
    """Specialized agent for speech-to-text, neural speech synthesis, and voice interaction."""

    def __init__(
        self,
        name: str = "VoiceAgent",
        required_permission: PermissionLevel = PermissionLevel.LOW,
        use_fake: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            description="Audio and speech agent for speech recognition, synthesis, and voice session orchestration.",
            capabilities=[AgentCapability.VOICE],
            required_permission=required_permission,
        )
        self.use_fake = use_fake
        self.voice_manager = get_voice_manager(use_fake=use_fake)
        self.tool_registry = get_tool_registry()

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        """Execute speech synthesis, transcription, or status query."""
        tools_called = []
        try:
            phrase = task.metadata.get("text", "Voice test from Zetta VoiceAgent.")
            fake_mode = task.metadata.get("fake", self.use_fake)
            synth_res = self.tool_registry.execute(
                "voice_synthesize",
                input_data={"text": phrase, "fake": fake_mode},
                task_id=task.id,
            )
            tools_called.append("voice_synthesize")

            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=synth_res.success,
                data=synth_res.data,
                steps_executed=len(tools_called),
                tools_called=tools_called,
            )

        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=False,
                error=ErrorInfo(code="VoiceExecutionError", message=str(e)),
                tools_called=tools_called,
            )
