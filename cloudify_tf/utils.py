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

from cloudify_common_sdk.resource_downloader import get_shared_resource
from cloudify_common_sdk.resource_downloader import unzip_archive
from cloudify_common_sdk.resource_downloader import untar_archive
from cloudify_common_sdk.resource_downloader import TAR_FILE_EXTENSTIONS


from contextlib import contextmanager
import copy
import tempfile
import base64
import threading
import zipfile
import os
from io import BytesIO
from tempfile import mkstemp
import StringIO
import shutil
import subprocess

from . import TERRAFORM_BACKEND

TERRAFORM_STATE_FILE = "terraform.tfstate"


def run_subprocess(command, logger, cwd=None,
                   additional_env=None,
                   additional_args=None, return_output=False):
    if additional_args is None:
        additional_args = {}
    args_to_pass = copy.deepcopy(additional_args)
    if additional_env:
        passed_env = args_to_pass.setdefault('env', {})
        passed_env.update(os.environ)
        passed_env.update(additional_env)

    logger.info("Running: command=%s, cwd=%s, additional_args=%s",
                command, cwd, args_to_pass)
    process = subprocess.Popen(
        args=command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=None,
        cwd=cwd,
        **args_to_pass)

    if return_output:
        stdout_consumer = CapturingOutputConsumer(
            process.stdout)
    else:
        stdout_consumer = LoggingOutputConsumer(
            process.stdout, logger, "<out> ")
    stderr_consumer = LoggingOutputConsumer(
        process.stderr, logger, "<err> ")

    return_code = process.wait()
    stdout_consumer.join()
    stderr_consumer.join()

    if return_code:
        raise subprocess.CalledProcessError(return_code, command)

    output = stdout_consumer.buffer.getvalue() if return_output else None
    logger.info("Returning output:\n%s",
                output if output is not None else '<None>')
    return output


def _zip_archive(ctx, extracted_source, **_):
    arhcive_file_path = None
    ctx.logger.info("Zipping %s", extracted_source)
    with tempfile.NamedTemporaryFile(suffix=".zip",
                                     delete=False) as updated_zip:
        updated_zip.close()
        with zipfile.ZipFile(
                updated_zip.name, mode='w',
                compression=zipfile.ZIP_DEFLATED) as output_file:
            for dir_name, subdirs, filenames in os.walk(extracted_source):
                for filename in filenames:
                    file_to_add = os.path.join(dir_name, filename)
                    arc_name = file_to_add[len(extracted_source)+1:]
                    output_file.write(file_to_add, arcname=arc_name)
        arhcive_file_path = updated_zip.name
    return arhcive_file_path


def _unzip_archive(ctx, archive_path, storage_path, **_):
    """
    Unzip a zip archive.
    """

    # Create a temporary directory.
    # Create a zip archive object.
    # Extract the object.
    ctx.logger.info("Extracting %s to %s", archive_path, storage_path)
    directory_to_extract_to = tempfile.mkdtemp(dir=storage_path)
    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
        zip_ref.extractall(directory_to_extract_to)

    return directory_to_extract_to


def clean_strings(string):
    if isinstance(string, unicode):
        return string.encode('utf-8').rstrip("'").lstrip("'")
    return string


@contextmanager
def get_terraform_source(ctx, _resource_config):
    def _file_to_base64(file_path):
        base64_rep = BytesIO()
        with open(file_path, 'rb') as f:
            base64.encode(f, base64_rep)
        return base64_rep.getvalue()

    # Look for the archive in the runtime properties.
    encoded_source = ctx.instance.runtime_properties.get('terraform_source')
    if not encoded_source:
        # Not found, so we need to fetch the file from source,
        # and then set it as a runtime property for future operations.
        terraform_source = _resource_config['source']
        source_tmp_path = get_shared_resource(terraform_source)
        # check if we actually downloaded something or not
        if source_tmp_path == terraform_source:
            # didn't download anything so check the provided path
            # if file and absolute path or not
            if not os.path.isabs(source_tmp_path):
                # bundled and need to be downloaded from blurprint
                source_tmp_path = ctx.download_resource(source_tmp_path)
            if os.path.isfile(source_tmp_path):
                file_name = source_tmp_path.rsplit('/', 1)[1]
                file_type = file_name.rsplit('.', 1)[1]
                # check type
                if file_type == 'zip':
                    source_tmp_path = unzip_archive(source_tmp_path)
                elif file_type in TAR_FILE_EXTENSTIONS:
                    source_tmp_path = untar_archive(source_tmp_path)

        # By getting here we will have extracted source
        # Zip the file to store in runtime
        terraform_source_zip = _zip_archive(ctx, source_tmp_path)
        # By getting here, "terraform_source_zip" is the path to a ZIP
        # file containing the Terraform files.
        # We need to encode the contents of the file and set them
        # as a runtime property.
        base64_rep = _file_to_base64(terraform_source_zip)
        ctx.instance.runtime_properties['terraform_source'] = base64_rep
        ctx.instance.runtime_properties['last_source_location'] = \
            terraform_source
    else:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            base64.decode(StringIO.StringIO(encoded_source), f)
            terraform_source_zip = f.name

    # By getting here, "terraform_source_zip" is the path
    #  to a ZIP file containing the Terraform files.
    storage_path = ctx.instance.runtime_properties.get('storage_path', "")
    if storage_path and not os.path.isdir(storage_path):
        os.makedirs(storage_path)
    extracted_source = _unzip_archive(ctx, terraform_source_zip, storage_path)
    os.remove(terraform_source_zip)

    module_root = extracted_source
    extracted_source_files = os.listdir(module_root)
    if len(extracted_source_files) == 1:
        extracted_only_entry = os.path.join(extracted_source,
                                            extracted_source_files[0])
        if os.path.isdir(extracted_only_entry):
            module_root = extracted_only_entry

    ctx.logger.info("Will use %s as module root", module_root)

    backend = _resource_config.get('backend')
    if backend:
        backend_string = create_backend_string(
            backend['name'], backend.get('options', {}))
        backend_file_path = os.path.join(
            extracted_source, '{0}.tf'.format(backend['name']))
        with open(backend_file_path, 'w') as infile:
            infile.write(backend_string)

    ctx.logger.debug("Extracted Terraform files: %s", extracted_source)
    try:
        yield module_root
    finally:
        ctx.logger.debug("Re-packaging Terraform files from %s",
                         extracted_source)
        archived_file = _zip_archive(ctx, extracted_source)
        base64_rep = _file_to_base64(archived_file)
        ctx.instance.runtime_properties['terraform_source'] = base64_rep
        os.remove(archived_file)
        shutil.rmtree(extracted_source)


def get_terraform_state_file(ctx):
    state_file_path = None
    encoded_source = ctx.instance.runtime_properties.get('terraform_source')
    with tempfile.NamedTemporaryFile(delete=False) as f:
        base64.decode(StringIO.StringIO(encoded_source), f)
        terraform_source_zip = f.name
    storage_path = ctx.instance.runtime_properties.get('storage_path', "")
    if storage_path and not os.path.isdir(storage_path):
        os.makedirs(storage_path)
    extracted_source = _unzip_archive(ctx, terraform_source_zip, storage_path)
    os.remove(terraform_source_zip)
    for dir_name, subdirs, filenames in os.walk(extracted_source):
        for filename in filenames:
            if filename == TERRAFORM_STATE_FILE:
                fd, state_file_path = mkstemp()
                os.close(fd)
                shutil.move(os.path.join(dir_name, filename), state_file_path)
                break
    shutil.rmtree(extracted_source)
    return state_file_path


def move_state_file(src, dst):
    shutil.move(src, os.path.join(dst, TERRAFORM_STATE_FILE))


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
