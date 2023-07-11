import uuid
from dataclasses import dataclass

import grpc
import pytest

from aserto.client.directory import (
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


@pytest.fixture(scope="module")
def directory_client(topaz):
    client = Directory(address=topaz.directory.address, ca_cert=topaz.directory.ca_cert_path)

    yield client

    client.close()


@pytest.fixture
def directory(directory_client):
    key_1 = uuid.uuid4().hex
    key_2 = uuid.uuid4().hex
    key_3 = uuid.uuid4().hex

    obj_1 = directory_client.set_object(Object(key=key_1, type="user", display_name="test user"))
    obj_2 = directory_client.set_object(Object(key=key_2, type="group", display_name="test group"))
    obj_3 = directory_client.set_object(
        Object(key=key_3, type="user", display_name="another test user")
    )

    relation_1 = directory_client.set_relation(
        relation={
            "subject": {"key": obj_1.key, "type": obj_1.type},
            "object": {"key": obj_2.key, "type": obj_2.type},
            "relation": "member",
        }
    )

    relation_2 = directory_client.set_relation(
        relation={
            "subject": {"key": obj_1.key, "type": obj_1.type},
            "object": {"key": obj_3.key, "type": obj_3.type},
            "relation": "manager",
        }
    )

    yield SetupData(
        client=directory_client,
        obj_1=obj_1,
        obj_2=obj_2,
        obj_3=obj_3,
        relation_1=relation_1,
        relation_2=relation_2,
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

    objects = directory_client.get_objects(page=PaginationRequest(size=30)).results
    for obj in objects:
        directory_client.delete_object(key=obj.key, type=obj.type)


def test_delete_object(directory):
    directory.client.delete_object(key=directory.obj_1.key, type=directory.obj_1.type)
    with pytest.raises(NotFoundError):
        directory.client.get_object(key=directory.obj_1.key, type=directory.obj_1.type)


def test_get_object(directory):
    obj = directory.client.get_object(key=directory.obj_1.key, type=directory.obj_1.type)

    assert obj.key == directory.obj_1.key
    assert obj.type == directory.obj_1.type
    assert obj.display_name == directory.obj_1.display_name


def test_object_not_found(directory):
    key = uuid.uuid4().hex
    with pytest.raises(NotFoundError):
        directory.client.get_object(key=key, type="user")


def test_object_invalid_arg(directory):
    with pytest.raises(grpc.RpcError, match="object identifier invalid argument") as err:
        directory.client.get_object(key=directory.obj_1.key, type="")


@pytest.mark.skip(reason="topaz directory doesn't filter on type")
def test_get_objects_by_type(directory):
    objs = directory.client.get_objects(
        object_type=directory.obj_1.type, page=PaginationRequest(size=10)
    ).results

    assert directory.obj_1 in objs
    assert directory.obj_1.type == directory.obj_3.type
    assert directory.obj_1.type != directory.obj_2.type
    assert directory.obj_3 in objs
    assert directory.obj_2 not in objs


def test_get_objects(directory):
    objs = directory.client.get_objects(page=PaginationRequest(size=10)).results

    assert directory.obj_1 in objs
    assert directory.obj_2 in objs
    assert directory.obj_3 in objs
    assert len(objs) == 3


def test_get_objects_many(directory):
    objs = directory.client.get_objects_many(
        objects=[
            ObjectIdentifier(key=directory.obj_1.key, type=directory.obj_1.type),
            ObjectIdentifier(key=directory.obj_2.key, type=directory.obj_2.type),
        ]
    )

    assert directory.obj_1 in objs
    assert directory.obj_2 in objs
    assert len(objs) == 2


def test_set_object(directory):
    obj = directory.client.get_object(key=directory.obj_1.key, type=directory.obj_1.type)
    updated_obj = directory.client.set_object(
        Object(key=obj.type, type=obj.type, hash=obj.hash, display_name="changed user")
    )

    assert updated_obj.display_name == "changed user"


def test_delete_relation(directory):
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


def test_get_relation(directory):
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


def test_get_relation_with_objects(directory):
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
    assert f"{directory.relation_1.object.type}:{directory.relation_1.object.key}" in rel.objects


def test_get_relations(directory):
    rels = directory.client.get_relations(page=PaginationRequest(size=10)).results

    assert directory.relation_2 in rels
    assert len(rels) == 2


def test_set_relation(directory):
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


def test_check_relation(directory):
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


# def test_check_permission(directory):
#     assert True == True
