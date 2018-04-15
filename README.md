
# Cloudify Terraform Plugin

Package a Terraform Project as a Cloudify Node Type


## Pre-install

Compress the /blueprints/resources/aws-two-tier directory in a zip in the same folder:


## Manager Installation

```
deploymentid=tf
cfy blueprints upload \
    earthmant/terraform-integration/blueprint.yaml \
    -b deploymentid;
cfy deployments create \
    -b deploymentid --skip-plugins-validation;
cfy executions start install -vv \
    -d deploymentid;
cfy node-instances list -d deploymentid
```


## Update Deployment to Expose Nodes (Manager Only)

```
cfy executions start export_resource -vv -d deploymentid -p resource_name=aws_instance.web -p node_instance_id=aws_two_tier_example_XXXXX
```


## Local Installation

```shell
cfy install -vv \
    -i terraform_path=/PATH/TO/terraform \
    -i AWS_ACCESS_KEY_ID=... \
    -i AWS_SECRET_ACCESS_KEY=... \
    -i public_key_path=/PATH/TO/.ssh/id_rsa.pub \
    terraform-integration/blueprint.yaml;
cfy node-inst -b terraform-integration;
```


## Uninstall 

```
cfy uninstall deploymentid --allow-custom-parameters -p ignore_failure=true
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

  * Write a special "install_and_expose" workflow for handling applications as part of the blueprint from day 0.
  * Create a Terraform [Backend Service using HTTP Node Type](https://www.terraform.io/docs/backends/types/http.html).
    * Package in the plugin w/ a node type.
    * The service should run as a daemon.
    * Exposing Terraform resources via Terraform outputs should trigger `execute_resource` workflow on those resources.
    * This should enable a user to interact with Terraform and Cloudify from Terraform CLI.
  * Support more packaging methods for `cloudify.nodes.terraform.Module`.
    * Today we use zip and require the user to pre-package this. It's not good.
  * Support Multiple Modules.
