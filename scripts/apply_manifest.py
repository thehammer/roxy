#!/usr/bin/env python3
"""
Apply slack_manifest.yml to the existing Slack app via the App Configuration API.

Requires (in .env or environment):
  SLACK_APP_ID       — from api.slack.com/apps > Basic Information
  SLACK_APP_TOKEN    — xapp-... token with app_configurations:write scope

Usage:
  python scripts/apply_manifest.py
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

MANIFEST_PATH = Path(__file__).parent.parent / "slack_manifest.yml"
MANIFEST_UPDATE_URL = "https://slack.com/api/apps.manifest.update"


def main() -> None:
    app_id = os.getenv("SLACK_APP_ID")
    if not app_id:
        sys.exit("SLACK_APP_ID is required")

    app_token = os.getenv("SLACK_APP_TOKEN")
    if not app_token:
        sys.exit("SLACK_APP_TOKEN is required")

    manifest_yaml = MANIFEST_PATH.read_text()

    resp = requests.post(
        MANIFEST_UPDATE_URL,
        headers={"Authorization": f"Bearer {app_token}"},
        json={"app_id": app_id, "manifest": manifest_yaml},
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ok"):
        sys.exit(f"Manifest update failed: {data.get('error')}\n{data}")

    print(f"✓ Manifest applied to {app_id}")


if __name__ == "__main__":
    main()
