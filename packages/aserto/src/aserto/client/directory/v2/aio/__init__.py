from typing import List, Literal, Optional, Sequence, Union, overload

import grpc.aio as grpc
from aserto.directory.common.v2 import Object
from aserto.directory.common.v2 import ObjectIdentifier as ObjectIdentifierProto
from aserto.directory.common.v2 import (
    ObjectTypeIdentifier,
    PaginationRequest,
    PermissionIdentifier,
    Relation,
    RelationIdentifier,
    RelationTypeIdentifier,
)
from aserto.directory.exporter.v2 import ExporterStub
from aserto.directory.importer.v2 import ImporterStub
from aserto.directory.reader.v2 import (
    CheckPermissionRequest,
    CheckRelationRequest,
    GetObjectManyRequest,
    GetObjectRequest,
    GetObjectResponse,
    GetObjectsRequest,
    GetObjectsResponse,
    GetRelationRequest,
    GetRelationsRequest,
    GetRelationsResponse,
    ReaderStub,
)
from aserto.directory.writer.v2 import (
    DeleteObjectRequest,
    DeleteRelationRequest,
    SetObjectRequest,
    SetRelationRequest,
    WriterStub,
)
from grpc import RpcError, StatusCode

from aserto.client.directory import NotFoundError, channel_credentials, get_metadata
from aserto.client.directory.v2.helpers import (
    ObjectIdentifier,
    RelationResponse,
    relation_objects,
)


class Directory:
    def __init__(
        self,
        *,
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
        self.importer = ImporterStub(self._channel)
        self.exporter = ExporterStub(self._channel)

    @overload
    async def get_object(
        self,
        object_type: str,
        object_key: str,
        with_relations: Literal[False] = False,
        page: Optional[PaginationRequest] = None,
    ) -> Object:
        ...

    @overload
    async def get_object(
        self,
        object_type: str,
        object_key: str,
        with_relations: Literal[True],
        page: Optional[PaginationRequest] = None,
    ) -> GetObjectResponse:
        ...

    async def get_object(
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
            response = await self.reader.GetObject(
                GetObjectRequest(
                    param=ObjectIdentifierProto(type=object_type, key=object_key),
                    with_relations=with_relations,
                    page=page,
                ),
                metadata=self._metadata,
            )
            if with_relations:
                return response

            return response.result

        except RpcError as err:
            if err.code() == StatusCode.NOT_FOUND:  # type: ignore
                raise NotFoundError from err
            raise

    async def get_objects(
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
        response = await self.reader.GetObjects(
            GetObjectsRequest(param=ObjectTypeIdentifier(name=object_type), page=page),
            metadata=self._metadata,
        )
        return response

    async def get_object_many(
        self,
        identifiers: Sequence[ObjectIdentifier],
    ) -> List[Object]:
        """Retrieve a list of directory object using a list of object key and type pairs.
        Returns a list of each objects, if an object with the specified key and type exists.

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
            response = await self.reader.GetObjectMany(
                GetObjectManyRequest(param=(i.proto for i in identifiers)), metadata=self._metadata
            )
        except RpcError as err:
            if err.code() == StatusCode.NOT_FOUND:  # type: ignore
                raise NotFoundError from err
            raise
        return response.results

    async def set_object(self, object: Object) -> Object:
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

        response = await self.writer.SetObject(
            SetObjectRequest(object=object), metadata=self._metadata
        )
        return response.result

    async def delete_object(
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

        await self.writer.DeleteObject(
            DeleteObjectRequest(
                param=ObjectIdentifierProto(type=object_type, key=object_key),
                with_relations=with_relations,
            ),
            metadata=self._metadata,
        )

    async def get_relations(
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

        return await self.reader.GetRelations(
            GetRelationsRequest(
                param=RelationIdentifier(
                    object=ObjectIdentifierProto(type=object_type, key=object_key),
                    subject=ObjectIdentifierProto(type=subject_type, key=subject_key),
                    relation=RelationTypeIdentifier(name=relation, object_type=object_type),
                ),
                page=page,
            ),
            metadata=self._metadata,
        )

    @overload
    async def get_relation(
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
    async def get_relation(
        self,
        object_type: str = "",
        object_key: str = "",
        relation: str = "",
        subject_type: str = "",
        subject_key: str = "",
        with_objects: Literal[True] = True,
    ) -> RelationResponse:
        ...

    async def get_relation(
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
            response = await self.reader.GetRelation(
                GetRelationRequest(
                    param=RelationIdentifier(
                        object=ObjectIdentifierProto(type=object_type, key=object_key),
                        subject=ObjectIdentifierProto(type=subject_type, key=subject_key),
                        relation=RelationTypeIdentifier(name=relation, object_type=object_type),
                    ),
                    with_objects=with_objects,
                ),
                metadata=self._metadata,
            )
            if not with_objects:
                return response.results[0]

            rel = response.results[0]
            objects = relation_objects(response.objects)
            return RelationResponse(
                relation=rel,
                object=objects[ObjectIdentifier(rel.object.type, rel.object.key)],
                subject=objects[ObjectIdentifier(rel.subject.type, rel.subject.key)],
            )

        except RpcError as err:
            if err.code() == StatusCode.NOT_FOUND:  # type: ignore
                raise NotFoundError from err
            raise

    async def set_relation(
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

        response = await self.writer.SetRelation(
            SetRelationRequest(
                relation=Relation(
                    object=ObjectIdentifierProto(type=object_type, key=object_key),
                    relation=relation,
                    subject=ObjectIdentifierProto(type=subject_type, key=subject_key),
                )
            ),
            metadata=self._metadata,
        )
        return response.result

    async def delete_relation(
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

        relation_identifier = RelationIdentifier(
            object=ObjectIdentifierProto(type=object_type, key=object_key),
            subject=ObjectIdentifierProto(type=subject_type, key=subject_key),
            relation=RelationTypeIdentifier(name=relation, object_type=object_type),
        )
        await self.writer.DeleteRelation(
            DeleteRelationRequest(param=relation_identifier), metadata=self._metadata
        )

    async def check_relation(
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

        response = await self.reader.CheckRelation(
            CheckRelationRequest(
                object=ObjectIdentifierProto(type=object_type, key=object_key),
                relation=RelationTypeIdentifier(name=relation, object_type=object_type),
                subject=ObjectIdentifierProto(type=subject_type, key=subject_key),
            ),
            metadata=self._metadata,
        )
        return response.check

    async def check_permission(
        self,
        subject_type: str,
        subject_key: str,
        object_type: str,
        object_key: str,
        permission: str,
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

        response = await self.reader.CheckPermission(
            CheckPermissionRequest(
                object=ObjectIdentifierProto(type=object_type, key=object_key),
                subject=ObjectIdentifierProto(type=subject_type, key=subject_key),
                permission=PermissionIdentifier(name=permission),
            ),
            metadata=self._metadata,
        )
        return response.check

    async def close(self) -> None:
        """Closes the gRPC channel"""

        await self._channel.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        await self.close()
