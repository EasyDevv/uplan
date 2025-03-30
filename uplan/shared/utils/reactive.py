"""Reactive stream implementation for better streaming control."""

import asyncio
from typing import Any, AsyncIterator, Callable, Generic, Optional, TypeVar, Set

T = TypeVar("T")


class ReactiveStream(Generic[T]):
    """A reactive stream that can be observed by multiple subscribers."""

    def __init__(self):
        """Initialize an empty stream with no subscribers."""
        self._subscribers: Set[Callable[[T], None]] = set()
        self._complete_subscribers: Set[Callable[[], None]] = set()
        self._error_subscribers: Set[Callable[[Exception], None]] = set()
        self._is_closed = False
        self._buffer: asyncio.Queue[T] = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None

    def subscribe(
        self,
        on_next: Callable[[T], None],
        on_complete: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> Callable[[], None]:
        """Subscribe to stream events.

        Returns:
            A function that can be called to unsubscribe
        """
        if self._is_closed:
            if on_complete:
                on_complete()
            return lambda: None

        self._subscribers.add(on_next)

        if on_complete:
            self._complete_subscribers.add(on_complete)

        if on_error:
            self._error_subscribers.add(on_error)

        # Return unsubscribe function
        def unsubscribe():
            self._subscribers.discard(on_next)
            if on_complete:
                self._complete_subscribers.discard(on_complete)
            if on_error:
                self._error_subscribers.discard(on_error)

        return unsubscribe

    async def push(self, value: T) -> None:
        """Push a new value to all subscribers."""
        if self._is_closed:
            return

        await self._buffer.put(value)

        # Start processor if not running
        if not self._processor_task or self._processor_task.done():
            self._processor_task = asyncio.create_task(self._process_buffer())

    async def _process_buffer(self) -> None:
        """Process queued values and notify subscribers."""
        try:
            while not self._is_closed:
                try:
                    value = self._buffer.get_nowait()
                    for subscriber in list(self._subscribers):
                        try:
                            subscriber(value)
                        except Exception as e:
                            print(f"Error in subscriber: {e}")
                    self._buffer.task_done()
                except asyncio.QueueEmpty:
                    await asyncio.sleep(0.01)
                    if self._buffer.empty():
                        break
        except Exception as e:
            self._notify_error(e)

    def _notify_error(self, error: Exception) -> None:
        """Notify all error subscribers."""
        for subscriber in list(self._error_subscribers):
            try:
                subscriber(error)
            except Exception as e:
                print(f"Error in error subscriber: {e}")

    def complete(self) -> None:
        """Mark the stream as complete and notify subscribers."""
        if self._is_closed:
            return

        self._is_closed = True

        for subscriber in list(self._complete_subscribers):
            try:
                subscriber()
            except Exception as e:
                print(f"Error in complete subscriber: {e}")

    async def from_async_iterator(self, iterator: AsyncIterator[T]) -> None:
        """Create a stream from an async iterator."""
        try:
            async for value in iterator:
                if self._is_closed:
                    break
                await self.push(value)
            self.complete()
        except Exception as e:
            self._notify_error(e)
            self.complete()
