"""ZETTA Task Graph and Dependency Resolution Engine."""

from collections import defaultdict, deque
from typing import Dict, List, Set
from core.zetta.utils.errors import ValidationError
from shared.types.contracts import SubTask


class TaskGraph:
    """Directed Acyclic Graph (DAG) for subtask dependency resolution and parallel staging."""

    def __init__(self, subtasks: List[SubTask]) -> None:
        self.subtasks: Dict[str, SubTask] = {t.id: t for t in subtasks}
        self.adj_list: Dict[str, List[str]] = defaultdict(list)
        self.in_degree: Dict[str, int] = {t.id: 0 for t in subtasks}
        self._build_graph()

    def _build_graph(self) -> None:
        """Construct adjacency list and in-degrees from subtask dependencies."""
        for task in self.subtasks.values():
            for dep_id in task.dependencies:
                if dep_id not in self.subtasks:
                    raise ValidationError(
                        f"Subtask '{task.name}' [ID: {task.id}] depends on unknown task ID '{dep_id}'."
                    )
                # dep_id must complete before task.id can run
                self.adj_list[dep_id].append(task.id)
                self.in_degree[task.id] += 1

        # Check for cycles
        self._validate_acyclic()

    def _validate_acyclic(self) -> None:
        """Validate that the dependency graph contains no cycles using Kahn's algorithm."""
        in_deg = dict(self.in_degree)
        queue = deque([task_id for task_id, deg in in_deg.items() if deg == 0])
        visited_count = 0

        while queue:
            curr = queue.popleft()
            visited_count += 1
            for neighbor in self.adj_list[curr]:
                in_deg[neighbor] -= 1
                if in_deg[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(self.subtasks):
            raise ValidationError("Task dependency cycle detected! The plan must be a Directed Acyclic Graph (DAG).")

    def validate_dag(self) -> bool:
        """Explicit DAG validity check."""
        self._validate_acyclic()
        return True


    def get_execution_stages(self) -> List[List[SubTask]]:
        """Compute parallel execution stages (layers of tasks whose dependencies are satisfied)."""
        in_deg = dict(self.in_degree)
        current_layer = [task_id for task_id, deg in in_deg.items() if deg == 0]
        stages: List[List[SubTask]] = []

        while current_layer:
            stages.append([self.subtasks[tid] for tid in current_layer])
            next_layer: List[str] = []
            for tid in current_layer:
                for neighbor in self.adj_list[tid]:
                    in_deg[neighbor] -= 1
                    if in_deg[neighbor] == 0:
                        next_layer.append(neighbor)
            current_layer = next_layer

        return stages

    def get_ready_tasks(self, completed_task_ids: Set[str]) -> List[SubTask]:
        """Return all tasks whose dependencies are fully satisfied in completed_task_ids."""
        ready = []
        for task in self.subtasks.values():
            if task.id in completed_task_ids:
                continue
            if all(dep_id in completed_task_ids for dep_id in task.dependencies):
                ready.append(task)
        return ready
