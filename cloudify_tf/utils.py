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

import tempfile
import threading
import zipfile
import os
import StringIO

import requests

from cloudify.exceptions import NonRecoverableError

from . import COMPUTE_ATTRIBUTES, COMPUTE_RESOURCE_TYPES, TERRAFORM_BACKEND


def clean_strings(string):
    if isinstance(string, unicode):
        return string.encode('utf-8').rstrip("'").lstrip("'")
    return string


def get_terraform_source(ctx, _resource_config):
    source = ctx.instance.runtime_properties.get('terraform_source')
    if not source:
        storage_path = ctx.node.properties['storage_path'] or None
        if storage_path and not os.path.isdir(storage_path):
            os.makedirs(storage_path)
        terraform_source = _resource_config['source']
        split = terraform_source.split('://')
        schema = split[0]
        if schema in ['http', 'https']:
            ctx.logger.info("Downloading template from %s", terraform_source)
            with requests.get(terraform_source, allow_redirects=True,
                              stream=True) as response:
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(
                        suffix=".zip", delete=False) as source_temp:
                    terraform_source_zip = source_temp.name
                    for chunk in response.iter_content(chunk_size=None):
                        source_temp.write(chunk)
            ctx.logger.info("Template downloaded successfully")
        else:
            terraform_source_zip = \
                ctx.download_resource(terraform_source)

        source = tempfile.mkdtemp(dir=storage_path)
        with zipfile.ZipFile(terraform_source_zip, 'r') as zip_ref:
            zip_ref.extractall(source)

        os.remove(terraform_source_zip)
        ctx.instance.runtime_properties['terraform_source'] = source
    backend = _resource_config.get('backend')
    if backend:
        backend_string = create_backend_string(
            backend['name'], backend.get('options', {}))
        backend_file_path = os.path.join(
            source, '{0}.tf'.format(backend['name']))
        with open(backend_file_path, 'w') as infile:
            infile.write(backend_string)
    return source


def create_backend_string(name, options):
    # TODO: Get a better way of setting backends.
    option_string = ''
    for option_name, option_value in options.items():
        if isinstance(option_value, basestring):
            option_value = '"%s"' % option_value
        option_string += '    %s = %s\n' % (option_name, option_value)
    backend_block = TERRAFORM_BACKEND % (name, option_string)
    return 'terraform {\n%s\n}' % backend_block


# Stolen from the script plugin, until this class
# moves to a utils module in cloudify-common.
class OutputConsumer(object):
    def __init__(self, out):
        self.out = out
        self.consumer = threading.Thread(target=self.consume_output)
        self.consumer.daemon = True

    def consume_output(self):
        for line in self.out:
            self.handle_line(line)
        self.out.close()

    def handle_line(self, line):
        raise NotImplementedError("Must be implemented by subclass")

    def join(self):
        self.consumer.join()


class LoggingOutputConsumer(OutputConsumer):
    def __init__(self, out, logger, prefix):
        OutputConsumer.__init__(self, out)
        self.logger = logger
        self.prefix = prefix
        self.consumer.start()

    def handle_line(self, line):
        self.logger.info("%s%s", self.prefix, line.rstrip('\n'))


class CapturingOutputConsumer(OutputConsumer):
    def __init__(self, out):
        OutputConsumer.__init__(self, out)
        self.buffer = StringIO.StringIO()
        self.consumer.start()

    def handle_line(self, line):
        self.buffer.write(line)

    def get_buffer(self):
        return self.buffer