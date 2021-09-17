from mock import MagicMock
from unittest import TestCase
from cloudify.mocks import MockContext
from cloudify.state import current_ctx

from .. import workflows


class TFWorkflowTests(TestCase):

    @staticmethod
    def _mock_node_context():
        context = MagicMock()
        context.id = 'foo'
        return context

    @staticmethod
    def _mock_instance_context():
        context = MagicMock()
        relationship = MagicMock()
        target_node_instance = MagicMock()
        target_node_instance.state = 'uninitialized'
        relationship.target_node_instance = target_node_instance
        relationship.relationship = MagicMock(
            _relationship={
                workflows.HIERARCHY: [
                    'cloudify.nodes.Root',
                    workflows.REL
                ]
            }
        )
        context.relationships = [relationship]
        return context

    @staticmethod
    def _mock_sequence():
        sequence = MagicMock()
        sequence.add.return_value = None
        return sequence

    def test_plan_module_instance(self):
        ctx = MockContext()
        current_ctx.set(ctx)
        node = self._mock_node_context()
        instance = self._mock_instance_context()
        sequence = self._mock_sequence()
        workflows._plan_module_instance(ctx, node, instance, sequence, {})
        assert sequence.add.call_count == 4
