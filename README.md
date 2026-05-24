# roxy

A Slack bot for dynamic channel management, built for the [ReadWriteExecute](https://readwriteexecute.com) community. Spawns focused sub-channels on demand, tracks activity, and prunes stale ones automatically.

## Features

- **`/spawn <name>`** — create a sub-channel under the current channel (e.g. `/spawn f1` in `#sports`)
- **`/monitor`** — register an existing channel for activity tracking
- **`/prune`** — manually archive stale sub-channels
- **Auto-prune** — daily background job archives sub-channels inactive for 30 days (configurable)
- **LLM agent** — coming soon, powered by LangGraph

## Stack

- Python + [Slack Bolt](https://slack.dev/bolt-python/) (Socket Mode)
- AWS ECS Fargate + DynamoDB
- Infrastructure as code via AWS CDK (Python)

## Setup

### 1. Create the Slack app

Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From a manifest** → paste the contents of [`slack_manifest.yml`](slack_manifest.yml).

After creating:
- **OAuth & Permissions** → install to workspace → copy the **Bot Token** (`xoxb-...`)
- **Basic Information** → App-Level Tokens → generate with `connections:write` + `app_configurations:write` → copy the **App Token** (`xapp-...`)
- Note the **App ID** from Basic Information

### 2. Configure environment

```bash
cp .env.example .env
# fill in SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_APP_ID
```

### 3. Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m app.main
```

### 4. Deploy to AWS

Requires AWS credentials and the [CDK CLI](https://docs.aws.amazon.com/cdk/v2/guide/cli.html).

```bash
pip install -e ".[infra]"

# one-time bootstrap per account/region
cd infra && cdk bootstrap

# deploy
cdk deploy
```

After deploying, store your Slack tokens in the created Secrets Manager secret (`roxy/slack-tokens`):

```bash
aws secretsmanager put-secret-value \
  --secret-id roxy/slack-tokens \
  --secret-string '{"SLACK_BOT_TOKEN":"xoxb-...","SLACK_APP_TOKEN":"xapp-..."}'
```

### 5. Update the Slack manifest

After adding slash commands, apply the updated manifest via the Slack UI:
**api.slack.com/apps** → your app → **App Manifest** → paste updated `slack_manifest.yml`.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SLACK_BOT_TOKEN` | — | Bot user OAuth token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | — | App-level token (`xapp-...`) |
| `AWS_REGION` | `us-east-1` | AWS region |
| `ROXY_DYNAMODB_TABLE` | `roxy-channels` | DynamoDB table name |
| `INACTIVITY_PRUNE_DAYS` | `30` | Days of inactivity before a sub-channel is archived |
| `LOG_LEVEL` | `INFO` | Log level |

## Architecture

```
Slack (Socket Mode WebSocket)
        │
        ▼
   ECS Fargate (roxy)
   ├── Bolt event handlers  ← message events → touch activity timestamp
   ├── Slash commands       ← /spawn, /monitor, /prune
   ├── Channel manager      ← create, register, archive via Slack API
   ├── Prune scheduler      ← daily background thread
   └── DynamoDB registry    ← channel state & activity tracking
```

## License

MIT
