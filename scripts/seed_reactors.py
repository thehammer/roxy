#!/usr/bin/env python3
"""
Seed the roxy-reactors DynamoDB table with initial reactor rules.

Covers the behaviour previously handled by inner-drew.

Requires:
  DREW_USER_ID — Slack user ID to monitor (U...)
  AWS_REGION   — defaults to us-east-1

Usage:
  DREW_USER_ID=U... python scripts/seed_reactors.py
"""

import os
import sys
import time

import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = os.getenv("AWS_REGION", "us-east-1")
TABLE = os.getenv("ROXY_REACTORS_TABLE", "roxy-reactors")
DREW_USER_ID = os.getenv("DREW_USER_ID")

if not DREW_USER_ID:
    sys.exit("DREW_USER_ID is required")

table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE)
now = int(time.time())

RULES = [
    {
        "rule_id": "inner-drew-game-purchase",
        "name": "Encourage Drew to buy cheap games",
        "enabled": True,
        "scope_type": "user",
        "scope_value": DREW_USER_ID,
        "keyword_groups": [
            ["game", "buy", "worth", "should i", "on sale",
             "steam", "itch", "gog", "humble", "epic"],
            ["$", "dollar", "price", "cost", "cheap", "sale"],
        ],
        "response_text": "Just buy it. You know you want to. It's basically free.",
        "cooldown_seconds": 300,
        "created_at": now,
    },
    {
        "rule_id": "inner-drew-mac-complaint",
        "name": "Suggest Drew build a PC when complaining about Mac gaming",
        "enabled": True,
        "scope_type": "user",
        "scope_value": DREW_USER_ID,
        "keyword_groups": [
            ["mac", "macos", "apple silicon", "m1", "m2", "m3", "m4"],
            ["not supported", "doesn't work", "won't run", "can't play",
             "no mac version", "windows only", "pc only",
             "ugh", "annoyed", "frustrated", "hate", "sucks", "damn", "wish"],
        ],
        "response_text": "This wouldn't happen if you built a PC. Just saying.",
        "cooldown_seconds": 300,
        "created_at": now,
    },
]

for rule in RULES:
    table.put_item(Item=rule)
    print(f"✓ Seeded rule: {rule['name']}")

print(f"\nSeeded {len(RULES)} rule(s) into {TABLE}.")
