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

COMPUTE_RESOURCE_TYPES = \
    [
        'alicloud_instance',
        'aws_instance',
        'azurerm_virtual_machine',
        'google_compute_instance',
        'opc_compute_instance',
        'vsphere_virtual_machine',
    ]

COMPUTE_ATTRIBUTES = \
    [
         'private_ip',
         'public_ip',
    ]

# TODO: Get a better way of setting backends.
TERRAFORM_BACKEND = \
    """
  backend "%s" {
%s
  }
"""
