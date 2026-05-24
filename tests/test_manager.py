from unittest.mock import MagicMock

import pytest

from app.channels.manager import ChannelManager
from app.channels.registry import ChannelRecord


@pytest.fixture
def slack_client():
    client = MagicMock()
    client.conversations_create.return_value = {"channel": {"id": "C_NEW", "name": "new-sub"}}
    return client


@pytest.fixture
def manager(registry, slack_client):
    return ChannelManager(registry=registry, slack_client=slack_client, inactivity_days=30)


# --- /spawn ---

def test_spawn_creates_channel_and_registers(manager, registry, slack_client):
    success, msg = manager.spawn_sub_channel(
        name="new-sub",
        parent_channel_id="C_PARENT",
        parent_channel_name="parent",
        requesting_user_id="U123",
    )
    assert success
    assert "C_NEW" in msg
    record = registry.get("C_NEW")
    assert record is not None
    assert record.is_sub_channel is True
    assert record.parent_channel_id == "C_PARENT"
    assert record.status == "active"


def test_spawn_invites_requesting_user(manager, slack_client):
    manager.spawn_sub_channel("new-sub", "C_P", "parent", "U123")
    slack_client.conversations_invite.assert_called_once_with(channel="C_NEW", users="U123")


def test_spawn_posts_welcome_message(manager, slack_client):
    manager.spawn_sub_channel("new-sub", "C_P", "parent", "U123")
    slack_client.chat_postMessage.assert_called_once()
    call_kwargs = slack_client.chat_postMessage.call_args[1]
    assert call_kwargs["channel"] == "C_NEW"


def test_spawn_rejects_invalid_name(manager):
    success, msg = manager.spawn_sub_channel("INVALID NAME!", "C_P", "parent", "U123")
    assert not success
    assert "not a valid" in msg


def test_spawn_handles_name_taken(manager, slack_client):
    slack_client.conversations_create.side_effect = Exception("name_taken")
    success, msg = manager.spawn_sub_channel("taken", "C_P", "parent", "U123")
    assert not success
    assert "already exists" in msg


def test_spawn_handles_slack_error(manager, slack_client):
    slack_client.conversations_create.side_effect = Exception("missing_scope")
    success, msg = manager.spawn_sub_channel("oops", "C_P", "parent", "U123")
    assert not success
    assert "permissions" in msg


# --- /monitor ---

def test_register_channel(manager, registry):
    msg = manager.register_channel(channel_id="C_OLD", channel_name="existing")
    assert "now being monitored" in msg
    record = registry.get("C_OLD")
    assert record is not None
    assert record.is_sub_channel is False


def test_register_channel_already_monitored(manager):
    manager.register_channel(channel_id="C_OLD", channel_name="existing")
    msg = manager.register_channel(channel_id="C_OLD", channel_name="existing")
    assert "already being monitored" in msg


# --- /prune ---

def test_prune_archives_stale_channels(manager, registry, slack_client):
    registry.upsert(ChannelRecord(
        channel_id="C_STALE", channel_name="stale-sub",
        created_at=100, last_activity_at=100,
        is_sub_channel=True, status="active",
    ))
    archived = manager.prune_stale_channels()
    assert "stale-sub" in archived
    slack_client.conversations_archive.assert_called_once_with(channel="C_STALE")
    assert registry.get("C_STALE").status == "archived"


def test_prune_skips_fresh_channels(manager, registry):
    import time
    registry.upsert(ChannelRecord(
        channel_id="C_FRESH", channel_name="fresh-sub",
        created_at=int(time.time()), last_activity_at=int(time.time()),
        is_sub_channel=True, status="active",
    ))
    archived = manager.prune_stale_channels()
    assert "fresh-sub" not in archived


def test_prune_skips_non_sub_channels(manager, registry):
    registry.upsert(ChannelRecord(
        channel_id="C_TOP", channel_name="top-level",
        created_at=100, last_activity_at=100,
        is_sub_channel=False, status="active",
    ))
    archived = manager.prune_stale_channels()
    assert "top-level" not in archived
