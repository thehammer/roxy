import os
from dataclasses import dataclass


@dataclass
class Config:
    slack_bot_token: str
    slack_app_token: str  # xapp-... token for Socket Mode

    aws_region: str
    dynamodb_table: str
    reactors_table: str

    # How long a sub-channel can be idle before pruning eligibility (days)
    inactivity_prune_days: int

    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            slack_bot_token=_require("SLACK_BOT_TOKEN"),
            slack_app_token=_require("SLACK_APP_TOKEN"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            dynamodb_table=os.getenv("ROXY_DYNAMODB_TABLE", "roxy-channels"),
            reactors_table=os.getenv("ROXY_REACTORS_TABLE", "roxy-reactors"),
            inactivity_prune_days=int(os.getenv("INACTIVITY_PRUNE_DAYS", "30")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Required environment variable {key!r} is not set")
    return val
