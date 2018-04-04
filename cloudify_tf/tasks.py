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
from cloudify.exception import NonRecoverableError
import subprocess


TERRAFORM_COMMAND = 'terraform'

def configure(**kwargs):
    """
    Get the TF File and verify that everything is ready.
    """

    # Check that Terraform executable is available.
    if execute_command(TERRAFORM_COMMAND) is not False:
    	raise NonRecoverableError('Terraform binary is not in $PATH.')

    # TODO: Download the Blueprint Resource
    # TODO: Store the Blueprint Resource in a Temp folder (Use StringIO later).


def execute_command(command):

    ctx.logger.debug('command {0}.'.format(repr(command)))

    subprocess_args = {
        'args': command,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE
    }

    ctx.logger.debug('subprocess_args {0}.'.format(subprocess_args))

    process = subprocess.Popen(**subprocess_args)
    output, error = process.communicate()

    ctx.logger.debug('error: {0} '.format(error))
    ctx.logger.debug('process.returncode: {0} '.format(process.returncode))

    if process.returncode:
        ctx.logger.error('Running `{0}` returns error.'.format(repr(command)))
        return False

    return output
