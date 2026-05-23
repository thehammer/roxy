"""Slash command handlers."""

from __future__ import annotations

import structlog

from app.channels.manager import ChannelManager

log = structlog.get_logger()


def register(app, manager: ChannelManager) -> None:

    @app.command("/spawn")
    def spawn_command(ack, command, say):
        """
        /spawn <name>
        Creates a sub-channel under the current channel.
        """
        ack()

        name = (command.get("text") or "").strip()
        if not name:
            say("Usage: `/spawn <channel-name>`")
            return

        parent_id = command["channel_id"]
        parent_name = command["channel_name"]
        user_id = command["user_id"]

        success, msg = manager.spawn_sub_channel(
            name=name,
            parent_channel_id=parent_id,
            parent_channel_name=parent_name,
            requesting_user_id=user_id,
        )
        say(msg)

    @app.command("/prune")
    def prune_command(ack, command, say):
        """
        /prune
        Manually trigger stale sub-channel archival (admin use).
        """
        ack()
        # TODO: restrict to workspace admins
        archived = manager.prune_stale_channels(manager._registry._inactivity_days)
        if archived:
            names = ", ".join(f"`#{n}`" for n in archived)
            say(f"Archived {len(archived)} stale sub-channel(s): {names}")
        else:
            say("No stale sub-channels found.")
