"""Unit tests for Task lifecycle management."""

import unittest
from core.zetta.tasks.manager import TaskManager
from shared.types.enums import TaskStatus


class TestTasks(unittest.TestCase):

    def test_task_lifecycle(self):
        manager = TaskManager()
        task = manager.create_task(name="test_task", description="Sample description")
        self.assertEqual(task.status, TaskStatus.CREATED)

        manager.queue_task(task.id)
        self.assertEqual(task.status, TaskStatus.QUEUED)

        manager.start_task(task.id)
        self.assertEqual(task.status, TaskStatus.RUNNING)
        self.assertIsNotNone(task.started_at)

        manager.complete_task(task.id, result={"output": "success"})
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(task.completed_at)
        self.assertEqual(task.result["output"], "success")

    def test_task_failure(self):
        manager = TaskManager()
        task = manager.create_task(name="failing_task")
        manager.start_task(task.id)
        manager.fail_task(task.id, error_message="Task crashed")

        self.assertEqual(task.status, TaskStatus.FAILED)
        self.assertEqual(task.error.message, "Task crashed")


if __name__ == "__main__":
    unittest.main()
