import time
from unittest.mock import MagicMock

import pytest

from app.reactors.engine import ReactorEngine
from app.reactors.models import ReactorRule


def make_rule(**kwargs) -> ReactorRule:
    defaults = dict(
        rule_id="r1",
        name="test rule",
        enabled=True,
        scope_type="any",
        scope_value=None,
        keyword_groups=[["hello"]],
        response_text="hi there",
        cooldown_seconds=300,
        created_at=1000,
    )
    defaults.update(kwargs)
    return ReactorRule(**defaults)


@pytest.fixture
def engine():
    registry = MagicMock()
    registry.list_enabled.return_value = []
    return ReactorEngine(registry=registry)


def set_rules(engine, rules):
    engine._rules = rules
    engine._last_refresh = time.time()


# --- scope matching ---

def test_any_scope_matches_all(engine):
    set_rules(engine, [make_rule(scope_type="any")])
    assert engine.process_message("U_ANY", "C_ANY", "hello") == ["hi there"]


def test_user_scope_matches_correct_user(engine):
    set_rules(engine, [make_rule(scope_type="user", scope_value="U_DREW")])
    assert engine.process_message("U_DREW", "C1", "hello") == ["hi there"]


def test_user_scope_ignores_wrong_user(engine):
    set_rules(engine, [make_rule(scope_type="user", scope_value="U_DREW")])
    assert engine.process_message("U_OTHER", "C1", "hello") == []


def test_channel_scope_matches_correct_channel(engine):
    set_rules(engine, [make_rule(scope_type="channel", scope_value="C_SPORTS")])
    assert engine.process_message("U1", "C_SPORTS", "hello") == ["hi there"]


def test_channel_scope_ignores_wrong_channel(engine):
    set_rules(engine, [make_rule(scope_type="channel", scope_value="C_SPORTS")])
    assert engine.process_message("U1", "C_OTHER", "hello") == []


# --- keyword matching ---

def test_single_group_matches(engine):
    set_rules(engine, [make_rule(keyword_groups=[["buy", "game"]])])
    assert engine.process_message("U1", "C1", "should I buy this game?") == ["hi there"]


def test_single_group_no_match(engine):
    set_rules(engine, [make_rule(keyword_groups=[["buy", "game"]])])
    assert engine.process_message("U1", "C1", "the weather is nice") == []


def test_multiple_groups_all_must_match(engine):
    rule = make_rule(keyword_groups=[["game", "steam"], ["$", "price"]])
    set_rules(engine, [rule])
    assert engine.process_message("U1", "C1", "is this game on steam for $10?") == ["hi there"]
    assert engine.process_message("U1", "C1", "this game is great") == []
    assert engine.process_message("U1", "C1", "only $10!") == []


def test_keyword_matching_is_case_insensitive(engine):
    set_rules(engine, [make_rule(keyword_groups=[["mac", "macos"]])])
    assert engine.process_message("U1", "C1", "My MAC won't run this") == ["hi there"]


def test_empty_keyword_groups_never_matches(engine):
    set_rules(engine, [make_rule(keyword_groups=[])])
    assert engine.process_message("U1", "C1", "hello anything") == []


# --- cooldown ---

def test_cooldown_prevents_rapid_refiring(engine):
    set_rules(engine, [make_rule(cooldown_seconds=60)])
    first = engine.process_message("U1", "C1", "hello")
    second = engine.process_message("U1", "C1", "hello")
    assert first == ["hi there"]
    assert second == []


def test_cooldown_is_per_channel(engine):
    set_rules(engine, [make_rule(cooldown_seconds=60)])
    engine.process_message("U1", "C1", "hello")
    assert engine.process_message("U1", "C2", "hello") == ["hi there"]


def test_cooldown_expires(engine):
    set_rules(engine, [make_rule(cooldown_seconds=1)])
    engine.process_message("U1", "C1", "hello")
    engine._cooldowns["r1:C1"] = time.time() - 2
    assert engine.process_message("U1", "C1", "hello") == ["hi there"]


# --- multiple rules ---

def test_all_matching_rules_fire(engine):
    rules = [
        make_rule(rule_id="r1", keyword_groups=[["hello"]], response_text="response 1"),
        make_rule(rule_id="r2", keyword_groups=[["hello"]], response_text="response 2"),
    ]
    set_rules(engine, rules)
    responses = engine.process_message("U1", "C1", "hello")
    assert set(responses) == {"response 1", "response 2"}


# --- rule refresh ---

def test_rules_refreshed_when_stale(engine):
    engine._last_refresh = 0  # force stale
    engine._registry.list_enabled.return_value = [make_rule()]
    result = engine.process_message("U1", "C1", "hello")
    assert result == ["hi there"]
    engine._registry.list_enabled.assert_called()
