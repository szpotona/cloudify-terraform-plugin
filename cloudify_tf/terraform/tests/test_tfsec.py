########
# Copyright (c) 2018-2022 Cloudify Platform Ltd. All rights reserved
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
import shutil
from pytest import fixture
from tempfile import mkdtemp
from mock import patch, MagicMock

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext

from .. import tfsec

TFSEC_URL = 'https://github.com/aquasecurity/tfsec/' \
            'releases/download/v1.1.3/tfsec-linux-amd64'


@fixture
def tfsec_params():
    logger_mock = MagicMock()
    params = {
        'logger': logger_mock,
        'deployment_name': 'foo_deployment',
        'node_instance_name': 'foo_instance',
        'installation_source': TFSEC_URL,
        'executable_path': None,
        'config': {},
        'flags_override': ['run-statistics'],
        'env': {}
    }
    return params


def test_config_property_name(tfsec_params):
    tfsec_obj = tfsec.TFSec(**tfsec_params)
    assert tfsec_obj.config_property_name == 'tfsec_config'


def test_installation_source(tfsec_params):
    tfsec_obj = tfsec.TFSec(**tfsec_params)
    assert tfsec_obj.installation_source == TFSEC_URL


@patch('cloudify_common_sdk.cli_tool_base.sdk_utils.get_deployment_dir')
def test_executable_path(get_deployment_dir_sdk, tfsec_params):
    ctx = MockCloudifyContext(
        'test',
        deployment_id='deployment',
        tenant={'name': 'foo'},
        properties={},
        runtime_properties={},
    )
    current_ctx.set(ctx)

    deployment_dir = mkdtemp()
    get_deployment_dir_sdk.return_value = deployment_dir
    expected_path = os.path.join(deployment_dir,
                                 tfsec_params['node_instance_name'],
                                 'tfsec')
    os.makedirs(os.path.dirname(expected_path))
    try:
        tfsec_obj = tfsec.TFSec(**tfsec_params)
        actual_path = tfsec_obj.executable_path
        assert expected_path == actual_path
        assert os.path.isfile(actual_path)
        assert os.listdir(os.path.dirname(actual_path)) == ['tfsec']
        assert os.path.exists(actual_path)
    finally:
        shutil.rmtree(deployment_dir)


@patch('cloudify_common_sdk.cli_tool_base.sdk_utils')
def test_validation(sdk_utils_mock, tfsec_params):
    download_file_mock = MagicMock()
    get_deployment_dir_mock = MagicMock(return_value='foo')
    sdk_utils_mock.download_file = download_file_mock
    sdk_utils_mock.get_deployment_dir = get_deployment_dir_mock
    tfsec_obj = tfsec.TFSec(**tfsec_params)
    tfsec_obj.tool_name = 'test_validate'
    tfsec_obj.validate()
    download_file_mock.assert_called_once_with(
        'foo/foo_instance', TFSEC_URL)
    assert tfsec_obj.flags == ['--run-statistics']
