import json
from datetime import datetime, timedelta
from typing import Collection, Dict, Literal, Mapping, Optional, Union
from urllib.parse import urlparse

import google.protobuf.struct_pb2 as structpb
import grpc
import grpc.aio as grpcaio
from aserto.authorizer.v2 import (
    AuthorizerStub,
    CompileRequest,
    CompileResponse,
    DecisionTreeOptions,
    DecisionTreeRequest,
    DecisionTreeResponse,
    GetPolicyRequest,
    GetPolicyResponse,
    IsRequest,
    ListPoliciesRequest,
    ListPoliciesResponse,
    PathSeparator,
    QueryOptions,
    QueryRequest,
    QueryResponse,
)
from aserto.authorizer.v2.api import (
    IdentityContext,
    IdentityType,
    PolicyContext,
    PolicyInstance,
)

from .._deadline import monotonic_time_from_deadline
from .._typing import assert_unreachable
from ..identity import Identity
from ..options import AuthorizerOptions
from ..resource_context import ResourceContext

DecisionTree = Dict[str, Dict[str, bool]]


class AuthorizerClient:
    def __init__(
        self,
        *,
        tenant_id: Optional[str] = None,
        identity: Identity,
        options: AuthorizerOptions,
    ) -> None:
        self._tenant_id = tenant_id
        self._options = options
        self._identity_context_field = IdentityContext(
            identity=identity.value or "",
            type=identity.type,
        )
        self._channel = grpc.secure_channel(
            target=self._options.url,
            credentials=grpc.ssl_channel_credentials(self._options.cert),
        )
        self.client = AuthorizerStub(self._channel)

    @property
    def _headers(self) -> Mapping[str, str]:
        return self._options.auth_headers

    @property
    def _metadata(self) -> grpcaio.Metadata:
        return grpcaio.Metadata(*tuple(self._headers.items()))

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
    def _serialize_resource_context(cls, resource_context: object) -> structpb.Struct:
        try:
            json.dumps(resource_context)
        except ValueError as error:
            if error.args == ("Circular reference detected",):  # type: ignore[misc]
                raise TypeError("Resource context is circularly defined") from error
            else:
                raise TypeError("Invalid resource context") from error

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

    def decision_tree(
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

        response = self.client.DecisionTree(
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

    def decisions(
        self,
        *,
        policy_path: str,
        decisions: Collection[str],
        policy_instance_name: Optional[str],
        policy_instance_label: Optional[str] = None,
        resource_context: Optional[ResourceContext] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> Dict[str, bool]:
        response = self.client.Is(
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
        results = {}
        for decision_object in response.decisions:
            results[decision_object.decision] = getattr(decision_object, "is")

        return results

    def query(
        self,
        *,
        query: str,
        input: str,
        policy_path: str,
        decisions: Collection[str],
        policy_instance_name: Optional[str],
        policy_instance_label: Optional[str] = None,
        resource_context: Optional[ResourceContext] = None,
        options: Optional[QueryOptions] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> QueryResponse:
        response = self.client.Query(
            QueryRequest(
                query=query,
                input=input,
                options=options,
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

        return response

    def compile(
        self,
        *,
        query: str,
        input: str,
        unknowns: Collection[str],
        disable_inlining: Collection[str],
        policy_path: str,
        decisions: Collection[str],
        policy_instance_name: Optional[str],
        policy_instance_label: Optional[str] = None,
        resource_context: Optional[ResourceContext] = None,
        options: Optional[QueryOptions] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> CompileResponse:
        response = self.client.Compile(
            CompileRequest(
                query=query,
                input=input,
                unknowns=list(unknowns),
                disable_inlining=list(disable_inlining),
                options=options,
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

        return response

    def list_policies(
        self,
        *,
        policy_instance_name: Optional[str],
        policy_instance_label: Optional[str] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> ListPoliciesResponse:
        response = self.client.ListPolicies(
            ListPoliciesRequest(
                policy_instance=PolicyInstance(
                    name=policy_instance_name,
                    instance_label=policy_instance_label,
                ),
            ),
            metadata=self._metadata,
            timeout=(monotonic_time_from_deadline(deadline) if deadline is not None else None),
        )

        return response

    def get_policy(
        self,
        *,
        id: str,
        policy_instance_name: Optional[str],
        policy_instance_label: Optional[str] = None,
        deadline: Optional[Union[datetime, timedelta]] = None,
    ) -> GetPolicyResponse:
        response = self.client.GetPolicy(
            GetPolicyRequest(
                id=id,
                policy_instance=PolicyInstance(
                    name=policy_instance_name,
                    instance_label=policy_instance_label,
                ),
            ),
            metadata=self._metadata,
            timeout=(monotonic_time_from_deadline(deadline) if deadline is not None else None),
        )

        return response

    def close(self) -> None:
        """Closes the gRPC channel"""

        self._channel.close()
