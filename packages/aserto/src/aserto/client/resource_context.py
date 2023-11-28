import json
from typing import Dict, Mapping, Sequence

import google.protobuf.struct_pb2 as structpb

__all__ = ["ResourceContext"]


# No better way to type a JSON serializable dict?
ResourceContext = Dict[str, object]


def serialize_resource_context(resource_context: object) -> structpb.Struct:
    try:
        json.dumps(resource_context)
    except ValueError as error:
        if error.args == ("Circular reference detected",):  # type: ignore[misc]
            raise TypeError("Resource context is circularly defined") from error
        else:
            raise TypeError("Invalid resource context") from error

    proto_value = serialize_resource_context_value(resource_context)
    return proto_value.struct_value


def serialize_resource_context_value(resource_value: object) -> structpb.Value:
    # `Mapping` is a subclass of `Collection` so this check must come first
    if isinstance(resource_value, Mapping):
        struct_value = structpb.Struct()
        struct_value.update(resource_value)
        return structpb.Value(struct_value=struct_value)
    # `str` is a subclass of `Collection` so this check must come first
    elif isinstance(resource_value, str):
        return structpb.Value(string_value=resource_value)
    elif isinstance(resource_value, Sequence):
        list_value = structpb.ListValue(
            values=(serialize_resource_context_value(v) for v in resource_value)
        )
        return structpb.Value(list_value=list_value)
    # `bool` is subclass of `int` so this check must come first
    elif isinstance(resource_value, bool):
        return structpb.Value(bool_value=resource_value)
    elif isinstance(resource_value, (int, float)):
        return structpb.Value(number_value=float(resource_value))
    elif resource_value is None:
        return structpb.Value(null_value=structpb.NullValue.NULL_VALUE)
    else:
        raise TypeError("Invalid resource context")
