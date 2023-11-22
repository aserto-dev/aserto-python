from dataclasses import dataclass
from typing import List, Mapping, Optional

from aserto.directory.common.v3 import (
    Object,
    ObjectIdentifier,
    PaginationResponse,
    Relation,
)


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


def relation_objects(objects: Mapping[str, Object]) -> Mapping[ObjectIdentifier, Object]:
    res: Mapping[ObjectIdentifier, Object] = {}
    for k, obj in objects.items():
        obj_type, obj_key = k.split(":", 1)
        res[ObjectIdentifier(obj_type, obj_key)] = obj

    return res
