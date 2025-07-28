from dataclasses import dataclass


@dataclass
class Region:
    id: str  # region id, uuids used for api ids
    name: str  # region name
    active_workers_count: int  # number of active workers in the region
    kind: str  # any object has kind property, defines class of object
