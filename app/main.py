import threading
import time

import structlog
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.channels.manager import ChannelManager
from app.channels.registry import ChannelRegistry
from app.config import Config
from app.handlers import commands, events
from app.reactors.engine import ReactorEngine
from app.reactors.registry import ReactorRegistry

load_dotenv()

log = structlog.get_logger()

_PRUNE_INTERVAL_SECONDS = 24 * 60 * 60  # daily


def _start_prune_scheduler(manager: ChannelManager) -> None:
    def loop():
        while True:
            time.sleep(_PRUNE_INTERVAL_SECONDS)
            try:
                archived = manager.prune_stale_channels()
                if archived:
                    log.info("auto-pruned stale sub-channels", count=len(archived), channels=archived)
                else:
                    log.debug("auto-prune ran, no stale channels found")
            except Exception as e:
                log.error("auto-prune failed", error=str(e))

    t = threading.Thread(target=loop, daemon=True, name="prune-scheduler")
    t.start()


def build_app(config: Config) -> tuple[App, SocketModeHandler]:
    app = App(token=config.slack_bot_token)

    registry = ChannelRegistry(
        table_name=config.dynamodb_table,
        region=config.aws_region,
    )
    manager = ChannelManager(
        registry=registry,
        slack_client=app.client,
        inactivity_days=config.inactivity_prune_days,
    )
    reactor_registry = ReactorRegistry(
        table_name=config.reactors_table,
        region=config.aws_region,
    )
    engine = ReactorEngine(registry=reactor_registry)

    events.register(app, registry, engine)
    commands.register(app, manager)
    _start_prune_scheduler(manager)

    handler = SocketModeHandler(app, config.slack_app_token)
    return app, handler


def main():
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(20))
    config = Config.from_env()
    _, handler = build_app(config)
    log.info(
        "roxy starting",
        table=config.dynamodb_table,
        reactors_table=config.reactors_table,
        region=config.aws_region,
        prune_days=config.inactivity_prune_days,
    )
    handler.start()


if __name__ == "__main__":
    main()
