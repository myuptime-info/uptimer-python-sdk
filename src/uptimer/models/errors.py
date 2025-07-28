"""Error classes for model operations."""


class ModelError(Exception):
    """Base class for all model-related errors."""


class DeserializationError(ModelError):
    """Base class for deserialization errors."""


class MissingKindError(DeserializationError):
    """Raised when an object is missing the 'kind' property."""

    def __init__(self, data: dict):
        self.data = data
        super().__init__("Data must contain a 'kind' property")


class UnknownKindError(DeserializationError):
    """Raised when an object has an unknown 'kind' property."""

    def __init__(self, kind: str):
        self.kind = kind
        super().__init__(f"Unknown kind: {kind}")


class InvalidDataTypeError(DeserializationError):
    """Raised when data is not a dictionary."""

    def __init__(self, data_type: type):
        self.data_type = data_type
        super().__init__(
            f"Data must be a dictionary, got {data_type.__name__}",
        )


class TypeMismatchError(DeserializationError):
    """Raised when the deserialized object is not of the expected type."""

    def __init__(self, expected_type: str, actual_type: str):
        self.expected_type = expected_type
        self.actual_type = actual_type
        super().__init__(f"Expected {expected_type}, got {actual_type}")
