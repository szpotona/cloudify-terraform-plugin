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

import os
import StringIO
import tarfile
import tempfile
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from cloudify.decorators import workflow
from cloudify.manager import get_rest_client
from cloudify.workflows import ctx
from cloudify.exceptions import NonRecoverableError

COMPUTE_TYPE = 'cloudify.nodes.Compute'
NOT_FOUND = '{0} not found.'


def generate_node_template(node_type,
                           node_properties=None,
                           relationships=None):

    """
    Generate a node template.

    :param string node_type:
        The name of a Cloudify Node Template supported in the blueprint.
    :param dict node_properties:
        A dictionary of keys and values to set as properties
        on the node template.
    :param list relationships:
        A list of dict items containing relationship targets and types
        on this node template.
    """

    ctx.logger.debug('Generating a new node template.')

    node_properties = node_properties or {}
    relationships = relationships or []

    node_template = \
        {'type': node_type, 'properties': {}, 'relationships': relationships}

    for property_name, property_value in node_properties.items():
        node_template['properties'][property_name] = property_value

    return node_template


def get_node_instances(_node_instance_id, _client=None):

    """
    See: http://docs.getcloudify.org/api/v3.1/#get-node-instance.
    :param string _node_instance_id: The node instance ID.
    :param CloudifyClient _client: The authenticated client.

    """

    ctx.logger.debug('Getting the Terraform node instance.')

    _client = _client or get_rest_client()
    return _client.node_instances.get(_node_instance_id)


# TODO: Update docstring.
def start_deployment_update(
        blueprint_or_archive_path, application_file_name, _client=None):

    """
    Executes a deployment update.
    There is no good documentation on this operation.

    :param string blueprint_path: The path to a blueprint archive.
    :param CloudifyClient _client: The authenticated client.

    """

    ctx.logger.debug('Starting deployment update.')
    _client = _client or get_rest_client()
    return _client.deployment_updates.update(
        ctx.deployment.id,
        blueprint_or_archive_path,
        application_file_name,
        force=True)


def get_blueprint(_client=None):

    """
    See: http://docs.getcloudify.org/api/v3.1/#get-blueprint.
    See: http://docs.getcloudify.org/api/v3.1/#download-blueprint.

    :param CloudifyClient _client: The authenticated client.

    """

    ctx.logger.debug(
        'Getting the blueprint filename and the blueprint archive.')

    _client = _client or get_rest_client()
    work_dir = tempfile.mkdtemp()
    response = _client.blueprints.get(blueprint_id=ctx.blueprint.id)
    filename = response['main_file_name']
    archive_path = _client.blueprints.download(
        blueprint_id=ctx.blueprint.id,
        output_file=os.path.join(work_dir, 'archive.tar.gz'))
    return archive_path, filename


# TODO: Break this up into smaller operations.
def update_blueprint(old_archive_path, blueprint_file, new_node_template):

    """
    This method takes the old blueprint archive and copies everything over.
    In the process, it modifes the main blueprint to add the new node template.

    :param dict new_node_template: This contains the new node template.

    Example usage:
    ```
    update_blueprint(
        'my.zip',
        'blueprint.yaml',
        {'vm': {'type': 'cloudify.nodes.Compute'}}
    )
    ```
    """

    ctx.logger.debug('Updating the blueprint.')

    work_dir = os.path.dirname(old_archive_path)
    # _, new_archive_path = tempfile.mkstemp(dir=work_dir)

    if not os.access(old_archive_path, os.R_OK):
        raise NonRecoverableError(
            'Cannot read {0}'.format(old_archive_path))

    if not tarfile.is_tarfile(old_archive_path):
        raise NonRecoverableError(
            '{0} is neither a tarfile nor a zipfile.'.format(old_archive_path))

    _, new_archive_path = tempfile.mkstemp(dir=work_dir, suffix='.tar.gz')
    with tarfile.open(old_archive_path, 'r:gz') as infile:
        with tarfile.open(new_archive_path, 'w:gz') as outfile:
            for member_info in infile.getmembers():
                member_file_obj = infile.extractfile(member_info)
                if not member_file_obj:
                    continue
                if os.path.basename(member_info.path) == blueprint_file:
                    blueprint_yaml = load(
                        member_file_obj.read(), Loader=Loader)
                    blueprint_yaml['node_templates'].update(
                        new_node_template)
                    member_file_obj = StringIO.StringIO()
                    member_file_obj.write(
                        dump(blueprint_yaml,
                             Dumper=Dumper,
                             default_flow_style=False))
                    member_file_obj.seek(0)
                if hasattr(member_file_obj, 'len'):
                    member_info = tarfile.TarInfo(member_info.path)
                    member_info.size = member_file_obj.len
                outfile.addfile(member_info, member_file_obj)

    return new_archive_path


def upload_blueprint_update(archive, main_file_name, _client=None):
    _client = _client or get_rest_client()
    # TODO: Figure out a better way to do this.
    blueprints = _client.blueprints.list()
    new_blueprint_id = '{0}-{1}'.format(
        ctx.blueprint.id, len(blueprints.items))
    upload = \
        _client.blueprints._upload(archive, new_blueprint_id, main_file_name)
    return upload['id']


@workflow
def export_resource(node_instance_id,
                    resource_name,
                    node_type=COMPUTE_TYPE,
                    **_):

    """
    Run deployment update on the deployment to expose a
    Terraform resource as a new node template on the deployment.

    :param string node_instance_id: The node instance ID of a
        Terraform Module in the deployment.
    :param string resource_name: The name of the Terraform resource.
    :param node_type: The name of a Cloudify node type.
        The node type must be supported by one of the plugins that
        are already importent by the deployments blueprints.

    """

    if isinstance(resource_name, unicode):
        resource_name = resource_name.encode('utf-8')
    if isinstance(resource_name, unicode):
        node_type = node_type.encode('utf-8')

    # Get the Terraform node instance object.
    node_instance = get_node_instances(node_instance_id)

    # Make sure there are resources to expose.
    if 'resources' not in node_instance.runtime_properties:
        raise NonRecoverableError(
            'No resources exist in this deployment. '
            'Have you executed the install workflow?')

    # Get the resource.
    resource = node_instance.runtime_properties.get(
        'resources', {}).get(resource_name)
    if not resource:
        raise NonRecoverableError(NOT_FOUND.format(resource_name))

    # Prepare a relationship from the new node template to the Terraform node.
    target_node = node_instance.node_id
    if isinstance(target_node, unicode):
        target_node = target_node.encode('utf-8')
    default_relationship = {
        'type': 'cloudify.relationships.contained_in',
        'target': target_node
    }

    # Get a basic node template.
    new_node_template = generate_node_template(
        node_type,
        relationships=[default_relationship])

    # Make sure that we provide Compute specific properties if needed.
    if node_type is COMPUTE_TYPE:
        private_ip = resource['primary']['attributes']['private_ip']
        if isinstance(private_ip, unicode):
            private_ip = private_ip.encode('utf-8')
        new_node_template['properties'] = {
            'ip': private_ip,
            'agent_config': {
                'install_method': 'none',
            }
        }

    blueprint_archive, blueprint_file_name = get_blueprint()

    # Get the blueprint and update it.
    new_archive = \
        update_blueprint(
            blueprint_archive,
            blueprint_file_name,
            {resource_name: new_node_template})

    # Update the deployment.
    start_deployment_update(
        new_archive, blueprint_file_name)
