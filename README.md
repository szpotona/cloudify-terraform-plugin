
Compress the /blueprints/resources/eip directory in a zip in the same folder and execute:

```shell
cfy install \
    -vv \
    --task-retries=30 \
    --task-retry-interval=5 \
    -i terraform_path=/Path/To/terraform \
    -i AWS_ACCESS_KEY_ID=XXXXXXXXXX \
    -i AWS_SECRET_ACCESS_KEY=XXXXXXXXXXX \
    terraform-integration/blueprint.yaml
```

Todo:

  ** Consider changing the delivery method of the terraform templates. These should not need to be zips. Unfortunately, today that is all that download resource accepts.
  ** Support `terraform apply`
  ** Create a Method of Reading Different Types from the Plan. (Maybe use this: https://github.com/palantir/tfjson).
  ** Store Compute types in a special object.
  ** Figure out some way to export compute types, for example running a post-install deployment update to add new nodes representing VMs.
