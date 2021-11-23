"""Handle registration and publication of supported goal codes."""

from typing import Sequence

from ..utils.classloader import ClassLoader


class GoalCodeRegistry:
    """Goal code registry."""

    def __init__(self):
        """Initialize a `GoalCodeRegistry` instance."""
        self.goal_codes = []

    def register_controllers(self, *controller_sets):
        """
        Add new controllers.

        Args:
            controller_sets: Mappings of controller to coroutines

        """
        for controlset in controller_sets:
            for key, ctl_cls in controlset.items():
                ctl_cls = ClassLoader.load_class(ctl_cls)
                ctl_inst = ctl_cls(protocol=key)
                goal_codes_to_add = ctl_inst.determine_goal_codes()
                for goal_code in goal_codes_to_add:
                    if goal_code not in self.goal_codes:
                        self.goal_codes.append(goal_code)

    def goal_codes_matching_query(self, query: str) -> Sequence[str]:
        """Return a list of goal codes matching a query string."""
        all_types = self.goal_codes
        result = None

        if query == "*" or query is None:
            result = all_types
        elif query:
            if query.endswith("*"):
                match = query[:-1]
                result = tuple(k for k in all_types if k.startswith(match))
            elif query in all_types:
                result = (query,)
        return result or ()
