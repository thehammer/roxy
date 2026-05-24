import boto3
import pytest
from moto import mock_aws

from app.channels.registry import ChannelRegistry

TABLE_NAME = "test-channels"
REGION = "us-east-1"


@pytest.fixture
def mock_aws_env(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)


@pytest.fixture
def registry(mock_aws_env):
    with mock_aws():
        boto3.resource("dynamodb", region_name=REGION).create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "channel_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "channel_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield ChannelRegistry(table_name=TABLE_NAME, region=REGION)
