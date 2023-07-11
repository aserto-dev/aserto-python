import asyncio
import uuid
from dataclasses import dataclass

import grpc
import pytest
from google.protobuf.json_format import MessageToJson

from aserto.client.directory.aio import (
    Directory,
    NotFoundError,
    Object,
    ObjectIdentifier,
    PaginationRequest,
    Relation,
)


@dataclass(frozen=True)
class SetupData:
    client: Directory
    obj_1: Object
    obj_2: Object
    obj_3: Object
    relation_1: Relation
    relation_2: Relation


@pytest.fixture(scope="session")
def event_loop():
    """Overrides pytest default function scoped event loop"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def async_directory_client(topaz):
    client = Directory(address=topaz.directory.address, ca_cert=topaz.directory.ca_cert_path)

    yield client

    await client.close()


@pytest.fixture
async def directory_async(async_directory_client):
    key_1 = uuid.uuid4().hex
    key_2 = uuid.uuid4().hex
    key_3 = uuid.uuid4().hex

    obj_1 = await async_directory_client.set_object(
        Object(key=key_1, type="user", display_name="test user")
    )
    obj_2 = await async_directory_client.set_object(
        Object(key=key_2, type="group", display_name="test group")
    )
    obj_3 = await async_directory_client.set_object(
        Object(key=key_3, type="user", display_name="another test user")
    )

    relation_1 = await async_directory_client.set_relation(
        relation={
            "subject": {"key": obj_1.key, "type": obj_1.type},
            "object": {"key": obj_2.key, "type": obj_2.type},
            "relation": "member",
        }
    )

    relation_2 = await async_directory_client.set_relation(
        relation={
            "subject": {"key": obj_1.key, "type": obj_1.type},
            "object": {"key": obj_3.key, "type": obj_3.type},
            "relation": "manager",
        }
    )

    yield SetupData(
        client=async_directory_client,
        obj_1=obj_1,
        obj_2=obj_2,
        obj_3=obj_3,
        relation_1=relation_1,
        relation_2=relation_2,
    )

    relations_response = await async_directory_client.get_relations(page=PaginationRequest(size=30))
    relations = relations_response.results
    for rel in relations:
        await async_directory_client.delete_relation(
            subject_type=rel.subject.type,
            subject_key=rel.subject.key,
            object_type=rel.object.type,
            object_key=rel.object.key,
            relation_type=rel.relation,
        )

    objects_response = await async_directory_client.get_objects(page=PaginationRequest(size=30))
    objects = objects_response.results
    for obj in objects:
        await async_directory_client.delete_object(key=obj.key, type=obj.type)


@pytest.mark.asyncio
async def test_get_object(directory_async):
    obj = await directory_async.client.get_object(
        key=directory_async.obj_1.key, type=directory_async.obj_1.type
    )

    assert obj.key == directory_async.obj_1.key
    assert obj.type == directory_async.obj_1.type
    assert obj.display_name == directory_async.obj_1.display_name


@pytest.mark.asyncio
async def test_object_not_found(directory_async):
    key = uuid.uuid4().hex
    with pytest.raises(NotFoundError):
        await directory_async.client.get_object(key=key, type="user")


@pytest.mark.asyncio
async def test_get_relation(directory_async):
    rel = await directory_async.client.get_relation(
        subject_type=directory_async.relation_1.subject.type,
        subject_key=directory_async.relation_1.subject.key,
        object_type=directory_async.relation_1.object.type,
        object_key=directory_async.relation_1.object.key,
        relation_type=directory_async.relation_1.relation,
    )

    assert rel.relation.relation == directory_async.relation_1.relation
    assert rel.relation.object.key == directory_async.relation_1.object.key
    assert rel.relation.subject.key == directory_async.relation_1.subject.key
    assert rel.objects == {}


@pytest.mark.asyncio
async def test_get_relation_with_objects(directory_async):
    rel = await directory_async.client.get_relation(
        subject_type=directory_async.relation_1.subject.type,
        subject_key=directory_async.relation_1.subject.key,
        object_type=directory_async.relation_1.object.type,
        object_key=directory_async.relation_1.object.key,
        relation_type=directory_async.relation_1.relation,
        with_objects=True,
    )

    assert rel.relation.relation == directory_async.relation_1.relation
    assert rel.relation.object.key == directory_async.relation_1.object.key
    assert rel.relation.subject.key == directory_async.relation_1.subject.key
    assert (
        ObjectIdentifier(
            type=directory_async.relation_1.object.type, key=directory_async.relation_1.object.key
        )
        in rel.objects
    )


@pytest.mark.asyncio
async def test_check_relation(directory_async):
    check_true = await directory_async.client.check_relation(
        subject_type=directory_async.relation_1.subject.type,
        subject_key=directory_async.relation_1.subject.key,
        object_type=directory_async.relation_1.object.type,
        object_key=directory_async.relation_1.object.key,
        relation_type=directory_async.relation_1.relation,
    )

    check_false = await directory_async.client.check_relation(
        subject_type=directory_async.relation_1.subject.type,
        subject_key=directory_async.relation_1.subject.key,
        object_type=directory_async.relation_1.object.type,
        object_key=directory_async.relation_1.object.key,
        relation_type=directory_async.relation_2.relation,
    )

    assert check_true == True
    assert check_false == False
