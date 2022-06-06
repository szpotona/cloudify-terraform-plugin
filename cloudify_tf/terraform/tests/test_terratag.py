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
from tempfile import mkdtemp
from unittest.mock import patch

from mock import MagicMock
from pytest import fixture

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext

from .. import terratag

TERRATAG_URL = 'https://github.com/env0/terratag/releases/download/v0.1.35/' \
            'terratag_0.1.35_linux_amd64.tar.gz'

ctx = MockCloudifyContext(
        'test',
        deployment_id='deployment',
        tenant={'name': 'tenant_test'},
        properties={},
        runtime_properties={},
    )


@fixture
def terratag_params():
    logger_mock = MagicMock()
    params = {
        'logger': logger_mock,
        'deployment_name': 'foo_deployment',
        'node_instance_name': 'foo_instance',
        'installation_source': TERRATAG_URL,
        'executable_path': None,
        'tags': {'tag1: value1'},
        'flags_override': ['verbose=True', 'rename=False'],
        'env': {},
        'enable': True
    }
    return params


def test_terratag_property_name(terratag_params):
    terratag_obj = terratag.Terratag(**terratag_params)
    assert terratag_obj.config_property_name == 'terratag_config'


def test_installation_source(terratag_params):
    terratag_obj = terratag.Terratag(**terratag_params)
    assert terratag_obj.installation_source == TERRATAG_URL


@patch('cloudify_common_sdk.utils.get_deployment_dir')
def test_executable_path(get_deployment_dir_sdk, terratag_params):
    current_ctx.set(ctx)
    deployment_dir = mkdtemp()
    get_deployment_dir_sdk.return_value = deployment_dir
    expected_path = os.path.join(deployment_dir,
                                 terratag_params['node_instance_name'],
                                 'terratag')
    os.makedirs(os.path.dirname(expected_path))
    try:
        terratag_obj = terratag.Terratag(**terratag_params)
        actual_path = terratag_obj.executable_path
        assert expected_path == actual_path
        assert os.path.isfile(actual_path)
        assert os.path.exists(actual_path)
    finally:
        shutil.rmtree(deployment_dir)


@patch('cloudify_common_sdk.utils.get_deployment_dir')
def test_validate(get_deployment_dir_sdk, terratag_params):
    current_ctx.set(ctx)
    deployment_dir = mkdtemp()
    get_deployment_dir_sdk.return_value = deployment_dir
    expected_path = os.path.join(deployment_dir,
                                 terratag_params['node_instance_name'],
                                 'terratag')
    os.makedirs(os.path.dirname(expected_path))
    try:
        terratag_obj = terratag.Terratag(**terratag_params)
        terratag_obj.validate()
    finally:
        shutil.rmtree(deployment_dir)
    assert terratag_obj.tags == {'tag1: value1'}
    assert terratag_obj.flags == ['-verbose=True', '-rename=False']
