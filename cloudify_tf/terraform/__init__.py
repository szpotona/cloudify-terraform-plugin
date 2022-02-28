########
########
# Copyright (c) 2018-2020 GigaSpaces Technologies Ltd. All rights reserved
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
import re
import json
import tempfile
from distutils.version import LooseVersion as parse_version

from contextlib import contextmanager
from cloudify import exceptions as cfy_exc
from cloudify_common_sdk.utils import run_subprocess

from .. import utils

from cloudify_common_sdk.cli_tool_base import CliTool


class Terraform(CliTool):
    # TODO: Rework this to put the execute method in its own module.
    # TODO: After you do that, move all the SSH commands to the tasks module.

    def __init__(self,
                 logger,
                 binary_path,
                 plugins_dir,
                 root_module,
                 variables=None,
                 environment_variables=None,
                 backend=None,
                 provider=None,
                 provider_upgrade=False,
                 additional_args=None,
                 version=None,
                 flags_override=None,
                 log_stdout=True):

        try:
            deployment_name = root_module.split('/')[-2]
            node_instance_name = root_module.split('/')[-1]
        except (IndexError, AttributeError):
            logger.info('Invalid root module: {}'.format(root_module))
            deployment_name = None
            node_instance_name = None

        super().__init__(logger, deployment_name, node_instance_name)

        backend = backend or {}

        self.binary_path = binary_path
        self.plugins_dir = self.set_plugins_dir(plugins_dir)
        self.root_module = root_module
        self.logger = logger
        self.additional_args = additional_args
        self._version = version
        self._flags_override = flags_override or []
        self._log_stdout = log_stdout
        self._tflint = None
        self._tfsec = None

        if not isinstance(environment_variables, dict):
            raise Exception(
                "Unexpected type for environment variables (should be a "
                "dict): {0}".format(type(
                    environment_variables)))

        if not isinstance(variables, dict):
            raise Exception(
                "Unexpected type for variables (should be a "
                "dict): {0}".format(type(
                    variables)))

        self._env = self.convert_bools_in_env(environment_variables)
        self._backend = backend
        self._provider = provider
        self._variables = variables
        self.provider_upgrade = provider_upgrade

    @property
    def flags(self):
        if not self._flags:
            self._flags = self._format_flags(self._flags_override)
        return self._flags

    @property
    def env(self):
        return self._env

    @env.setter
    def env(self, value):
        new_value = self.convert_bools_in_env(value)
        if self._env:
            self._env.update(new_value)
        else:
            self._env = new_value

    @property
    def variables(self):
        return self._variables

    @variables.setter
    def variables(self, value):
        if self._variables:
            self._variables.update(value)
        else:
            self._variables = value

    @property
    def backend(self):
        if self._backend:
            return utils.create_backend_string(
                self._backend.get('name'), self._backend.get('options', {}))

    @property
    def provider(self):
        if self._provider:
            return utils.create_provider_string(
                self._provider.get('providers', {}))

    @staticmethod
    def convert_bools_in_env(env):
        for k, v in env.items():
            if isinstance(v, bool):
                env[k] = str(v).lower()
        return env

    @staticmethod
    def set_plugins_dir(path):
        if not os.listdir(path):
            return
        return path

    def execute(self, command, return_output=None):
        return_output = return_output or self._log_stdout
        return run_subprocess(
            command,
            self.logger,
            self.root_module,
            self.env,
            self.additional_args,
            return_output=return_output)

    def _tf_command(self, args):
        cmd = [self.binary_path]
        cmd.extend(args)
        # TODO: Add flags override.
        #  But there are some commands, e.g. init that are not relevant.
        return cmd

    def put_backend(self):
        utils.dump_file(self.backend, self.root_module, 'backend.tf')

    def put_provider(self):
        if self.provider:
            utils.dump_file(self.provider,
                            self.root_module,
                            self._provider.get('filename', 'provider.tf'))

    @contextmanager
    def runtime_file(self, command):
        with tempfile.NamedTemporaryFile(suffix=".json",
                                         delete=False,
                                         mode="w",
                                         dir=self.root_module) as f:
            json.dump(self.variables, f)
            f.close()
            command.extend(['-var-file', f.name])
            yield
        os.remove(f.name)

    @property
    def version(self):
        if not self._version:
            returned_output = self.execute(
                self._tf_command(['version', '-json']), False)
            self._version = self.read_version(returned_output)
        return self._version

    @staticmethod
    def read_version_from_text(text):
        try:
            return re.search(
                'Terraform\\sv(.*)\\n', text.decode('utf-8')).group(1)
        except AttributeError:
            return '0.0.0'

    def read_version(self, response):
        try:
            return json.loads(response)
        except (ValueError, json.JSONDecodeError):
            return {
                'terraform_version': self.read_version_from_text(response),
                'terraform_outdated': True
            }

    @property
    def terraform_version(self):
        return self.version.get('terraform_version')

    @property
    def terraform_outdated(self):
        return self.version.get('terraform_outdated')

    @property
    def tflint(self):
        return self._tflint

    @tflint.setter
    def tflint(self, value):
        self._tflint = value

    @property
    def tfsec(self):
        return self._tfsec

    @tfsec.setter
    def tfsec(self, value):
        self._tfsec = value

    def init(self, command_line_args=None):
        cmdline = ['init', '-no-color', '-input=false']
        if self.plugins_dir:
            cmdline.append('--plugin-dir=%s' % self.plugins_dir)
        if self.provider_upgrade:
            cmdline.append('--upgrade')
        command = self._tf_command(cmdline)
        if command_line_args:
            command.extend(command_line_args)
        with self.runtime_file(command):
            return self.execute(command)

    def destroy(self):
        command = self._tf_command(['destroy',
                                    '-auto-approve',
                                    '-no-color',
                                    '-input=false'])
        with self.runtime_file(command):
            return self.execute(command)

    def plan(self, out_file_path=None):
        command = self._tf_command(['plan', '-no-color', '-input=false'])
        if out_file_path:
            command.extend(['-out', out_file_path])
        with self.runtime_file(command):
            return self.execute(command, False)

    def apply(self):
        command = self._tf_command(['apply',
                                    '-auto-approve',
                                    '-no-color',
                                    '-input=false'])
        with self.runtime_file(command):
            return self.execute(command)

    def output(self):
        command = self._tf_command(['output', '-json', '-no-color'])
        returned_output = self.execute(command, False)
        if returned_output:
            return json.loads(returned_output)

    def graph(self):
        command = self._tf_command(['graph'])
        return self.execute(command)

    def state_pull(self):
        command = self._tf_command(['state', 'pull'])
        pulled_state = self.execute(command, False)
        # If we got here, then the "state pull" return code must
        # be zero, and pulled_state actually contains a parse-able
        # JSON.
        if pulled_state:
            return json.loads(pulled_state)

    def refresh(self):
        if parse_version(self.terraform_version) >= parse_version("0.15.4"):
            command = self._tf_command(['apply',
                                        '-refresh-only',
                                        '-auto-approve',
                                        '-no-color',
                                        '-input=false'])
        else:
            command = self._tf_command(['refresh', '-no-color'])
        with self.runtime_file(command):
            return self.execute(command)

    def state_list(self, plan_file_path=None):
        options = ['state', 'list']
        if plan_file_path:
            options.append('-state={}'.format(plan_file_path))
        command = self._tf_command(options)
        output = self.execute(command)
        return output

    def show(self, plan_file_path=None):
        options = ['show', '-no-color', '-json']
        if plan_file_path:
            options.append(plan_file_path)
        command = self._tf_command(options)
        output = self.execute(command, False)
        if output:
            return json.loads(output)

    def show_plain_text(self, plan_file_path=None):
        options = ['show', '-no-color']
        if plan_file_path:
            options.append(plan_file_path)
        command = self._tf_command(options)
        return self.execute(command)

    def plan_and_show(self):
        """
        Execute terraform plan,
        then terraform show on the generated tfplan file
        """
        with tempfile.NamedTemporaryFile() as plan_file:
            self.plan(plan_file.name)
            return self.show(plan_file.name)

    def plan_and_show_two_formats(self):
        """
        Execute terraform plan,
        then terraform show on the generated tfplan file
        """
        with tempfile.NamedTemporaryFile() as plan_file:
            self.plan(plan_file.name)
            json_result = self.show(plan_file.name)
            plain_text_result = self.show_plain_text(plan_file.name)
            return json_result, plain_text_result

    def plan_and_show_state(self):
        """
        Execute terraform plan,
        then terraform show on the generated tfplan file
        """
        status_problems = []
        with tempfile.NamedTemporaryFile() as plan_file:
            self.plan(plan_file.name)
            plan = self.show(plan_file.name)
            self.refresh()
            for key, value in plan['planned_values']['root_module'].items():
                if key == 'resources':
                    status_problems.extend(
                        self._show_state_resource_list(value))
                elif key == 'child_modules':
                    status_problems.extend(self._show_state_of_modules(value))
        return status_problems

    def _show_state_of_modules(self, value):
        status_problems = []
        for module in value:
            if not isinstance(module, dict) or 'resources' not in module:
                continue
            status_problems.extend(self._show_state_resource_list(
                module['resources']))
        return status_problems

    def _show_state_resource_list(self, value):
        status_problems = []
        for resource in value:
            try:
                self.show_state(
                    resource['address'],
                    os.path.join(self.root_module, 'terraform.tfstate'))
            except Exception:
                status_problems.append(resource)
        return status_problems

    def show_state(self, resource_name, plan_file_path=None):
        options = ['state', 'show', '-no-color']
        if plan_file_path:
            options.append('-state={}'.format(plan_file_path))
        options.append(resource_name)
        command = self._tf_command(options)
        return self.execute(command)

    @staticmethod
    def from_ctx(ctx, terraform_source, skip_tf=False):
        try:
            executable_path = utils.get_executable_path() or \
                              utils.get_binary_location_from_rel()
        except cfy_exc.NonRecoverableError:
            if skip_tf:
                executable_path = None
            else:
                raise
        plugins_dir = utils.get_plugins_dir()
        resource_config = utils.get_resource_config()
        provider_upgrade = utils.get_provider_upgrade()
        general_executor_process = ctx.node.properties.get(
            'general_executor_process')
        if not os.path.exists(plugins_dir) and utils.is_using_existing():
            utils.mkdir_p(plugins_dir)
        env_variables = resource_config.get('environment_variables')
        terraform_version = ctx.instance.runtime_properties.get(
            'terraform_version', {})
        flags_override = resource_config.get('flags_override')
        tf = Terraform(
                ctx.logger,
                executable_path,
                plugins_dir,
                terraform_source,
                variables=resource_config.get('variables'),
                environment_variables=env_variables or {},
                backend=resource_config.get('backend'),
                provider=resource_config.get('provider'),
                provider_upgrade=provider_upgrade,
                additional_args=general_executor_process,
                version=terraform_version,
                flags_override=flags_override,
                log_stdout=resource_config.get('log_stdout', True)
        )
        tf.put_backend()
        tf.put_provider()
        if not terraform_version and not skip_tf:
            ctx.instance.runtime_properties['terraform_version'] = \
                tf.version
        return tf

    def check_tflint(self):
        if not hasattr(self, 'tflint') or not self.tflint:
            return
        self.tflint.validate()
        self.tflint.terraform_root_module = self.root_module
        commands = []
        with self.runtime_file(commands):
            self.tflint.tflint(commands[-1])

    def check_tfsec(self):
        if not hasattr(self, 'tfsec') or not self.tfsec:
            return
        self.tfsec.validate()
        self.tfsec.terraform_root_module = self.root_module
        commands = []
        with self.runtime_file(commands):
            self.tfsec.tfsec()
