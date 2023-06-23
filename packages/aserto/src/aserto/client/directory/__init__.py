from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, TypedDict

import grpc
from aserto.directory.common.v2 import (
    Object,
    ObjectIdentifier,
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


class NotFoundError(Exception):
    pass


class Directory:
    def __init__(self, *, address: str, api_key: str, tenant_id: str, ca_cert: str) -> None:
        self._channel = grpc.secure_channel(
            target=address, credentials=self._channel_credentials(cert=ca_cert)
        )
        self._metadata = self._get_metadata(api_key=api_key, tenant_id=tenant_id)
        self.reader = ReaderStub(self._channel)
        self.writer = WriterStub(self._channel)
        self.importer = ImporterStub(self._channel)
        self.exporter = ExporterStub(self._channel)

    def get_objects(
        self, object_type: Optional[str] = None, page: Optional[PaginationRequest] = None
    ) -> GetObjectsResponse:
        response = self.reader.GetObjects(
            GetObjectsRequest(
                param=ObjectTypeIdentifier(name=object_type), page=PaginationRequest(page)
            ),
            metadata=self._metadata,
        )
        return response

    def get_many_objects(
        self,
        objects: Optional[List[TypedDict("ObjectParams", {"key": str, "type": str})]] = None,
    ) -> List[Object]:
        """Retrieve a list of directory object using a list of object key and type pairs.
        Returns a list of each objects, if an object with the specified key and type exists.

        Parameters
        ----------
        objects : list( dict(key: str, type: str) )
            list of object key and object type pairs

        Returns
        ----------
        list
            list of directory objects
        """

        identifiers = [ObjectIdentifier(key=x["key"], type=x["type"]) for x in objects]
        print("identifiers", identifiers)
        response = self.reader.GetObjectMany(
            GetObjectManyRequest(param=identifiers),
            metadata=self._metadata,
        )
        return response.results

    def get_object(self, key: str, type: str) -> Object:
        """Retrieve a directory object by its key and type.
        Returns the object or raises a NotFoundError if an object with the
        specified key and type doesn't exist.

        Parameters
        -------
        key : str
            an object key
        type : str
            an object type

        Returns
        -------
        object
            a directory object"""

        try:
            identifier = ObjectIdentifier(type=type, key=key)
            response = self.reader.GetObject(
                GetObjectRequest(param=identifier), metadata=self._metadata
            )
            return response.result

        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundError from err
            raise

    def set_object(self, object: Object) -> Object:
        response = self.writer.SetObject(SetObjectRequest(object=object), metadata=self._metadata)
        return response.result

    def delete_object(self, key: str, type: str) -> None:
        identifier = ObjectIdentifier(type=type, key=key)
        self.writer.DeleteObject(DeleteObjectRequest(param=identifier), metadata=self._metadata)

    def get_relations(
        self,
        subject_type: Optional[str] = None,
        subject_key: Optional[str] = None,
        object_type: Optional[str] = None,
        object_key: Optional[str] = None,
        relation_type: Optional[str] = None,
        page: Optional[PaginationRequest] = None,
    ) -> GetRelationsResponse:
        response = self.reader.GetRelations(
            GetRelationsRequest(
                param=RelationIdentifier(
                    object=ObjectIdentifier(type=object_type, key=object_key),
                    subject=ObjectIdentifier(type=subject_type, key=subject_key),
                    relation=RelationTypeIdentifier(name=relation_type, object_type=object_type),
                ),
                page=PaginationRequest(page),
            ),
            metadata=self._metadata,
        )
        return response

    def get_relation(
        self,
        subject_type: Optional[str] = None,
        subject_key: Optional[str] = None,
        object_type: Optional[str] = None,
        object_key: Optional[str] = None,
        relation_type: Optional[str] = None,
        with_objects: Optional[bool] = None,
    ) -> Dict[Relation, Optional[Dict[str, Object]]]:
        response = self.reader.GetRelation(
            GetRelationRequest(
                param=RelationIdentifier(
                    object=ObjectIdentifier(type=object_type, key=object_key),
                    subject=ObjectIdentifier(type=subject_type, key=subject_key),
                    relation=RelationTypeIdentifier(name=relation_type, object_type=object_type),
                ),
                with_objects=with_objects,
            ),
            metadata=self._metadata,
        )

        if not len(response.results):
            raise NotFoundError
        return {"relation": response.results[0], "objects": response.objects}

    def set_relation(self, relation: Relation) -> Relation:
        response = self.writer.SetRelation(
            SetRelationRequest(relation=relation), metadata=self._metadata
        )
        return response.result

    def delete_relation(
        self,
        subject_type: str,
        subject_key: str,
        object_type: str,
        object_key: str,
        relation_type: str,
    ) -> None:
        relation_identifier = RelationIdentifier(
            object=ObjectIdentifier(type=object_type, key=object_key),
            subject=ObjectIdentifier(type=subject_type, key=subject_key),
            relation=RelationTypeIdentifier(name=relation_type, object_type=object_type),
        )
        self.writer.DeleteRelation(
            DeleteRelationRequest(param=relation_identifier), metadata=self._metadata
        )

    def check_relation(
        self,
        subject_type: str,
        subject_key: str,
        object_type: str,
        object_key: str,
        relation_type: str,
    ) -> bool:
        response = self.reader.CheckRelation(
            CheckRelationRequest(
                object=ObjectIdentifier(type=object_type, key=object_key),
                subject=ObjectIdentifier(type=subject_type, key=subject_key),
                relation=RelationTypeIdentifier(name=relation_type, object_type=object_type),
            ),
            metadata=self._metadata,
        )
        return response.check

    def check_permission(
        self,
        subject_type: str,
        subject_key: str,
        object_type: str,
        object_key: str,
        permission: str,
    ) -> bool:
        response = self.reader.CheckPermission(
            CheckPermissionRequest(
                object=ObjectIdentifier(type=object_type, key=object_key),
                subject=ObjectIdentifier(type=subject_type, key=subject_key),
                permission=PermissionIdentifier(name=permission),
            ),
            metadata=self._metadata,
        )
        return response.check

    def close_channel(self) -> None:
        self._channel.close()

    def _get_metadata(self, api_key, tenant_id) -> Tuple:
        md = ()
        if api_key:
            md += (("authorization", f"basic {api_key}"),)
        if tenant_id:
            md += (("aserto-tenant-id", tenant_id),)
        return md

    def _channel_credentials(self, cert) -> grpc.ChannelCredentials:
        if cert:
            with open(cert, "rb") as f:
                return grpc.ssl_channel_credentials(f.read())
        else:
            return grpc.ssl_channel_credentials()
