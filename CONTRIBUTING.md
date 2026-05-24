# Contributing to roxy

## Development setup

```bash
git clone git@github.com:thehammer/roxy.git
cd roxy
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # fill in your Slack tokens
```

## Running tests

```bash
pytest tests/ -v
```

Tests use [moto](https://docs.getmoto.org/) to mock DynamoDB — no AWS credentials needed.

## Linting

```bash
ruff check .
ruff check --fix .  # auto-fix
```

## Running locally

```bash
python -m app.main
```

Requires valid `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` in `.env`. See the [README](README.md) for Slack app setup.

## Pull requests

- Open a PR against `main`
- CI runs lint + tests automatically — both must pass
- Keep changes focused; one feature or fix per PR
- Add tests for new behaviour in `app/channels/`

## Deploying

Deploys to AWS ECS Fargate happen automatically on merge to `main` via GitHub Actions. No manual `cdk deploy` needed after the initial setup.
