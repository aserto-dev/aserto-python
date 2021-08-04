from typing import Dict

__all__ = ["ResourceContext"]


# No better way to type a JSON serializable dict?
ResourceContext = Dict[str, object]
