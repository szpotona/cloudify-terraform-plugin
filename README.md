
# Cloudify Terraform Plugin

Package a Terraform Project as a Cloudify Node Type


## Pre-install

Install terraform binary on your Cloudify Manager at /usr/bin/terraform, for example these steps

```shell
    1  sudo yum install -y wget unzip
    2  wget https://releases.hashicorp.com/terraform/0.11.7/terraform_0.11.7_linux_amd64.zip
    3  unzip terraform_0.11.7_linux_amd64.zip
    4  sudo cp terraform /usr/bin/
    5  sudo chmod 775 /usr/bin/terraform 
    6  sudo chown root:root /usr/bin/terraform 
```

Compress the blueprints/resources/aws-two-tier directory in a zip in the blueprints/resources directory.


## Installation

There are two example blueprints.

  1. A simple "wordpress and terraform" blueprint, `wordpress-blueprint.yaml`.
  1. A simple "terraform only" blueprint, `blueprint.yaml`.

```
blueprint=wordpress-blueprint.yaml
deploymentid=terraform
cfy blueprints upload \
    blueprints/$blueprint \
    -b $deploymentid;
cfy deployments create \
    -b $deploymentid --skip-plugins-validation;
cfy executions start install -vv \
    -d $deploymentid;
cfy node-instances list -d $deploymentid
```


## Refresh a state and store it

If a state has changed and you want to store it, you can run like this:

```shell
cfy executions start execute_operation -d $deploymentid -p operation='cloudify.interfaces.lifecycle.configure' -p node_instance_ids='["aws_two_tier_example_XXXXXX"]'
```


## Update Deployment to Expose Nodes (Manager Only)

If you selected the simple blueprint, you can expose the aws_instance.web node using the following workflow:

```shell
cfy executions start export_resource -vv -d $deploymentid -p resource_name=aws_instance.web -p node_instance_id=aws_two_tier_example_XXXXX
```

If you want to expose and install an agent, you can do so like this:

```shell
cfy executions start export_resource -vv -d $deploymentid --allow-custom-parameters -p resource_name=aws_instance.web -p install_method=remote -p user=ubuntu -p key='{ "get_secret": "agent_key_private" }' -p network=external -p use_public_ip=1 -p node_instance_id=aws_two_tier_example_XXXXX
```



## Uninstall 

```
cfy uninstall $deploymentid --allow-custom-parameters -p ignore_failure=true
```


## Development and Testing on a Manager

```
flake8 cloudify_tf/
git add .; git commit -m 'changes'; git log | head -n 1 | awk '{print $2}'
# Add commit to plugin.yaml
git add .; git commit -m 'plugin.yaml'; git push; git log | head -n 1 | awk '{print $2}'
# Add commit to blueprint.yaml
```

## Todo

  * Create a Terraform [Backend Service using HTTP Node Type](https://www.terraform.io/docs/backends/types/http.html).
    * Package in the plugin w/ a node type.
    * The service should run as a daemon.
    * Exposing Terraform resources via Terraform outputs should trigger `execute_resource` workflow on those resources.
    * This should enable a user to interact with Terraform and Cloudify from Terraform CLI.
  * Support more packaging methods for `cloudify.nodes.terraform.Module`.
    * Today we use zip and require the user to pre-package this. It's not good.
  * Support Multiple Modules.
