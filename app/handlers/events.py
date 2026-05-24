"""Slack event handlers — activity tracking and reactor processing."""

from __future__ import annotations

import structlog

from app.channels.registry import ChannelRegistry
from app.reactors.engine import ReactorEngine

log = structlog.get_logger()


def register(app, registry: ChannelRegistry, engine: ReactorEngine) -> None:
    @app.event("message")
    def on_message(event, say):
        channel_id = event.get("channel")
        subtype = event.get("subtype")

        # Ignore bot messages and edits/deletes to avoid noise
        if subtype in ("bot_message", "message_changed", "message_deleted"):
            return

        # Activity tracking for sub-channels
        record = registry.get(channel_id)
        if record and record.is_sub_channel:
            registry.touch(channel_id)
            log.debug("touched sub-channel activity", channel_id=channel_id)

        # Reactor processing
        user_id = event.get("user")
        text = event.get("text") or ""
        if user_id and text:
            for response in engine.process_message(user_id, channel_id, text):
                say(response)
