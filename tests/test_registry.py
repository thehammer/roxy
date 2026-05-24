import time

from app.channels.registry import ChannelRecord


def make_record(**kwargs) -> ChannelRecord:
    defaults = dict(
        channel_id="C123",
        channel_name="test-channel",
        created_at=1000,
        last_activity_at=1000,
        is_sub_channel=True,
        status="active",
    )
    defaults.update(kwargs)
    return ChannelRecord(**defaults)


def test_upsert_and_get(registry):
    registry.upsert(make_record())
    result = registry.get("C123")
    assert result is not None
    assert result.channel_name == "test-channel"
    assert result.is_sub_channel is True


def test_get_missing_returns_none(registry):
    assert registry.get("CNOPE") is None


def test_touch_updates_timestamp(registry):
    registry.upsert(make_record(last_activity_at=1000))
    before = int(time.time())
    registry.touch("C123")
    result = registry.get("C123")
    assert result.last_activity_at >= before


def test_touch_ignores_unregistered_channel(registry):
    registry.touch("CNOPE")  # must not raise or create a record
    assert registry.get("CNOPE") is None


def test_archive_sets_status(registry):
    registry.upsert(make_record())
    registry.archive("C123")
    result = registry.get("C123")
    assert result.status == "archived"


def test_list_sub_channels_returns_active_only(registry):
    registry.upsert(make_record(channel_id="C1", channel_name="sub1", is_sub_channel=True))
    registry.upsert(make_record(channel_id="C2", channel_name="top", is_sub_channel=False))
    registry.upsert(make_record(channel_id="C3", channel_name="archived-sub", status="archived"))
    subs = registry.list_sub_channels()
    ids = {r.channel_id for r in subs}
    assert ids == {"C1"}


def test_list_sub_channels_filtered_by_parent(registry):
    registry.upsert(make_record(channel_id="C1", channel_name="sub1", parent_channel_id="P1"))
    registry.upsert(make_record(channel_id="C2", channel_name="sub2", parent_channel_id="P2"))
    results = registry.list_sub_channels(parent_channel_id="P1")
    assert len(results) == 1
    assert results[0].channel_id == "C1"


def test_list_stale_sub_channels(registry):
    registry.upsert(make_record(channel_id="C_OLD", channel_name="old", last_activity_at=100))
    now = int(time.time())
    registry.upsert(make_record(channel_id="C_NEW", channel_name="new", last_activity_at=now))
    stale = registry.list_stale_sub_channels(older_than_ts=1000)
    assert len(stale) == 1
    assert stale[0].channel_id == "C_OLD"


def test_roundtrip_preserves_optional_fields(registry):
    record = make_record(parent_channel_id="PXYZ", parent_channel_name="parent")
    registry.upsert(record)
    result = registry.get("C123")
    assert result.parent_channel_id == "PXYZ"
    assert result.parent_channel_name == "parent"
