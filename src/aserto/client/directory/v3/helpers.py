import datetime
from dataclasses import dataclass
from typing import List, Mapping, Optional

from aserto.directory.common.v3 import Object
from aserto.directory.common.v3 import ObjectIdentifier as ObjectIdentifierProto
from aserto.directory.common.v3 import PaginationResponse, Relation
from aserto.directory.exporter.v3 import Option

MAX_CHUNK_BYTES = 64 * 1024


class ETagMismatchError(Exception):
    pass


ExportOption = Option


@dataclass(frozen=True)
class ObjectIdentifier:
    """
    Unique identifier of a directory object.
    """

    type: str
    id: str

    @property
    def proto(self) -> ObjectIdentifierProto:
        return ObjectIdentifierProto(object_type=self.type, object_id=self.id)


@dataclass(frozen=True)
class RelationResponse:
    """
    Response to get_relation calls when with_objects is True.
    """

    relation: Relation
    object: Object
    subject: Object


@dataclass(frozen=True)
class RelationsResponse:
    """
    Response to get_relations calls.

    Attributes
    ----
    relation    The returned relation.
    objects     If with_relations is True, a mapping from "type:key" to the corresponding object.
    page        The next page's token if there are more results.
    """

    relations: List[Relation]
    objects: Optional[Mapping[ObjectIdentifier, Object]]
    page: PaginationResponse


@dataclass(frozen=True)
class Manifest:
    updated_at: datetime.datetime
    etag: str
    body: Optional[bytes]


@dataclass(frozen=True)
class ImportCounter:
    recv: int = 0
    set: int = 0
    delete: int = 0
    error: int = 0

    def add(self, other: "ImportCounter") -> "ImportCounter":
        return ImportCounter(
            recv=self.recv + other.recv,
            set=self.set + other.set,
            delete=self.delete + other.delete,
            error=self.error + other.error,
        )


@dataclass(frozen=True)
class ImportResponse:
    objects: ImportCounter
    relations: ImportCounter


def relation_objects(objects: Mapping[str, Object]) -> Mapping[ObjectIdentifier, Object]:
    res: Mapping[ObjectIdentifier, Object] = {}
    for k, obj in objects.items():
        obj_type, obj_id = k.split(":", 1)
        res[ObjectIdentifier(obj_type, obj_id)] = obj

    return res
