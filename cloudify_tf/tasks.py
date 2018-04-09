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

from cloudify.exceptions import NonRecoverableError
from terraform import Terraform
from utils import (
    delete_runtime_properties,
    update_runtime_properties,
    get_terraform_source)

ERROR_MESSAGE = 'Failed see log.'


def init(executable_path, resource_config, **_):
    """
    Execute `terraform init`.
    """

    tf = Terraform(
        executable_path,
        get_terraform_source(resource_config),
        variables=resource_config.get('variables'),
        environment_variables=resource_config.get('environment_variables'))

    if not tf.init():
        raise NonRecoverableError(ERROR_MESSAGE)
    if not tf.plan():
        raise NonRecoverableError(ERROR_MESSAGE)


def apply(executable_path, resource_config, **_):
    """
    Execute `terraform apply`.
    """

    tf = Terraform(
        executable_path,
        get_terraform_source(resource_config),
        variables=resource_config.get('variables'),
        environment_variables=resource_config.get('environment_variables'))

    tf_apply = tf.apply()
    tf_state = tf.state_pull()

    resources = {}
    for module in tf_state['modules']:
        resources.update(module.get('resources'))
    update_runtime_properties('resources', resources)

    if not tf_apply:
        raise NonRecoverableError(ERROR_MESSAGE)


def destroy(executable_path, resource_config, **_):
    """
    Execute `terraform destroy`.
    """

    tf = Terraform(
        executable_path,
        get_terraform_source(resource_config),
        variables=resource_config.get('variables'),
        environment_variables=resource_config.get('environment_variables'))
    if not tf.destroy():
        raise NonRecoverableError(ERROR_MESSAGE)
    delete_runtime_properties()
