from dataclasses import dataclass

from aserto.authorizer.v2.api import IdentityType


@dataclass
class Identity:
    type: IdentityType
    value: str
