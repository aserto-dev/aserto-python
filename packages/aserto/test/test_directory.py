import uuid
from dataclasses import dataclass

import grpc
import pytest

from aserto.client.directory import (
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


@pytest.fixture(scope="module")
def directory_client(topaz):
    client = Directory(address=topaz.directory.address, ca_cert=topaz.directory.ca_cert_path)

    yield client

    client.close()


@pytest.fixture
def directory(directory_client: Directory):
    key_1 = uuid.uuid4().hex
    key_2 = uuid.uuid4().hex
    key_3 = uuid.uuid4().hex

    obj_1: Object = directory_client.set_object(
        Object(key=key_1, type="user", display_name="test user")
    )
    obj_2: Object = directory_client.set_object(
        Object(key=key_2, type="group", display_name="test group")
    )
    obj_3: Object = directory_client.set_object(
        Object(key=key_3, type="user", display_name="another test user")
    )

    permission_1: Permission = directory_client.writer.SetPermission(
        SetPermissionRequest(permission=Permission(name="view-todo"))
    ).result
    relation_type_1: RelationType = directory_client.writer.SetRelationType(
        SetRelationTypeRequest(
            relation_type=RelationType(
                name="member", object_type="group", permissions=["view-todo"]
            )
        )
    ).result

    permission_2: Permission = directory_client.writer.SetPermission(
        SetPermissionRequest(permission=Permission(name="delete-todo"))
    ).result
    relation_type_2: RelationType = directory_client.writer.SetRelationType(
        SetRelationTypeRequest(
            relation_type=RelationType(
                name="manager", object_type="user", permissions=["delete-todo"]
            )
        )
    ).result

    relation_1: Relation = directory_client.set_relation(
        relation={
            "subject": {"key": obj_1.key, "type": obj_1.type},
            "object": {"key": obj_2.key, "type": obj_2.type},
            "relation": relation_type_1.name,
        }
    )

    relation_2: Relation = directory_client.set_relation(
        relation={
            "subject": {"key": obj_1.key, "type": obj_1.type},
            "object": {"key": obj_3.key, "type": obj_3.type},
            "relation": relation_type_2.name,
        }
    )

    yield SetupData(
        client=directory_client,
        obj_1=obj_1,
        obj_2=obj_2,
        obj_3=obj_3,
        relation_1=relation_1,
        relation_2=relation_2,
        permission_1=permission_1,
        permission_2=permission_2,
    )

    relations = directory_client.get_relations(page=PaginationRequest(size=30)).results
    for rel in relations:
        directory_client.delete_relation(
            subject_type=rel.subject.type,
            subject_key=rel.subject.key,
            object_type=rel.object.type,
            object_key=rel.object.key,
            relation_type=rel.relation,
        )

    for relation_type in [relation_type_1, relation_type_2]:
        directory_client.writer.DeleteRelationType(
            DeleteRelationTypeRequest(
                param=RelationTypeIdentifier(
                    name=relation_type.name, object_type=relation_type.object_type
                )
            )
        )

    for permission in [permission_1, permission_2]:
        directory_client.writer.DeletePermission(
            DeletePermissionRequest(param=PermissionIdentifier(name=permission.name))
        )

    objects = directory_client.get_objects(page=PaginationRequest(size=30)).results
    for obj in objects:
        directory_client.delete_object(key=obj.key, type=obj.type)


def test_delete_object(directory: SetupData):
    directory.client.delete_object(key=directory.obj_1.key, type=directory.obj_1.type)
    with pytest.raises(NotFoundError):
        directory.client.get_object(key=directory.obj_1.key, type=directory.obj_1.type)


def test_get_object(directory: SetupData):
    obj = directory.client.get_object(key=directory.obj_1.key, type=directory.obj_1.type)

    assert obj.key == directory.obj_1.key
    assert obj.type == directory.obj_1.type
    assert obj.display_name == directory.obj_1.display_name


def test_object_not_found(directory: SetupData):
    key = uuid.uuid4().hex
    with pytest.raises(NotFoundError):
        directory.client.get_object(key=key, type="user")


def test_object_invalid_arg(directory: SetupData):
    with pytest.raises(grpc.RpcError, match="object identifier invalid argument") as err:
        directory.client.get_object(key=directory.obj_1.key, type="")


@pytest.mark.skip(reason="topaz directory doesn't filter on type")
def test_get_objects_by_type(directory: SetupData):
    objs = directory.client.get_objects(
        object_type=directory.obj_1.type, page=PaginationRequest(size=10)
    ).results

    assert directory.obj_1 in objs
    assert directory.obj_1.type == directory.obj_3.type
    assert directory.obj_1.type != directory.obj_2.type
    assert directory.obj_3 in objs
    assert directory.obj_2 not in objs


def test_get_objects(directory: SetupData):
    objs = directory.client.get_objects(page=PaginationRequest(size=10)).results

    assert directory.obj_1 in objs
    assert directory.obj_2 in objs
    assert directory.obj_3 in objs
    assert len(objs) == 3


def test_get_objects_paging(directory: SetupData):
    objs_response_1 = directory.client.get_objects(page=PaginationRequest(size=2))
    assert len(objs_response_1.results) == 2
    assert objs_response_1.page.next_token

    objs_response_2 = directory.client.get_objects(
        page=PaginationRequest(size=2, token=objs_response_1.page.next_token)
    )
    assert len(objs_response_2.results) == 1
    assert not objs_response_2.page.next_token


def test_get_objects_many(directory: SetupData):
    objs = directory.client.get_objects_many(
        objects=[
            ObjectIdentifier(key=directory.obj_1.key, type=directory.obj_1.type),
            ObjectIdentifier(key=directory.obj_2.key, type=directory.obj_2.type),
        ]
    )

    assert directory.obj_1 in objs
    assert directory.obj_2 in objs
    assert len(objs) == 2


def test_set_object(directory: SetupData):
    obj = directory.client.get_object(key=directory.obj_1.key, type=directory.obj_1.type)
    updated_obj = directory.client.set_object(
        Object(key=obj.type, type=obj.type, hash=obj.hash, display_name="changed user")
    )

    assert updated_obj.display_name == "changed user"


def test_delete_relation(directory: SetupData):
    directory.client.delete_relation(
        subject_type=directory.relation_1.subject.type,
        subject_key=directory.relation_1.subject.key,
        object_type=directory.relation_1.object.type,
        object_key=directory.relation_1.object.key,
        relation_type=directory.relation_1.relation,
    )

    with pytest.raises(NotFoundError):
        directory.client.get_relation(
            subject_type=directory.relation_1.subject.type,
            subject_key=directory.relation_1.subject.key,
            object_type=directory.relation_1.object.type,
            object_key=directory.relation_1.object.key,
            relation_type=directory.relation_1.relation,
        )


def test_get_relation(directory: SetupData):
    rel = directory.client.get_relation(
        subject_type=directory.relation_1.subject.type,
        subject_key=directory.relation_1.subject.key,
        object_type=directory.relation_1.object.type,
        object_key=directory.relation_1.object.key,
        relation_type=directory.relation_1.relation,
    )

    assert rel.relation.relation == directory.relation_1.relation
    assert rel.relation.object.key == directory.relation_1.object.key
    assert rel.relation.subject.key == directory.relation_1.subject.key
    assert rel.objects == {}


def test_get_relation_with_objects(directory: SetupData):
    rel = directory.client.get_relation(
        subject_type=directory.relation_1.subject.type,
        subject_key=directory.relation_1.subject.key,
        object_type=directory.relation_1.object.type,
        object_key=directory.relation_1.object.key,
        relation_type=directory.relation_1.relation,
        with_objects=True,
    )

    assert rel.relation.relation == directory.relation_1.relation
    assert rel.relation.object.key == directory.relation_1.object.key
    assert rel.relation.subject.key == directory.relation_1.subject.key
    assert (
        ObjectIdentifier(type=directory.relation_1.object.type, key=directory.relation_1.object.key)
        in rel.objects
    )


def test_get_relations(directory: SetupData):
    rels = directory.client.get_relations(page=PaginationRequest(size=10)).results

    assert directory.relation_2 in rels
    assert len(rels) == 2


def test_set_relation(directory: SetupData):
    rel = directory.client.get_relation(
        subject_type=directory.relation_1.subject.type,
        subject_key=directory.relation_1.subject.key,
        object_type=directory.relation_1.object.type,
        object_key=directory.relation_1.object.key,
        relation_type=directory.relation_1.relation,
    )

    updated_rel = directory.client.set_relation(
        relation={
            "subject": {"key": rel.relation.subject.key, "type": rel.relation.subject.type},
            "object": {"key": rel.relation.object.key, "type": rel.relation.object.type},
            "relation": "changed relation",
        }
    )

    assert updated_rel.relation == "changed relation"


def test_check_relation(directory: SetupData):
    check_true = directory.client.check_relation(
        subject_type=directory.relation_1.subject.type,
        subject_key=directory.relation_1.subject.key,
        object_type=directory.relation_1.object.type,
        object_key=directory.relation_1.object.key,
        relation_type=directory.relation_1.relation,
    )

    check_false = directory.client.check_relation(
        subject_type=directory.relation_1.subject.type,
        subject_key=directory.relation_1.subject.key,
        object_type=directory.relation_1.object.type,
        object_key=directory.relation_1.object.key,
        relation_type=directory.relation_2.relation,
    )

    assert check_true == True
    assert check_false == False


def test_check_permission(directory: SetupData):
    check_true = directory.client.check_permission(
        object_key=directory.relation_2.object.key,
        object_type=directory.relation_2.object.type,
        subject_key=directory.relation_2.subject.key,
        subject_type=directory.relation_2.subject.type,
        permission=directory.permission_2.name,
    )

    check_false = directory.client.check_permission(
        subject_type=directory.relation_1.subject.type,
        subject_key=directory.relation_1.subject.key,
        object_type=directory.relation_1.object.type,
        object_key=directory.relation_1.object.key,
        permission=directory.permission_2.name,
    )

    assert check_true == True
    assert check_false == False
