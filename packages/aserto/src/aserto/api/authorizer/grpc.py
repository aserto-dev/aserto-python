import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import AsyncGenerator, Collection, Dict, Mapping, Optional, Union, cast
from urllib.parse import urlparse

from aserto_authorizer_grpc import Proto
from aserto_authorizer_grpc.aserto.api.v1 import IdentityContext, IdentityType
from aserto_authorizer_grpc.aserto.api.v1 import PolicyContext as PolicyContextField
from aserto_authorizer_grpc.aserto.authorizer.authorizer.v1 import (
    AuthorizerStub,
    DecisionTreeOptions,
    DecisionTreeResponse,
    PathSeparator,
)
from grpclib.client import Channel
from grpclib.exceptions import StreamTerminatedError
from typing_extensions import Literal

from ..._deadline import monotonic_time_from_deadline
from ..._typing import assert_unreachable
from ...authorizer import Authorizer
from ...identity import Identity
from ...resource_context import ResourceContext
from ._protocol import AuthorizerClientProtocol, DecisionTree


class AuthorizerGrpcClient(AuthorizerClientProtocol):
    def __init__(
        self,
        *,
        tenant_id: Optional[str] = None,
        identity: Identity,
        authorizer: Authorizer,
    ):
        self._tenant_id = tenant_id
        self._authorizer = authorizer
        self._identity_context_field = IdentityContext(
            identity=identity.identity_field or "",
            type=cast(IdentityType, IdentityType.from_string(identity.type_field)),
        )

    @property
    def _headers(self) -> Mapping[str, str]:
        return self._authorizer.auth_headers

    @asynccontextmanager  # type: ignore[misc]
    async def _authorizer_client(self, deadline: Optional[Union[datetime, timedelta]]) -> AsyncGenerator[AuthorizerStub, None]:  # type: ignore[misc]
        result = urlparse(self._authorizer.url)
        channel = Channel(
            host=result.hostname,
            port=result.port,
            ssl=self._authorizer.ssl_context or True,
        )

        async with channel as channel:
            yield AuthorizerStub(
                channel,
                metadata=self._headers,
                timeout=(monotonic_time_from_deadline(deadline) if deadline is not None else None),
            )

    @staticmethod
    def _policy_path_separator_field(
        policy_path_separator: Literal["DOT", "SLASH"]
    ) -> PathSeparator:
        if policy_path_separator == "DOT":
            return PathSeparator.PATH_SEPARATOR_DOT
        elif policy_path_separator == "SLASH":
            return PathSeparator.PATH_SEPARATOR_SLASH
        else:
            assert_unreachable(policy_path_separator)

    @classmethod
    def _serialize_resource_context(cls, resource_context: object) -> Proto.Struct:
        try:
            json.dumps(resource_context)
        except ValueError as error:
            if error.args == ("Circular reference detected",):  # type: ignore[misc]
                raise TypeError("Resource context is circularly defined")
            else:
                raise TypeError("Invalid resource context")

        proto_value = cls._serialize_resource_context_value(resource_context)
        return proto_value.struct_value

    @classmethod
    def _serialize_resource_context_value(cls, resource_value: object) -> Proto.Value:
        # `Mapping` is a subclass of `Collection` so this check must come first
        if isinstance(resource_value, Mapping):
            struct_value = Proto.Struct()
            for key, value in resource_value.items():
                struct_value.fields[key] = cls._serialize_resource_context_value(value)
            return Proto.Value(struct_value=struct_value)
        # `str` is a subclass of `Collection` so this check must come first
        elif isinstance(resource_value, str):
            return Proto.Value(string_value=resource_value)
        elif isinstance(resource_value, Collection):
            list_value = Proto.ListValue()
            for value in resource_value:
                list_value.values.append(cls._serialize_resource_context_value(value))
            return Proto.Value(list_value=list_value)
        # `bool` is subclass of `int` so this check must come first
        elif isinstance(resource_value, bool):
            return Proto.Value(bool_value=resource_value)
        elif isinstance(resource_value, (int, float)):
            return Proto.Value(number_value=float(resource_value))
        elif resource_value is None:
            return Proto.Value(null_value=Proto.NullValue.NULL_VALUE)
        else:
            raise TypeError("Invalid resource context")

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
        options = DecisionTreeOptions()
        if policy_path_separator is not None:
            options.path_separator = self._policy_path_separator_field(policy_path_separator)

        try:
            async with self._authorizer_client(deadline=deadline) as client:
                response = await client.decision_tree(
                    policy_context=PolicyContextField(
                        id=policy_id,
                        path=policy_path_root,
                        decisions=list(decisions),
                    ),
                    identity_context=self._identity_context_field,
                    resource_context=self._serialize_resource_context(resource_context or {}),
                    options=options,
                )
        except (OSError, StreamTerminatedError) as error:
            raise ConnectionError(*error.args) from error  # type: ignore[misc]

        return self._validate_decision_tree(response)

    @staticmethod
    def _validate_decision_tree(response: DecisionTreeResponse) -> DecisionTree:
        error = TypeError("Received unexpected response data")

        decision_tree: DecisionTree = {}

        for path, decisions in response.path.fields.items():
            if decisions._group_current.get("kind") != "struct_value":
                raise error

            for name, decision in decisions.struct_value.fields.items():
                if decision._group_current.get("kind") != "bool_value":
                    raise error

                decision_tree.setdefault(path, {})[name] = decision.bool_value

        return decision_tree

    async def decisions(
        self,
        *,
        decisions: Collection[str],
        policy_id: str,
        policy_path: str,
        resource_context: Optional[ResourceContext] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> Dict[str, bool]:
        try:
            async with self._authorizer_client(deadline=deadline) as client:
                response = await client.is_(
                    policy_context=PolicyContextField(
                        id=policy_id,
                        path=policy_path,
                        decisions=list(decisions),
                    ),
                    identity_context=self._identity_context_field,
                    resource_context=self._serialize_resource_context(resource_context or {}),
                )
        except (OSError, StreamTerminatedError) as error:
            raise ConnectionError(*error.args) from error  # type: ignore[misc]

        results = {}
        for decision_object in response.decisions:
            results[decision_object.decision] = decision_object.is_

        return results
