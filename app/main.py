import structlog
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from app.channels.manager import ChannelManager
from app.channels.registry import ChannelRegistry
from app.config import Config
from app.handlers import commands, events

load_dotenv()

log = structlog.get_logger()


def build_app(config: Config) -> tuple[App, SocketModeHandler]:
    app = App(token=config.slack_bot_token)

    registry = ChannelRegistry(
        table_name=config.dynamodb_table,
        region=config.aws_region,
    )
    manager = ChannelManager(registry=registry, slack_client=app.client)

    events.register(app, registry)
    commands.register(app, manager)

    handler = SocketModeHandler(app, config.slack_app_token)
    return app, handler


def main():
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(20))
    config = Config.from_env()
    _, handler = build_app(config)
    log.info("roxy starting", table=config.dynamodb_table, region=config.aws_region)
    handler.start()


if __name__ == "__main__":
    main()
