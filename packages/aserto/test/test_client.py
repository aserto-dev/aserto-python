from typing import Dict

import google.protobuf.struct_pb2 as structpb
import pytest
from aserto.authorizer.v2 import Decision, DecisionTreeResponse, IsResponse

from aserto.client import AuthorizerOptions, Identity
from aserto.client.authorizer import AuthorizerClient, DecisionTree, IdentityType


@pytest.fixture(scope="module")
def authorizer(topaz):
    client = AuthorizerClient(
        identity=Identity(type=IdentityType.IDENTITY_TYPE_NONE),
        options=AuthorizerOptions(
            url=topaz.authorizer.address,
            cert_file_path=topaz.authorizer.ca_cert_path,
        ),
    )

    yield client

    client.close()


def make_decision_tree_request(client: AuthorizerClient) -> DecisionTree:
    return client.decision_tree(
        decisions=["enabled", "allowed"],
        policy_instance_name="todo",
        policy_path_root="todoApp",
    )


def make_decision_request(client: AuthorizerClient) -> Dict[str, bool]:
    return client.decisions(
        decisions=["allowed"],
        policy_instance_name="todo",
        policy_path="todoApp.GET.users.__userID",
        resource_context={"id": "USER-ID"},
    )


def test_decision_tree_grpc(authorizer) -> None:
    expected = {
        "todoApp.DELETE.todos.__id": {"allowed": False},
        "todoApp.GET.todos": {"allowed": True},
        "todoApp.GET.users.__userID": {"allowed": True},
        "todoApp.POST.todos": {"allowed": False},
        "todoApp.PUT.todos.__id": {"allowed": False},
    }

    result = make_decision_tree_request(authorizer)

    assert result == expected


def test_decision_grpc(authorizer) -> None:
    result = make_decision_request(authorizer)

    assert result == {
        "allowed": True,
    }
