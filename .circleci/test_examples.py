########
# Copyright (c) 2014-2019 Cloudify Platform Ltd. All rights reserved
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

import unittest

from ecosystem_tests.dorkl.runners import handle_uninstall_on_success
from ecosystem_tests.dorkl import (cleanup_on_failure, executions_start)

reload_url = 'https://github.com/cloudify-community/blueprint-examples/' \
             'raw/master/virtual-machine/resources/terraform/template.zip'


class TestWorflow(unittest.TestCase):

    def test_blueprint_examples(self):
        try:
            executions_start('reload_terraform_template',
                             'virtual-machine',
                             timeout=300,
                             params={'source': reload_url})
        except:
            cleanup_on_failure('virtual-machine')
            raise
        handle_uninstall_on_success('virtual-machine', 300)
