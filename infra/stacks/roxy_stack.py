from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_dynamodb as dynamodb,
    aws_ecr_assets as ecr_assets,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_iam as iam,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class RoxyStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- DynamoDB ---
        table = dynamodb.Table(
            self,
            "ChannelsTable",
            table_name="roxy-channels",
            partition_key=dynamodb.Attribute(
                name="channel_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # --- Secrets (Slack tokens) ---
        slack_secret = secretsmanager.Secret(
            self,
            "SlackTokens",
            secret_name="roxy/slack-tokens",
            description="SLACK_BOT_TOKEN and SLACK_APP_TOKEN for roxy",
        )

        # --- ECS Cluster ---
        cluster = ecs.Cluster(self, "RoxyCluster", cluster_name="roxy")

        # --- Task definition ---
        task_role = iam.Role(
            self,
            "RoxyTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        table.grant_read_write_data(task_role)
        slack_secret.grant_read(task_role)

        task_def = ecs.FargateTaskDefinition(
            self,
            "RoxyTaskDef",
            cpu=256,
            memory_limit_mib=512,
            task_role=task_role,
        )

        image = ecs.ContainerImage.from_asset(
            "..",  # repo root — Dockerfile is there
            platform=ecr_assets.Platform.LINUX_AMD64,
        )

        log_group = logs.LogGroup(
            self,
            "RoxyLogs",
            log_group_name="/ecs/roxy",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        task_def.add_container(
            "roxy",
            image=image,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="roxy",
                log_group=log_group,
            ),
            environment={
                "AWS_REGION": self.region,
                "ROXY_DYNAMODB_TABLE": table.table_name,
                "INACTIVITY_PRUNE_DAYS": "30",
                "LOG_LEVEL": "INFO",
            },
            secrets={
                "SLACK_BOT_TOKEN": ecs.Secret.from_secrets_manager(
                    slack_secret, field="SLACK_BOT_TOKEN"
                ),
                "SLACK_APP_TOKEN": ecs.Secret.from_secrets_manager(
                    slack_secret, field="SLACK_APP_TOKEN"
                ),
            },
        )

        # --- Fargate service (no load balancer — Socket Mode is outbound only) ---
        ecs.FargateService(
            self,
            "RoxyService",
            cluster=cluster,
            task_definition=task_def,
            desired_count=1,
            service_name="roxy",
            assign_public_ip=True,  # needed for outbound unless using NAT gateway
        )
