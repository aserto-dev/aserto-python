from typing import Dict, Literal

from aserto.authorizer.v2 import DecisionTreeResponse, PathSeparator

DecisionTree = Dict[str, Dict[str, bool]]


def policy_path_separator_field(
    policy_path_separator: Literal["DOT", "SLASH"],
) -> PathSeparator.ValueType:
    if policy_path_separator == "DOT":
        return PathSeparator.PATH_SEPARATOR_DOT
    if policy_path_separator == "SLASH":
        return PathSeparator.PATH_SEPARATOR_SLASH

    raise ValueError(f"Invalid PathSeparator: {policy_path_separator}")


def validate_decision_tree(response: DecisionTreeResponse) -> DecisionTree:
    error = TypeError("Received unexpected response data")

    decision_tree: DecisionTree = {}

    for path, decisions in response.path.fields.items():
        if decisions.WhichOneof("kind") != "struct_value":
            raise error

        for name, decision in decisions.struct_value.fields.items():
            if decision.WhichOneof("kind") != "bool_value":
                raise error

            decision_tree.setdefault(path, {})[name] = decision.bool_value

    return decision_tree
