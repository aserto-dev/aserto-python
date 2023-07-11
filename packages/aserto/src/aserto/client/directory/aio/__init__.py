from dataclasses import asdict, dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import grpc.aio as grpc
from aserto.directory.common.v2 import Object
from aserto.directory.common.v2 import ObjectIdentifier as ObjectIdentifierV2
from aserto.directory.common.v2 import (
    ObjectTypeIdentifier,
    PaginationRequest,
    PaginationResponse,
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
from grpc import ChannelCredentials, StatusCode, ssl_channel_credentials


@dataclass(frozen=True)
class ObjectIdentifier:
    """
    Unique identifier of a directory object.
    """

    key: str
    type: str


@dataclass(frozen=True)
class GetRelationResponse:
    """
    Response to get_relation calls.

    Attributes
    ----
    relation    The returned relation.
    objects     If with_relations is True, a mapping from "type:key" to the corresponding object.
    """

    relation: Relation
    objects: Optional[Mapping[ObjectIdentifier, Object]]


class NotFoundError(Exception):
    pass


class Directory:
    def __init__(
        self,
        *,
        address: str,
        api_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        ca_cert: Optional[str] = None,
    ) -> None:
        self._channel = grpc.secure_channel(
            target=address, credentials=self._channel_credentials(cert=ca_cert)
        )
        self._metadata = self._get_metadata(api_key=api_key, tenant_id=tenant_id)
        self.reader = ReaderStub(self._channel)
        self.writer = WriterStub(self._channel)
        self.importer = ImporterStub(self._channel)
        self.exporter = ExporterStub(self._channel)

    async def get_objects(
        self, object_type: Optional[str] = None, page: Optional[PaginationRequest] = None
    ) -> GetObjectsResponse:
        """Retrieve a page of directory objects by object type and page size.
        Returns a list of directory objects and a token for the next page if it exists.

        Parameters
        ----
        object_type : str
            a directory object type
        page : PaginationRequest(size: int, token: str)
            paging information — the size of the page, and the pagination
            start token

        Returns
        ----
        GetObjectsResponse
            results : list(Object)
                list of directory objects
            page : PaginationResponse(result_size: int, next_token: str)
                retrieved page information — the size of the page,
                and the next page's token
        """

        response = await self.reader.GetObjects(
            GetObjectsRequest(param=ObjectTypeIdentifier(name=object_type), page=page),
            metadata=self._metadata,
        )
        return response

    async def get_objects_many(
        self,
        objects: Sequence[ObjectIdentifier],
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

        identifiers = [ObjectIdentifierV2(**asdict(x)) for x in objects]
        response = await self.reader.GetObjectMany(
            GetObjectManyRequest(param=identifiers),
            metadata=self._metadata,
        )
        return response.results

    async def get_object(self, key: str, type: str) -> Object:
        """Retrieve a directory object by its key and type.
        Returns the object or raises a NotFoundError if an object with the
        specified key and type doesn't exist.

        Parameters
        ----
        key : str
            an object key
        type : str
            an object type

        Returns
        ----
        a directory object
        """

        try:
            identifier = ObjectIdentifierV2(type=type, key=key)
            response = await self.reader.GetObject(
                GetObjectRequest(param=identifier), metadata=self._metadata
            )
            return response.result

        except grpc.AioRpcError as err:
            if err.code() == StatusCode.NOT_FOUND:
                raise NotFoundError from err
            raise

    async def set_object(self, object: Object) -> Object:
        """Updates a directory object given its key and type, or creates a new object.
        Returns the created/updated object.

        Parameters
        ----
        object : Object
            key : str
            type : str
            display_name : str, optional
            properties : dict, optional
            hash : str (required, if updating existing object)

        Returns
        ----
        a directory object
        """

        response = await self.writer.SetObject(
            SetObjectRequest(object=object), metadata=self._metadata
        )
        return response.result

    async def delete_object(self, key: str, type: str) -> None:
        """Deletes a directory object given its key and type.
        Returns None.

        Parameters
        ----
        key : str
            an object key
        type : str
            an object type

        Returns
        ----
        None
        """

        identifier = ObjectIdentifierV2(type=type, key=key)
        await self.writer.DeleteObject(
            DeleteObjectRequest(param=identifier), metadata=self._metadata
        )

    async def get_relations(
        self,
        subject_type: Optional[str] = None,
        subject_key: Optional[str] = None,
        object_type: Optional[str] = None,
        object_key: Optional[str] = None,
        relation_type: Optional[str] = None,
        page: Optional[PaginationRequest] = None,
    ) -> GetRelationsResponse:
        """Retrieve a page of directory relations by any of the parameters
        object's type and key, subject's type and key, relation type name, and page size.
        Returns a list of directory relations and a token for the next page if it exists.
        object --relation_type--> subject

        Parameters
        ----
        subject_type : str
            the subject of the relation, a directory object type
        subject_key : str
            the subject of the relation, a directory object key
        object_type : str
            the object of the relation, a directory object type
        object_key : str
            the object of the relation, a directory object key
        relation_type : str
            a directory relation type
        page : PaginationRequest(size: int, token: str)
            paging information — the size of the page, and the pagination
            start token

        Returns
        ----
        GetRelationsResponse
            results : list(Relation)
                list of directory relations
            page : PaginationResponse(result_size: int, next_token: str)
                retrieved page information — the size of the page,
                and the next page's token
        """

        response = await self.reader.GetRelations(
            GetRelationsRequest(
                param=RelationIdentifier(
                    object=ObjectIdentifierV2(type=object_type, key=object_key),
                    subject=ObjectIdentifierV2(type=subject_type, key=subject_key),
                    relation=RelationTypeIdentifier(name=relation_type, object_type=object_type),
                ),
                page=page,
            ),
            metadata=self._metadata,
        )
        return response

    async def get_relation(
        self,
        subject_type: Optional[str] = None,
        subject_key: Optional[str] = None,
        object_type: Optional[str] = None,
        object_key: Optional[str] = None,
        relation_type: Optional[str] = None,
        with_objects: Optional[bool] = None,
    ) -> GetRelationResponse:
        """Retrieve a directory relation by the object's type and key, the subject's type and key,
        and relation type name.
        Returns the relation or raises a NotFoundError if an relation with the
        specified parameters doesn't exist. Also returns the object if with_objects is set to True.
        object --relation_type--> subject

        Parameters
        ----
        subject_type : str
            the subject of the relation, a directory object type
        subject_key : str
            the subject of the relation, a directory object key
        object_type : str (required if relation_type is specified)
            the object of the relation, a directory object type
        object_key : str
            the object of the relation, a directory object key
        relation_type : str
            a directory relation type
        with_objects : bool
            if True, returns the object

        Returns
        ----
        relation : Relation
            a directory relations
        objects : dict(str, Object)
            returned with an Object if with_objects is set to True
        """

        try:
            response = await self.reader.GetRelation(
                GetRelationRequest(
                    param=RelationIdentifier(
                        object=ObjectIdentifierV2(type=object_type, key=object_key),
                        subject=ObjectIdentifierV2(type=subject_type, key=subject_key),
                        relation=RelationTypeIdentifier(
                            name=relation_type, object_type=object_type
                        ),
                    ),
                    with_objects=with_objects,
                ),
                metadata=self._metadata,
            )

            return GetRelationResponse(
                relation=response.results[0],
                objects={
                    ObjectIdentifier(type=k.split(":")[0], key=k.split(":")[1]): obj
                    for (k, obj) in response.objects.items()
                },
            )

        except grpc.AioRpcError as err:
            if err.code() == StatusCode.NOT_FOUND:
                raise NotFoundError from err
            raise

    async def set_relation(self, relation: Relation) -> Relation:
        """Updates a directory relation given the relation name and object type,
        or creates a new relation.
        Returns the created/updated object.

        Parameters
        ----
        relation : Relation
            subject: Object
            relation: str
            object: Object
            hash: str (required, if updating existing relation)

        Returns
        ----
        a directory relation
        """

        response = await self.writer.SetRelation(
            SetRelationRequest(relation=relation), metadata=self._metadata
        )
        return response.result

    async def delete_relation(
        self,
        subject_type: str,
        subject_key: str,
        object_type: str,
        object_key: str,
        relation_type: str,
    ) -> None:
        """Deletes a directory relation the object's type and key, the subject's type and key,
        and relation type name.
        Returns None.
        object --relation_type--> subject

        Parameters
        ----
        subject_type : str
            the subject of the relation, a directory object type
        subject_key : str
            the subject of the relation, a directory object key
        object_type : str
            the object of the relation, a directory object type
        object_key : str
            the object of the relation, a directory object key
        relation_type : str
            a directory relation type

        Returns
        ----
        None
        """

        await self.writer.DeleteRelation(
            DeleteRelationRequest(
                param=RelationIdentifier(
                    object=ObjectIdentifierV2(type=object_type, key=object_key),
                    subject=ObjectIdentifierV2(type=subject_type, key=subject_key),
                    relation=RelationTypeIdentifier(name=relation_type, object_type=object_type),
                )
            ),
            metadata=self._metadata,
        )

    async def check_relation(
        self,
        subject_type: str,
        subject_key: str,
        object_type: str,
        object_key: str,
        relation_type: str,
    ) -> bool:
        """Checks if a subject has a given relation to an object given
        the object's type and key, the subject's type and key,
        and relation type name.
        Returns the result of the relation check, True or False.
        object --relation_type--> subject

        Parameters
        ----
        subject_type : str
            the subject of the relation, a directory object type
        subject_key : str
            the subject of the relation, a directory object key
        object_type : str
            the object of the relation, a directory object type
        object_key : str
            the object of the relation, a directory object key
        relation_type : str
            a directory relation type

        Returns
        ----
        True or False
        """

        response = await self.reader.CheckRelation(
            CheckRelationRequest(
                object=ObjectIdentifierV2(type=object_type, key=object_key),
                subject=ObjectIdentifierV2(type=subject_type, key=subject_key),
                relation=RelationTypeIdentifier(name=relation_type, object_type=object_type),
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
        """Checks if a subject has a given permission on an object given
        the object's type and key, the subject's type and key,
        and permission name.
        Returns the result of the permission check, True or False.

        Parameters
        ----
        subject_type : str
            the subject to check the permission for, a directory object type
        subject_key : str
            the subject to check the permission for, a directory object key
        object_type : str
            the object to check the permission on, a directory object type
        object_key : str
            the object to check the permission on, a directory object key
        permission : str
            a directory permission

        Returns
        ----
        True or False
        """

        response = await self.reader.CheckPermission(
            CheckPermissionRequest(
                object=ObjectIdentifierV2(type=object_type, key=object_key),
                subject=ObjectIdentifierV2(type=subject_type, key=subject_key),
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

    @staticmethod
    def _get_metadata(api_key, tenant_id) -> Tuple:
        md = ()
        if api_key:
            md += (("authorization", f"basic {api_key}"),)
        if tenant_id:
            md += (("aserto-tenant-id", tenant_id),)
        return md

    @staticmethod
    def _channel_credentials(cert) -> ChannelCredentials:
        if cert:
            with open(cert, "rb") as f:
                return ssl_channel_credentials(f.read())
        else:
            return ssl_channel_credentials()
