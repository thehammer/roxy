from __future__ import annotations

from typing import Optional

import boto3
from boto3.dynamodb.conditions import Attr

from app.reactors.models import ReactorRule


class ReactorRegistry:
    def __init__(self, table_name: str, region: str):
        self._table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def upsert(self, rule: ReactorRule) -> None:
        self._table.put_item(Item=rule.to_item())

    def get(self, rule_id: str) -> Optional[ReactorRule]:
        resp = self._table.get_item(Key={"rule_id": rule_id})
        item = resp.get("Item")
        return ReactorRule.from_item(item) if item else None

    def delete(self, rule_id: str) -> None:
        self._table.delete_item(Key={"rule_id": rule_id})

    def list_enabled(self) -> list[ReactorRule]:
        resp = self._table.scan(FilterExpression=Attr("enabled").eq(True))
        return [ReactorRule.from_item(i) for i in resp.get("Items", [])]
