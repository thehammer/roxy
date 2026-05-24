# roxy — Claude Code context

## Project

Slack bot for dynamic channel management. Python + Slack Bolt (Socket Mode) + DynamoDB + ECS Fargate + AWS CDK.

## Structure

```
app/
  main.py              # entry point — wires Bolt, registry, manager, handlers
  config.py            # Config dataclass, all settings from env
  channels/
    registry.py        # ChannelRegistry — DynamoDB CRUD for ChannelRecord
    manager.py         # ChannelManager — spawn/register/prune orchestration
  handlers/
    events.py          # message events → registry.touch()
    commands.py        # /spawn, /monitor, /prune slash commands
infra/
  app.py               # CDK app entry point
  stacks/roxy_stack.py # all AWS resources
tests/
  conftest.py          # shared registry fixture (moto mock)
  test_registry.py
  test_manager.py
```

## Key conventions

- Slash commands live in `app/handlers/commands.py`, registered via `register(app, manager)`
- Channel state lives in DynamoDB as `ChannelRecord` — always go through `ChannelRegistry`
- `is_sub_channel=True` + `status=active` is what the pruner targets
- `touch()` only updates existing records (has a `ConditionExpression`) — do not remove this or it will create phantom records on join events

## Running

```bash
pip install -e ".[dev]"
cp .env.example .env   # fill in SLACK_BOT_TOKEN and SLACK_APP_TOKEN
python -m app.main
```

## Testing

```bash
pytest tests/ -v   # no AWS creds needed, uses moto
```

## Deploying

```bash
cd infra && cdk deploy --require-approval never
```

Merging to `main` triggers an automatic deploy via GitHub Actions.

## Slack manifest

`slack_manifest.yml` is the source of truth for the Slack app config. After changing it, apply via the Slack UI: api.slack.com/apps → App Manifest.
