from dataclasses import dataclass
from typing import TYPE_CHECKING

import boto3
from aws_cdk import (
    CfnOutput,
    Stack,
    aws_iam as iam,
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

        # Lookup RDS instance details by its identifier
        db_details = self.lookup_db(config.db_instance_identifier)

        with open(config.userdata_file, "r") as f:
            user_data = f.read()

        instance = self.build_instance(vpc_id=db_details.vpc_id, user_data=user_data)

        # Assign elastic IP
        ec2.CfnEIP(self, "Ip", instance_id=instance.instance_id)

        # Allow Bastion Host to connect to DB
        self.allow_db_connection(
            instance=instance,
            security_group_id=db_details.vpc_security_group_id,
            port=db_details.port,
        )

        # Allow IP access to Bastion Host
        for ipv4 in config.ipv4_allowlist:
            instance.connections.allow_from(
                ec2.Peer.ipv4(str(ipv4)),
                ec2.Port.tcp(config.ssh_port),
                "SSH access",
            )

        # Integrate with SSM
        instance.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ssmmessages:*",
                    "ssm:UpdateInstanceInformation",
                    "ec2messages:*",
                ],
                resources=["*"],
            )
        )

    def build_instance(
        self,
        vpc_id: str,
        user_data: str,
    ) -> ec2.IInstance:
        instance = ec2.Instance(
            self,
            f"bastion-host",
            vpc=ec2.Vpc.from_lookup(self, "vpc", vpc_id=vpc_id),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            instance_name=Stack.of(self).stack_name,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.NANO
            ),
            machine_image=ec2.MachineImage.latest_amazon_linux(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),
            user_data=ec2.UserData.custom(user_data),
            user_data_causes_replacement=True,
        )
        CfnOutput(
            self,
            "instance-id-output",
            value=instance.instance_id,
            export_name="bastion-instance-id",
        )
        CfnOutput(
            self,
            "instance-public-ip-output",
            value=instance.instance_public_ip,
            export_name="bastion-instance-public-ip",
        )
        CfnOutput(
            self,
            "instance-public-dns-name-output",
            value=instance.instance_public_dns_name,
            export_name="bastion-public-dns-name",
        )
        return instance

    def allow_db_connection(
        self,
        security_group_id: str,
        instance: ec2.IInstance,
        port: int,
    ) -> ec2.ISecurityGroup:
        sg = ec2.SecurityGroup.from_lookup_by_id(
            self,
            "rds_security_group",
            security_group_id=security_group_id,
        )
        instance.connections.allow_to(
            sg,
            port_range=ec2.Port.tcp(port),
            description="Allow connection from bastion host",
        )
        return sg

    def lookup_db(self, instance_name: str) -> "DbDetails":
        client: "Client" = boto3.client("rds")
        response = client.describe_db_instances(DBInstanceIdentifier=instance_name)

        if num_instances := len(response["DBInstances"]) != 1:
            raise Exception(
                f"Expected 1 DB instance returned, received {num_instances}"
            )

        db = response["DBInstances"][0]
        details = DbDetails(
            vpc_id=db["DBSubnetGroup"]["VpcId"],
            vpc_security_group_id=db["VpcSecurityGroups"][0]["VpcSecurityGroupId"],
            port=db["Endpoint"]["Port"],
        )

        CfnOutput(
            self,
            "db-hostname-output",
            value=db["Endpoint"]["Address"],
            export_name="db-host",
        )
        return details


@dataclass
class DbDetails:
    vpc_id: str
    vpc_security_group_id: str
    port: int
