# RDS Bastion Host

CDK Configuration for simplifying the generation of a Bastion Host (aka JumpBox) used to connect to a non-public (ie placed in a private subnet) RDS instance.

## How it works

At time of deployment, this codebase will look up the RDS Instance by the identifier provided as an environment variable `DB_INSTANCE_IDENTIFIER` and will deploy a bastion host along with updating thee RDS Instance's security to permit incomming traffic from the bastion host. The bastion host will be placed in a public subnet and be assigned an Elastic IP address. At startup the user-provided `userdata.yaml` [cloud-config](https://cloudinit.readthedocs.io/en/latest/) file will be run, creating system user in order to allow SSH access.

Further information about this pattern of connection can be found here: [Deploy bastion hosts into private subnets with AWS CDK](https://aws.amazon.com/blogs/infrastructure-and-automation/deploy-bastion-hosts-into-private-subnets-with-aws-cdk/)

## Usage

### Deployment

1.  Copy `.env.example` to `.env`, populate as deemed necessary.

    - You will likely want to add your external IP address to the `ipv4_allowlist`. You can obtain this value via the following:

      ```
      curl api.ipify.org
      ```

1.  Copy `.userdata.yaml.example` to `.userdata.yaml`, populate as deemed necessary.
1.  Install system requirements: `poetry install`
1.  Deploy: `poetry run cdk deploy`

Make note of the bastion host ID (e.g. `i-0a1234b567c890`) returned in the stack's output. You will make use of this value when connecting via the AWS Systems Manager Session Manager.

## Tips & Tricks

### Connecting to RDS Instance via SSM

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

### Setting up an SSH tunnel

In your `~/.ssh/config` file, add an entry like:

```
Host db-tunnel
  Hostname {the-bastion-host-address}
  LocalForward 54322 {the-db-hostname}:5432
```

Then a tunnel can be opened via:

```
ssh -N db-tunnel
```

And a connection to the DB can be made via:

```
psql -h 127.0.0.1 -p 5433 -U {username} -d {database}
```

### Handling `REMOTE HOST IDENTIFICATION HAS CHANGED!` error

If you've redeployed a bastion host that you've previously connected to, you may see an error like:

```
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!
Someone could be eavesdropping on you right now (man-in-the-middle attack)!
It is also possible that a host key has just been changed.
The fingerprint for the ECDSA key sent by the remote host is
SHA256:mPnxAOXTpb06PFgI1Qc8TMQ2e9b7goU8y2NdS5hzIr8.
Please contact your system administrator.
Add correct host key in /Users/username/.ssh/known_hosts to get rid of this message.
Offending ECDSA key in /Users/username/.ssh/known_hosts:28
ECDSA host key for ec2-12-34-56-789.us-west-2.compute.amazonaws.com has changed and you have requested strict checking.
Host key verification failed.
```

This is due to the server's fingerprint changing. We can scrub the fingerprint from our system with a command like:

```
ssh-keygen -R 12.34.56.789
```
