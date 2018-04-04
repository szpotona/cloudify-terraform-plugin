########
# Copyright (c) 2018 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import zipfile

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from terraform import Terraform
from utils import update_runtime_properties, unzip_archive

TERRAFORM_PATH = '/usr/bin/terraform'


def configure(resource_config, **_):
    """
    Get the TF File and verify that everything is ready.
    """

    ctx.logger.info('resource_config: {0}'.format(resource_config))
    ctx.logger.info('_: {0}'.format(_))

    terraform_source_zip = ctx.download_resource(resource_config.get('source'))
    terraform_source = unzip_archive(terraform_source_zip)
    update_runtime_properties('terraform_source', terraform_source)

    tf = Terraform(
        _.get('terraform_path', TERRAFORM_PATH),
        terraform_source,
        variables=resource_config.get('variables') or None,
        environment_variables=resource_config.get('environment_variables') or None
    )

    init_output = tf.init()
    ctx.logger.info('terraform init output: {0}'.format(init_output))
    plan_output = tf.plan()
    ctx.logger.info('terraform plan output: {0}'.format(plan_output))
