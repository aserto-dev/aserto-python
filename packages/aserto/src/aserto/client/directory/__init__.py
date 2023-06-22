from dataclasses import dataclass
from typing import Tuple

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


@dataclass(frozen=True)
class Config:
    address: str
    api_key: str
    tenant_id: str
    cert: str


class Directory:
    def __init__(self, *, address: str, api_key: str, tenant_id: str, ca_cert: str) -> None:
        self._config = Config(address=address, api_key=api_key, tenant_id=tenant_id, cert=ca_cert)
        self._channel = grpc.secure_channel(
            target=self._config.address, credentials=self._channel_credentials()
        )
        self.reader = ReaderStub(self._channel)
        self.writer = WriterStub(self._channel)
        self.importer = ImporterStub(self._channel)
        self.exporter = ExporterStub(self._channel)

    def get_objects(self, name: str, page: PaginationRequest) -> GetObjectsResponse:
        response = self.reader.GetObjects(
            GetObjectsRequest(param=ObjectTypeIdentifier(name=name), page=PaginationRequest(page))
        )
        return response

    def get_object(self, key: str, type: str) -> Object:
        identifier = ObjectIdentifier(type=type, key=key)
        response = self.reader.GetObject(GetObjectRequest(param=identifier))
        return response["result"]

    def set_object(self, object: Object) -> Object:
        response = self.writer.SetObject(SetObjectRequest(object=object))
        return response["result"]

    def delete_object(self, key: str, type: str) -> None:
        identifier = ObjectIdentifier(type=type, key=key)
        self.writer.DeleteObject(DeleteObjectRequest(param=identifier))

    def get_relations(
        self,
        subject_type: str,
        subject_key: str,
        object_type: str,
        object_key: str,
        relation_type: str,
        page: PaginationRequest,
    ) -> GetRelationsResponse:
        response = self.reader.GetRelations(
            GetRelationsRequest(
                param=RelationIdentifier(
                    object=ObjectIdentifier(type=object_type, key=object_key),
                    subject=ObjectIdentifier(type=subject_type, key=subject_key),
                    relation=RelationTypeIdentifier(name=relation_type, object_type=object_type),
                ),
                page=PaginationRequest(page),
            )
        )
        return response

    def get_relation(
        self,
        subject_type: str,
        subject_key: str,
        object_type: str,
        object_key: str,
        relation_type: str,
    ) -> Relation:
        response = self.reader.GetRelation(
            GetRelationRequest(
                param=RelationIdentifier(
                    object=ObjectIdentifier(type=object_type, key=object_key),
                    subject=ObjectIdentifier(type=subject_type, key=subject_key),
                    relation=RelationTypeIdentifier(name=relation_type, object_type=object_type),
                )
            )
        )
        return response["results"]

    def set_relation(self, relation: Relation) -> Relation:
        response = self.writer.SetRelation(SetRelationRequest(relation=relation))
        return response["result"]

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
        self.writer.DeleteRelation(DeleteRelationRequest(param=relation_identifier))

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
            )
        )
        return response["check"]

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
            )
        )
        return response["check"]

    def close_channel(self) -> None:
        self._channel.close()

    def _metadata(self) -> Tuple:
        md = ()
        if self._config.api_key:
            md += (("authorization", f"basic {self._config.api_key}"),)
        if self._config.tenant_id:
            md += (("aserto-tenant-id", self._config.tenant_id),)
        return md

    def _channel_credentials(self) -> grpc.ChannelCredentials:
        if self._config.cert:
            with open(self._config.cert, "rb") as f:
                return grpc.ssl_channel_credentials(f.read())
        else:
            return grpc.ssl_channel_credentials()
