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

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
import subprocess

TERRAFORM_PATH = '/usr/bin/terraform'


def configure(resource_config, **_):
    """
    Get the TF File and verify that everything is ready.
    """

    # Check that Terraform executable is available.
    terraform_path = _.get('terraform_path', TERRAFORM_PATH)
    terraform_command_output = subprocess.call([terraform_path])
    if int(terraform_command_output) != 127:
        raise NonRecoverableError(
            '{0} binary does not exist or is not executable.'.format(
                terraform_path))

    # TODO: Download the Blueprint Resource
    terraform_root_module = resource_config.get('source')
    ctx.logger.info('Root Module: {0}'.format(terraform_root_module))

    # TODO: Store the Blueprint Resource in a Temp folder (Use StringIO later).
