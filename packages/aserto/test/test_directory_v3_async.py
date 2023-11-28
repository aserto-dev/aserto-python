import asyncio
import datetime

import pytest
from grpc import RpcError

from aserto.client.directory.v3.aio import (
    Directory,
    ETagMismatchError,
    ExportOption,
    NotFoundError,
    Object,
    ObjectIdentifier,
    PaginationRequest,
    Relation,
    Struct,
)


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


@pytest.mark.asyncio
async def test_get_object(directory: Directory):
    obj = await directory.get_object(object_type="user", object_id="summer@the-smiths.com")

    assert obj.id == "summer@the-smiths.com"
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
            ObjectIdentifier(type="user", id="jerry@the-smiths.com"),
            ObjectIdentifier(type="identity", id="summer@the-smiths.com"),
        ]
    )

    assert len(objs) == 2
    assert objs[0].type == "user"
    assert objs[0].id == "jerry@the-smiths.com"
    assert objs[1].type == "identity"
    assert objs[1].id == "summer@the-smiths.com"


@pytest.mark.asyncio
async def test_get_objects_many_not_found(directory: Directory):
    with pytest.raises(NotFoundError):
        await directory.get_object_many(
            [
                ObjectIdentifier(type="user", id="jerry@the-smiths.com"),
                ObjectIdentifier(type="identity", id="summer@the-smiths.com"),
                ObjectIdentifier(type="user", id="no-such-user"),
            ]
        )


@pytest.mark.asyncio
async def test_set_object_from_message(directory: Directory):
    obj = await directory.get_object("user", "beth@the-smiths.com")
    obj.display_name = "Beth Smith (modified)"
    updated_obj = await directory.set_object(object=obj)

    assert obj.type == updated_obj.type
    assert obj.id == updated_obj.id
    assert obj.properties == updated_obj.properties
    assert updated_obj.display_name == "Beth Smith (modified)"
    assert obj.etag != updated_obj.etag


@pytest.mark.asyncio
async def test_set_object_from_args_with_dict_props(directory: Directory):
    props = {"email": "user@acmecorp.com"}
    new_obj = await directory.set_object(
        object_type="user",
        object_id="new_user",
        properties=props,
    )

    assert new_obj.type == "user"
    assert new_obj.id == "new_user"
    assert new_obj.display_name == ""
    assert all(new_obj.properties[k] == v for k, v in props.items())


@pytest.mark.asyncio
async def test_set_object_from_args_with_struct_props(directory: Directory):
    props = Struct()
    props.update({"email": "user@acmecorp.com"})
    new_obj = await directory.set_object(
        object_type="user",
        object_id="new_user",
        properties=props,
    )

    assert new_obj.type == "user"
    assert new_obj.id == "new_user"
    assert new_obj.display_name == ""
    assert all(new_obj.properties[k] == v for k, v in props.items())


@pytest.mark.asyncio
async def test_delete_object(directory: Directory):
    # Delete an existing object
    await directory.delete_object(object_type="user", object_id="morty@the-citadel.com")

    # get_object should raise NotFoundError
    with pytest.raises(NotFoundError):
        await directory.get_object(object_type="user", object_id="morty@the-citadel.com")

    # Relations should remain intact
    rel = await directory.get_relation(
        "user", "rick@the-citadel.com", "manager", "user", "morty@the-citadel"
    )
    assert rel is not None
    assert rel.object_type == "user"
    assert rel.object_id == "rick@the-citadel.com"
    assert rel.relation == "manager"
    assert rel.subject_type == "user"
    assert rel.subject_id == "morty@the-citadel.com"


@pytest.mark.asyncio
async def test_delete_relation(directory: Directory):
    await directory.delete_relation(
        object_type="group",
        object_id="viewer",
        relation="member",
        subject_type="user",
        subject_id="jerry@the-smiths.com",
    )

    with pytest.raises(NotFoundError):
        await directory.get_relation(
            object_type="group",
            object_id="viewer",
            relation="member",
            subject_type="user",
            subject_id="jerry@the-smiths.com",
        )


@pytest.mark.asyncio
async def test_get_relation(directory: Directory):
    rel = await directory.get_relation(
        object_type="group",
        object_id="evil_genius",
        relation="member",
        subject_type="user",
        subject_id="rick@the-citadel.com",
    )

    assert rel.relation == "member"
    assert rel.object_id == "evil_genius"
    assert rel.subject_id == "rick@the-citadel.com"


@pytest.mark.asyncio
async def test_get_relation_with_objects(directory: Directory):
    resp = await directory.get_relation(
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


@pytest.mark.asyncio
async def test_get_relations(directory: Directory):
    resp = await directory.get_relations(
        object_type="user", relation="manager", page=PaginationRequest(size=10)
    )

    assert len(resp.relations) == 4


@pytest.mark.asyncio
async def test_check_relation(directory: Directory):
    check_true = await directory.check_relation(
        object_type="group",
        object_id="evil_genius",
        relation="member",
        subject_type="user",
        subject_id="rick@the-citadel.com",
    )

    check_false = await directory.check_relation(
        object_type="group",
        object_id="evil_genius",
        relation="member",
        subject_type="user",
        subject_id="morty@the-citadel.com",
    )

    assert check_true == True
    assert check_false == False


@pytest.mark.asyncio
async def test_check_permission(directory: Directory):
    check_true = await directory.check_permission(
        object_type="user",
        object_id="rick@the-citadel.com",
        permission="complain",
        subject_type="user",
        subject_id="morty@the-citadel.com",
    )

    check_false = await directory.check_permission(
        object_type="user",
        object_id="summer@the-smiths.com",
        permission="complain",
        subject_type="user",
        subject_id="morty@the-citadel.com",
    )

    assert check_true == True
    assert check_false == False


@pytest.mark.asyncio
async def test_get_manifest(directory: Directory):
    manifest = await directory.get_manifest()

    with open("test/assets/manifest.yaml", "rb") as f:
        expected = f.read()

    assert manifest is not None
    assert manifest.etag
    assert manifest.updated_at.date() == datetime.datetime.utcnow().date()
    assert manifest.body == expected


@pytest.mark.asyncio
async def test_get_manifest_not_modified(directory: Directory):
    m1 = await directory.get_manifest()
    assert m1 is not None

    m2 = await directory.get_manifest(m1.etag)
    assert m2 is None


@pytest.mark.asyncio
async def test_set_manifest(directory: Directory):
    with open("test/assets/manifest.yaml", "rb") as f:
        manifest = f.read()

    manifest += b"\n  baz: {}"

    await directory.set_manifest(manifest)

    new_manifest = await directory.get_manifest()

    assert new_manifest.body == manifest


@pytest.mark.asyncio
async def test_set_manifest_if_match(directory: Directory):
    with open("test/assets/manifest.yaml", "rb") as f:
        manifest = f.read()

    manifest += b"\n  bam: {}"

    with pytest.raises(ETagMismatchError):
        await directory.set_manifest(manifest, etag="1234")

    current = await directory.get_manifest()

    await directory.set_manifest(manifest, etag=current.etag)


@pytest.mark.asyncio
async def test_import(directory: Directory):
    async def data():
        yield Object(type="user", id="test@acmecorp.com")
        yield Relation(
            object_type="user",
            object_id="rick@the-citadel.com",
            relation="manager",
            subject_type="user",
            subject_id="test@acmecorp.com",
        )

    resp = await directory.import_data(data())
    assert resp is not None
    assert resp.objects.recv == 1
    assert resp.objects.set == 1
    assert resp.relations.recv == 1
    assert resp.relations.set == 1


@pytest.mark.asyncio
async def test_export(directory: Directory):
    obj_count = 0
    rel_count = 0
    async for item in directory.export_data(ExportOption.OPTION_DATA):
        if isinstance(item, Object):
            obj_count += 1
        elif isinstance(item, Relation):
            rel_count += 1

    assert obj_count == 20
    assert rel_count == 20
