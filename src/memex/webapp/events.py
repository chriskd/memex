"""Server-Sent Events broadcaster for live reload."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events that can be broadcast."""

    FILE_CHANGED = "file_changed"
    FILE_CREATED = "file_created"
    FILE_DELETED = "file_deleted"
    REINDEX_COMPLETE = "reindex_complete"
    HEARTBEAT = "heartbeat"


@dataclass
class Event:
    """An event to broadcast to clients."""

    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_sse(self) -> str:
        """Format as SSE message."""
        import json

        data_str = json.dumps({"type": self.type.value, **self.data})
        return f"event: {self.type.value}\ndata: {data_str}\n\n"


class EventBroadcaster:
    """Broadcast events to multiple SSE clients."""

    def __init__(self):
        self._subscribers: set[asyncio.Queue[Event]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> AsyncGenerator[Event, None]:
        """Subscribe to events. Yields events as they arrive."""
        queue: asyncio.Queue[Event] = asyncio.Queue()

        async with self._lock:
            self._subscribers.add(queue)
            logger.debug(f"Client subscribed, {len(self._subscribers)} total")

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                self._subscribers.discard(queue)
                logger.debug(f"Client unsubscribed, {len(self._subscribers)} total")

    async def broadcast(self, event: Event) -> None:
        """Broadcast an event to all subscribers."""
        async with self._lock:
            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning("Event queue full, dropping event")

    def broadcast_sync(self, event: Event) -> None:
        """Broadcast from synchronous code (schedules in event loop)."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(event))
        except RuntimeError:
            # No running loop - this can happen during shutdown
            logger.debug("No event loop available for broadcast")

    @property
    def subscriber_count(self) -> int:
        """Number of active subscribers."""
        return len(self._subscribers)


# Global broadcaster instance
_broadcaster: EventBroadcaster | None = None


def get_broadcaster() -> EventBroadcaster:
    """Get the global event broadcaster, creating if needed."""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = EventBroadcaster()
    return _broadcaster
