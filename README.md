# RDS Bastion Host

CDK Configuration for simplifying the generation of a Bastion Host (aka JumpBox) used to connect to a non-public (ie placed in a private subnet) RDS instance.

## How it works

At time of deployment, this codebase will look up the RDS Instance by the identifier provided as an environment variable `DB_INSTANCE_IDENTIFIER` and will deploy a bastion host along with updating thee RDS Instance's security to permit incomming traffic from the bastion host. The bastion host will be placed in a _private subnet_, thereby only permitting connections via the [AWS Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html).

Further information about this pattern of connection can be found here: [Deploy bastion hosts into private subnets with AWS CDK](https://aws.amazon.com/blogs/infrastructure-and-automation/deploy-bastion-hosts-into-private-subnets-with-aws-cdk/)

## Usage

### Deployment

1.  Copy `.env.example` to `.env`, populate as deemed necessary.

    - You will likely want to add your external IP address to the `ipv4_allowlist`. You can obtain this value via the following:

      ```py
      python3 -c "import urllib.request; print(urllib.request.urlopen('https://api.ipify.org').read().decode('utf8'))"
      ```

1.  Install system requirements: `poetry install`
1.  Deploy: `poetry run cdk deploy`

Make note of the bastion host ID (e.g. `i-0a1234b567c890`) returned in the stack's output. You will make use of this value when connecting via the AWS Systems Manager Session Manager.

### Connect to RDS Instance via tunneling through Bastion Host

```sh
aws ssm start-session --target $INSTANCE_ID \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters '{
        "host": [
            "example-db.c5abcdefghij.us-west-2.rds.amazonaws.com"
        ],
        "portNumber": [
            "5432"
        ],
        "localPortNumber": [
            "9999"
        ]
    }' \
    --profile $AWS_PROFILE
```

```sh
psql -h localhost -p 9999 # continue adding username (-U) and db (-d) here...
```

Connect directly to Bastion Host:

```sh
aws ssm start-session --target $INSTANCE_ID --profile $AWS_PROFILE
```
