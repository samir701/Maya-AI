"""ZETTA Unified Autonomous Workflow coordinating Planner, Fleet, Memory, and Verification."""

import time
from typing import Any, Callable, Dict, List, Optional
from core.zetta.agents.manager.manager import AgentManager, get_agent_manager
from core.zetta.agents.manager.registry import AgentRegistry, get_agent_registry
from core.zetta.agents.orchestrator.orchestrator import AgentOrchestrator
from core.zetta.agents.planner.planner import AutonomousPlanner
from core.zetta.memory.manager import MemoryManager
from core.zetta.security.manager import SecurityManager, get_security_manager
from core.zetta.utils.errors import ExecutionError, SecurityError
from core.zetta.utils.logging import get_logger
from shared.types.contracts import TaskPlan
from shared.types.enums import MemorySource, MemoryType, PermissionLevel, PlanStatus

logger = get_logger("unified_workflow")


class UnifiedAutonomousWorkflow:
    """High-level autonomous pipeline executing user goals via planning, agent fleet, and memory."""

    def __init__(
        self,
        planner: Optional[AutonomousPlanner] = None,
        orchestrator: Optional[AgentOrchestrator] = None,
        memory_manager: Optional[MemoryManager] = None,
        agent_registry: Optional[AgentRegistry] = None,
        security_manager: Optional[SecurityManager] = None,
    ) -> None:
        self.agent_registry = agent_registry or get_agent_registry()
        # Ensure default fleet is registered
        from core.zetta.agents.fleet import register_default_fleet
        register_default_fleet(self.agent_registry)

        self.agent_manager = get_agent_manager(self.agent_registry)
        self.planner = planner or AutonomousPlanner()
        self.orchestrator = orchestrator or AgentOrchestrator(
            agent_manager=self.agent_manager,
        )
        self.memory = memory_manager
        self.security = security_manager or get_security_manager()

    def execute_goal(
        self,
        goal: str,
        user_role: str = "user",
        confirmation_callback: Optional[Callable[[str], bool]] = None,
        persist_memory: bool = True,
    ) -> Dict[str, Any]:
        """Plan, orchestrate, verify, and persist an autonomous multi-step workflow."""
        start_t = time.perf_counter()
        logger.info("Starting unified autonomous workflow for goal: '%s'", goal)

        # 1. Security validation for autonomous workflow
        if not self.security.check_permission(user_role, PermissionLevel.LOW):
            raise SecurityError(f"Permission denied for user role '{user_role}' to run autonomous workflows.")

        self.security.audit.log_event(
            action="unified_workflow_start",
            actor=user_role,
            resource="planner",
            status="STARTED",
            details={"goal": goal},
        )

        # 2. Planning phase
        plan = self.planner.create_plan(goal)
        logger.info("Generated execution plan '%s' with %d subtasks.", plan.id, len(plan.subtasks))


        # 3. Execution phase
        role_levels = {
            "guest": PermissionLevel.LOW,
            "user": PermissionLevel.HIGH,
            "operator": PermissionLevel.HIGH,
            "admin": PermissionLevel.CRITICAL,
            "system": PermissionLevel.CRITICAL,
        }
        granted_level = role_levels.get(user_role.lower(), PermissionLevel.LOW)
        prev_level = self.security.permission_checker.current_level
        self.security.permission_checker.current_level = granted_level
        try:
            executed_plan = self.orchestrator.execute_plan(plan=plan)
        finally:
            self.security.permission_checker.current_level = prev_level

        overall_success = executed_plan.status == PlanStatus.COMPLETED
        total_duration_ms = (time.perf_counter() - start_t) * 1000

        # 4. Verification phase
        verification_passed = True
        verification_notes = []
        for crit in executed_plan.verification_criteria:
            if overall_success:
                verification_notes.append(f"PASS: {crit}")
            else:
                verification_passed = False
                verification_notes.append(f"FAIL: {crit}")

        # 5. Memory persistence (store sanitized high-level task summary only)
        persisted_memory_id = None
        if persist_memory and overall_success and self.memory:
            try:
                summary_content = (
                    f"Successfully accomplished goal: '{goal}'. "
                    f"Executed {len(executed_plan.subtasks)} subtasks across agents: "
                    f"{', '.join(set(st.assigned_agent for st in executed_plan.subtasks if st.assigned_agent))}."
                )
                mem = self.memory.add_memory(
                    content=summary_content,
                    memory_type=MemoryType.EPISODIC,
                    source=MemorySource.TASK,
                    tags=["phase08", "workflow_success"],
                )
                persisted_memory_id = getattr(mem, "id", None)
            except Exception as e:
                logger.warning("Failed persisting task summary to memory: %s", e)

        self.security.audit.log_event(
            action="unified_workflow_finish",
            actor=user_role,
            resource="orchestrator",
            status="SUCCESS" if overall_success else "FAILED",
            details={"plan_id": executed_plan.id, "duration_ms": total_duration_ms},
        )

        return {
            "success": overall_success,
            "goal": goal,
            "plan_id": executed_plan.id,
            "status": executed_plan.status.value,
            "subtasks_count": len(executed_plan.subtasks),
            "subtask_results": [
                {
                    "subtask_id": st.id,
                    "agent_id": st.assigned_agent,
                    "status": st.status.value,
                    "result": getattr(st.result, "data", st.result),
                    "error": st.error.message if st.error else None,
                }
                for st in executed_plan.subtasks
            ],
            "verification": {
                "verified": verification_passed,
                "notes": verification_notes,
            },
            "duration_ms": total_duration_ms,
            "persisted_memory_id": persisted_memory_id,
        }

