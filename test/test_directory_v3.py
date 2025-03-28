import datetime

import pytest

from aserto.client.directory import ConfigError
from aserto.client.directory.v3 import (
    Directory,
    ETagMismatchError,
    ExportOption,
    InvalidArgumentError,
    NotFoundError,
    Object,
    ObjectIdentifier,
    PaginationRequest,
    Relation,
    Struct,
)


@pytest.fixture(name="directory", scope="module")
def fixture_directory(topaz):
    client = Directory(
        address=topaz.directory_grpc.address, ca_cert_path=topaz.directory_grpc.ca_cert_path
    )

    yield client

    client.close()


def test_client_without_address(topaz):
    with pytest.raises(ValueError):
        Directory(ca_cert_path=topaz.directory_grpc.ca_cert_path)


def test_client_without_writer(topaz):
    client = Directory(
        reader_address=topaz.directory_grpc.address, ca_cert_path=topaz.directory_grpc.ca_cert_path
    )
    obj = client.get_object("user", "beth@the-smiths.com")
    assert obj.type == "user"
    assert obj.id == "beth@the-smiths.com"

    obj.display_name = "Beth Smith (modified)"

    with pytest.raises(ConfigError):
        client.set_object(object=obj)


def test_get_object(directory: Directory):
    obj = directory.get_object(object_type="user", object_id="summer@the-smiths.com")

    assert obj.id == "summer@the-smiths.com"
    assert obj.type == "user"
    assert obj.display_name == "Summer Smith"


def test_object_not_found(directory: Directory):
    with pytest.raises(NotFoundError):
        directory.get_object("user", "no-such-user")


def test_object_invalid_arg(directory: Directory):
    with pytest.raises(InvalidArgumentError, match="invalid argument object identifier: type"):
        directory.get_object("", "morty@the-citadel")


def test_get_objects_by_type(directory: Directory):
    objs = directory.get_objects(object_type="user", page=PaginationRequest(size=10)).results

    assert len(objs) == 5
    assert all(obj.type == "user" for obj in objs)


def test_get_objects(directory: Directory):
    objs = directory.get_objects(page=PaginationRequest(size=10)).results

    assert len(objs) == 10
    assert all(obj.type in ("user", "group", "identity") for obj in objs)


def test_get_objects_paging(directory: Directory):
    page_1 = directory.get_objects(page=PaginationRequest(size=10))
    assert len(page_1.results) == 10
    assert page_1.page.next_token

    page_2 = directory.get_objects(page=PaginationRequest(size=10, token=page_1.page.next_token))
    assert len(page_2.results) == 10
    assert not page_2.page.next_token


def test_get_objects_many(directory: Directory):
    objs = directory.get_object_many(
        [
            ObjectIdentifier(type="user", id="jerry@the-smiths.com"),
            ObjectIdentifier(type="identity", id="summer@the-smiths.com"),
        ]
    )

    assert len(objs) == 2
    assert objs[0].type == "user"
    assert objs[0].id == "jerry@the-smiths.com"
    assert objs[1].type == "identity"
    assert objs[1].id == "summer@the-smiths.com"


def test_get_objects_many_not_found(directory: Directory):
    with pytest.raises(NotFoundError):
        directory.get_object_many(
            [
                ObjectIdentifier(type="user", id="jerry@the-smiths.com"),
                ObjectIdentifier(type="identity", id="summer@the-smiths.com"),
                ObjectIdentifier(type="user", id="no-such-user"),
            ]
        )


def test_set_object_from_message(directory: Directory):
    obj = directory.get_object("user", "beth@the-smiths.com")
    obj.display_name = "Beth Smith (modified)"
    obj.properties["department"] = "parents"
    updated_obj = directory.set_object(object=obj)

    assert obj.type == updated_obj.type
    assert obj.id == updated_obj.id
    assert obj.properties == updated_obj.properties
    assert updated_obj.display_name == "Beth Smith (modified)"
    assert obj.etag != updated_obj.etag


def test_set_object_from_args_with_dict_props(directory: Directory):
    props = {"email": "user@acmecorp.com"}
    new_obj = directory.set_object(
        object_type="user",
        object_id="new_user",
        properties=props,
    )

    assert new_obj.type == "user"
    assert new_obj.id == "new_user"
    assert new_obj.display_name == ""
    assert all(new_obj.properties[k] == v for k, v in props.items())


def test_set_object_from_args_with_struct_props(directory: Directory):
    props = Struct()
    props.update({"email": "user@acmecorp.com"})
    new_obj = directory.set_object(
        object_type="user",
        object_id="new_user",
        properties=props,
    )

    assert new_obj.type == "user"
    assert new_obj.id == "new_user"
    assert new_obj.display_name == ""
    assert all(new_obj.properties[k] == v for k, v in props.items())


def test_delete_object(directory: Directory):
    # Delete an existing object
    directory.delete_object(object_type="user", object_id="morty@the-citadel.com")

    # get_object should raise NotFoundError
    with pytest.raises(NotFoundError):
        directory.get_object(object_type="user", object_id="morty@the-citadel.com")

    # Relations should remain intact
    rel = directory.get_relation(
        with_objects=False,
        object_type="user",
        object_id="morty@the-citadel.com",
        relation="manager",
        subject_type="user",
        subject_id="rick@the-citadel.com",
    )
    assert rel is not None
    assert rel.object_type == "user"
    assert rel.object_id == "morty@the-citadel.com"
    assert rel.relation == "manager"
    assert rel.subject_type == "user"
    assert rel.subject_id == "rick@the-citadel.com"


def test_delete_relation(directory: Directory):
    directory.delete_relation(
        object_type="group",
        object_id="viewer",
        relation="member",
        subject_type="user",
        subject_id="jerry@the-smiths.com",
    )

    with pytest.raises(NotFoundError):
        directory.get_relation(
            object_type="group",
            object_id="viewer",
            relation="member",
            subject_type="user",
            subject_id="jerry@the-smiths.com",
        )


def test_get_relation(directory: Directory):
    rel = directory.get_relation(
        object_type="group",
        object_id="evil_genius",
        relation="member",
        subject_type="user",
        subject_id="rick@the-citadel.com",
    )

    assert rel.relation == "member"
    assert rel.object_id == "evil_genius"
    assert rel.subject_id == "rick@the-citadel.com"


def test_get_relation_with_objects(directory: Directory):
    resp = directory.get_relation(
        object_type="group",
        object_id="evil_genius",
        relation="member",
        subject_type="user",
        subject_id="rick@the-citadel.com",
        with_objects=True,
    )

    assert resp.relation.relation == "member"
    assert resp.relation.object_id == "evil_genius"
    assert resp.relation.subject_id == "rick@the-citadel.com"
    assert resp.object.type == "group"
    assert resp.object.id == "evil_genius"
    assert resp.subject.type == "user"
    assert resp.subject.id == "rick@the-citadel.com"
    assert resp.subject.properties


def test_get_relations(directory: Directory):
    rels = directory.get_relations(
        object_type="user", relation="manager", page=PaginationRequest(size=10)
    ).relations

    assert len(rels) == 4


def test_check_relation(directory: Directory):
    check_true = directory.check_relation(
        object_type="group",
        object_id="evil_genius",
        relation="member",
        subject_type="user",
        subject_id="rick@the-citadel.com",
    )

    check_false = directory.check_relation(
        object_type="group",
        object_id="evil_genius",
        relation="member",
        subject_type="user",
        subject_id="morty@the-citadel.com",
    )

    assert check_true is True
    assert check_false is False


def test_check_permission(directory: Directory):
    check_true = directory.check_permission(
        object_type="resource-creator",
        object_id="resource-creators",
        permission="can_create_resource",
        subject_type="user",
        subject_id="rick@the-citadel.com",
    )

    check_false = directory.check_permission(
        object_type="resource-creator",
        object_id="resource-creators",
        permission="can_create_resource",
        subject_type="user",
        subject_id="beth@the-smiths.com",
    )

    assert check_true is True
    assert check_false is False


def test_find_objects(directory: Directory):
    results = directory.find_objects(
        object_type="resource-creator",
        relation="can_create_resource",
        subject_type="user",
        subject_id="morty@the-citadel.com",
        explain=True,
        trace=True,
    )

    assert len(results.results) == 1
    assert results.results[0].id == "resource-creators"
    assert results.results[0].type == "resource-creator"

    assert "resource-creator:resource-creators" in results.explanation
    assert len(results.explanation["resource-creator:resource-creators"]) == 1
    assert len(results.explanation["resource-creator:resource-creators"][0]) == 1
    assert isinstance(results.explanation["resource-creator:resource-creators"][0][0], str)


def test_find_subjects(directory: Directory):
    results = directory.find_subjects(
        object_type="resource-creator",
        object_id="resource-creators",
        relation="can_create_resource",
        subject_type="user",
    )

    assert len(results.results) == 3
    assert ObjectIdentifier(type="user", id="morty@the-citadel.com") in results.results


def test_get_manifest(directory: Directory):
    manifest = directory.get_manifest()

    assert manifest is not None
    assert manifest.etag
    assert manifest.updated_at.date() == datetime.datetime.now(datetime.timezone.utc).date()
    assert manifest.body


def test_get_manifest_not_modified(directory: Directory):
    m1 = directory.get_manifest()
    assert m1 is not None

    m2 = directory.get_manifest(m1.etag)
    assert m2 is None


def test_set_manifest(directory: Directory):
    manifest = directory.get_manifest()
    assert manifest.body is not None

    new_body = bytes(manifest.body) + b"\n  foo: {}"

    directory.set_manifest(new_body)

    new_manifest = directory.get_manifest()

    assert new_manifest.body == new_body


def test_set_manifest_if_match(directory: Directory):
    manifest = directory.get_manifest()
    assert manifest.body is not None

    new_body = bytes(manifest.body) + b"\n  bar: {}"

    with pytest.raises(ETagMismatchError):
        directory.set_manifest(new_body, etag="1234")

    directory.set_manifest(new_body, etag=manifest.etag)


def test_import(directory: Directory):
    with pytest.raises(NotFoundError):
        # verify that the object doesn't exist
        directory.get_object("user", "test@acmecorp.com")

    with pytest.raises(NotFoundError):
        # verify that the relation doesn't exist
        directory.get_relation(
            with_objects=False,
            object_type="user",
            object_id="rick@the-citadel.com",
            relation="manager",
            subject_type="user",
            subject_id="test@acmecorp.com",
        )

    data = (
        Object(type="user", id="test@acmecorp.com"),
        Relation(
            object_type="user",
            object_id="rick@the-citadel.com",
            relation="manager",
            subject_type="user",
            subject_id="test@acmecorp.com",
        ),
    )

    resp = directory.import_data(data)
    assert resp is not None
    assert resp.objects.recv == 1
    assert resp.objects.set == 1
    assert resp.relations.recv == 1
    assert resp.relations.set == 1

    obj = directory.get_object("user", "test@acmecorp.com")
    assert obj is not None

    rel = directory.get_relation(
        with_objects=False,
        object_type="user",
        object_id="rick@the-citadel.com",
        relation="manager",
        subject_type="user",
        subject_id="test@acmecorp.com",
    )
    assert rel is not None


def test_export(directory: Directory):
    obj_count = 0
    rel_count = 0
    for item in directory.export_data(ExportOption.OPTION_DATA):
        if isinstance(item, Object):
            obj_count += 1
        elif isinstance(item, Relation):
            rel_count += 1

    assert obj_count == 21
    assert rel_count == 25
