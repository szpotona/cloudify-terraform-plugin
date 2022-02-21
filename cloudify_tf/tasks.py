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

import os
import sys

from cloudify.decorators import operation
from cloudify import ctx as ctx_from_imports
from cloudify.exceptions import NonRecoverableError, RecoverableError
from cloudify.utils import exception_to_error_cause
from cloudify_common_sdk.utils import get_node_instance_dir, install_binary

from . import utils
from ._compat import mkdir_p
from .decorators import (
    with_terraform,
    skip_if_existing)
from .terraform import Terraform


@operation
@with_terraform
def setup_tflint(ctx, tf, **_):
    tf.tflint.validate()
    ctx.instance.runtime_properties['tflint_config'] = \
        tf.tflint.export_config()


@operation
@with_terraform
def apply(ctx, tf, force=False, **kwargs):
    """
    Execute `terraform apply`.
    """
    if ctx.workflow_id == 'update':
        resource_config = utils.get_resource_config()
        source = resource_config.get('source')
        source_path = resource_config.get('source_path')
        _reload_template(ctx,
                         tf,
                         source,
                         source_path,
                         **kwargs)
    else:
        old_plan = ctx.instance.runtime_properties.get('plan')
        _apply(tf, old_plan, force)
    ctx.instance.runtime_properties['tflint_config'] = \
        tf.tflint.export_config()


class FailedPlanValidation(NonRecoverableError):
    pass


def compare_plan_results(new_plan, old_plan, force):
    if old_plan != new_plan:
        ctx_from_imports.logger.debug('New plan and old plan diff {}'.format(
            set(old_plan) ^ set(new_plan)))
        raise FailedPlanValidation(
            'The new plan differs from the old plan. '
            'Please Rerun plan workflow before executing apply worfklow.')


def _apply(tf, old_plan=None, force=False):
    try:
        tf.init()
        if old_plan and not force:
            new_plan = tf.plan_and_show()
            compare_plan_results(new_plan, old_plan, force)
        if not force:
            tf.check_tflint()
        tf.apply()
        tf_state = tf.show()
        tf_output = tf.output()
    except FailedPlanValidation:
        raise
    except FileNotFoundError as ex:
        _, _, tb = sys.exc_info()
        raise RecoverableError(
            "Failed applying due to syncthing error",
            causes=[exception_to_error_cause(ex, tb)])
    except Exception as ex:
        _, _, tb = sys.exc_info()
        raise NonRecoverableError(
            "Failed applying",
            causes=[exception_to_error_cause(ex, tb)])
    utils.refresh_resources_properties(tf_state, tf_output)


def _plan(tf):
    try:
        tf.init()
        tf.state_pull()
        return tf.plan_and_show()
    except Exception as ex:
        _, _, tb = sys.exc_info()
        raise NonRecoverableError(
            "Failed executing terraform plan. "
            "If you ran plan prior to installation, verify that the "
            "cloudify.nodes.terraform.Module node template is not dependent "
            "on any uninstalled nodes. Plan is intended for use with "
            "deployment update.",
            causes=[exception_to_error_cause(ex, tb)])


def _handle_new_vars(runtime_props,
                     tf,
                     variables=None,
                     environment_variables=None,
                     update=False):

    if variables:
        tf.variables = variables
        if update:
            runtime_props['resource_config']['variables'] = tf.variables
    if environment_variables:
        tf.env = environment_variables
        if update:
            runtime_props['resource_config']['environment_variables'] = tf.env


@operation
@with_terraform
def plan(ctx,
         tf,
         source=None,
         source_path=None,
         variables=None,
         environment_variables=None,
         **_):
    """
    Execute `terraform plan`.
    """
    _handle_new_vars(ctx.instance.runtime_properties,
                     tf,
                     variables,
                     environment_variables)

    if source or source_path:
        with utils.update_terraform_source(source, source_path) as tf_src:
            tf = Terraform.from_ctx(ctx, tf_src)
            result = _plan(tf)
    else:
        result = _plan(tf)
    ctx.instance.runtime_properties['plan'] = result


@operation
@with_terraform
def check_status(ctx, tf, **_):
    """
    Execute `terraform state pull`.
    """
    status_problems = tf.plan_and_show_state()
    if status_problems:
        ctx.abort_operation(
            'The cloudify.nodes.terraform.Module node template {} '
            'has status problems with these nodes: {}'.format(
                ctx.instance.id, status_problems))
    else:
        ctx.returns(
            'The cloudify.nodes.terraform.Module node template {} '
            'has no status problems.'.format(ctx.instance.id))


@operation
@with_terraform
def state_pull(ctx, tf, **_):
    """
    Execute `terraform state pull`.
    """
    if ctx.operation.name == 'cloudify.interfaces.lifecycle.pull':
        raise NonRecoverableError(
            'The operation cloudify.interfaces.lifecycle.pull is not a '
            'valid operation. Please use terraform.pull.')
    _state_pull(tf)


def _state_pull(tf):
    try:
        tf.refresh()
        tf_state = tf.state_pull()
        plan_json = tf.plan_and_show()
        tf_output = tf.output()
    except Exception as ex:
        _, _, tb = sys.exc_info()
        raise RecoverableError(
            "Failed pulling state",
            causes=[exception_to_error_cause(ex, tb)])
    utils.refresh_resources_properties(tf_state, tf_output)
    utils.refresh_resources_drifts_properties(plan_json)


@operation
@with_terraform
def destroy(ctx, tf, **_):
    """
    Execute `terraform destroy`.
    """
    _destroy(tf)
    try:
        _state_pull(tf)
    except Exception as e:
        ctx.logger.error('State pull after destroy failed: {}'.format(str(e)))
    for runtime_property in ['terraform_source',
                             'last_source_location',
                             'resource_config']:
        ctx.instance.runtime_properties.pop(runtime_property, None)
    tf.tflint.uninstall_binary()


def _destroy(tf):
    try:
        tf.plan()
        tf.destroy()
    except Exception as ex:
        _, _, tb = sys.exc_info()
        raise NonRecoverableError(
            "Failed destroying",
            causes=[exception_to_error_cause(ex, tb)])


def _reload_template(ctx,
                     tf,
                     source=None,
                     source_path=None,
                     variables=None,
                     environment_variables=None,
                     destroy_previous=False,
                     force=False,
                     **_):

    _handle_new_vars(ctx.instance.runtime_properties,
                     tf,
                     variables,
                     environment_variables,
                     update=True)
    if not any([source, source_path, variables, environment_variables]):
        raise NonRecoverableError(
            "A new value for one of the following parameters must be provided:"
            " source, source_path, variables, environment_variables.")

    resource_config = utils.get_resource_config()
    if not source:
        source = resource_config.get('source')
    if not source_path:
        source_path = resource_config.get('source_path')

    source = utils.handle_previous_source_format(source)
    if destroy_previous:
        destroy(tf=tf, ctx=ctx)
    with utils.update_terraform_source(source,
                                       source_path) as terraform_source:
        new_tf = Terraform.from_ctx(ctx, terraform_source)
        old_plan = ctx.instance.runtime_properties.get('plan')
        _apply(new_tf, old_plan, force)
        ctx.instance.runtime_properties['resource_config'] = \
            utils.get_resource_config()
        _state_pull(new_tf)


@operation
@with_terraform
def reload_template(ctx,
                    tf,
                    source=None,
                    source_path=None,
                    destroy_previous=False,
                    variables=None,
                    environment_variables=None,
                    force=False,
                    **kwargs):
    """
    Terraform reload plan given new location as input
    """

    _reload_template(ctx,
                     tf,
                     source,
                     source_path,
                     variables,
                     environment_variables,
                     destroy_previous,
                     force,
                     **kwargs)


@operation
@skip_if_existing
def install(ctx, **_):
    installation_dir = get_node_instance_dir()
    executable_path = utils.get_executable_path()
    plugins = utils.get_plugins()
    plugins_dir = utils.get_plugins_dir()
    installation_source = utils.get_installation_source()

    if os.path.isfile(executable_path):
        ctx.logger.info(
            'Terraform executable already found at {path}; '
            'skipping installation of executable'.format(
                path=executable_path))
    else:
        ctx.logger.warn('You are requesting to write a new file to {loc}. '
                        'If you do not have sufficient permissions, that '
                        'installation will fail.'.format(
                            loc=executable_path))
        install_binary(
            installation_dir, executable_path, installation_source, 'tf.zip')

    # store the values in the runtime for safe keeping -> validation
    ctx.instance.runtime_properties['executable_path'] = executable_path
    utils.handle_plugins(plugins, plugins_dir, installation_dir)


@operation
@skip_if_existing
def uninstall(ctx, **_):
    terraform_config = utils.get_terraform_config()
    resource_config = utils.get_resource_config()
    exc_path = terraform_config.get('executable_path', '')
    system_exc = resource_config.get('use_existing_resource')

    if os.path.isfile(exc_path):
        if system_exc:
            ctx.logger.info(
                'Not removing Terraform installation at {loc} as'
                'it was provided externally'.format(loc=exc_path))
        else:
            ctx.logger.info('Removing executable: {path}'.format(
                path=exc_path))
            os.remove(exc_path)

    for property_name, property_desc in [
        ('plugins_dir',
         'plugins directory'),
        ('storage_path',
         'storage_directory')]:
        dir_to_delete = terraform_config.get(property_name, None)
        if dir_to_delete:
            utils.remove_dir(dir_to_delete, property_desc)


@operation
def set_directory_config(ctx, **_):
    exc_path = utils.get_executable_path(target=True)
    plugins_dir = utils.get_plugins_dir(target=True)
    storage_path = utils.get_storage_path(target=True)
    deployment_terraform_dir = os.path.join(storage_path,
                                            '.terraform')
    resource_node_instance_dir = get_node_instance_dir(source=True)
    if not os.path.exists(resource_node_instance_dir):
        mkdir_p(resource_node_instance_dir)
    resource_terraform_dir = os.path.join(resource_node_instance_dir,
                                          '.terraform')
    resource_plugins_dir = plugins_dir.replace(
        ctx.target.instance.id, ctx.source.instance.id)
    resource_storage_dir = storage_path.replace(
        ctx.target.instance.id, ctx.source.instance.id)

    if utils.is_using_existing(target=True):
        # We are going to use a TF binary at another location.
        # However, we still need to make sure that this directory exists.
        # Otherwise TF will complain. It does not create it.
        # In our other scenario, a symlink is created.
        mkdir_p(resource_terraform_dir)
    else:
        # We don't want to put all the plugins for all the node instances in a
        # deployment multiple times on the system. So here,
        # we already stored it once on the file system, and now we create
        # symlinks so other deployments can use it.
        # TODO: Possibly put this in "apply" and remove the relationship in
        # the future.

        ctx.logger.debug('Creating link {src} {dst}'.format(
            src=deployment_terraform_dir, dst=resource_terraform_dir))
        try:
            os.symlink(deployment_terraform_dir, resource_terraform_dir)
        except OSError:
            ctx.logger.warn('Unable to link {src} {dst}'.format(
                src=deployment_terraform_dir, dst=resource_terraform_dir))
    ctx.logger.debug("setting executable_path to {path}".format(
        path=exc_path))
    ctx.logger.debug("setting plugins_dir to {dir}".format(
        dir=resource_plugins_dir))
    ctx.logger.debug("setting storage_path to {dir}".format(
        dir=resource_storage_dir))
    ctx.source.instance.runtime_properties['executable_path'] = \
        exc_path
    ctx.source.instance.runtime_properties['plugins_dir'] = \
        resource_plugins_dir
    ctx.source.instance.runtime_properties['storage_path'] = \
        resource_storage_dir
