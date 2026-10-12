"""ZETTA Background Agent and Task Runner."""

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import threading
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4
from core.zetta.utils.errors import NotFoundError
from core.zetta.utils.logging import get_logger

logger = get_logger("background_runner")


class JobStatus(str, Enum):
    """Execution status of a background job."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class BackgroundJob:
    """Descriptor and state for a long-running background job."""
    name: str
    job_id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _cancel_requested: bool = False


class BackgroundAgentRunner:
    """Manages background task submission, tracking, and cancellation."""

    def __init__(self, max_workers: int = 4) -> None:
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="zetta_bg_worker")
        self._jobs: Dict[str, BackgroundJob] = {}
        self._futures: Dict[str, Future] = {}
        self._lock = threading.RLock()

    def submit_job(
        self,
        name: str,
        target_fn: Callable[..., Any],
        *args: Any,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> BackgroundJob:
        """Submit a task/function to run asynchronously in the background."""
        job = BackgroundJob(name=name, metadata=metadata or {})
        with self._lock:
            self._jobs[job.job_id] = job

        def worker_wrapper():
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc).isoformat()
            logger.info("Background job '%s' [%s] started.", job.name, job.job_id)
            try:
                # Pass cancel check if the target accepts it, or just call target
                res = target_fn(*args, **kwargs)
                if job._cancel_requested:
                    job.status = JobStatus.CANCELLED
                    job.error = "Job cancelled by user request."
                    try:
                        logger.info("Background job '%s' [%s] cancelled.", job.name, job.job_id)
                    except Exception:
                        pass
                else:
                    job.status = JobStatus.COMPLETED
                    job.progress = 1.0
                    job.result = res
                    try:
                        logger.info("Background job '%s' [%s] completed successfully.", job.name, job.job_id)
                    except Exception:
                        pass
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                try:
                    logger.error("Background job '%s' [%s] failed: %s", job.name, job.job_id, e)
                except Exception:
                    pass
            finally:
                job.completed_at = datetime.now(timezone.utc).isoformat()


        future = self.executor.submit(worker_wrapper)
        with self._lock:
            self._futures[job.job_id] = future

        return job

    def cancel_job(self, job_id: str) -> bool:
        """Request cancellation of a running background job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise NotFoundError(f"Background job '{job_id}' not found.")
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return False

            job._cancel_requested = True
            job.status = JobStatus.CANCELLED
            future = self._futures.get(job_id)
            if future:
                future.cancel()
            logger.info("Cancellation signalled for background job '%s'", job_id)
            return True

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        """Retrieve background job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List status summary of all tracked background jobs."""
        with self._lock:
            return [
                {
                    "job_id": j.job_id,
                    "name": j.name,
                    "status": j.status.value,
                    "progress": j.progress,
                    "created_at": j.created_at,
                    "started_at": j.started_at,
                    "completed_at": j.completed_at,
                    "error": j.error,
                }
                for j in self._jobs.values()
            ]

    def shutdown(self, wait: bool = False) -> None:
        """Shutdown background thread pool."""
        self.executor.shutdown(wait=wait)


_global_background_runner: Optional[BackgroundAgentRunner] = None
_runner_lock = threading.Lock()


def get_background_runner() -> BackgroundAgentRunner:
    """Get or initialize global BackgroundAgentRunner singleton."""
    global _global_background_runner
    with _runner_lock:
        if _global_background_runner is None:
            _global_background_runner = BackgroundAgentRunner()
        return _global_background_runner
