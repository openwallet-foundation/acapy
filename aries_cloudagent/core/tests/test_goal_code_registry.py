from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ...protocols.issue_credential.v1_0.message_types import CONTROLLERS

from ..goal_code_registry import GoalCodeRegistry


class TestGoalCodeRegistry(AsyncTestCase):
    test_goal_code_queries = "*"
    test_goal_code_queries_fail = "aries.fake.*"

    def setUp(self):
        self.registry = GoalCodeRegistry()

    def test_goal_codes(self):
        self.registry.register_controllers(CONTROLLERS)
        matches = self.registry.goal_codes_matching_query(self.test_goal_code_queries)
        assert tuple(matches) == ("aries.vc", "aries.vc.issue")
        matches = self.registry.goal_codes_matching_query(
            self.test_goal_code_queries_fail
        )
        assert tuple(matches) == ()
