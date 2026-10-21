from typing import Callable, Any

class EventDispatcher:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[dict[str, Any]], None]] = {}

    def register(self, topic: str, handler: Callable[[dict[str, Any]], None]) -> None:
        self._handlers[topic] = handler

    def dispatch(self, topic: str, payload: dict[str, Any]) -> None:
        handler = self._handlers.get(topic)
        if handler:
            handler(payload)
