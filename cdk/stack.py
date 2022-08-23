from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict

import boto3
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
)
from constructs import Construct

from .config import Deployment


if TYPE_CHECKING:
    from boto3_type_annotations.rds import Client


class RdsBastionHost(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: Deployment,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        db_details = self.lookup_db(config.db_instance_identifier)

        sg = ec2.SecurityGroup.from_lookup_by_id(
            self,
            "rds_security_group",
            security_group_id=db_details.vpc_security_group_id,
        )

        vpc = ec2.Vpc.from_lookup(self, "vpc", vpc_id=db_details.vpc_id)
        bastion_host = ec2.BastionHostLinux(self, "bastion-host", vpc=vpc)

        bastion_host.instance.connections.allow_to(
            sg,
            port_range=ec2.Port.tcp(db_details.port),
            description="Allow connection from bastion host",
        )

        for ipv4 in config.ipv4_allowlist:
            bastion_host.allow_ssh_access_from(ec2.Peer.ipv4(ipv4))

    @staticmethod
    def lookup_db(instance_name: str) -> "DbDetails":
        client: Client = boto3.client("rds")
        response = client.describe_db_instances(DBInstanceIdentifier=instance_name)
        if num_instances := len(response["DBInstances"]) != 1:
            raise Exception(
                f"Expected 1 DB instance returned, received {num_instances}"
            )
        db = response["DBInstances"][0]
        return DbDetails(
            vpc_id=db["DBSubnetGroup"]["VpcId"],
            vpc_security_group_id=db["VpcSecurityGroups"][0]["VpcSecurityGroupId"],
            port=db["Endpoint"]["Port"],
        )


@dataclass
class DbDetails:
    vpc_id: str
    vpc_security_group_id: str
    port: int