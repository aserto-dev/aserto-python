import asyncio

import grpc.aio as grpc
import pytest
from grpc import RpcError

from aserto.client.directory.v2.aio import (
    Directory,
    NotFoundError,
    Object,
    ObjectIdentifier,
    PaginationRequest,
)

from aserto.client.directory import ConfigError

@pytest.fixture(scope="session")
def event_loop():
    """Overrides pytest default function scoped event loop"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def directory(topaz):
    client = Directory(
        address=topaz.directory_grpc.address, ca_cert_path=topaz.directory_grpc.ca_cert_path
    )

    yield client

    await client.close()

def test_client_without_address(topaz):
    with pytest.raises(ValueError):
        Directory(ca_cert_path=topaz.directory_grpc.ca_cert_path)

@pytest.mark.asyncio
async def test_client_without_writer(topaz):
    client = Directory(
        reader_address=topaz.directory_grpc.address, ca_cert_path=topaz.directory_grpc.ca_cert_path
    )
    obj = await client.get_object("user", "beth@the-smiths.com")
    assert obj.type == "user"
    assert obj.key == "beth@the-smiths.com"

    with pytest.raises(ConfigError):
        await client.set_object(
        Object(
            type=obj.type,
            key=obj.key,
            hash=obj.hash,
            display_name="Beth Smith (modified)",
            properties=obj.properties,
        )
    )


@pytest.mark.asyncio
async def test_get_object(directory: Directory):
    obj = await directory.get_object(object_type="user", object_key="summer@the-smiths.com")

    assert obj.key == "summer@the-smiths.com"
    assert obj.type == "user"
    assert obj.display_name == "Summer Smith"


@pytest.mark.asyncio
async def test_object_not_found(directory: Directory):
    with pytest.raises(NotFoundError):
        await directory.get_object("user", "no-such-user")


@pytest.mark.asyncio
async def test_object_invalid_arg(directory: Directory):
    with pytest.raises(RpcError, match="object_type: value is required"):
        await directory.get_object("", "morty@the-citadel")


@pytest.mark.asyncio
async def test_get_objects_by_type(directory: Directory):
    resp = await directory.get_objects(object_type="user", page=PaginationRequest(size=10))
    objs = resp.results

    assert len(objs) == 5
    assert all(obj.type == "user" for obj in objs)


@pytest.mark.asyncio
async def test_get_objects(directory: Directory):
    resp = await directory.get_objects(page=PaginationRequest(size=10))
    objs = resp.results

    assert len(objs) == 10
    assert all(obj.type in ("user", "group", "identity") for obj in objs)


@pytest.mark.asyncio
async def test_get_objects_paging(directory: Directory):
    page_1 = await directory.get_objects(page=PaginationRequest(size=10))
    assert len(page_1.results) == 10
    assert page_1.page.next_token

    page_2 = await directory.get_objects(
        page=PaginationRequest(size=10, token=page_1.page.next_token)
    )
    assert len(page_2.results) == 9
    assert not page_2.page.next_token


@pytest.mark.asyncio
async def test_get_objects_many(directory: Directory):
    objs = await directory.get_object_many(
        [
            ObjectIdentifier(type="user", key="jerry@the-smiths.com"),
            ObjectIdentifier(type="identity", key="summer@the-smiths.com"),
        ]
    )

    assert len(objs) == 2
    assert objs[0].type == "user"
    assert objs[0].key == "jerry@the-smiths.com"
    assert objs[1].type == "identity"
    assert objs[1].key == "summer@the-smiths.com"


@pytest.mark.asyncio
async def test_get_objects_many_not_found(directory: Directory):
    with pytest.raises(NotFoundError):
        await directory.get_object_many(
            [
                ObjectIdentifier(type="user", key="jerry@the-smiths.com"),
                ObjectIdentifier(type="identity", key="summer@the-smiths.com"),
                ObjectIdentifier(type="user", key="no-such-user"),
            ]
        )


@pytest.mark.asyncio
async def test_set_object(directory: Directory):
    obj = await directory.get_object("user", "beth@the-smiths.com")
    updated_obj = await directory.set_object(
        Object(
            type=obj.type,
            key=obj.key,
            hash=obj.hash,
            display_name="Beth Smith (modified)",
            properties=obj.properties,
        )
    )

    assert obj.type == updated_obj.type
    assert obj.key == updated_obj.key
    assert obj.properties == updated_obj.properties
    assert updated_obj.display_name == "Beth Smith (modified)"
    assert obj.hash != updated_obj.hash


@pytest.mark.asyncio
async def test_delete_object(directory: Directory):
    # Delete an existing object
    await directory.delete_object(object_type="user", object_key="morty@the-citadel.com")

    # get_object should raise NotFoundError
    with pytest.raises(NotFoundError):
        await directory.get_object(object_type="user", object_key="morty@the-citadel.com")

    # Relations should remain intact
    rel = await directory.get_relation(
        "user", "rick@the-citadel.com", "manager", "user", "morty@the-citadel"
    )
    assert rel is not None
    assert rel.object.type == "user"
    assert rel.object.key == "rick@the-citadel.com"
    assert rel.relation == "manager"
    assert rel.subject.type == "user"
    assert rel.subject.key == "morty@the-citadel.com"


@pytest.mark.asyncio
async def test_delete_relation(directory: Directory):
    await directory.delete_relation(
        object_type="group",
        object_key="viewer",
        relation="member",
        subject_type="user",
        subject_key="jerry@the-smiths.com",
    )

    with pytest.raises(NotFoundError):
        await directory.get_relation(
            object_type="group",
            object_key="viewer",
            relation="member",
            subject_type="user",
            subject_key="jerry@the-smiths.com",
        )


@pytest.mark.asyncio
async def test_get_relation(directory: Directory):
    rel = await directory.get_relation(
        object_type="group",
        object_key="evil_genius",
        relation="member",
        subject_type="user",
        subject_key="rick@the-citadel.com",
    )

    assert rel.relation == "member"
    assert rel.object.key == "evil_genius"
    assert rel.subject.key == "rick@the-citadel.com"


@pytest.mark.asyncio
async def test_get_relation_with_objects(directory: Directory):
    resp = await directory.get_relation(
        object_type="group",
        object_key="evil_genius",
        relation="member",
        subject_type="user",
        subject_key="rick@the-citadel.com",
        with_objects=True,
    )

    assert resp.relation.relation == "member"
    assert resp.relation.object.key == "evil_genius"
    assert resp.relation.subject.key == "rick@the-citadel.com"
    assert resp.object.type == "group"
    assert resp.object.key == "evil_genius"
    assert resp.subject.type == "user"
    assert resp.subject.key == "rick@the-citadel.com"
    assert resp.subject.properties


@pytest.mark.asyncio
async def test_get_relations(directory: Directory):
    resp = await directory.get_relations(
        object_type="user", relation="manager", page=PaginationRequest(size=10)
    )

    assert len(resp.results) == 4


@pytest.mark.asyncio
async def test_check_relation(directory: Directory):
    check_true = await directory.check_relation(
        object_type="group",
        object_key="evil_genius",
        relation="member",
        subject_type="user",
        subject_key="rick@the-citadel.com",
    )

    check_false = await directory.check_relation(
        object_type="group",
        object_key="evil_genius",
        relation="member",
        subject_type="user",
        subject_key="morty@the-citadel.com",
    )

    assert check_true == True
    assert check_false == False


@pytest.mark.asyncio
async def test_check_permission(directory: Directory):
    check_true = await directory.check_permission(
        object_type="user",
        object_key="rick@the-citadel.com",
        permission="complain",
        subject_type="user",
        subject_key="morty@the-citadel.com",
    )

    check_false = await directory.check_permission(
        object_type="user",
        object_key="summer@the-smiths.com",
        permission="complain",
        subject_type="user",
        subject_key="morty@the-citadel.com",
    )

    assert check_true == True
    assert check_false == False
