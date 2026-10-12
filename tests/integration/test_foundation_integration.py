"""Integration test linking EventBus, ToolRegistry, TaskManager, and SecurityManager."""

import unittest
from core.zetta.events import get_event_bus, Event
from core.zetta.security import get_security_manager
from core.zetta.tasks import get_task_manager
from core.zetta.tools import get_tool_registry
from core.zetta.tools.system.system_info import SystemInfoTool
from shared.types.enums import EventType, TaskStatus


class TestFoundationIntegration(unittest.TestCase):

    def test_full_foundation_integration(self):
        event_bus = get_event_bus()
        task_manager = get_task_manager()
        tool_registry = get_tool_registry()
        security = get_security_manager()

        events_captured = []

        def on_event(evt: Event):
            events_captured.append(evt)

        event_bus.subscribe_all(on_event)

        # 1. Create Task
        task = task_manager.create_task(name="integration_task")
        self.assertEqual(task.status, TaskStatus.CREATED)

        # 2. Register Tool
        tool = SystemInfoTool()
        tool_registry.register(tool)

        # 3. Check Security
        self.assertTrue(security.check_tool_permission(tool.required_permission))

        # 4. Start Task & Execute Tool
        task_manager.start_task(task.id)
        res = tool_registry.execute("system_info", {}, task_id=task.id)
        self.assertTrue(res.success)

        # 5. Complete Task
        task_manager.complete_task(task.id, result=res.data)
        self.assertEqual(task.status, TaskStatus.COMPLETED)

        # Verify captured events
        event_types = [e.event_type for e in events_captured]
        self.assertIn(EventType.TASK_CREATED, event_types)
        self.assertIn(EventType.TASK_STARTED, event_types)
        self.assertIn(EventType.TOOL_STARTED, event_types)
        self.assertIn(EventType.TOOL_COMPLETED, event_types)
        self.assertIn(EventType.TASK_COMPLETED, event_types)


if __name__ == "__main__":
    unittest.main()
