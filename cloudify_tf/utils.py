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
import zipfile
import os

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError


def update_runtime_properties(_key, _value, operation='configure'):
    """
    We want to be good about deleting keys during uninstallation.
    So we track, which keys were added in which operation.
    """

    # Make sure that we are ready to fiddle with this Key.
    if 'operation_keys' not in ctx.instance.runtime_properties:
        ctx.instance.runtime_properties['operation_keys'] = {}

    # Get the current list of keys set by this operation.
    # Append the new key to the list and update the Key.
    operation_keys = ctx.instance.runtime_properties['operation_keys'].get(operation, [])
    operation_keys.append(_key)
    ctx.instance.runtime_properties['operation_keys'][operation] = operation_keys

    # Assign the runtime property
    ctx.instance.runtime_properties[_key] = _value

    return


def unzip_archive(archive_path, **_):
    """
    Unzip a zip archive.
    """

    # Create a temporary directory.
    # Create a zip archive object.
    # Extract the object.
    directory_to_extract_to = tempfile.mkdtemp()
    zip_ref = zipfile.ZipFile(archive_path, 'r')
    zip_ref.extractall(directory_to_extract_to)
    zip_ref.close()

    update_runtime_properties('directory_to_extract_to', directory_to_extract_to)
    unzipped_work_directory = os.path.join(directory_to_extract_to, zip_ref.namelist()[0])

    if not os.path.isdir(unzipped_work_directory):
        raise NonRecoverableError('{0} is not a valid directory path.'.format(unzipped_work_directory))

    return unzipped_work_directory
