import datetime
from typing import Iterator, List, Literal, Optional, Sequence, Union, overload

import grpc
from aserto.directory.common.v3 import (
    Object,
    PaginationRequest,
    PaginationResponse,
    Relation,
)
from aserto.directory.exporter.v3 import ExporterStub
from aserto.directory.importer.v3 import ImporterStub, ImportRequest, Opcode
from aserto.directory.model.v3 import (
    Body,
    GetManifestRequest,
    ModelStub,
    SetManifestRequest,
)
from aserto.directory.reader.v3 import (
    CheckPermissionRequest,
    CheckRelationRequest,
    CheckRequest,
    GetObjectManyRequest,
    GetObjectRequest,
    GetObjectResponse,
    GetObjectsRequest,
    GetObjectsResponse,
    GetRelationRequest,
    GetRelationsRequest,
    ReaderStub,
)
from aserto.directory.writer.v3 import (
    DeleteObjectRequest,
    DeleteRelationRequest,
    SetObjectRequest,
    SetRelationRequest,
    WriterStub,
)

from aserto.client.directory import NotFoundError, channel_credentials, get_metadata
from aserto.client.directory.v3.helpers import (
    MAX_CHUNK_BYTES,
    ETagMismatchError,
    ImportCounter,
    ImportResponse,
    Manifest,
    ObjectIdentifier,
    RelationResponse,
    RelationsResponse,
    relation_objects,
)


class Directory:
    def __init__(
        self,
        address: str,
        api_key: str = "",
        tenant_id: str = "",
        ca_cert_path: str = "",
    ) -> None:
        self._channel = grpc.secure_channel(
            target=address, credentials=channel_credentials(cert=ca_cert_path)
        )
        self._metadata = get_metadata(api_key=api_key, tenant_id=tenant_id)
        self.reader = ReaderStub(self._channel)
        self.writer = WriterStub(self._channel)
        self.model = ModelStub(self._channel)
        self.importer = ImporterStub(self._channel)
        self.exporter = ExporterStub(self._channel)

    @overload
    def get_object(
        self,
        object_type: str,
        object_id: str,
        with_relations: Literal[False] = False,
        page: Optional[PaginationRequest] = None,
    ) -> Object:
        ...

    @overload
    def get_object(
        self,
        object_type: str,
        object_id: str,
        with_relations: Literal[True],
        page: Optional[PaginationRequest] = None,
    ) -> GetObjectResponse:
        ...

    def get_object(
        self,
        object_type: str,
        object_id: str,
        with_relations: bool = False,
        page: Optional[PaginationRequest] = None,
    ) -> Union[Object, GetObjectResponse]:
        """Retrieve a directory object by its type and id, optionally with the object's relations.
        Raises a NotFoundError if an object with the specified type and id doesn't exist.

        Parameters
        ----
        object_type: str
            the type of object to retrieve.
        object_id: str
            the ID of the object to retrieve.
        with_relations: bool
            if True, the response includes all relations for the object. Default: False.
        page: Optional[PaginationRequest]
            paging information - used to iterate over all relations for an object when with_relations is True.

        Returns
        ----
        a directory object or, if with_relations is True, a GetObjectResponse.
        """

        try:
            response = self.reader.GetObject(
                GetObjectRequest(
                    object_type=object_type,
                    object_id=object_id,
                    with_relations=with_relations,
                    page=page,
                ),
                metadata=self._metadata,
            )
            if with_relations:
                return response

            return response.result

        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.NOT_FOUND:  # type: ignore
                raise NotFoundError from err
            raise

    def get_object_many(
        self,
        identifiers: Sequence[ObjectIdentifier],
    ) -> List[Object]:
        """Retrieve a list of directory object using a list of object key and type pairs.
        Returns a list of the requested objects.
        Raises a NotFoundError if any of the objects don't exist.

        Parameters
        ----
        identifiers: Sequence[ObjectIdentifier]
            sequence of object type and id pairs.

        Returns
        ----
        list
            list of directory objects
        """

        try:
            response = self.reader.GetObjectMany(
                GetObjectManyRequest(param=(i.proto for i in identifiers)),
                metadata=self._metadata,
            )
            return response.results
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.NOT_FOUND:  # type: ignore
                raise NotFoundError from err
            raise

    def get_objects(
        self, object_type: str = "", page: Optional[PaginationRequest] = None
    ) -> GetObjectsResponse:
        """Lists directory objects, optionally filtered by type.

        Parameters
        ----
        object_type : str
            the type of object to retrieve. If empty, all objects are returned.
        page : PaginationRequest
            paging information — the size of the page, and the pagination token

        Returns
        ----
        GetObjectsResponse
            results : list(Object)
                list of directory objects
            page : PaginationResponse
                the next page's token if there are more results
        """

        response = self.reader.GetObjects(
            GetObjectsRequest(object_type=object_type, page=page),
            metadata=self._metadata,
        )
        return response

    def set_object(self, object: Object) -> Object:
        """Create a new directory object or updates an existing object if an object with the same type and id already exists.
        To update an existing object, the etag field must be set to the value of the current object's etag.
        Returns the created/updated object.

        Parameters
        ----
        object : Object

        Returns
        ----
        The created/updated object.
        """

        response = self.writer.SetObject(SetObjectRequest(object=object), metadata=self._metadata)
        return response.result

    def delete_object(self, object_type: str, object_id: str, with_relations: bool = False) -> None:
        """Deletes a directory object given its type and id.

        Parameters
        ----
        object_type: str
            the type of object to delete.
        object_id: str
            the id of the object to delete.
        with_relations: bool
            if True, delete the object and all its relations. Default: False.

        Returns
        ----
        None
        """

        self.writer.DeleteObject(
            DeleteObjectRequest(
                object_type=object_type, object_id=object_id, with_relations=with_relations
            ),
            metadata=self._metadata,
        )

    @overload
    def get_relation(
        self,
        object_type: str = "",
        object_id: str = "",
        relation: str = "",
        subject_type: str = "",
        subject_id: str = "",
        subject_relation: str = "",
        with_objects: Literal[False] = False,
    ) -> Relation:
        ...

    @overload
    def get_relation(
        self,
        object_type: str = "",
        object_id: str = "",
        relation: str = "",
        subject_type: str = "",
        subject_id: str = "",
        subject_relation: str = "",
        with_objects: Literal[True] = True,
    ) -> RelationResponse:
        ...

    def get_relation(
        self,
        object_type: str = "",
        object_id: str = "",
        relation: str = "",
        subject_type: str = "",
        subject_id: str = "",
        subject_relation: str = "",
        with_objects: bool = False,
    ) -> Union[Relation, RelationResponse]:
        """Retrieve a directory relation that matches the specified filters.
        Raises a NotFoundError no matching relation is found.
        Also returns the relation's object and subject if with_objects is set to True.

        Parameters
        ----
        object_type : str
            the type of the relation's object.
        object_id: str
            the id of the relation's object.
        relation: str
            the type of relation. If specified, object_type must also be specified.
        subject_type : str
            the type of the relation's subject.
        subject_id: str
            the id of the relation's subject. If specified, subject_type must also be specified.
        subject_relation: str
            the type of subject relation. If specified, subject_type must also be specified.
        with_objects : bool
            if True, include the relation's object and subject in the reponse.

        Returns
        ----
            a directory relations
        OR
            a RelationResponse if with_objects is set to True
        """

        try:
            response = self.reader.GetRelation(
                GetRelationRequest(
                    object_type=object_type,
                    object_id=object_id,
                    relation=relation,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    subject_relation=subject_relation,
                    with_objects=with_objects,
                ),
                metadata=self._metadata,
            )

            if not with_objects:
                return response.result

            rel = response.result
            objects = relation_objects(response.objects)
            return RelationResponse(
                relation=rel,
                object=objects[ObjectIdentifier(rel.object_type, rel.object_id)],
                subject=objects[ObjectIdentifier(rel.subject_type, rel.subject_id)],
            )

        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.NOT_FOUND:  # type: ignore
                raise NotFoundError from err
            raise

    def get_relations(
        self,
        object_type: str = "",
        object_id: str = "",
        relation: str = "",
        subject_type: str = "",
        subject_id: str = "",
        subject_relation: str = "",
        with_objects: bool = False,
        page: Optional[PaginationRequest] = None,
    ) -> RelationsResponse:
        """Searches for relations matching the specified fields.

        Parameters
        ----
        object_type : str
            include relations where the object is of this type.
        object_id: str
            include relations where the object has this id. If specified, object_type must also be specified.
        relation: str
            include relations of this type.
        subject_type : str
            include relations where the subject is of this type.
        subject_id: str
            include relations where the subject has this id. If specified, subject_type must also be specified.
        subject_relation: str
            include relations the specified subject relation.
        with_objects: bool
            If True, the response includes the object and subject for each relation. Default: False.
        page : PaginationRequest
            paging information — the size of the page, and the pagination start token

        Returns
        ----
        GetRelationsResponse
            results: list(Relation)
                list of directory relations
            objects: Mapping[str, Object]
                map from "type:id" to the corresponding object, if with_objects is True.
            page : PaginationResponse(result_size: int, next_token: str)
                retrieved page information — the size of the page, and the next page's token
        """

        response = self.reader.GetRelations(
            GetRelationsRequest(
                object_type=object_type,
                object_id=object_id,
                relation=relation,
                subject_type=subject_type,
                subject_id=subject_id,
                subject_relation=subject_relation,
                with_objects=with_objects,
                page=page,
            ),
            metadata=self._metadata,
        )

        return RelationsResponse(
            relations=response.results,
            objects=relation_objects(response.objects),
            page=response.page,
        )

    def set_relation(
        self,
        object_type: str,
        object_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
        subject_relation: str = "",
    ) -> Relation:
        """Creates a directory relation.

        Parameters
        ----
        object_type : str
            the type of the relation's object.
        object_key: str
            the key of the relation's object.
        relation: str
            the type of relation.
        subject_type : str
            the type of the relation's subject.
        subject_key: str
            the key of the relation's subject.
        subject_relation: str
            optional type of subject relation.

        Returns
        ----
        The created relation
        """

        response = self.writer.SetRelation(
            SetRelationRequest(
                relation=Relation(
                    object_type=object_type,
                    object_id=object_id,
                    relation=relation,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    subject_relation=subject_relation,
                )
            ),
            metadata=self._metadata,
        )
        return response.result

    def delete_relation(
        self,
        object_type: str,
        object_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
        subject_relation: Optional[str] = None,
    ) -> None:
        """Deletes a relation.

        Parameters
        ----
        object_type : str
            the type of the relation's object.
        object_id: str
            the id of the relation's object.
        relation: str
            the type of relation.
        subject_type : str
            the type of the relation's subject.
        subject_id: str
            the id of the relation's subject.
        subject_relation: Optional[str]
            the type of subject relation, if any.

        Returns
        ----
        None
        """

        self.writer.DeleteRelation(
            DeleteRelationRequest(
                object_type=object_type,
                object_id=object_id,
                relation=relation,
                subject_type=subject_type,
                subject_id=subject_id,
                subject_relation=subject_relation,
            ),
            metadata=self._metadata,
        )

    def check(
        self,
        object_type: str,
        object_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        """Checks if a subject has a given permissions or relation to an object.
        Returns True if the subject has the specified permission/relation to the object. False, otherwise.

        Parameters
        ----
        object_type : str
            the type of object to check.
        object_id: str
            the id of the object to check.
        relation: str
            the relation or permission to look for.
        subject_type : str
            the type of subject to check.
        subject_id: str
            the id of the subject to check.

        Returns
        ----
        True or False
        """
        response = self.reader.Check(
            CheckRequest(
                object_type=object_type,
                object_id=object_id,
                relation=relation,
                subject_type=subject_type,
                subject_id=subject_id,
            ),
            metadata=self._metadata,
        )
        return response.check

    def check_relation(
        self,
        object_type: str,
        object_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        """Returns True if the specified relation exists between the given object and subject.

        Parameters
        ----
        object_type : str
            the type of object to check.
        object_id: str
            the id of the object to check.
        relation: str
            the type of relation to look for.
        subject_type : str
            the type of subject to check.
        subject_id: str
            the id of the subject to check.

        Returns
        ----
        True or False
        """

        response = self.reader.CheckRelation(
            CheckRelationRequest(
                object_type=object_type,
                object_id=object_id,
                relation=relation,
                subject_type=subject_type,
                subject_id=subject_id,
            ),
            metadata=self._metadata,
        )
        return response.check

    def check_permission(
        self,
        object_type: str,
        object_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        """Checks if a subject has a given permission on an object.
        Returns True if the subject has the specified permission on the object. False, otherwise.

        Parameters
        ----
        object_type : str
            the type of object to check.
        object_id: str
            the id of the object to check.
        permission: str
            the permission to look for.
        subject_type : str
            the type of subject to check.
        subject_id: str
            the id of the subject to check.

        Returns
        ----
        True or False
        """

        response = self.reader.CheckPermission(
            CheckPermissionRequest(
                object_type=object_type,
                object_id=object_id,
                permission=permission,
                subject_type=subject_type,
                subject_id=subject_id,
            ),
            metadata=self._metadata,
        )
        return response.check

    @overload
    def get_manifest(self) -> Manifest:
        ...

    @overload
    def get_manifest(self, etag: str) -> Optional[Manifest]:
        ...

    def get_manifest(self, etag: str = "") -> Optional[Manifest]:
        """Returns the current manifest.
        Returns None if etag is provided and the manifest has not changed.

        Parameters
        ----
        etag: str
            etag of the last known manifest. If the manifest has not changed, None is returned.

        Returns
        ----
        The current manifest or None.
        """
        headers = self._metadata
        if etag:
            headers += (("if-none-match", etag),)

        updated_at = datetime.datetime.min
        current_etag = ""
        body: bytes = b""
        for resp in self.model.GetManifest(GetManifestRequest(), metadata=headers):
            field = resp.WhichOneof("msg")
            if field == "metadata":
                updated_at = resp.metadata.updated_at.ToDatetime()
                current_etag = resp.metadata.etag
            elif field == "body":
                body += resp.body.data

        if etag and not body:
            return None

        return Manifest(updated_at, current_etag, body)

    def set_manifest(self, body: bytes, etag: str = "") -> None:
        """Sets the manifest.

        Parameters
        ----
        body: bytes
            the manifest body.

        Returns
        ----
        None
        """

        headers = self._metadata
        if etag:
            headers += (("if-match", etag),)

        try:
            self.model.SetManifest(
                (
                    SetManifestRequest(body=Body(data=body[i : i + MAX_CHUNK_BYTES]))
                    for i in range(0, len(body), MAX_CHUNK_BYTES)
                ),
                metadata=headers,
            )
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.FAILED_PRECONDITION:  # type: ignore
                raise ETagMismatchError from err
            raise

    def import_data(self, data: Sequence[Union[Object, Relation]]) -> ImportResponse:
        def _import_iter() -> Iterator[ImportRequest]:
            for item in data:
                if isinstance(item, Object):
                    yield ImportRequest(op_code=Opcode.OPCODE_SET, object=item)
                elif isinstance(item, Relation):
                    yield ImportRequest(op_code=Opcode.OPCODE_SET, relation=item)

        obj_counter = ImportCounter()
        rel_counter = ImportCounter()

        for r in self.importer.Import(_import_iter(), metadata=self._metadata):
            if r.object:
                obj_counter = obj_counter.add(
                    ImportCounter(r.object.recv, r.object.set, r.object.delete, r.object.error)
                )
            if r.relation:
                rel_counter = rel_counter.add(
                    ImportCounter(
                        r.relation.recv, r.relation.set, r.relation.delete, r.relation.error
                    )
                )

        return ImportResponse(obj_counter, rel_counter)

    def close(self) -> None:
        """Closes the gRPC channel"""

        self._channel.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback) -> None:
        self.close()
