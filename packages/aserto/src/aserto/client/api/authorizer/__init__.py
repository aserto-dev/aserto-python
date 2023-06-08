from datetime import datetime, timedelta
from typing import Collection, Dict, Optional, Union

from typing_extensions import Literal

from ..._typing import assert_unreachable
from ...options import AuthorizerOptions
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
        options: AuthorizerOptions,
    ):
        service_type = options.service_type
        if service_type == "gRPC":
            self._client: AuthorizerClientProtocol = AuthorizerGrpcClient(
                identity=identity,
                options=options,
            )
        elif service_type == "REST":
            self._client = AuthorizerRestClient(
                identity=identity,
                options=options,
            )
        else:
            assert_unreachable(service_type)

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
        return await self._client.decision_tree(
            policy_path_root=policy_path_root,
            decisions=decisions,
            policy_instance_name=policy_instance_name,
            policy_instance_label=policy_instance_label,
            resource_context=resource_context,
            policy_path_separator=policy_path_separator,
            deadline=deadline,
        )

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
        return await self._client.decisions(
            policy_path=policy_path,
            decisions=decisions,
            policy_instance_name=policy_instance_name,
            policy_instance_label=policy_instance_label,
            resource_context=resource_context,
            deadline=deadline,
        )
