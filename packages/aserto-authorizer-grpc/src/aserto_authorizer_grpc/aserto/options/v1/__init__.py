# Generated by the protocol buffer compiler.  DO NOT EDIT!
# sources: aserto/options/v1/ids.proto
# plugin: python-_asertoproto
from dataclasses import dataclass

import _asertoproto
from _asertoproto.grpc.grpclib_server import ServiceBase


class IdType(_asertoproto.Enum):
    ID_TYPE_UNKNOWN = 0
    ID_TYPE_ACCOUNT = 1
    ID_TYPE_TENANT = 2
    ID_TYPE_ERROR = 3
    ID_TYPE_POLICY = 4
    ID_TYPE_REQUEST = 5
    ID_TYPE_PROVIDER = 6
    ID_TYPE_CONNECTION = 7
    ID_TYPE_INVITE = 8
