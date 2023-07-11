import uuid

from aserto.client.directory import Directory, Object


def test_set_object(topaz):
    directory = Directory.connect(address=topaz.directory.address, ca_cert=topaz.directory.ca_cert_path)

    key = uuid.uuid4().hex

    directory.set_object(Object(key=key, type="user", display_name="test user"))

    obj = directory.get_object(key=key, type="user")
    assert obj.key == key
    assert obj.type == "user"
    assert obj.display_name == "test user"
