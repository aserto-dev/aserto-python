from datetime import datetime, timedelta
from typing import Collection, Dict, Optional, Union

from typing_extensions import Literal, Protocol

from ...resource_context import ResourceContext

__all__ = [
    "AuthorizerClientProtocol",
    "DecisionTree",
]


DecisionTree = Dict[str, Dict[str, bool]]


class AuthorizerClientProtocol(Protocol):
    async def decision_tree(
        self,
        *,
        policy_path_root: str,
        decisions: Collection[str],
        policy_instance_name: Optional[str] = None,
        policy_instance_label: Optional[str] = None,
        resource_context: Optional[ResourceContext] = None,
        policy_path_separator: Optional[Literal["DOT", "SLASH"]] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> DecisionTree:
        ...

    async def decisions(
        self,
        *,
        policy_path: str,
        decisions: Collection[str],
        policy_instance_name: Optional[str] = None,
        policy_instance_label: Optional[str] = None,
        resource_context: Optional[ResourceContext] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> Dict[str, bool]:
        ...
