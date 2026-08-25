from dataclasses import dataclass


@dataclass
class Workspace:
    id: str  # workspace id, uuids used for api ids
    name: str  # workspace name
    role: str  # user role in workspace
    kind: str  # any object has kind property, defines class of object
