from functools import wraps

from .terraform import Terraform
from .utils import (is_using_existing,
                    get_terraform_source)


def with_terraform(func):
    """Read the terraform source, dump it in the working directory (where
        terraform executable is called), and store the state for later dumping.

    This wrapper is the entry point for the following process:
    1. Call the get_terraform_source, which is the Terraform Template
        "main.tf", for example. This can be stored in runtime properties or
        gathered from a URL or as a resource in a blueprint.
    2. Check for the terraform source in runtime properties or in node
        properties via "get_terraform_source_material".
    3. Update the retrieved source in the runtime properties using
        update_terraform_source_material.
    4. Dump the terraform source in the node template working directory
        in the deployment directory using _yield_terraform_source.
    5. This location is passed to Terraform.from_ctx as the terraform_source
        variable below.
    6. Create the Terraform interface "tf", which then gets executed as
        tf.apply() or tf.destroy(), etc.

    :param func:
    :return:
    """

    @wraps(func)
    def f(*args, **kwargs):
        ctx = kwargs['ctx']
        with get_terraform_source() as terraform_source:
            tf = Terraform.from_ctx(ctx, terraform_source)
            kwargs['tf'] = tf
            return func(*args, **kwargs)
    return f


def skip_if_existing(func):
    @wraps(func)
    def f(*args, **kwargs):
        if not is_using_existing():
            return func(*args, **kwargs)
    return f
