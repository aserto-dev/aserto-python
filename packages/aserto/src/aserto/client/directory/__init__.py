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
        self, name: "str | None" = None, page: "PaginationRequest | None" = None
    ) -> GetObjectsResponse:
        response = self.reader.GetObjects(
            GetObjectsRequest(param=ObjectTypeIdentifier(name=name), page=PaginationRequest(page)),
            metadata=self._metadata,
        )
        return response

    def get_object(self, key: "str | None" = None, type: "str | None" = None) -> Object:
        identifier = ObjectIdentifier(type=type, key=key)
        response = self.reader.GetObject(
            GetObjectRequest(param=identifier), metadata=self._metadata
        )
        return response.result

    def set_object(self, object: "Object | None" = None) -> Object:
        response = self.writer.SetObject(SetObjectRequest(object=object), metadata=self._metadata)
        return response.result

    def delete_object(self, key: "str | None" = None, type: "str | None" = None) -> None:
        identifier = ObjectIdentifier(type=type, key=key)
        self.writer.DeleteObject(DeleteObjectRequest(param=identifier), metadata=self._metadata)

    def get_relations(
        self,
        subject_type: "str | None" = None,
        subject_key: "str | None" = None,
        object_type: "str | None" = None,
        object_key: "str | None" = None,
        relation_type: "str | None" = None,
        page: "PaginationRequest | None" = None,
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
        subject_type: "str | None" = None,
        subject_key: "str | None" = None,
        object_type: "str | None" = None,
        object_key: "str | None" = None,
        relation_type: "str | None" = None,
    ) -> Relation:
        response = self.reader.GetRelation(
            GetRelationRequest(
                param=RelationIdentifier(
                    object=ObjectIdentifier(type=object_type, key=object_key),
                    subject=ObjectIdentifier(type=subject_type, key=subject_key),
                    relation=RelationTypeIdentifier(name=relation_type, object_type=object_type),
                )
            ),
            metadata=self._metadata,
        )
        return response.results[0]

    def set_relation(self, relation: "Relation | None" = None) -> Relation:
        response = self.writer.SetRelation(
            SetRelationRequest(relation=relation), metadata=self._metadata
        )
        return response.result

    def delete_relation(
        self,
        subject_type: "str | None" = None,
        subject_key: "str | None" = None,
        object_type: "str | None" = None,
        object_key: "str | None" = None,
        relation_type: "str | None" = None,
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
        subject_type: "str | None" = None,
        subject_key: "str | None" = None,
        object_type: "str | None" = None,
        object_key: "str | None" = None,
        relation_type: "str | None" = None,
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
        subject_type: "str | None" = None,
        subject_key: "str | None" = None,
        object_type: "str | None" = None,
        object_key: "str | None" = None,
        permission: "str | None" = None,
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
