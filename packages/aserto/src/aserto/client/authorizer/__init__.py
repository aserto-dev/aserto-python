import datetime
import typing

import aserto.authorizer.v2 as authorizer
import aserto.authorizer.v2.api as api
import grpc
import grpc.aio as grpcaio
from aserto.authorizer.v2 import (
    CompileResponse,
    GetPolicyResponse,
    ListPoliciesResponse,
    QueryOptions,
    QueryResponse,
)
from aserto.authorizer.v2.api import IdentityContext, IdentityType

import aserto.client._deadline as timeout
import aserto.client.authorizer.helpers as helpers
import aserto.client.resource_context as res_ctx
from aserto.client.authorizer.helpers import DecisionTree
from aserto.client.identity import Identity
from aserto.client.options import AuthorizerOptions
from aserto.client.resource_context import ResourceContext


class AuthorizerClient:
    def __init__(
        self,
        *,
        tenant_id: typing.Optional[str] = None,
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
        self.client = authorizer.AuthorizerStub(self._channel)

    @property
    def _headers(self) -> typing.Mapping[str, str]:
        return self._options.auth_headers

    @property
    def _metadata(self) -> grpcaio.Metadata:
        return grpcaio.Metadata(*tuple(self._headers.items()))

    def decision_tree(
        self,
        *,
        policy_path_root: str,
        decisions: typing.Sequence[str],
        policy_instance_name: typing.Optional[str] = None,
        policy_instance_label: typing.Optional[str] = None,
        resource_context: typing.Optional[ResourceContext] = None,
        policy_path_separator: typing.Optional[typing.Literal["DOT", "SLASH"]] = None,
        deadline: typing.Optional[typing.Union[datetime.datetime, datetime.timedelta]] = None,
    ) -> DecisionTree:
        options = authorizer.DecisionTreeOptions()
        if policy_path_separator is not None:
            options.path_separator = helpers.policy_path_separator_field(policy_path_separator)

        response = self.client.DecisionTree(
            authorizer.DecisionTreeRequest(
                policy_context=api.PolicyContext(
                    path=policy_path_root,
                    decisions=list(decisions),
                ),
                identity_context=self._identity_context_field,
                resource_context=res_ctx.serialize_resource_context(resource_context or {}),
                options=options,
                policy_instance=api.PolicyInstance(
                    name=policy_instance_name,
                    instance_label=policy_instance_label,
                ),
            ),
            metadata=self._metadata,
            timeout=(
                timeout.monotonic_time_from_deadline(deadline) if deadline is not None else None
            ),
        )

        return helpers.validate_decision_tree(response)

    def decisions(
        self,
        *,
        policy_path: str,
        decisions: typing.Sequence[str],
        policy_instance_name: typing.Optional[str],
        policy_instance_label: typing.Optional[str] = None,
        resource_context: typing.Optional[ResourceContext] = None,
        deadline: typing.Optional[typing.Union[datetime.datetime, datetime.timedelta]] = None,
    ) -> typing.Dict[str, bool]:
        response = self.client.Is(
            authorizer.IsRequest(
                policy_context=api.PolicyContext(
                    path=policy_path,
                    decisions=list(decisions),
                ),
                identity_context=self._identity_context_field,
                resource_context=res_ctx.serialize_resource_context(resource_context or {}),
                policy_instance=api.PolicyInstance(
                    name=policy_instance_name,
                    instance_label=policy_instance_label,
                ),
            ),
            metadata=self._metadata,
            timeout=(
                timeout.monotonic_time_from_deadline(deadline) if deadline is not None else None
            ),
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
        decisions: typing.Sequence[str],
        policy_instance_name: typing.Optional[str],
        policy_instance_label: typing.Optional[str] = None,
        resource_context: typing.Optional[ResourceContext] = None,
        options: typing.Optional[QueryOptions] = None,
        deadline: typing.Optional[typing.Union[datetime.datetime, datetime.timedelta]] = None,
    ) -> QueryResponse:
        response = self.client.Query(
            authorizer.QueryRequest(
                query=query,
                input=input,
                options=options,
                policy_context=api.PolicyContext(
                    path=policy_path,
                    decisions=list(decisions),
                ),
                identity_context=self._identity_context_field,
                resource_context=res_ctx.serialize_resource_context(resource_context or {}),
                policy_instance=api.PolicyInstance(
                    name=policy_instance_name,
                    instance_label=policy_instance_label,
                ),
            ),
            metadata=self._metadata,
            timeout=(
                timeout.monotonic_time_from_deadline(deadline) if deadline is not None else None
            ),
        )

        return response

    def compile(
        self,
        *,
        query: str,
        input: str,
        unknowns: typing.Sequence[str],
        disable_inlining: typing.Sequence[str],
        policy_path: str,
        decisions: typing.Sequence[str],
        policy_instance_name: typing.Optional[str],
        policy_instance_label: typing.Optional[str] = None,
        resource_context: typing.Optional[ResourceContext] = None,
        options: typing.Optional[QueryOptions] = None,
        deadline: typing.Optional[typing.Union[datetime.datetime, datetime.timedelta]] = None,
    ) -> CompileResponse:
        response = self.client.Compile(
            authorizer.CompileRequest(
                query=query,
                input=input,
                unknowns=list(unknowns),
                disable_inlining=list(disable_inlining),
                options=options,
                policy_context=api.PolicyContext(
                    path=policy_path,
                    decisions=list(decisions),
                ),
                identity_context=self._identity_context_field,
                resource_context=res_ctx.serialize_resource_context(resource_context or {}),
                policy_instance=api.PolicyInstance(
                    name=policy_instance_name,
                    instance_label=policy_instance_label,
                ),
            ),
            metadata=self._metadata,
            timeout=(
                timeout.monotonic_time_from_deadline(deadline) if deadline is not None else None
            ),
        )

        return response

    def list_policies(
        self,
        *,
        policy_instance_name: typing.Optional[str],
        policy_instance_label: typing.Optional[str] = None,
        deadline: typing.Optional[typing.Union[datetime.datetime, datetime.timedelta]] = None,
    ) -> ListPoliciesResponse:
        response = self.client.ListPolicies(
            authorizer.ListPoliciesRequest(
                policy_instance=api.PolicyInstance(
                    name=policy_instance_name,
                    instance_label=policy_instance_label,
                ),
            ),
            metadata=self._metadata,
            timeout=(
                timeout.monotonic_time_from_deadline(deadline) if deadline is not None else None
            ),
        )

        return response

    def get_policy(
        self,
        *,
        id: str,
        policy_instance_name: typing.Optional[str],
        policy_instance_label: typing.Optional[str] = None,
        deadline: typing.Optional[typing.Union[datetime.datetime, datetime.timedelta]] = None,
    ) -> GetPolicyResponse:
        response = self.client.GetPolicy(
            authorizer.GetPolicyRequest(
                id=id,
                policy_instance=api.PolicyInstance(
                    name=policy_instance_name,
                    instance_label=policy_instance_label,
                ),
            ),
            metadata=self._metadata,
            timeout=(
                timeout.monotonic_time_from_deadline(deadline) if deadline is not None else None
            ),
        )

        return response

    def close(self) -> None:
        """Closes the gRPC channel"""

        self._channel.close()
