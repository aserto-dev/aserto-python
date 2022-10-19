# TODO: Test thrown exceptions
from typing import Dict

import pytest
import google.protobuf.struct_pb2 as structpb
from aserto.authorizer.v2 import (
    Decision,
    DecisionTreeResponse,
    IsResponse,
)
from typing_extensions import Literal

from aserto.client import AuthorizerOptions, Identity
from aserto.client.api.authorizer import AuthorizerClient, DecisionTree

from .mock import mock_grpc_request, mock_rest_request


def create_client(service_type: Literal["gRPC", "REST"]) -> AuthorizerClient:
    return AuthorizerClient(
        identity=Identity(type="NONE"),
        options=AuthorizerOptions(
            url="https://aserto.test",
            api_key="API-KEY",
            tenant_id="TENANT-ID",
            service_type=service_type,
        ),
    )


async def make_decision_tree_request(client: AuthorizerClient) -> DecisionTree:
    return await client.decision_tree(
        decisions=["enabled", "allowed"],
        policy_name="POLICY-NAME",
        policy_path_root="policy_root",
    )


async def make_decision_request(client: AuthorizerClient) -> Dict[str, bool]:
    return await client.decisions(
        decisions=["visible", "enabled", "allowed"],
        policy_name="POLICY-NAME",
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


@pytest.mark.skip(reason="mock doesn't work with grpcio.aio")
@pytest.mark.asyncio
async def test_decision_tree_grpc() -> None:
    client = create_client(service_type="gRPC")

    authorizer_response = DecisionTreeResponse(
        path_root="policy_root",
        path=structpb.Struct(
            fields={
                "GET/user/__id": structpb.Value(
                    struct_value=structpb.Struct(
                        fields={
                            "enabled": structpb.Value(bool_value=True),
                            "allowed": structpb.Value(bool_value=False),
                        },
                    ),
                ),
                "PUT/user": structpb.Value(
                    struct_value=structpb.Struct(
                        fields={
                            "enabled": structpb.Value(bool_value=True),
                            "allowed": structpb.Value(bool_value=False),
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


@pytest.mark.skip(reason="mock doesn't work with grpcio.aio")
@pytest.mark.asyncio
async def test_decision_grpc() -> None:
    client = create_client(service_type="gRPC")

    expected = [
        Decision(decision="visible"),
        Decision(decision="enabled"),
        Decision(decision="allowed"),
    ]
    setattr(expected[0], "is", True)
    setattr(expected[1], "is", True)
    setattr(expected[2], "is", False)
    authorizer_response = IsResponse(decisions=expected)

    with mock_grpc_request(authorizer_response):
        result = await make_decision_request(client)

    assert result == {
        "visible": True,
        "enabled": True,
        "allowed": False,
    }
