"""Orchestrates sub-channel lifecycle: create, notify, prune."""

from __future__ import annotations

import re
import time
from datetime import timedelta

import structlog

from app.channels.registry import ChannelRecord, ChannelRegistry

log = structlog.get_logger()

# Slack channel names: lowercase, alphanumeric + hyphens, max 80 chars
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,78}[a-z0-9]$|^[a-z0-9]$")


class ChannelManager:
    def __init__(self, registry: ChannelRegistry, slack_client, inactivity_days: int):
        self._registry = registry
        self._client = slack_client
        self._inactivity_days = inactivity_days

    def spawn_sub_channel(
        self,
        name: str,
        parent_channel_id: str,
        parent_channel_name: str,
        requesting_user_id: str,
    ) -> tuple[bool, str]:
        """
        Create a sub-channel under parent_channel.
        Returns (success, message).
        """
        name = name.lower().strip()

        if not _NAME_RE.match(name):
            return False, f"`{name}` is not a valid Slack channel name (lowercase, hyphens only)."

        existing = self._registry.get(name)  # we key by ID, so check via Slack API
        # Create the channel via Slack API
        try:
            resp = self._client.conversations_create(name=name, is_private=False)
        except Exception as e:
            err = str(e)
            if "name_taken" in err:
                return False, f"A channel named `#{name}` already exists."
            log.error("conversations_create failed", name=name, error=err)
            return False, "Failed to create channel — check bot permissions."

        channel = resp["channel"]
        now = int(time.time())

        record = ChannelRecord(
            channel_id=channel["id"],
            channel_name=name,
            created_at=now,
            last_activity_at=now,
            is_sub_channel=True,
            status="active",
            parent_channel_id=parent_channel_id,
            parent_channel_name=parent_channel_name,
        )
        self._registry.upsert(record)

        # Invite the requesting user into the new channel
        try:
            self._client.conversations_invite(channel=channel["id"], users=requesting_user_id)
        except Exception as e:
            log.warning("Could not invite user to new channel", error=str(e))

        # Post a welcome note in the new channel
        self._client.chat_postMessage(
            channel=channel["id"],
            text=f"👋 Welcome to <#{channel['id']}>! This sub-channel was spawned from <#{parent_channel_id}> by <@{requesting_user_id}>.",
        )

        log.info("spawned sub-channel", name=name, parent=parent_channel_name)
        return True, f"Created <#{channel['id']}>."

    def register_channel(self, channel_id: str, channel_name: str) -> str:
        """Register an existing channel for activity monitoring (not prune-eligible)."""
        existing = self._registry.get(channel_id)
        if existing:
            return f"<#{channel_id}> is already being monitored."

        now = int(time.time())
        record = ChannelRecord(
            channel_id=channel_id,
            channel_name=channel_name,
            created_at=now,
            last_activity_at=now,
            is_sub_channel=False,
            status="active",
        )
        self._registry.upsert(record)
        log.info("registered channel for monitoring", channel=channel_name)
        return f"<#{channel_id}> is now being monitored for activity."

    def prune_stale_channels(self) -> list[str]:
        """
        Archive sub-channels with no activity for inactivity_days.
        Returns list of archived channel names.
        """
        cutoff = int(time.time()) - int(timedelta(days=self._inactivity_days).total_seconds())
        stale = self._registry.list_stale_sub_channels(older_than_ts=cutoff)
        archived = []

        for record in stale:
            try:
                self._client.conversations_archive(channel=record.channel_id)
                self._registry.archive(record.channel_id)
                archived.append(record.channel_name)
                log.info("archived stale sub-channel", name=record.channel_name)
            except Exception as e:
                log.error("failed to archive channel", name=record.channel_name, error=str(e))

        return archived
