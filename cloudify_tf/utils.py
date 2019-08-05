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

from cloudify.exceptions import NonRecoverableError

from . import COMPUTE_ATTRIBUTES, COMPUTE_RESOURCE_TYPES, TERRAFORM_BACKEND


def delete_runtime_properties(ctx):
    for op in ctx.instance.runtime_properties['operation_keys']:
        for prop in ctx.instance.runtime_properties['operation_keys'][op]:
            ctx.instance.runtime_properties.pop(prop, None)


def update_runtime_properties(ctx, _key, _value, operation='any'):
    """
    We want to be good about deleting keys during uninstallation.
    So we track, which keys were added in which operation.
    """

    # Make sure that we are ready to fiddle with this Key.
    if 'operation_keys' not in ctx.instance.runtime_properties:
        ctx.instance.runtime_properties['operation_keys'] = {}

    # Get the current list of keys set by this operation.
    # Append the new key to the list and update the Key.
    operation_keys = \
        ctx.instance.runtime_properties['operation_keys'].get(
            operation, [])
    if _key not in operation_keys:
        operation_keys.append(_key)
    ctx.instance.runtime_properties['operation_keys'][operation] = \
        operation_keys

    # Assign the runtime property
    ctx.instance.runtime_properties[_key] = _value


def unzip_archive(ctx, archive_path, **_):
    """
    Unzip a zip archive.
    """

    # Create a temporary directory.
    # Create a zip archive object.
    # Extract the object.
    directory_to_extract_to = tempfile.mkdtemp()
    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
        zip_ref.extractall(directory_to_extract_to)

    update_runtime_properties(
        ctx,
        'directory_to_extract_to',
        directory_to_extract_to)
    unzipped_work_directory = os.path.join(
        directory_to_extract_to, zip_ref.namelist()[0])

    if not os.path.isdir(unzipped_work_directory):
        raise NonRecoverableError(
            '{0} is not a valid directory path.'.format(
                unzipped_work_directory))

    return unzipped_work_directory


def get_file_list(base_directory):
    filelist = []
    for (dirpath, dirnames, filenames) in os.walk(base_directory):
        filelist.extend(filenames)
    return filelist


def clean_strings(string):
    if isinstance(string, unicode):
        return string.encode('utf-8').rstrip("'").lstrip("'")
    return string


def get_terraform_source(ctx, _resource_config):
    source = ctx.instance.runtime_properties.get('terraform_source')
    if not source:
        # TODO: Use other sources than a zip file packaged with the blueprint.
        terraform_source_zip = \
            ctx.download_resource(_resource_config.get('source'))
        source = unzip_archive(ctx, terraform_source_zip)
    update_runtime_properties(
        ctx,
        'terraform_source',
        source)
    backend = _resource_config.get('backend')
    if backend:
        backend_string = create_backend_string(
            backend['name'], backend.get('options', {}))
        backend_file_path = os.path.join(
            source, '{0}.tf'.format(backend['name']))
        with open(backend_file_path, 'w') as infile:
            infile.write(backend_string)
    return source


def get_compute_resources(mixed_resources):
    """
    :param dictionary mixed_resources: Resources from a tfstate module.
    """

    mixed_resources = mixed_resources or {}
    compute_resources = []
    for resource_name, resource in mixed_resources.items():
        if any(resource_name.startswith(compute_type)
               for compute_type in COMPUTE_RESOURCE_TYPES):
            resource_id = resource['primary']['id']
            resource_attributes = \
                resource['primary'].get('attributes', {})
            compute_resource = {
                'id': resource_id,
            }
            for compute_attribute in COMPUTE_ATTRIBUTES:
                compute_resource[compute_attribute] = \
                    resource_attributes.get(compute_attribute)
            compute_resources.append(compute_resource)
    return compute_resources


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