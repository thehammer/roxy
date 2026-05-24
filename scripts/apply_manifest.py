#!/usr/bin/env python3
"""
Apply slack_manifest.yml to the existing Slack app via the Manifest API.

Slack's apps.manifest.update requires a "configuration token" (not a bot or
app-level token). We obtain one by rotating the refresh token via
tooling.tokens.rotate, then use the resulting access token for the update.
The rotated refresh token is written back to .env automatically.

Setup (one-time):
  1. Visit https://api.slack.com/tools/config-tokens
  2. Select your workspace and generate a refresh token
  3. Add it to .env:  SLACK_CONFIG_REFRESH_TOKEN=xoxe-1-...

Usage:
  python scripts/apply_manifest.py
"""

import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

MANIFEST_PATH = Path(__file__).parent.parent / "slack_manifest.yml"
ENV_PATH = Path(__file__).parent.parent / ".env"

ROTATE_URL = "https://slack.com/api/tooling.tokens.rotate"
UPDATE_URL = "https://slack.com/api/apps.manifest.update"


def rotate_token(refresh_token: str) -> tuple[str, str]:
    """Exchange a refresh token for a fresh (access_token, new_refresh_token)."""
    resp = requests.post(ROTATE_URL, data={"refresh_token": refresh_token})
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        sys.exit(f"tooling.tokens.rotate failed: {data.get('error')}\n{data}")
    return data["token"], data["refresh_token"]


def save_refresh_token(new_token: str) -> None:
    """Write the rotated refresh token back to .env."""
    if not ENV_PATH.exists():
        return
    content = ENV_PATH.read_text()
    if "SLACK_CONFIG_REFRESH_TOKEN" in content:
        content = re.sub(
            r"^SLACK_CONFIG_REFRESH_TOKEN=.*$",
            f"SLACK_CONFIG_REFRESH_TOKEN={new_token}",
            content,
            flags=re.MULTILINE,
        )
    else:
        content += f"\nSLACK_CONFIG_REFRESH_TOKEN={new_token}\n"
    ENV_PATH.write_text(content)


def main() -> None:
    app_id = os.getenv("SLACK_APP_ID")
    if not app_id:
        sys.exit("SLACK_APP_ID is required")

    refresh_token = os.getenv("SLACK_CONFIG_REFRESH_TOKEN")
    if not refresh_token:
        sys.exit(
            "SLACK_CONFIG_REFRESH_TOKEN is required.\n"
            "Get one at: https://api.slack.com/tools/config-tokens"
        )

    access_token, new_refresh_token = rotate_token(refresh_token)
    save_refresh_token(new_refresh_token)

    manifest_yaml = MANIFEST_PATH.read_text()
    resp = requests.post(
        UPDATE_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"app_id": app_id, "manifest": manifest_yaml},
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("ok"):
        sys.exit(f"Manifest update failed: {data.get('error')}\n{data}")

    print(f"✓ Manifest applied to {app_id}")


if __name__ == "__main__":
    main()
