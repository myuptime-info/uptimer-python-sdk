from __future__ import annotations

from typing import Any, TypeVar, Union

from .errors import (
    InvalidDataTypeError,
    MissingKindError,
    TypeMismatchError,
    UnknownKindError,
)
from .region import Region
from .rule import (
    Rule,
    RuleRequest,
    RuleResponse,
    RuleResponseBody,
)
from .workspace import Workspace

# Type variable for the return type
T = TypeVar("T")

# Union type for all possible return types
DeserializableType = Union[
    Rule,
    RuleRequest,
    RuleResponse,
    RuleResponseBody,
    Region,
    Workspace,
]

# Type for items that might be deserializable
DeserializableItem = Union[dict[str, Any], list[Any], Any]

# Registry of classes by their kind
_KIND_REGISTRY = {
    "rule": Rule,
    "rule_request": RuleRequest,
    "rule_response": RuleResponse,
    "rule_response_body": RuleResponseBody,
    "region": Region,
    "workspace": Workspace,
}


def from_api(data: dict[str, Any]) -> DeserializableType:
    """
    Universal deserializer that creates objects based on their 'kind' property.

    Recursively deserializes nested objects.

    Args:
        data: Dictionary containing the object data with a 'kind' property

    Returns:
        The appropriate object instance based on the 'kind' property

    Raises:
        InvalidDataTypeError: If data is not a dictionary
        MissingKindError: If the 'kind' property is missing
        UnknownKindError: If the 'kind' property is not recognized
    """
    if not isinstance(data, dict):
        raise InvalidDataTypeError(type(data))

    kind = data.get("kind")
    if not kind:
        raise MissingKindError(data)

    if kind not in _KIND_REGISTRY:
        raise UnknownKindError(kind)

    cls = _KIND_REGISTRY[kind]

    # Create a copy to avoid modifying the original
    obj_data = data.copy()

    # Recursively deserialize nested objects that have 'kind' properties
    for key, value in obj_data.items():
        if isinstance(value, dict) and value.get("kind"):
            obj_data[key] = from_api(value)
        elif isinstance(value, list):
            # Handle lists of objects
            obj_data[key] = [_deserialize_if_possible(item) for item in value]

    return cls(**obj_data)


def _deserialize_if_possible(item: DeserializableItem) -> DeserializableItem:
    """Deserialize an item if it has a kind property."""
    if isinstance(item, dict) and item.get("kind"):
        return from_api(item)
    return item


def from_api_rule(data: dict[str, Any]) -> Rule:
    """Type-safe deserializer for Rule objects."""
    result = from_api(data)
    if not isinstance(result, Rule):
        msg = "Rule"
        raise TypeMismatchError(msg, type(result).__name__)
    return result


def from_api_region(data: dict[str, Any]) -> Region:
    """Type-safe deserializer for Region objects."""
    result = from_api(data)
    if not isinstance(result, Region):
        msg = "Region"
        raise TypeMismatchError(msg, type(result).__name__)
    return result


def from_api_workspace(data: dict[str, Any]) -> Workspace:
    """Type-safe deserializer for Workspace objects."""
    result = from_api(data)
    if not isinstance(result, Workspace):
        msg = "Workspace"
        raise TypeMismatchError(msg, type(result).__name__)
    return result
