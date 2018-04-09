
Compress the /blueprints/resources/eip directory in a zip in the same folder and execute:

```shell
cfy install -vv \
    -i terraform_path=/PATH/TO/terraform \
    -i AWS_ACCESS_KEY_ID=... \
    -i AWS_SECRET_ACCESS_KEY=... \
    -i public_key_path=/PATH/TO/.ssh/id_rsa.pub \
    terraform-integration/blueprint.yaml;
cfy node-inst -b terraform-integration;
```

Todo:

  * Consider changing the delivery method of the terraform templates. These should not need to be zips. Unfortunately, today that is all that download resource accepts.
  * Store Compute types in a special object.
  * Figure out some way to export compute types, for example running a post-install deployment update to add new nodes representing VMs.
  * Create a Terraform Backend Service. Publish it as a plugin node type that can be included in a blueprint.
  * Enable exporting a resource from Terraform CLI to a deployment.

Plugin Changes for testing:
```
flake8 cloudify_tf/
git add .; git commit -m 'changes'; git log | head -n 1 | awk '{print $2}'
# Add commit to plugin.yaml
git add .; git commit -m 'plugin.yaml'; git push; git log | head -n 1 | awk '{print $2}'
# Add commit to blueprint.yaml
```
Manager Testing:

Execution:
```
testid=33
cfy blueprints upload \
    earthmant/terraform-integration/blueprint.yaml \
    -b test-$testid;
cfy deployments create \
    -b test-$testid --skip-plugins-validation;
cfy executions start install -vv \
    -d test-$testid;
cfy node-instances list -d test-$testid
cfy executions start export_resource -vv -d test-$testid -p resource_name=aws_instance.web -p node_instance_id=aws_two_tier_example_XXXXX
cfy uninstall test-$testid --allow-custom-parameters -p ignore_failure=true
```

