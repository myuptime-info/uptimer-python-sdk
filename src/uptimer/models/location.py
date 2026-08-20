from dataclasses import dataclass


@dataclass
class Location:
    """
    A place checks run from.

    API v1 called this a region. v2 uses the product's word; the underlying
    thing is unchanged.
    """

    id: str  # location id, uuids used for api ids
    name: str  # location name
    active_workers_count: int  # number of active workers in the location
    kind: str  # any object has kind property, defines class of object
