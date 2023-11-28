import re
from typing import Callable

from aserto.client import Identity, ResourceContext
from flask import request

__all__ = [
    "create_default_policy_path_resolver",
    "DEFAULT_RESOURCE_CONTEXT_PROVIDER_FOR_ENDPOINT",
    "DEFAULT_RESOURCE_CONTEXT_PROVIDER_FOR_DISPLAY_STATE_MAP",
]

IdentityMapper = Callable[[], Identity]
StringMapper = Callable[[], str]
ResourceMapper = Callable[[], ResourceContext]
DEFAULT_DISPLAY_STATE_MAP_ENDPOINT = "/__displaystatemap"


def DEFAULT_RESOURCE_CONTEXT_PROVIDER_FOR_ENDPOINT() -> ResourceContext:
    return request.view_args or {}


def DEFAULT_RESOURCE_CONTEXT_PROVIDER_FOR_DISPLAY_STATE_MAP() -> ResourceContext:
    return request.get_json(silent=True) or {}


def create_default_policy_path_resolver(policy_root: str) -> StringMapper:
    def default_policy_path_resolver() -> str:
        rule_string = str(request.url_rule)
        policy_sub_path = policy_path_heuristic(rule_string)
        return f"{policy_root}.{request.method.upper()}{policy_sub_path}"

    return default_policy_path_resolver


def policy_path_heuristic(path: str) -> str:
    # Replace route arguments surrounded in angle brackets to being
    # prefixed with two underscores, e.g. <id:str> -> __id
    path = re.sub("<([^:]*)(:[^>]*)?>", r"__\1", path)
    path = path.replace("/", ".")
    return path
