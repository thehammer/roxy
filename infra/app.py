#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.roxy_stack import RoxyStack

app = cdk.App()

RoxyStack(
    app,
    "RoxyStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
)

app.synth()
