from datetime import datetime, timedelta
from typing import Collection, Dict, Optional, Union

from typing_extensions import Literal

from ..._typing import assert_unreachable
from ...authorizer import Authorizer
from ...identity import Identity
from ...resource_context import ResourceContext
from ._protocol import AuthorizerClientProtocol, DecisionTree
from .grpc import AuthorizerGrpcClient
from .rest import AuthorizerRestClient

__all__ = ["AuthorizerClient", "DecisionTree"]


class AuthorizerClient(AuthorizerClientProtocol):
    def __init__(
        self,
        *,
        identity: Identity,
        authorizer: Authorizer,
    ):
        service_type = authorizer.service_type
        if service_type == "gRPC":
            self._client: AuthorizerClientProtocol = AuthorizerGrpcClient(
                identity=identity,
                authorizer=authorizer,
            )
        elif service_type == "REST":
            self._client = AuthorizerRestClient(
                identity=identity,
                authorizer=authorizer,
            )
        else:
            assert_unreachable(service_type)

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
        return await self._client.decision_tree(
            decisions=decisions,
            policy_id=policy_id,
            policy_path_root=policy_path_root,
            resource_context=resource_context,
            policy_path_separator=policy_path_separator,
            deadline=deadline,
        )

    async def decisions(
        self,
        *,
        decisions: Collection[str],
        policy_id: str,
        policy_path: str,
        resource_context: Optional[ResourceContext] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> Dict[str, bool]:
        return await self._client.decisions(
            decisions=decisions,
            policy_id=policy_id,
            policy_path=policy_path,
            resource_context=resource_context,
            deadline=deadline,
        )
