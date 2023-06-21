from typing import Tuple

import grpc

from aserto.directory.common.v2 import ObjectIdentifier, ObjectTypeIdentifier, Object, Relation, RelationIdentifier, RelationTypeIdentifier, PermissionIdentifier, PaginationRequest
from aserto.directory.reader.v2 import ReaderStub, GetObjectRequest, GetObjectsRequest, GetObjectsResponse, GetRelationRequest, GetRelationsResponse, CheckRelationRequest, CheckPermissionRequest
from aserto.directory.writer.v2 import WriterStub, SetObjectRequest, SetRelationRequest, DeleteObjectRequest, DeleteRelationRequest
from aserto.directory.importer.v2 import ImporterStub
from aserto.directory.exporter.v2 import ExporterStub

class Directory:
    def __init__(self, *, address: str, api_key: str, tenant_id: str, ca_cert: str) -> None:
        self._config = { "address": address, "api_key": api_key, "tenant_id": tenant_id, "cert": ca_cert }
        self._channel = grpc.secure_channel(target=self._config["address"], credentials=self._channel_credentials())
        self.reader = ReaderStub(self._channel)
        self.writer = WriterStub(self._channel)
        self.importer = ImporterStub(self._channel)
        self.exporter = ExporterStub(self._channel)

    def get_objects(self, name:str, size: int, token: str) -> GetObjectsResponse:
        identifier = ObjectTypeIdentifier(name=name)
        pagination = PaginationRequest(size=size, token=token)
        response = self.reader.GetObjects(GetObjectsRequest(param=identifier, page=pagination))
        return response
    
    def get_object(self, key: str, type:str) -> Object:
        identifier = ObjectIdentifier(type=type, key=key)
        response = self.reader.GetObject(GetObjectRequest(param=identifier))
        return response["result"]
    
    def set_object(self, object: Object) -> Object:
        response = self.writer.SetObject(SetObjectRequest(object=object))
        return response["result"]
    
    def delete_object(self, key: str, type:str):
        identifier = ObjectIdentifier(type=type, key=key)
        response = self.writer.DeleteObject(DeleteObjectRequest(param=identifier))
        return response["result"]
    
    def get_relations(self, subject_type: str, subject_key: str, object_type: str, object_key: str, relation_type: str, size: int, token: str) -> GetRelationsResponse:
        subject_identifier = ObjectIdentifier(type=subject_type, key=subject_key)
        object_identifier = ObjectIdentifier(type=object_type, key=object_key)

        relation_type_identifier = RelationTypeIdentifier(name=relation_type, object_type=object_type)
        
        relation_identifier = RelationIdentifier(object=object_identifier, subject=subject_identifier, relation=relation_type_identifier)
        pagination = PaginationRequest(size=size, token=token)
        response = self.reader.GetObjects(GetObjectsRequest(param=relation_identifier, page=pagination))
        return response
    
    def get_relation(self, subject_type: str, subject_key: str, object_type: str, object_key: str, relation_type: str) -> Relation:
        subject_identifier = ObjectIdentifier(type=subject_type, key=subject_key)
        object_identifier = ObjectIdentifier(type=object_type, key=object_key)

        relation_type_identifier = RelationTypeIdentifier(name=relation_type, object_type=object_type)

        relation_identifier = RelationIdentifier(object=object_identifier, subject=subject_identifier, relation=relation_type_identifier)
        response = self.reader.GetRelation(GetRelationRequest(param=relation_identifier))
        return response["results"]
    
    def set_relation(self, relation: Relation) -> Relation:
        response = self.writer.SetRelation(SetRelationRequest(relation=relation))
        return response["result"]
    
    def delete_relation(self, subject_type: str, subject_key: str, object_type: str, object_key: str, relation_type: str):
        subject_identifier = ObjectIdentifier(type=subject_type, key=subject_key)
        object_identifier = ObjectIdentifier(type=object_type, key=object_key)

        relation_type_identifier = RelationTypeIdentifier(name=relation_type, object_type=object_type)

        relation_identifier = RelationIdentifier(object=object_identifier, subject=subject_identifier, relation=relation_type_identifier)
        response = self.writer.DeleteObject(DeleteRelationRequest(param=relation_identifier))
        return response["result"]
    
    def check_relation(self, subject_type: str, subject_key: str, object_type: str, object_key: str, relation_type: str) -> bool:
        subject_identifier = ObjectIdentifier(type=subject_type, key=subject_key)
        object_identifier = ObjectIdentifier(type=object_type, key=object_key)

        relation_type_identifier = RelationTypeIdentifier(name=relation_type, object_type=object_type)

        response = self.reader.CheckRelation(CheckRelationRequest(object=object_identifier, subject=subject_identifier, relation=relation_type_identifier))
        return response["check"]
    
    def check_permission(self, subject_type: str, subject_key: str, object_type: str, object_key: str, permission: str) -> bool:
        subject_identifier = ObjectIdentifier(type=subject_type, key=subject_key)
        object_identifier = ObjectIdentifier(type=object_type, key=object_key)

        permission_identifier = PermissionIdentifier(name=permission)

        response = self.reader.CheckPermission(CheckPermissionRequest(object=object_identifier, subject=subject_identifier, permission=permission_identifier))
        return response["check"]

    def _metadata(self) -> Tuple:
        md = ()
        if self._config["api_key"]:
            md += (("authorization", f"basic {self._config['api_key']}"),)
        if self._config["tenant_id"]:
            md += (("aserto-tenant-id", self._config["tenant_id"]),)
        return md

    def _channel_credentials(self) -> grpc.ChannelCredentials:
        if self._config["cert"]:
            with open(self._config["cert"], "rb") as f:
                return grpc.ssl_channel_credentials(f.read())
        else:
            return grpc.ssl_channel_credentials()
