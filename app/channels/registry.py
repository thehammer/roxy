"""DynamoDB-backed registry for channel state and parent/child relationships."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Attr


@dataclass
class ChannelRecord:
    channel_id: str
    channel_name: str
    created_at: int          # unix timestamp
    last_activity_at: int    # unix timestamp
    is_sub_channel: bool
    status: str              # "active" | "archived"
    parent_channel_id: Optional[str] = None
    parent_channel_name: Optional[str] = None

    def to_item(self) -> dict:
        item = asdict(self)
        # DynamoDB doesn't store None values well; drop nulls
        return {k: v for k, v in item.items() if v is not None}

    @classmethod
    def from_item(cls, item: dict) -> "ChannelRecord":
        return cls(
            channel_id=item["channel_id"],
            channel_name=item["channel_name"],
            created_at=int(item["created_at"]),
            last_activity_at=int(item["last_activity_at"]),
            is_sub_channel=bool(item.get("is_sub_channel", False)),
            status=item.get("status", "active"),
            parent_channel_id=item.get("parent_channel_id"),
            parent_channel_name=item.get("parent_channel_name"),
        )


class ChannelRegistry:
    def __init__(self, table_name: str, region: str):
        self._table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def upsert(self, record: ChannelRecord) -> None:
        self._table.put_item(Item=record.to_item())

    def get(self, channel_id: str) -> Optional[ChannelRecord]:
        resp = self._table.get_item(Key={"channel_id": channel_id})
        item = resp.get("Item")
        return ChannelRecord.from_item(item) if item else None

    def touch(self, channel_id: str) -> None:
        """Update last_activity_at to now. No-ops if the channel isn't registered."""
        try:
            self._table.update_item(
                Key={"channel_id": channel_id},
                UpdateExpression="SET last_activity_at = :ts",
                ExpressionAttributeValues={":ts": int(time.time())},
                ConditionExpression="attribute_exists(channel_id)",
            )
        except self._table.meta.client.exceptions.ConditionalCheckFailedException:
            pass

    def archive(self, channel_id: str) -> None:
        self._table.update_item(
            Key={"channel_id": channel_id},
            UpdateExpression="SET #s = :archived",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":archived": "archived"},
        )

    def list_sub_channels(self, parent_channel_id: Optional[str] = None) -> list[ChannelRecord]:
        """Scan for active sub-channels, optionally filtered by parent."""
        filter_expr = Attr("is_sub_channel").eq(True) & Attr("status").eq("active")
        if parent_channel_id:
            filter_expr = filter_expr & Attr("parent_channel_id").eq(parent_channel_id)

        resp = self._table.scan(FilterExpression=filter_expr)
        return [ChannelRecord.from_item(i) for i in resp.get("Items", [])]

    def list_stale_sub_channels(self, older_than_ts: int) -> list[ChannelRecord]:
        """Return active sub-channels with last_activity_at before older_than_ts."""
        filter_expr = (
            Attr("is_sub_channel").eq(True)
            & Attr("status").eq("active")
            & Attr("last_activity_at").lt(older_than_ts)
        )
        resp = self._table.scan(FilterExpression=filter_expr)
        return [ChannelRecord.from_item(i) for i in resp.get("Items", [])]
