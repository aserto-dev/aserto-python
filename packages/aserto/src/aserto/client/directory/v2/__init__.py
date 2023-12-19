from typing import List, Literal, Optional, Sequence, Union, overload, Any

import aserto.directory.common.v2 as common
import aserto.directory.exporter.v2 as exporter
import aserto.directory.importer.v2 as importer
import aserto.directory.reader.v2 as reader
import aserto.directory.writer.v2 as writer
import grpc
from aserto.directory.common.v2 import Object, PaginationRequest, Relation
from aserto.directory.reader.v2 import (
    GetObjectResponse,
    GetObjectsResponse,
    GetRelationsResponse,
)

import aserto.client.directory as directory
import aserto.client.directory.v2.helpers as helpers
from aserto.client.directory import ConfigError, NotFoundError
from aserto.client.directory.v2.helpers import ObjectIdentifier, RelationResponse

class Directory:
    def __init__(
        self,
        *,
        api_key: str = "",
        tenant_id: str = "",
        ca_cert_path: str = "",
        address: str = "",
        reader_address: str = "",
        writer_address: str = "",
        importer_address: str = "",
        exporter_address: str = "",
    ) -> None:
        self._channels = directory.Channels(default_address=address, reader_address=reader_address, writer_address=writer_address,
                            importer_address=importer_address, exporter_address=exporter_address, ca_cert_path=ca_cert_path)

        self._metadata = directory.get_metadata(api_key=api_key, tenant_id=tenant_id)

        reader_channel = self._channels.get(reader_address, address)
        self._reader = (
            reader.ReaderStub(reader_channel)
            if reader_channel is not None
            else None
        )

        writer_channel = self._channels.get(writer_address, address)
        self._writer = (
            writer.WriterStub(writer_channel)
            if writer_channel is not None
            else None
        )

        importer_channel = self._channels.get(importer_address, address)
        self._importer = (
            importer.ImporterStub(importer_channel)
            if importer_channel is not None
            else None
        )

        exporter_channel = self._channels.get(exporter_address, address)
        self._exporter = (
            exporter.ExporterStub(exporter_channel)
            if exporter_channel is not None
            else None
        )

    def reader(self) -> reader.ReaderStub:
        if self._reader is None:
            raise ConfigError("reader service address not specified")
        
        return self._reader
    
    def writer(self) -> writer.WriterStub:
        if self._writer is None:
            raise ConfigError("writer service address not specified")
        
        return self._writer
    
    def importer(self) -> importer.ImporterStub:
        if self._importer is None:
            raise ConfigError("importer service address not specified")
        
        return self._importer
    
    def exporter(self) -> exporter.ExporterStub:
        if self._exporter is None:
            raise ConfigError("expoerter service address not specified")
        
        return self._exporter

    @overload
    def get_object(
        self,
        object_type: str,
        object_key: str,
        with_relations: Literal[False] = False,
        page: Optional[PaginationRequest] = None,
    ) -> Object:
        ...

    @overload
    def get_object(
        self,
        object_type: str,
        object_key: str,
        with_relations: Literal[True],
        page: Optional[PaginationRequest] = None,
    ) -> GetObjectResponse:
        ...

    def get_object(
        self,
        object_type: str,
        object_key: str,
        with_relations: bool = False,
        page: Optional[PaginationRequest] = None,
    ) -> Union[Object, GetObjectResponse]:
        """Retrieve a directory object by its type and id, optionally with the object's relations.
        Raises a NotFoundError if an object with the specified type and id doesn't exist.

        Parameters
        ----
        object_type: str
            the type of object to retrieve.
        object_key: str
            the key of the object to retrieve.
        with_relations: bool
            if True, the response includes all relations for the object. Default: False.
        page: Optional[PaginationRequest]
            paging information - used to iterate over all relations for an object when with_relations is True.

        Returns
        ----
        a directory object or, if with_relations is True, a GetObjectResponse.
        """

        try:
            response = self.reader().GetObject(
                reader.GetObjectRequest(
                    param=common.ObjectIdentifier(type=object_type, key=object_key),
                    with_relations=with_relations,
                    page=page,
                ),
                metadata=self._metadata,
            )
            if with_relations:
                return response

            return response.result

        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.NOT_FOUND:  # type: ignore # err.code() is a method on RpcError
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
        objects : list( dict(key: str, type: str) )
            list of object key and object type pairs

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

        response = self.reader().GetObjects(
            reader.GetObjectsRequest(
                param=common.ObjectTypeIdentifier(name=object_type), page=page
            ),
            metadata=self._metadata,
        )
        return response

    def set_object(self, object: Object) -> Object:
        """Create a new directory object or updates an existing object if an object with the same type and key already exists.
        To update an existing object, the etag field must be set to the value of the current object's etag.
        Returns the created/updated object.

        Parameters
        ----
        object : Object

        Returns
        ----
        The created/updated object.
        """

        response = self.writer().SetObject(
            writer.SetObjectRequest(object=object), metadata=self._metadata
        )
        return response.result

    def delete_object(
        self, object_type: str, object_key: str, with_relations: bool = False
    ) -> None:
        """Deletes a directory object given its type and key.

        Parameters
        ----
        object_type: str
            the type of object to delete.
        object_key: str
            the key of the object to delete.
        with_relations: bool
            if True, delete the object and all its relations. Default: False.

        Returns
        ----
        None
        """

        self.writer().DeleteObject(
            writer.DeleteObjectRequest(
                param=common.ObjectIdentifier(type=object_type, key=object_key),
                with_relations=with_relations,
            ),
            metadata=self._metadata,
        )

    @overload
    def get_relation(
        self,
        object_type: str = "",
        object_key: str = "",
        relation: str = "",
        subject_type: str = "",
        subject_key: str = "",
        with_objects: Literal[False] = False,
    ) -> Relation:
        ...

    @overload
    def get_relation(
        self,
        object_type: str = "",
        object_key: str = "",
        relation: str = "",
        subject_type: str = "",
        subject_key: str = "",
        with_objects: Literal[True] = True,
    ) -> RelationResponse:
        ...

    def get_relation(
        self,
        object_type: str = "",
        object_key: str = "",
        relation: str = "",
        subject_type: str = "",
        subject_key: str = "",
        with_objects: bool = False,
    ) -> Union[Relation, RelationResponse]:
        """Retrieve a directory relation that matches the specified filters.
        Raises a NotFoundError no matching relation is found.
        Also returns the relation's object and subject if with_objects is set to True.

        Parameters
        ----
        object_type : str
            the type of the relation's object.
        object_key: str
            the key of the relation's object.
        relation: str
            the type of relation. If specified, object_type must also be specified.
        subject_type : str
            the type of the relation's subject.
        subject_key: str
            the key of the relation's subject. If specified, subject_type must also be specified.
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
                    param=common.RelationIdentifier(
                        object=common.ObjectIdentifier(type=object_type, key=object_key),
                        subject=common.ObjectIdentifier(type=subject_type, key=subject_key),
                        relation=common.RelationTypeIdentifier(
                            name=relation, object_type=object_type
                        ),
                    ),
                    with_objects=with_objects,
                ),
                metadata=self._metadata,
            )
            if not with_objects:
                return response.results[0]

            rel = response.results[0]
            objects = helpers.relation_objects(response.objects)
            return RelationResponse(
                relation=rel,
                object=objects[ObjectIdentifier(rel.object.type, rel.object.key)],
                subject=objects[ObjectIdentifier(rel.subject.type, rel.subject.key)],
            )

        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.NOT_FOUND:  # type: ignore
                raise NotFoundError from err
            raise

    def get_relations(
        self,
        object_type: str = "",
        object_key: str = "",
        relation: str = "",
        subject_type: str = "",
        subject_key: str = "",
        page: Optional[PaginationRequest] = None,
    ) -> GetRelationsResponse:
        """Searches for relations matching the specified fields.

        Parameters
        ----
        object_type : str
            include relations where the object is of this type.
        object_key: str
            include relations where the object has this key. If specified, object_type must also be specified.
        relation: str
            include relations of this type. If specified, object_type must also be specified.
        subject_type : str
            include relations where the subject is of this type.
        subject_key: str
            include relations where the subject has this key. If specified, subject_type must also be specified.
        with_objects: bool
            If True, the response includes the object and subject for each relation. Default: False.
        page : PaginationRequest
            paging information — the size of the page, and the pagination start token

        Returns
        ----
        RelationsResponse
            results: list(Relation)
                list of directory relations
            objects: Mapping[str, Object]
                map from "type:id" to the corresponding object, if with_objects is True.
            page : PaginationResponse(result_size: int, next_token: str)
                retrieved page information — the size of the page, and the next page's token
        """

        return self.reader().GetRelations(
            reader.GetRelationsRequest(
                param=common.RelationIdentifier(
                    object=common.ObjectIdentifier(type=object_type, key=object_key),
                    subject=common.ObjectIdentifier(type=subject_type, key=subject_key),
                    relation=common.RelationTypeIdentifier(name=relation, object_type=object_type),
                ),
                page=page,
            ),
            metadata=self._metadata,
        )

    def set_relation(
        self, object_type: str, object_key: str, relation: str, subject_type: str, subject_key: str
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

        Returns
        ----
        The created relation
        """

        response = self.writer().SetRelation(
            writer.SetRelationRequest(
                relation=Relation(
                    object=common.ObjectIdentifier(type=object_type, key=object_key),
                    relation=relation,
                    subject=common.ObjectIdentifier(type=subject_type, key=subject_key),
                )
            ),
            metadata=self._metadata,
        )
        return response.result

    def delete_relation(
        self,
        object_type: str,
        object_key: str,
        relation: str,
        subject_type: str,
        subject_key: str,
    ) -> None:
        """Deletes a relation.

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

        Returns
        ----
        None
        """

        relation_identifier = common.RelationIdentifier(
            object=common.ObjectIdentifier(type=object_type, key=object_key),
            subject=common.ObjectIdentifier(type=subject_type, key=subject_key),
            relation=common.RelationTypeIdentifier(name=relation, object_type=object_type),
        )
        self.writer().DeleteRelation(
            writer.DeleteRelationRequest(param=relation_identifier), metadata=self._metadata
        )

    def check_relation(
        self,
        object_type: str,
        object_key: str,
        relation: str,
        subject_type: str,
        subject_key: str,
    ) -> bool:
        """Returns True if the specified relation exists between the given object and subject.

        Parameters
        ----
        object_type : str
            the type of object to check.
        object_key: str
            the key of the object to check.
        relation: str
            the type of relation to look for.
        subject_type : str
            the type of subject to check.
        subject_key: str
            the key of the subject to check.

        Returns
        ----
        True or False
        """

        response = self.reader().CheckRelation(
            reader.CheckRelationRequest(
                object=common.ObjectIdentifier(type=object_type, key=object_key),
                subject=common.ObjectIdentifier(type=subject_type, key=subject_key),
                relation=common.RelationTypeIdentifier(name=relation, object_type=object_type),
            ),
            metadata=self._metadata,
        )
        return response.check

    def check_permission(
        self,
        object_type: str,
        object_key: str,
        permission: str,
        subject_type: str,
        subject_key: str,
    ) -> bool:
        """Checks if a subject has a given permission on an object.
        Returns True if the subject has the specified permission on the object. False, otherwise.

        Parameters
        ----
        object_type : str
            the type of object to check.
        object_key: str
            the key of the object to check.
        permission: str
            the permission to look for.
        subject_type : str
            the type of subject to check.
        subject_key: str
            the key of the subject to check.
        Returns
        ----
        True or False
        """

        response = self.reader().CheckPermission(
            reader.CheckPermissionRequest(
                object=common.ObjectIdentifier(type=object_type, key=object_key),
                subject=common.ObjectIdentifier(type=subject_type, key=subject_key),
                permission=common.PermissionIdentifier(name=permission),
            ),
            metadata=self._metadata,
        )
        return response.check

    def close(self) -> None:
        """Closes the gRPC channel"""
        self._channels.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


__all__ = [
    "Directory",
    "GetObjectResponse",
    "GetObjectsResponse",
    "GetRelationsResponse",
    "NotFoundError",
    "Object",
    "ObjectIdentifier",
    "PaginationRequest",
    "Relation",
    "RelationResponse",
]
