import datetime
import typing

from aserto.directory.common.v3 import Object, PaginationRequest, Relation
import aserto.directory.exporter.v3 as exporter
import aserto.directory.importer.v3 as importer
import aserto.directory.model.v3 as model
import aserto.directory.reader.v3 as reader
from aserto.directory.reader.v3 import GetObjectResponse, GetObjectsResponse
import aserto.directory.writer.v3 as writer
import google.protobuf.json_format as json_format
from google.protobuf.struct_pb2 import Struct
import grpc

import aserto.client.directory as directory
from aserto.client.directory import NotFoundError
import aserto.client.directory.v3.helpers as helpers
from aserto.client.directory.v3.helpers import (
    ETagMismatchError,
    ExportOption,
    FindResponse,
    ImportCounter,
    ImportResponse,
    Manifest,
    ObjectIdentifier,
    RelationResponse,
    RelationsResponse,
)


class Directory:
    def __init__(
        self,
        api_key: str = "",
        tenant_id: str = "",
        ca_cert_path: str = "",
        address: str = "",
        reader_address: str = "",
        writer_address: str = "",
        importer_address: str = "",
        exporter_address: str = "",
        model_address: str = "",
    ) -> None:
        self._channels = directory.Channels(
            default_address=address,
            reader_address=reader_address,
            writer_address=writer_address,
            importer_address=importer_address,
            exporter_address=exporter_address,
            model_address=model_address,
            ca_cert_path=ca_cert_path,
        )

        self._metadata = directory.get_metadata(api_key=api_key, tenant_id=tenant_id)

        reader_channel = self._channels.get(reader_address, address)
        self._reader = reader.ReaderStub(reader_channel) if reader_channel is not None else None

        writer_channel = self._channels.get(writer_address, address)
        self._writer = writer.WriterStub(writer_channel) if writer_channel is not None else None

        model_channel = self._channels.get(model_address, address)
        self._model = model.ModelStub(model_channel) if model_channel is not None else None

        importer_channel = self._channels.get(importer_address, address)
        self._importer = (
            importer.ImporterStub(importer_channel) if importer_channel is not None else None
        )

        exporter_channel = self._channels.get(exporter_address, address)
        self._exporter = (
            exporter.ExporterStub(exporter_channel) if exporter_channel is not None else None
        )

    def reader(self) -> reader.ReaderStub:
        if self._reader is None:
            raise directory.ConfigError("reader service address not specified")

        return self._reader

    def writer(self) -> writer.WriterStub:
        if self._writer is None:
            raise directory.ConfigError("writer service address not specified")

        return self._writer

    def importer(self) -> importer.ImporterStub:
        if self._importer is None:
            raise directory.ConfigError("importer service address not specified")

        return self._importer

    def exporter(self) -> exporter.ExporterStub:
        if self._exporter is None:
            raise directory.ConfigError("expoerter service address not specified")

        return self._exporter

    def model(self) -> model.ModelStub:
        if self._model is None:
            raise directory.ConfigError("model service address not specified")

        return self._model

    @typing.overload
    def get_object(
        self,
        object_type: str,
        object_id: str,
        with_relations: typing.Literal[False] = False,
        page: typing.Optional[PaginationRequest] = None,
    ) -> Object:
        ...

    @typing.overload
    def get_object(
        self,
        object_type: str,
        object_id: str,
        with_relations: typing.Literal[True],
        page: typing.Optional[PaginationRequest] = None,
    ) -> GetObjectResponse:
        ...

    def get_object(
        self,
        object_type: str,
        object_id: str,
        with_relations: bool = False,
        page: typing.Optional[PaginationRequest] = None,
    ) -> typing.Union[Object, GetObjectResponse]:
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
        page: typing.Optional[PaginationRequest]
            paging information - used to iterate over all relations for an object when with_relations is True.

        Returns
        ----
        a directory object or, if with_relations is True, a GetObjectResponse.
        """

        try:
            response = self.reader().GetObject(
                reader.GetObjectRequest(
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
        identifiers: typing.Sequence[ObjectIdentifier],
    ) -> typing.List[Object]:
        """Retrieve a list of directory object using a list of object key and type pairs.
        Returns a list of the requested objects.
        Raises a NotFoundError if any of the objects don't exist.

        Parameters
        ----
        identifiers: typing.Sequence[ObjectIdentifier]
            sequence of object type and id pairs.

        Returns
        ----
        list
            list of directory objects
        """

        try:
            response = self.reader().GetObjectMany(
                reader.GetObjectManyRequest(param=(i.proto for i in identifiers)),
                metadata=self._metadata,
            )
            return response.results
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.NOT_FOUND:  # type: ignore
                raise NotFoundError from err
            raise

    def get_objects(
        self, object_type: str = "", page: typing.Optional[PaginationRequest] = None
    ) -> GetObjectsResponse:
        """typing.Lists directory objects, optionally filtered by type.

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

        response = self.reader().GetObjects(
            reader.GetObjectsRequest(object_type=object_type, page=page),
            metadata=self._metadata,
        )
        return response

    @typing.overload
    def set_object(self, *, object: Object) -> Object:
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
        ...

    @typing.overload
    def set_object(
        self,
        *,
        object_type: str,
        object_id: str,
        display_name: str = "",
        properties: typing.Optional[typing.Union[typing.Mapping[str, typing.Any], Struct]] = None,
        etag: str = "",
    ) -> Object:
        """Create a new directory object or updates an existing object if an object with the same type and id already exists.
        To update an existing object, the etag argument must be set to the value of the current object's etag.
        Returns the created/updated object.

        Parameters
        ----
        object_type: str
            the type of object to create/update.
        object_id: str
            the ID of the object to create/update.
        display_name: str,
            optional display name for the object.
        properties: typing.Optional[typing.Union[typing.Mapping[str, typing.Any], Struct]],
            optional JSON properties to set on the object. This can be passed in as a dict with string keys and
            JSON-serializable values, or as a Struct.
        etag: str
            optional etag. If set and the current object's etag doesn't match, the call raises an EtagMismatchError.

        Returns
        ----
        The created/updated object.
        """
        ...

    def set_object(
        self,
        *,
        object: typing.Optional[Object] = None,
        object_type: str = "",
        object_id: str = "",
        display_name: str = "",
        properties: typing.Optional[typing.Union[typing.Mapping[str, typing.Any], Struct]] = None,
        etag: str = "",
    ) -> Object:
        obj = object
        if obj is None:
            properties = properties or {}
            props = (
                properties
                if isinstance(properties, Struct)
                else json_format.ParseDict(properties, Struct())
            )

            obj = Object(
                type=object_type,
                id=object_id,
                display_name=display_name,
                properties=props,
                etag=etag,
            )

        try:
            response = self.writer().SetObject(
                writer.SetObjectRequest(object=obj), metadata=self._metadata
            )
            return response.result
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.FAILED_PRECONDITION:  # type: ignore
                raise ETagMismatchError from err
            raise

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

        self.writer().DeleteObject(
            writer.DeleteObjectRequest(
                object_type=object_type, object_id=object_id, with_relations=with_relations
            ),
            metadata=self._metadata,
        )

    @typing.overload
    def get_relation(
        self,
        object_type: str = "",
        object_id: str = "",
        relation: str = "",
        subject_type: str = "",
        subject_id: str = "",
        subject_relation: str = "",
        with_objects: typing.Literal[False] = False,
    ) -> Relation:
        ...

    @typing.overload
    def get_relation(
        self,
        object_type: str = "",
        object_id: str = "",
        relation: str = "",
        subject_type: str = "",
        subject_id: str = "",
        subject_relation: str = "",
        with_objects: typing.Literal[True] = True,
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
    ) -> typing.Union[Relation, RelationResponse]:
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
            response = self.reader().GetRelation(
                reader.GetRelationRequest(
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
            objects = helpers.relation_objects(response.objects)
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
        page: typing.Optional[PaginationRequest] = None,
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
            objects: typing.Mapping[str, Object]
                map from "type:id" to the corresponding object, if with_objects is True.
            page : PaginationResponse(result_size: int, next_token: str)
                retrieved page information — the size of the page, and the next page's token
        """

        response = self.reader().GetRelations(
            reader.GetRelationsRequest(
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
            objects=helpers.relation_objects(response.objects),
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

        response = self.writer().SetRelation(
            writer.SetRelationRequest(
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
        subject_relation: typing.Optional[str] = None,
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
        subject_relation: typing.Optional[str]
            the type of subject relation, if any.

        Returns
        ----
        None
        """

        self.writer().DeleteRelation(
            writer.DeleteRelationRequest(
                object_type=object_type,
                object_id=object_id,
                relation=relation,
                subject_type=subject_type,
                subject_id=subject_id,
                subject_relation=subject_relation,
            ),
            metadata=self._metadata,
        )

    def find_subjects(
        self,
        object_type: str,
        object_id: str,
        relation: str,
        subject_type: str,
        subject_relation: str = "",
        explain: bool = False,
        trace: bool = False,
    ) -> FindResponse:
        """Find subjects that have a given relation to or permission on a specified object.

        Parameters
        ----
        object_type : str
            the type of object to search from.
        object_id: str
            the id of the object to search from.
        relation: str
            the relation or permission to look for.
        subject_type : str
            the type of subject to search for.
        subject_relation: str
            optional subject relation. This is useful when searching for intermediate subjects like groups.
        explain: bool
            if True, the response includes, for each match, the set of relations that grant the specified relation or
            permission .
        trace: bool
            if True, the response includes the trace of the search process.

        Returns
        ----
        FindResponse
        """
        resp = self.reader().GetGraph(
            reader.GetGraphRequest(
                object_type=object_type,
                object_id=object_id,
                relation=relation,
                subject_type=subject_type,
                subject_relation=subject_relation,
                explain=explain,
                trace=trace,
            ),
            metadata=self._metadata,
        )

        return FindResponse(
            [ObjectIdentifier(type=r.object_type, id=r.object_id) for r in resp.results],
            helpers.explanation_to_dict(resp.explanation),
            resp.trace,
        )

    def find_objects(
        self,
        object_type: str,
        relation: str,
        subject_type: str,
        subject_id: str,
        subject_relation: str = "",
        explain: bool = False,
        trace: bool = False,
    ) -> FindResponse:
        """Find objects that a given subject has a specified relation to or permission on.

        Parameters
        ----
        object_type : str
            the type of object to search for.
        relation: str
            the relation or permission to look for.
        subject_type : str
            the type of subject to search from.
        subject_id: str
            the id of the subject to search from.
        subject_relation: str
            optional subject relation. This is useful when searching for intermediate subjects like groups.
        explain: bool
            if True, the response includes, for each match, the set of relations that grant the specified relation or
            permission .
        trace: bool
            if True, the response includes the trace of the search process.

        Returns
        ----
        FindResponse
        """
        resp = self.reader().GetGraph(
            reader.GetGraphRequest(
                object_type=object_type,
                relation=relation,
                subject_type=subject_type,
                subject_id=subject_id,
                subject_relation=subject_relation,
                explain=explain,
                trace=trace,
            ),
            metadata=self._metadata,
        )

        return FindResponse(
            [ObjectIdentifier(type=r.object_type, id=r.object_id) for r in resp.results],
            helpers.explanation_to_dict(resp.explanation),
            resp.trace,
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

        response = self.reader().Check(
            reader.CheckRequest(
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

        response = self.reader().CheckRelation(
            reader.CheckRelationRequest(
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

        response = self.reader().CheckPermission(
            reader.CheckPermissionRequest(
                object_type=object_type,
                object_id=object_id,
                permission=permission,
                subject_type=subject_type,
                subject_id=subject_id,
            ),
            metadata=self._metadata,
        )
        return response.check

    @typing.overload
    def get_manifest(self) -> Manifest:
        ...

    @typing.overload
    def get_manifest(self, etag: str) -> typing.Optional[Manifest]:
        ...

    def get_manifest(self, etag: str = "") -> typing.Optional[Manifest]:
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
        for resp in self.model().GetManifest(model.GetManifestRequest(), metadata=headers):
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
            self.model().SetManifest(
                (
                    model.SetManifestRequest(
                        body=model.Body(data=body[i : i + helpers.MAX_CHUNK_BYTES])
                    )
                    for i in range(0, len(body), helpers.MAX_CHUNK_BYTES)
                ),
                metadata=headers,
            )
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.FAILED_PRECONDITION:  # type: ignore
                raise ETagMismatchError from err
            raise

    def import_data(self, data: typing.Sequence[typing.Union[Object, Relation]]) -> ImportResponse:
        """Imports data into the directory.

        Parameters
        ----
        data: typing.Sequence[typing.Union[Object, Relation]]
            a sequence of objects and/or relations to import.

        Returns:
        ----
        ImportResponse:
            a summary of the total number of object and relations imported.
        """

        def _import_iter() -> typing.Iterator[importer.ImportRequest]:
            for item in data:
                if isinstance(item, Object):
                    yield importer.ImportRequest(op_code=importer.Opcode.OPCODE_SET, object=item)
                elif isinstance(item, Relation):
                    yield importer.ImportRequest(op_code=importer.Opcode.OPCODE_SET, relation=item)

        obj_counter = ImportCounter()
        rel_counter = ImportCounter()

        for r in self.importer().Import(_import_iter(), metadata=self._metadata):
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

    def export_data(
        self, options: ExportOption, start_from: typing.Optional[datetime.datetime] = None
    ) -> typing.Iterator[typing.Union[Object, Relation]]:
        """Exports data from the directory.

        Parameters
        ----
        options: ExportOption
            OPTION_DATA_OBJECTS - only export objects
            OPTION_DATA_RELATIONS - only export relations
            OPTION_DATA - export both objects and relations

        start_from: typing.Optional[datetime.datetime]
            if provided, only objects and relations that have been modified after this date are exported.
        """

        req = exporter.ExportRequest(options=options)
        if start_from is not None:
            req.start_from.FromDatetime(dt=start_from)

        for resp in self.exporter().Export(req, metadata=self._metadata):
            field = resp.WhichOneof("msg")
            if field == "object":
                yield resp.object
            elif field == "relation":
                yield resp.relation

    def close(self) -> None:
        """Closes the gRPC channel"""
        self._channels.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback) -> None:
        self.close()


__all__ = [
    "Directory",
    "GetObjectResponse",
    "GetObjectsResponse",
    "Object",
    "NotFoundError",
    "PaginationRequest",
    "Relation",
    "Struct",
    "ETagMismatchError",
    "ExportOption",
    "ImportCounter",
    "ImportResponse",
    "Manifest",
    "ObjectIdentifier",
    "RelationResponse",
    "RelationsResponse",
]
