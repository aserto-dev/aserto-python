# TODO: Test thrown exceptions
from typing import Dict

import pytest
from aserto_authorizer_grpc import Proto
from aserto_authorizer_grpc.aserto.authorizer.authorizer.v1 import (
    Decision,
    DecisionTreeResponse,
    IsResponse,
)
from typing_extensions import Literal

from aserto import HostedAuthorizer, Identity
from aserto.api.authorizer import AuthorizerClient, DecisionTree

from .mock import mock_grpc_request, mock_rest_request


def create_client(service_type: Literal["gRPC", "REST"]) -> AuthorizerClient:
    return AuthorizerClient(
        identity=Identity(type="NONE"),
        authorizer=HostedAuthorizer(
            url="https://aserto.test",
            api_key="API-KEY",
            tenant_id="TENANT-ID",
            service_type=service_type,
        ),
    )


async def make_decision_tree_request(client: AuthorizerClient) -> DecisionTree:
    return await client.decision_tree(
        decisions=["enabled", "allowed"],
        policy_id="POLICY-ID",
        policy_path_root="policy_root",
    )


async def make_decision_request(client: AuthorizerClient) -> Dict[str, bool]:
    return await client.decisions(
        decisions=["visible", "enabled", "allowed"],
        policy_id="POLICY-ID",
        policy_path="policy_root.GET.user__id",
        resource_context={"id": "USER-ID"},
    )


@pytest.mark.asyncio
async def test_decision_tree_rest() -> None:
    client = create_client(service_type="REST")

    authorizer_response = {
        "path": {
            "policy_root.GET.user__id": {
                "enabled": True,
                "allowed": False,
            },
            "policy_root.PUT.user": {
                "enabled": True,
                "allowed": False,
            },
        },
    }

    with mock_rest_request(authorizer_response):
        result = await make_decision_tree_request(client)

    assert result == authorizer_response["path"]


@pytest.mark.asyncio
async def test_decision_tree_grpc() -> None:
    client = create_client(service_type="gRPC")

    authorizer_response = DecisionTreeResponse(
        path_root="policy_root",
        path=Proto.Struct(
            fields={
                "GET/user/__id": Proto.Value(
                    struct_value=Proto.Struct(
                        fields={
                            "enabled": Proto.Value(bool_value=True),
                            "allowed": Proto.Value(bool_value=False),
                        },
                    ),
                ),
                "PUT/user": Proto.Value(
                    struct_value=Proto.Struct(
                        fields={
                            "enabled": Proto.Value(bool_value=True),
                            "allowed": Proto.Value(bool_value=False),
                        },
                    ),
                ),
            },
        ),
    )

    with mock_grpc_request(authorizer_response):
        result = await make_decision_tree_request(client)

    assert result == {
        "GET/user/__id": {"enabled": True, "allowed": False},
        "PUT/user": {"enabled": True, "allowed": False},
    }


@pytest.mark.asyncio
async def test_decision_rest() -> None:
    client = create_client(service_type="REST")

    authorizer_response = {
        "decisions": [
            {
                "decision": "visible",
                "is": True,
            },
            {
                "decision": "enabled",
                "is": True,
            },
            {
                "decision": "allowed",
                "is": False,
            },
        ],
    }

    with mock_rest_request(authorizer_response):
        result = await make_decision_request(client)

    assert result == {
        "visible": True,
        "enabled": True,
        "allowed": False,
    }


@pytest.mark.asyncio
async def test_decision_grpc() -> None:
    client = create_client(service_type="gRPC")

    authorizer_response = IsResponse(
        [
            Decision(decision="visible", is_=True),
            Decision(decision="enabled", is_=True),
            Decision(decision="allowed", is_=False),
        ]
    )

    with mock_grpc_request(authorizer_response):
        result = await make_decision_request(client)

    assert result == {
        "visible": True,
        "enabled": True,
        "allowed": False,
    }
