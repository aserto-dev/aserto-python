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
        decisions: Collection[str],
        policy_id: str,
        policy_path_root: str,
        resource_context: Optional[ResourceContext] = None,
        policy_path_separator: Optional[Literal["DOT", "SLASH"]] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> DecisionTree:
        ...

    async def decisions(
        self,
        *,
        decisions: Collection[str],
        policy_id: str,
        policy_path: str,
        resource_context: Optional[ResourceContext] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> Dict[str, bool]:
        ...
