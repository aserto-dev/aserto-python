from typing import List, Optional, Tuple, TypedDict

import grpc.aio as grpc
from aserto.directory.common.v2 import (
    Object,
    ObjectIdentifier,
    ObjectTypeIdentifier,
    PaginationRequest,
    PaginationResponse,
)
from aserto.directory.exporter.v2 import ExporterStub
from aserto.directory.importer.v2 import ImporterStub
from aserto.directory.reader.v2 import (
    GetObjectManyRequest,
    GetObjectRequest,
    GetObjectsRequest,
    GetObjectsResponse,
    ReaderStub,
)
from aserto.directory.writer.v2 import DeleteObjectRequest, SetObjectRequest, WriterStub
from grpc import ChannelCredentials, StatusCode, ssl_channel_credentials


class NotFoundError(Exception):
    pass


class Directory:
    def __init__(self, channel: grpc.Channel, api_key: str, tenant_id: str) -> None:
        self._channel = channel
        self._metadata = self._get_metadata(api_key=api_key, tenant_id=tenant_id)
        self.reader = ReaderStub(self._channel)
        self.writer = WriterStub(self._channel)
        self.importer = ImporterStub(self._channel)
        self.exporter = ExporterStub(self._channel)

    @classmethod
    async def connect(cls, *, address: str, api_key: str, tenant_id: str, ca_cert: str):
        channel = grpc.secure_channel(
            target=address, credentials=cls._channel_credentials(cert=ca_cert)
        )
        return Directory(channel, api_key, tenant_id)

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

    async def get_many_objects(
        self,
        objects: Optional[List[TypedDict("ObjectParams", {"key": str, "type": str})]] = None,
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

        identifiers = [ObjectIdentifier(key=x["key"], type=x["type"]) for x in objects]
        print("identifiers", identifiers)
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
            identifier = ObjectIdentifier(type=type, key=key)
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

        identifier = ObjectIdentifier(type=type, key=key)
        await self.writer.DeleteObject(
            DeleteObjectRequest(param=identifier), metadata=self._metadata
        )

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
