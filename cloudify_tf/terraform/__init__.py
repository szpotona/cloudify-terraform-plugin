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
import subprocess

from ..utils import (clean_strings,
                     CapturingOutputConsumer,
                     LoggingOutputConsumer)


class Terraform(object):
    # TODO: Rework this to put the execute method in its own module.
    # TODO: After you do that, move all the SSH commands to the tasks module.

    def __init__(self,
                 logger,
                 binary_path,
                 root_module,
                 variables=None,
                 environment_variables=None):

        self.binary_path = binary_path
        self.root_module = root_module
        self.logger = logger

        if isinstance(environment_variables, dict):
            execution_env = os.environ.copy()
            for ev_key, ev_val in environment_variables.items():
                ev_key = clean_strings(ev_key)
                ev_val = clean_strings(ev_val)
                execution_env[ev_key] = ev_val
            self.env = execution_env
        elif environment_variables is not None:
            raise Exception(
                "Unexpected type (should be a dict): {0}".format(type(
                    environment_variables)))
        else:
            self.env = None

        self.variables_list = []
        if isinstance(variables, dict):
            for var_key, var_val in variables.items():
                var_key = clean_strings(var_key)
                var_val = clean_strings(var_val)
                self.variables_list.extend(["-var", "{0}={1}".format(
                    var_key, var_val)])

        # Check that we can do any work at all.
        if not self.version():
            raise RuntimeError('Terraform is not installed.')

    def execute(self, command, return_output=False):
        additional_args = {}
        if self.env:
            additional_args['env'] = self.env

        self.logger.info("Running: %s", command)

        process = subprocess.Popen(
            args=command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=None,
            cwd=self.root_module,
            **additional_args)

        if return_output:
            stdout_consumer = CapturingOutputConsumer(
                process.stdout)
        else:
            stdout_consumer = LoggingOutputConsumer(
                process.stdout, self.logger, "<out> ")
        stderr_consumer = LoggingOutputConsumer(
            process.stderr, self.logger, "<err> ")

        return_code = process.wait()
        stdout_consumer.join()
        stderr_consumer.join()

        if return_code:
            raise subprocess.CalledProcessError(return_code, command)

        output = stdout_consumer.buffer.getvalue() if return_output else None
        self.logger.info("Returning output:\n%s", output if output is not None else '<None>')
        return output

    def _tf_command(self, args):
        cmd = [self.binary_path]
        cmd.extend(args)
        return cmd

    def version(self):
        return self.execute(self._tf_command(['version']), True)

    def init(self, additional_args=None):
        command = self._tf_command(['init'])
        if additional_args:
            command.extend(additional_args)
        return self.execute(command)

    def destroy(self):
        command = self._tf_command(['destroy', '-auto-approve', '-no-color'])
        command.extend(self.variables_list)
        return self.execute(command)

    def plan(self):
        command = self._tf_command(['plan'])
        command.extend(self.variables_list)
        return self.execute(command)

    def apply(self):
        command = self._tf_command(['apply', '-auto-approve', '-no-color'])
        command.extend(self.variables_list)
        return self.execute(command)

    def graph(self):
        command = self._tf_command(['graph'])
        return self.execute(command)

    def state_pull(self):
        command = self._tf_command(['state', 'pull'])
        pulled_state = self.execute(command, True)
        if not pulled_state:
            # Essentially, we are talking about a failure somewhere.
            # But for now, we'll just not store any data.
            # This return value is expected by the method that call this.
            return {'modules': []}
        return json.loads(pulled_state)

    def refresh(self):
        command = self._tf_command(['refresh', '-no-color'])
        command.extend(self.variables_list)
        return self.execute(command)
