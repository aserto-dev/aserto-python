from dataclasses import dataclass
from typing import Mapping

from aserto.directory.common.v2 import Object
from aserto.directory.common.v2 import ObjectIdentifier as ObjectIdentifierProto
from aserto.directory.common.v2 import Relation


@dataclass(frozen=True)
class ObjectIdentifier:
    """
    Unique identifier of a directory object.
    """

    type: str
    key: str

    @property
    def proto(self) -> ObjectIdentifierProto:
        return ObjectIdentifierProto(type=self.type, key=self.key)


@dataclass(frozen=True)
class RelationResponse:
    """
    Response to get_relation calls when with_objects is True.
    """

    relation: Relation
    object: Object
    subject: Object


def relation_objects(objects: Mapping[str, Object]) -> Mapping[ObjectIdentifier, Object]:
    res: Mapping[ObjectIdentifier, Object] = {}
    for k, obj in objects.items():
        obj_type, obj_key = k.split(":", 1)
        res[ObjectIdentifier(type=obj_type, key=obj_key)] = obj

    return res
