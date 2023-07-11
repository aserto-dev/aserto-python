import uuid
from dataclasses import dataclass

import pytest

from aserto.client.directory import Directory, NotFoundError, Object, Relation


@dataclass(frozen=True)
class TestData:
    client: Directory
    obj_1: Object
    obj_2: Object
    relation_1: Relation
    relation_2: Relation


@pytest.fixture(scope="module")
def directory_client(topaz):
    client = Directory.connect(
        address=topaz.directory.address, ca_cert=topaz.directory.ca_cert_path
    )

    yield client

    client.close()


@pytest.fixture
def directory(directory_client):
    key_1 = uuid.uuid4().hex
    key_2 = uuid.uuid4().hex

    obj_1 = directory_client.set_object(Object(key=key_1, type="user", display_name="test user"))
    obj_2 = directory_client.set_object(Object(key=key_2, type="group", display_name="test group"))
    obj_3 = directory_client.set_object(
        Object(key=key_2, type="user", display_name="another test user")
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
            "subject": {"key": obj_2.key, "type": obj_2.type},
            "object": {"key": obj_3.key, "type": obj_3.type},
            "relation": "manager",
        }
    )

    yield TestData(
        client=directory_client,
        obj_1=obj_1,
        obj_2=obj_2,
        relation_1=relation_1,
        relation_2=relation_2,
    )

    directory_client.delete_relation(
        subject_type=relation_1.subject.type,
        subject_key=relation_1.subject.type,
        object_type=relation_1.object.type,
        object_key=relation_1.object.key,
        relation_type=relation_1.relation,
    )

    directory_client.delete_relation(
        subject_type=relation_2.subject.type,
        subject_key=relation_2.subject.type,
        object_type=relation_2.object.type,
        object_key=relation_2.object.key,
        relation_type=relation_2.relation,
    )

    directory_client.delete_object(key=obj_1.key, type=obj_1.type)
    directory_client.delete_object(key=obj_2.key, type=obj_2.type)
    directory_client.delete_object(key=obj_3.key, type=obj_3.type)


def test_delete_object(directory):
    obj_to_delete = directory.client.get_object(key=directory.obj_1.key, type=directory.obj_1.type)
    directory.client.delete_object(key=obj_to_delete.key, type=obj_to_delete.type)
    with pytest.raises(NotFoundError):
        directory.client.get_object(key=directory.obj_1.key, type=directory.obj_1.type)


def test_get_object(directory):
    obj = directory.client.get_object(key=directory.obj_1.key, type=directory.obj_1.type)
    assert obj.key == directory.obj_1.key
    assert obj.type == directory.obj_1.type
    # assert obj.display_name == "test user"


def test_set_object(directory):
    key = uuid.uuid4().hex

    obj = directory.client.set_object(Object(key=key, type="user", display_name="test user"))

    assert obj.key == key
    assert obj.type == "user"
    assert obj.display_name == "test user"
