"""In-memory async queue for pipeline run jobs with DB recovery."""

import asyncio

from viper.db.repositories import RunRepository
from viper.db.session import async_session_maker

run_queue: asyncio.Queue[str] = asyncio.Queue()
_queued_ids: set[str] = set()


def enqueue(run_id: str) -> bool:
    """Enqueue a run ID for background execution if not already present."""
    if run_id in _queued_ids:
        return False
    _queued_ids.add(run_id)
    run_queue.put_nowait(run_id)
    return True


async def dequeue() -> str:
    """Wait for and retrieve the next run ID from the queue."""
    run_id = await run_queue.get()
    _queued_ids.discard(run_id)
    return run_id


def queue_size() -> int:
    """Return the number of pending items in the memory queue."""
    return run_queue.qsize()


def is_queued(run_id: str) -> bool:
    """Check if a run ID is currently in the queue."""
    return run_id in _queued_ids


def clear_queue() -> None:
    """Reset the in-memory queue state (primarily for testing)."""
    while not run_queue.empty():
        try:
            run_queue.get_nowait()
        except asyncio.QueueEmpty:
            break
    _queued_ids.clear()


async def enqueue_pending_from_db(limit: int = 100) -> int:
    """Poll DB for pending runs and add unqueued runs to queue."""
    async with async_session_maker() as session:
        repo = RunRepository(session)
        pending_runs = await repo.list(limit=limit, status='pending')
        enqueued_count = 0
        for run in pending_runs:
            if enqueue(run.id):
                enqueued_count += 1
        return enqueued_count
