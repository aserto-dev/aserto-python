from dataclasses import dataclass
from typing import Optional

from aserto.authorizer.v2.api import IdentityType


@dataclass
class Identity:
    type: IdentityType.ValueType
    value: Optional[str] = None
