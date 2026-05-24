from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ReactorRule:
    rule_id: str
    name: str
    enabled: bool
    scope_type: str               # "user" | "channel" | "any"
    scope_value: Optional[str]    # user_id or channel_id; None when scope_type="any"
    keyword_groups: list[list[str]]  # AND across groups, OR within each group
    response_text: str
    cooldown_seconds: int
    created_at: int

    def to_item(self) -> dict:
        item: dict = {
            "rule_id": self.rule_id,
            "name": self.name,
            "enabled": self.enabled,
            "scope_type": self.scope_type,
            "keyword_groups": self.keyword_groups,
            "response_text": self.response_text,
            "cooldown_seconds": self.cooldown_seconds,
            "created_at": self.created_at,
        }
        if self.scope_value is not None:
            item["scope_value"] = self.scope_value
        return item

    @classmethod
    def from_item(cls, item: dict) -> "ReactorRule":
        return cls(
            rule_id=item["rule_id"],
            name=item["name"],
            enabled=bool(item["enabled"]),
            scope_type=item["scope_type"],
            scope_value=item.get("scope_value"),
            keyword_groups=[list(group) for group in item["keyword_groups"]],
            response_text=item["response_text"],
            cooldown_seconds=int(item["cooldown_seconds"]),
            created_at=int(item["created_at"]),
        )
