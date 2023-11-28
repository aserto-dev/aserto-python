import asyncio
from typing import Dict

import pytest

from aserto.client import AuthorizerOptions, Identity
from aserto.client.authorizer.aio import AuthorizerClient, DecisionTree, IdentityType


@pytest.fixture(scope="session")
def event_loop():
    """Overrides pytest default function scoped event loop"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def authorizer(topaz):
    client = AuthorizerClient(
        identity=Identity(type=IdentityType.IDENTITY_TYPE_NONE),
        options=AuthorizerOptions(
            url=topaz.authorizer.address,
            cert_file_path=topaz.authorizer.ca_cert_path,
        ),
    )

    yield client

    await client.close()


async def make_decision_tree_request(client: AuthorizerClient) -> DecisionTree:
    return await client.decision_tree(
        decisions=["enabled", "allowed"],
        policy_instance_name="todo",
        policy_path_root="todoApp",
    )


async def make_decision_request(client: AuthorizerClient) -> Dict[str, bool]:
    return await client.decisions(
        decisions=["allowed"],
        policy_instance_name="todo",
        policy_path="todoApp.GET.users.__userID",
        resource_context={"id": "USER-ID"},
    )


@pytest.mark.asyncio
async def test_decision_tree_grpc(authorizer: AuthorizerClient) -> None:
    expected = {
        "todoApp.DELETE.todos.__id": {"allowed": False},
        "todoApp.GET.todos": {"allowed": True},
        "todoApp.GET.users.__userID": {"allowed": True},
        "todoApp.POST.todos": {"allowed": False},
        "todoApp.PUT.todos.__id": {"allowed": False},
    }

    result = await make_decision_tree_request(authorizer)

    assert result == expected


@pytest.mark.asyncio
async def test_decision_grpc(authorizer: AuthorizerClient) -> None:
    result = await make_decision_request(authorizer)

    assert result == {
        "allowed": True,
    }
