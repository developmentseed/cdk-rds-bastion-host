#!/usr/bin/env python3
from aws_cdk import App

from cdk import config, stack


deployment = config.Deployment(_env_file=".env")

app = App()

stack.RdsBastionHost(
    app,
    construct_id=deployment.stack_name,
    config=deployment,
    tags={
        k: v
        for k, v in {
            "Project": deployment.project,
            "Owner": deployment.owner,
            "Client": deployment.client,
            "Stack": deployment.stage,
        }.items()
        if v
    },
    env=deployment.env,
)

app.synth()
