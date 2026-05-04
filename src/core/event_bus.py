"""
EventBus - Simple publish/subscribe system so agents can communicate
without holding direct references to one another.

Usage:
    bus = EventBus()
    bus.subscribe("wolf_howl", my_callback)
    bus.publish("wolf_howl", pos=(100, 200), loudness=90)
"""

from collections import defaultdict


class EventBus:
    """Lightweight sync event bus."""

    def __init__(self):
        self._subscribers = defaultdict(list)
        # keep a short log for the debug overlay
        self.recent_events = []
        self.max_log = 8

    def subscribe(self, event_name: str, callback):
        """Register a callback for an event name."""
        self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback):
        if callback in self._subscribers[event_name]:
            self._subscribers[event_name].remove(callback)

    def publish(self, event_name: str, **data):
        """Fire an event to all subscribers. Extra kwargs are passed through."""
        # log it
        summary = f"{event_name}"
        if "pos" in data:
            summary += f" @ ({int(data['pos'][0])},{int(data['pos'][1])})"
        self.recent_events.append(summary)
        if len(self.recent_events) > self.max_log:
            self.recent_events.pop(0)

        # deliver to subscribers
        for callback in self._subscribers[event_name]:
            try:
                callback(**data)
            except TypeError:
                # allow callbacks that ignore kwargs
                callback()
