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

from cloudify.exceptions import NonRecoverableError

HIERARCHY = 'type_hierarchy'
TF_TYPE = 'cloudify.nodes.terraform'
NOT_STARTED = ['uninitialized', 'deleted']
CREATE = 'cloudify.interfaces.lifecycle.create'
REL = 'cloudify.terraform.relationships.run_on_host'
PRECONFIGURE = 'cloudify.interfaces.relationship_lifecycle.preconfigure'


def _terraform_operation(ctx, operation, node_ids,
                         node_instance_ids, **kwargs):
    graph = ctx.graph_mode()
    sequence = graph.sequence()
    # Iterate over all node instances of type "cloudify.nodes.terraform.Module"
    # and refresh states.
    for node_instance in ctx.node_instances:
        if node_ids and (node_instance.node.id not in node_ids):
            continue
        if node_instance_ids and (node_instance.id not in node_instance_ids):
            continue
        if 'cloudify.nodes.terraform.Module' in \
                node_instance.node.type_hierarchy:
            ctx.logger.info("Adding node instance: %s", node_instance.id)
            sequence.add(
                node_instance.execute_operation(
                    operation,
                    kwargs=kwargs,
                    allow_kwargs_override=True)
            )

    return graph


def refresh_resources(ctx, node_ids, node_instance_ids):
    _terraform_operation(
        ctx,
        "terraform.refresh",
        node_ids,
        node_instance_ids).execute()


def reload_resources(ctx,
                     node_ids,
                     node_instance_ids,
                     source,
                     source_path,
                     variables,
                     environment_variables,
                     destroy_previous,
                     force=False):
    kwargs = dict(destroy_previous=destroy_previous)
    if source:
        kwargs['source'] = source
    if source_path:
        kwargs['source_path'] = source_path
    if variables:
        kwargs['variables'] = variables
    if environment_variables:
        kwargs['environment_variables'] = environment_variables
    if force:
        kwargs['force'] = force
    _terraform_operation(
        ctx,
        "terraform.reload",
        node_ids,
        node_instance_ids,
        **kwargs).execute()


def terraform_plan(ctx,
                   node_ids=None,
                   node_instance_ids=None,
                   **kwargs):
    """Execute the terraform plan on nodes or node instances.
    :param ctx: The Cloudify Workflow Context from Workflow.
    :type ctx: CloudifyContext
    :param node_ids: A list of node IDs.
    :type node_ids: list
    :param node_instance_ids: A list of node IDs.
      Mutually exclusive with node_ids.
    :param node_instance_ids: list
    :return graph execution.
    :rtype: NoneType
    """

    graph = ctx.graph_mode()
    sequence = graph.sequence()

    if node_ids and node_instance_ids:
        raise NonRecoverableError(
            'The parameters node_ids and node_instance_ids are '
            'mutually exclusive. '
            '{} and {} were provided.'.format(node_ids, node_instance_ids)
        )
    elif node_ids or (not node_ids and not node_instance_ids):
        for node in ctx.nodes:
            if 'cloudify.nodes.terraform.Module' not in node.type_hierarchy:
                continue
            if not node_ids or node.id in node_ids:
                for instance in node.instances:
                    _plan_module_instance(
                        ctx, node, instance, sequence, kwargs)
    elif node_instance_ids:
        for instance in ctx.node_instances:
            if instance.id in node_instance_ids:
                _plan_module_instance(
                    ctx, instance.node, instance, sequence, kwargs)

    return graph.execute()


def _start_terraform_instance(sequence, r):
    sequence.add(
        r.target_node_instance.execute_operation(CREATE))
    sequence.add(
        r.execute_source_operation(PRECONFIGURE))
    sequence.add(
        r.target_node_instance.set_state('started'))


def _plan_module_instance(ctx, node, instance, sequence, kwargs):
    """ Create a task sequence that will execute a terraform plan on
    a list of nodes.

    :param ctx: CloudifyWorkflowContext
    :type ctx: CloudifyWorkflowContext
    :param node: CloudifyWorkflowNode
    :param instance: CloudifyWorkflowNodeInstance
    :param sequence: TaskSequence
    :param kwargs:
    :return: None
    """

    for rel in instance.relationships:
        if rel.target_node_instance.state in NOT_STARTED:
            if REL not in rel.relationship._relationship[HIERARCHY]:
                ctx.logger.error(
                    'The Terraform plan node {} is related to the '
                    'node instance {}, which is not in a started '
                    'state. If the Terraform plan is dependent on any '
                    'inputs from node instance {}, '
                    'the plan will fail.'.format(
                        node.id,
                        rel.target_node_instance.id,
                        rel.target_node_instance.id
                    )
                )
            else:
                _start_terraform_instance(sequence, rel)
    sequence.add(
        instance.execute_operation(
            'terraform.plan',
            kwargs=kwargs,
            allow_kwargs_override=True
        )
    )
