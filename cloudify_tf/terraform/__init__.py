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

import json
import os
import shlex
import subprocess

from cloudify import ctx
from ..utils import clean_strings

# import hcl


class Terraform(object):
    # TODO: Rework this to put the execute method in its own module.
    # TODO: After you do that, move all the SSH commands to the tasks module.

    def __init__(self,
                 binary_path,
                 root_module,
                 variables=None,
                 environment_variables=None,
                 logger=None):

        self.binary_path = binary_path
        self.root_module = root_module
        self.logger = logger or ctx.logger

        if isinstance(environment_variables, dict):
            execution_env = os.environ.copy()
            for ev_key, ev_val in environment_variables.items():
                ev_key = clean_strings(ev_key)
                ev_val = clean_strings(ev_val)
                execution_env[ev_key] = ev_val
            self.env = execution_env
        else:
            self.env = None

        if isinstance(variables, dict):
            if not hasattr(self, 'variables_list'):
                setattr(self, 'variables_list', [])
            for var_key, var_val in variables.items():
                var_key = clean_strings(var_key)
                var_val = clean_strings(var_val)
                self.variables_list.append(
                    '-var {0}="{1}"'.format(var_key, var_val))
        else:
            self.variables_list = []

        # Check that we can do any work at all.
        if not self.version():
            raise RuntimeError('Terraform is not installed.')

    def execute(self, command):

        subprocess_args = {
            'args': shlex.split(command),
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'cwd': self.root_module
        }

        if self.env:
            subprocess_args['env'] = self.env

        self.logger.debug('args: {0}'.format(subprocess_args))

        try:
            process = subprocess.Popen(**subprocess_args)
            output, error = process.communicate()
        except OSError as e:
            raise e
        else:
            self.logger.debug('returncode: {0}'.format(process.returncode))
            self.logger.debug('stdout: {0}'.format(output))
            self.logger.error('stderr: {0}'.format(error))

        if process.returncode:
            return False

        return output

    def version(self):
        _command = '{0} version'.format(self.binary_path)
        return self.execute(_command)

    def init(self, additional_args=None):
        _command = '{0} init'.format(self.binary_path)
        if additional_args:
            _command += ' ' + additional_args
        return self.execute(_command)

    def destroy(self):
        _command = '{0} destroy -auto-approve'.format(self.binary_path)
        if len(self.variables_list):
            _command = _command + ' ' + ' '.join(self.variables_list)
        return self.execute(_command)

    def plan(self):
        _command = '{0} plan'.format(self.binary_path)
        if len(self.variables_list):
            _command = _command + ' ' + ' '.join(self.variables_list)
        return self.execute(_command)

    def apply(self):
        _command = '{0} apply -auto-approve'.format(self.binary_path)
        if len(self.variables_list):
            _command = _command + ' ' + ' '.join(self.variables_list)
        return self.execute(_command)

    def graph(self):
        _command = '{0} graph'.format(self.binary_path)
        return self.execute(_command)

    def state_pull(self):
        _command = '{0} state pull'.format(self.binary_path)
        pulled_state = self.execute(_command)
        if not pulled_state:
            # Essentially, we are talking about a failure somewhere.
            # But for now, we'll just not store any data.
            # This return value is expected by the method that call this.
            return {'modules': []}
        return json.loads(pulled_state)

    def refresh(self):
        _command = '{0} refresh'.format(self.binary_path)
        if len(self.variables_list):
            _command = _command + ' ' + ' '.join(self.variables_list)
        return self.execute(_command)
