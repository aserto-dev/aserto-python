import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import AsyncGenerator, Collection, Dict, Mapping, Optional, Union
from urllib.parse import urlparse

import google.protobuf.struct_pb2 as structpb
from aserto.authorizer.v2.api import (
    IdentityContext,
    PolicyContext,
    IdentityType,
    PolicyInstance,
)
from aserto.authorizer.v2 import (
    AuthorizerStub,
    DecisionTreeOptions,
    DecisionTreeRequest,
    DecisionTreeResponse,
    PathSeparator,
    IsRequest,
)

import grpc
import grpc.aio as grpcaio
from typing_extensions import Literal

from ..._deadline import monotonic_time_from_deadline
from ..._typing import assert_unreachable
from ...options import AuthorizerOptions
from ...identity import Identity
from ...resource_context import ResourceContext
from ._protocol import AuthorizerClientProtocol, DecisionTree


class AuthorizerGrpcClient(AuthorizerClientProtocol):
    def __init__(
        self,
        *,
        tenant_id: Optional[str] = None,
        identity: Identity,
        options: AuthorizerOptions,
    ):
        self._tenant_id = tenant_id
        self._options = options
        self._identity_context_field = IdentityContext(
            identity=identity.identity_field or "",
            type=IdentityType.Value(identity.type_field),
        )

    @property
    def _headers(self) -> Mapping[str, str]:
        return self._options.auth_headers

    @property
    def _metadata(self) -> grpcaio.Metadata:
        return grpcaio.Metadata(*tuple(self._headers.items()))

    @asynccontextmanager  # type: ignore[misc]
    async def _authorizer_client(self, deadline: Optional[Union[datetime, timedelta]]) -> AsyncGenerator[AuthorizerStub, None]:  # type: ignore[misc]
        result = urlparse(self._options.url)
        channel = grpcaio.secure_channel(
            target=f"{result.hostname}:{result.port}",
            credentials=grpc.ssl_channel_credentials(self._options.cert),
        )

        async with channel as channel:
            yield AuthorizerStub(channel)

    @staticmethod
    def _policy_path_separator_field(
        policy_path_separator: Literal["DOT", "SLASH"]
    ) -> PathSeparator.ValueType:
        if policy_path_separator == "DOT":
            return PathSeparator.PATH_SEPARATOR_DOT
        elif policy_path_separator == "SLASH":
            return PathSeparator.PATH_SEPARATOR_SLASH
        else:
            assert_unreachable(policy_path_separator)

    @classmethod
    def _serialize_resource_context(cls, resource_context: object) -> structpb.Struct:
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
    def _serialize_resource_context_value(cls, resource_value: object) -> structpb.Value:
        # `Mapping` is a subclass of `Collection` so this check must come first
        if isinstance(resource_value, Mapping):
            struct_value = structpb.Struct()
            struct_value.update(resource_value)
            return structpb.Value(struct_value=struct_value)
        # `str` is a subclass of `Collection` so this check must come first
        elif isinstance(resource_value, str):
            return structpb.Value(string_value=resource_value)
        elif isinstance(resource_value, Collection):
            list_value = structpb.ListValue()
            for value in resource_value:
                list_value.append(cls._serialize_resource_context_value(value))
            return structpb.Value(list_value=list_value)
        # `bool` is subclass of `int` so this check must come first
        elif isinstance(resource_value, bool):
            return structpb.Value(bool_value=resource_value)
        elif isinstance(resource_value, (int, float)):
            return structpb.Value(number_value=float(resource_value))
        elif resource_value is None:
            return structpb.Value(null_value=structpb.NullValue.NULL_VALUE)
        else:
            raise TypeError("Invalid resource context")

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
        options = DecisionTreeOptions()
        if policy_path_separator is not None:
            options.path_separator = self._policy_path_separator_field(policy_path_separator)

        try:
            async with self._authorizer_client(deadline=deadline) as client:
                response = await client.DecisionTree(
                    DecisionTreeRequest(
                        policy_context=PolicyContext(
                            path=policy_path_root,
                            decisions=list(decisions),
                        ),
                        identity_context=self._identity_context_field,
                        resource_context=self._serialize_resource_context(resource_context or {}),
                        options=options,
                        policy_instance=PolicyInstance(
                            name=policy_instance_name,
                            instance_label=policy_instance_label,
                        ),
                    ),
                    metadata=self._metadata,
                    timeout=(monotonic_time_from_deadline(deadline) if deadline is not None else None),
                )
        except (OSError, grpc.RpcError) as error:
            raise ConnectionError(*error.args) from error  # type: ignore[misc]

        return self._validate_decision_tree(response)

    @staticmethod
    def _validate_decision_tree(response: DecisionTreeResponse) -> DecisionTree:
        error = TypeError("Received unexpected response data")

        decision_tree: DecisionTree = {}

        for path, decisions in response.path.fields.items():
            if decisions.WhichOneof("kind") != "struct_value":
                raise error

            for name, decision in decisions.struct_value.fields.items():
                if decision.WhichOneof("kind") != "bool_value":
                    raise error

                decision_tree.setdefault(path, {})[name] = decision.bool_value

        return decision_tree

    async def decisions(
        self,
        *,
        policy_path: str,
        decisions: Collection[str],
        policy_instance_name: Optional[str],
        policy_instance_label: Optional[str] = None,
        resource_context: Optional[ResourceContext] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> Dict[str, bool]:
        try:
            async with self._authorizer_client(deadline=deadline) as client:
                response = await client.Is(
                    IsRequest(
                        policy_context=PolicyContext(
                            path=policy_path,
                            decisions=list(decisions),
                        ),
                        identity_context=self._identity_context_field,
                        resource_context=self._serialize_resource_context(resource_context or {}),
                        policy_instance=PolicyInstance(
                            name=policy_instance_name,
                            instance_label=policy_instance_label,
                        ),
                    ),
                    metadata=self._metadata,
                    timeout=(monotonic_time_from_deadline(deadline) if deadline is not None else None),
                )
        except (OSError, grpc.RpcError) as error:
            raise ConnectionError(*error.args) from error  # type: ignore[misc]

        results = {}
        for decision_object in response.decisions:
            results[decision_object.decision] = getattr(decision_object, "is")

        return results
