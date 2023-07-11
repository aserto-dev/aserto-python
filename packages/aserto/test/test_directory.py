import uuid

from pytest import raises

from aserto.client.directory import Directory, NotFoundError, Object


def test_delete_object(topaz, directory_client, directory_setup):
    with raises(NotFoundError):
        directory = directory_client
        obj_1, _, _ = directory_setup

        directory.delete_object(key=obj_1.key, type=obj_1.type)
        obj = directory.get_object(key=obj_1.key, type=obj_1.type)


def test_get_object(topaz, directory_client, directory_setup):
    directory = directory_client
    obj_1, _, _ = directory_setup

    obj = directory.get_object(key=obj_1.key, type=obj_1.type)
    assert obj.key == obj_1.key
    assert obj.type == obj_1.type
    # assert obj.display_name == "test user"


def test_set_object(topaz, directory_client):
    directory = directory_client

    key = uuid.uuid4().hex

    obj = directory.set_object(Object(key=key, type="user", display_name="test user"))

    assert obj.key == key
    assert obj.type == "user"
    assert obj.display_name == "test user"
