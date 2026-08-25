"""
Model exceptions, and the versioned model namespaces beneath this one.

**No API type is exported here.** v2's types live in `uptimer.models.v2`:

    from uptimer.models.v2 import CreateWebsiteMonitorRequest, Location

Only the deserialization exceptions sit at this level, because they are
version-independent — the same `TypeMismatchError` is raised whichever API
version produced the payload.
"""

from .errors import (
    DeserializationError,
    InvalidDataTypeError,
    MissingKindError,
    ModelError,
    TypeMismatchError,
    UnknownKindError,
)

__all__ = [
    "DeserializationError",
    "InvalidDataTypeError",
    "MissingKindError",
    "ModelError",
    "TypeMismatchError",
    "UnknownKindError",
]
