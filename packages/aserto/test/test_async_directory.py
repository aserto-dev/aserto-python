import asyncio
import uuid
from dataclasses import dataclass

import grpc
import pytest
from google.protobuf.json_format import MessageToJson

from aserto.client.directory.aio import (
    DeletePermissionRequest,
    DeleteRelationTypeRequest,
    Directory,
    NotFoundError,
    Object,
    ObjectIdentifier,
    PaginationRequest,
    Permission,
    PermissionIdentifier,
    Relation,
    RelationType,
    RelationTypeIdentifier,
    SetPermissionRequest,
    SetRelationTypeRequest,
)


@dataclass(frozen=True)
class SetupData:
    client: Directory
    obj_1: Object
    obj_2: Object
    obj_3: Object
    relation_1: Relation
    relation_2: Relation
    permission_1: Permission
    permission_2: Permission


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
async def directory_async(async_directory_client: Directory):
    key_1 = uuid.uuid4().hex
    key_2 = uuid.uuid4().hex
    key_3 = uuid.uuid4().hex

    obj_1: Object = await async_directory_client.set_object(
        Object(key=key_1, type="user", display_name="test user")
    )
    obj_2: Object = await async_directory_client.set_object(
        Object(key=key_2, type="group", display_name="test group")
    )
    obj_3: Object = await async_directory_client.set_object(
        Object(key=key_3, type="user", display_name="another test user")
    )

    permission_1_response: Permission = await async_directory_client.writer.SetPermission(
        SetPermissionRequest(permission=Permission(name="view-todo"))
    )
    permission_1 = permission_1_response.result
    relation_type_1_response: RelationType = await async_directory_client.writer.SetRelationType(
        SetRelationTypeRequest(
            relation_type=RelationType(
                name="member", object_type="group", permissions=["view-todo"]
            )
        )
    )
    relation_type_1 = relation_type_1_response.result

    permission_2_response: Permission = await async_directory_client.writer.SetPermission(
        SetPermissionRequest(permission=Permission(name="delete-todo"))
    )
    permission_2 = permission_2_response.result
    relation_type_2_response: RelationType = await async_directory_client.writer.SetRelationType(
        SetRelationTypeRequest(
            relation_type=RelationType(
                name="manager", object_type="user", permissions=["delete-todo"]
            )
        )
    )
    relation_type_2 = relation_type_2_response.result

    relation_1: Relation = await async_directory_client.set_relation(
        relation={
            "subject": {"key": obj_1.key, "type": obj_1.type},
            "object": {"key": obj_2.key, "type": obj_2.type},
            "relation": relation_type_1.name,
        }
    )

    relation_2: Relation = await async_directory_client.set_relation(
        relation={
            "subject": {"key": obj_1.key, "type": obj_1.type},
            "object": {"key": obj_3.key, "type": obj_3.type},
            "relation": relation_type_2.name,
        }
    )

    yield SetupData(
        client=async_directory_client,
        obj_1=obj_1,
        obj_2=obj_2,
        obj_3=obj_3,
        relation_1=relation_1,
        relation_2=relation_2,
        permission_1=permission_1,
        permission_2=permission_2,
    )

    relations_response = await async_directory_client.get_relations(page=PaginationRequest(size=30))
    relations = relations_response.results

    while relations_response.page.next_token:
        relations_response = await async_directory_client.get_relations(
            page=PaginationRequest(size=30, token=relations_response.page.next_token)
        )
        relations += relations_response.results

    for rel in relations:
        await async_directory_client.delete_relation(
            subject_type=rel.subject.type,
            subject_key=rel.subject.key,
            object_type=rel.object.type,
            object_key=rel.object.key,
            relation_type=rel.relation,
        )

    for relation_type in [relation_type_1, relation_type_2]:
        await async_directory_client.writer.DeleteRelationType(
            DeleteRelationTypeRequest(
                param=RelationTypeIdentifier(
                    name=relation_type.name, object_type=relation_type.object_type
                )
            )
        )

    for permission in [permission_1, permission_2]:
        await async_directory_client.writer.DeletePermission(
            DeletePermissionRequest(param=PermissionIdentifier(name=permission.name))
        )

    objects_response = await async_directory_client.get_objects(page=PaginationRequest(size=30))
    objects = objects_response.results

    while objects_response.page.next_token:
        objects_response = await async_directory_client.get_objects(
            page=PaginationRequest(size=30, token=objects_response.page.next_token)
        )
        objects += objects_response.results

    for obj in objects:
        await async_directory_client.delete_object(key=obj.key, type=obj.type)


@pytest.mark.asyncio
async def test_get_object(directory_async: SetupData):
    obj = await directory_async.client.get_object(
        key=directory_async.obj_1.key, type=directory_async.obj_1.type
    )

    assert obj.key == directory_async.obj_1.key
    assert obj.type == directory_async.obj_1.type
    assert obj.display_name == directory_async.obj_1.display_name


@pytest.mark.asyncio
async def test_object_not_found(directory_async: SetupData):
    key = uuid.uuid4().hex
    with pytest.raises(NotFoundError):
        await directory_async.client.get_object(key=key, type="user")


@pytest.mark.asyncio
async def test_get_relation(directory_async: SetupData):
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
async def test_get_relation_with_objects(directory_async: SetupData):
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
    assert len(rel.objects) == 2
    assert (
        ObjectIdentifier(
            type=directory_async.relation_1.object.type, key=directory_async.relation_1.object.key
        )
        in rel.objects
    )
    assert (
        ObjectIdentifier(
            type=directory_async.relation_1.subject.type, key=directory_async.relation_1.subject.key
        )
        in rel.objects
    )


@pytest.mark.asyncio
async def test_check_relation(directory_async: SetupData):
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
