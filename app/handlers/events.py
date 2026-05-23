"""Slack event handlers — message tracking for activity timestamps."""

from __future__ import annotations

import structlog

from app.channels.registry import ChannelRegistry

log = structlog.get_logger()


def register(app, registry: ChannelRegistry) -> None:
    @app.event("message")
    def on_message(event, say):
        channel_id = event.get("channel")
        subtype = event.get("subtype")

        # Ignore bot messages and edits/deletes to avoid noise
        if subtype in ("bot_message", "message_changed", "message_deleted"):
            return

        record = registry.get(channel_id)
        if record and record.is_sub_channel:
            registry.touch(channel_id)
            log.debug("touched sub-channel activity", channel_id=channel_id)
