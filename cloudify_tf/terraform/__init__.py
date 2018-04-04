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

import os
import subprocess

from cloudify import ctx

class Terraform(object):

    def __init__(self,
                 binary_path,
                 root_module,
                 variables=None,
                 environment_variables=None):

        self.binary_path = binary_path
        self.root_module = root_module

        if isinstance(environment_variables, dict):
            execution_env = os.environ.copy()
            for ev_key, ev_val in environment_variables.items():
                execution_env[ev_key] = ev_val
            self.env = execution_env
        else:
            self.env = None

        if isinstance(variables, dict):
            self.variables_list = \
                ["-var %s=%r" % (key,val) for (key,val) in variables.items()]
        elif not variables:
            self.variables_list = []
        else:
            raise RuntimeError(
                'Terraform parameter variables is not required, '
                'but if given must be a dictionary.')

        # Check that we can do any work at all.
        if not self.version():
            raise RuntimeError('Terraform is not installed.')

    def execute(self, command):

        subprocess_args = {
            'args': command.split(),
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'cwd': self.root_module
        }

        if self.env:
            subprocess_args['env'] = self.env

        ctx.logger.info('args: {}'.format(subprocess_args))

        try:
            process = subprocess.Popen(**subprocess_args)
            output, error = process.communicate()
        except OSError as e:
            raise e
        if process.returncode:
            return False

        return output

    def version(self):
        _command = '{0} version'.format(self.binary_path)
        return self.execute(_command)

    def init(self):
        _command = '{0} init'.format(self.binary_path)
        return self.execute(_command)

    def plan(self):
        _command = '{0} plan'.format(self.binary_path)
        if len(self.variables_list):
            _command = _command + ' ' + ' '.join(self.variables_list)
        return self.execute(_command)

    def graph(self):
        _command = '{0} graph'.format(self.binary_path)
        return self.execute(_command)
