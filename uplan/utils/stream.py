"""Centralized stream control utilities."""

import asyncio
from typing import Optional, Callable, Set, Dict, Any


class StreamController:
    """Manages streaming operations with centralized cancellation support."""

    def __init__(self):
        """Initialize stream controller."""
        self._stop_requested = False
        self._active_tasks: Set[asyncio.Task] = set()
        self._callbacks: Dict[str, Callable] = {}

    @property
    def stop_requested(self) -> bool:
        """Check if stop was requested."""
        return self._stop_requested

    def request_stop(self) -> None:
        """Request all streaming operations to stop."""
        if self._stop_requested:
            return

        self._stop_requested = True

        # Cancel all running tasks
        for task in self._active_tasks:
            if not task.done():
                task.cancel()

        # Execute callbacks
        for callback in self._callbacks.values():
            try:
                callback()
            except Exception as e:
                raise e

    def reset(self) -> None:
        """Reset controller state."""
        self._stop_requested = False
        self._active_tasks = {t for t in self._active_tasks if not t.done()}

    def register_task(self, task: asyncio.Task) -> None:
        """Register task for automatic cancellation."""
        self._active_tasks.add(task)
        # Clean up completed tasks
        self._active_tasks = {t for t in self._active_tasks if not t.done()}

    def register_callback(self, key: str, callback: Callable) -> None:
        """Register callback to execute when stop is requested."""
        self._callbacks[key] = callback

    def unregister_callback(self, key: str) -> None:
        """Remove a registered callback."""
        self._callbacks.pop(key, None)

    async def run_cancellable(self, coro: Any) -> Any:
        """Run coroutine with cancellation support."""
        task = asyncio.create_task(coro)
        self.register_task(task)
        try:
            return await task
        except asyncio.CancelledError:
            raise
