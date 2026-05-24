from __future__ import annotations

import dataclasses
import time
from typing import Optional

import structlog

from app.reactors.registry import ReactorRegistry
from app.reactors.models import ReactorRule

log = structlog.get_logger()

_RULE_REFRESH_INTERVAL = 300  # reload rules from DynamoDB every 5 minutes


class ReactorEngine:
    def __init__(self, registry: ReactorRegistry, slack_client=None):
        self._registry = registry
        self._slack_client = slack_client
        self._rules: list[ReactorRule] = []
        self._last_refresh: float = 0
        self._cooldowns: dict[str, float] = {}  # "{rule_id}:{channel_id}" -> last fired ts

        self._load_rules()

    def _resolve_mention(self, mention: str) -> Optional[str]:
        """Resolve @username to a Slack user ID. Returns None if not found."""
        if not self._slack_client:
            return None
        username = mention.lstrip("@")
        try:
            response = self._slack_client.users_list()
        except Exception as e:
            log.warning("users.list failed — cannot resolve mention", mention=mention, error=str(e))
            return None
        for member in response.get("members", []):
            if member.get("deleted"):
                continue
            if member.get("name") == username or member.get("profile", {}).get("display_name") == username:
                return member["id"]
        log.warning("could not resolve slack mention", mention=mention)
        return None

    def _load_rules(self) -> None:
        rules = self._registry.list_enabled()
        resolved: list[ReactorRule] = []
        for rule in rules:
            if rule.scope_type == "user" and rule.scope_value and rule.scope_value.startswith("@"):
                user_id = self._resolve_mention(rule.scope_value)
                if not user_id:
                    log.warning("skipping rule — unresolvable mention", rule=rule.name, mention=rule.scope_value)
                    continue
                rule = dataclasses.replace(rule, scope_value=user_id)
            resolved.append(rule)
        self._rules = resolved
        self._last_refresh = time.time()
        log.info("reactor rules loaded", count=len(self._rules))

    def _refresh_if_stale(self) -> None:
        if time.time() - self._last_refresh > _RULE_REFRESH_INTERVAL:
            self._load_rules()

    def process_message(self, user_id: str, channel_id: str, text: str) -> list[str]:
        """
        Evaluate all enabled rules against a message.
        Returns a list of response texts for every rule that matched and is off cooldown.
        """
        self._refresh_if_stale()

        now = time.time()
        responses: list[str] = []

        for rule in self._rules:
            if not self._matches_scope(rule, user_id, channel_id):
                continue
            if not self._matches_keywords(rule, text):
                continue

            cooldown_key = f"{rule.rule_id}:{channel_id}"
            if now - self._cooldowns.get(cooldown_key, 0) < rule.cooldown_seconds:
                log.debug("rule on cooldown", rule=rule.name)
                continue

            self._cooldowns[cooldown_key] = now
            responses.append(rule.response_text)
            log.info("reactor rule fired", rule=rule.name, user=user_id, channel=channel_id)

        return responses

    @staticmethod
    def _matches_scope(rule: ReactorRule, user_id: str, channel_id: str) -> bool:
        if rule.scope_type == "any":
            return True
        if rule.scope_type == "user":
            return rule.scope_value == user_id
        if rule.scope_type == "channel":
            return rule.scope_value == channel_id
        return False

    @staticmethod
    def _matches_keywords(rule: ReactorRule, text: str) -> bool:
        """All keyword groups must match (AND); any keyword within a group matches (OR)."""
        if not rule.keyword_groups:
            return False
        text_lower = text.lower()
        return all(
            any(kw in text_lower for kw in group)
            for group in rule.keyword_groups
        )
