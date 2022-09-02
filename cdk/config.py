from getpass import getuser
from ipaddress import IPv4Interface
from typing import List, Optional

import aws_cdk
from pydantic import BaseSettings, Field, constr, DirectoryPath, FilePath


class Deployment(BaseSettings):
    project: Optional[constr(regex=r"^[a-z0-9_\-]+")]
    client: Optional[str]
    owner: str = Field(
        description=" ".join(
            [
                "Name of primary contact for Cloudformation Stack.",
                "Used to tag generated resources",
                "Defaults to current username.",
            ]
        ),
        default_factory=getuser,
    )
    stage: str = Field(
        description=" ".join(
            [
                "Stage of deployment (e.g. 'dev', 'prod').",
                "Used as suffix for stack name.",
                "Defaults to current username.",
            ]
        ),
        default_factory=getuser,
    )

    aws_account: str = Field(
        description="AWS account used for deployment",
        env="CDK_DEFAULT_ACCOUNT",
    )
    aws_region: str = Field(
        default="us-west-2",
        description="AWS region used for deployment",
        env="CDK_DEFAULT_REGION",
    )

    db_instance_identifier: str = Field(
        description="The instance identifier of database to which we want to connect."
    )

    ipv4_allowlist: List[IPv4Interface] = Field(
        default_factory=lambda: [],
        description="IPv4 CIDRs that are allowed SSH access to bastion host.",
    )

    userdata_file: FilePath = Field(default="./userdata.yaml")

    ssh_port: int = 22

    @property
    def stack_name(self) -> str:
        return f"{self.project}-{self.stage}-db-bastion"

    @property
    def env(self) -> aws_cdk.Environment:
        return aws_cdk.Environment(
            account=self.aws_account,
            region=self.aws_region,
        )
