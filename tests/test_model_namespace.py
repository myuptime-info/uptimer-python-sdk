"""
The model namespace boundary.

The API is versioned by path, so its types are versioned too. Every v2 name is
reachable as `uptimer.models.v2.<name>` and **only** there: not flat on
`uptimer.models`, not on the `uptimer` root, and not through a leftover module
such as `uptimer.models.location`. These tests are the negative half of that —
without them a stray re-export would pass everything else in the suite.
"""

import importlib

import pytest

import uptimer
import uptimer.models
import uptimer.models.v2 as models_v2

# Every public v2 symbol, taken from the package itself so a new export cannot
# be added without this boundary being applied to it too.
V2_NAMES = tuple(models_v2.__all__)

# Version-independent: raised whichever API version produced the payload, so
# they stay on uptimer.models.
EXCEPTION_NAMES = (
    "DeserializationError",
    "InvalidDataTypeError",
    "MissingKindError",
    "ModelError",
    "TypeMismatchError",
    "UnknownKindError",
)


def test_v2_exports_the_whole_public_surface():
    expected = {
        "AGREEMENT_ALL",
        "AGREEMENT_ANY",
        "AGREEMENT_MAJORITY",
        # The observation status words are prefixed: an incident STATUS_OK is a
        # derived display state, an observation's is what a sender reported.
        # Same string, different question — so they do not share a name.
        "OBSERVATION_STATUS_OK",
        "OBSERVATION_STATUS_PROBLEM",
        "REJECT_ACCEPTED",
        "REJECT_CLOCK_SKEW",
        "REJECT_LATE",
        "REJECT_OUT_OF_ORDER",
        "REJECT_OUT_OF_RETENTION",
        "STATUS_NO_DATA",
        "STATUS_OK",
        "STATUS_PENDING",
        "STATUS_PROBLEM",
        "STATUS_RECOVERING",
        "BaseWebsiteMonitor",
        "CreateObservationRequest",
        "CreateWebsiteMonitorRequest",
        "DeleteWebsiteMonitorResponse",
        "Incident",
        "IncidentLocations",
        "Location",
        "Observation",
        "UpdateWebsiteMonitorRequest",
        "WebsiteMonitor",
        "WebsiteMonitorRequest",
        "WebsiteMonitorResponse",
        "WebsiteMonitorResponseBody",
        "Workspace",
        "from_api",
        "from_api_incident",
        "from_api_location",
        "from_api_observation",
        "from_api_website_monitor",
        "from_api_workspace",
    }
    assert set(V2_NAMES) == expected


@pytest.mark.parametrize("name", V2_NAMES)
def test_every_v2_name_is_importable_from_the_v2_namespace(name: str):
    assert hasattr(models_v2, name)
    module = importlib.import_module("uptimer.models.v2")
    assert getattr(module, name) is getattr(models_v2, name)


@pytest.mark.parametrize("name", V2_NAMES)
def test_no_v2_name_is_reachable_flat(name: str):
    assert not hasattr(uptimer.models, name), (
        f"uptimer.models.{name} must not exist — import it from uptimer.models.v2"
    )
    assert not hasattr(uptimer, name), (
        f"uptimer.{name} must not exist — import it from uptimer.models.v2"
    )


@pytest.mark.parametrize(
    "name",
    ["Location", "Incident", "CreateWebsiteMonitorRequest"],
)
def test_a_flat_import_statement_fails(name: str):
    # exec, because the statement under test has to fail at import time and a
    # module-level `from uptimer.models import Location` would break collection.
    # `from X import Y` raises ImportError for a missing name, which is the
    # error a caller following stale 0.4.x-era guidance would actually see.
    with pytest.raises(ImportError):
        exec(f"from uptimer.models import {name}")  # noqa: S102


@pytest.mark.parametrize(
    "module",
    ["deserialize", "incident", "location", "monitor", "workspace"],
)
def test_the_old_flat_modules_are_gone(module: str):
    # A wrapper module left behind would keep `uptimer.models.location` working
    # and quietly undo the move.
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(f"uptimer.models.{module}")


@pytest.mark.parametrize("name", EXCEPTION_NAMES)
def test_model_exceptions_stay_version_independent(name: str):
    assert hasattr(uptimer.models, name)
    assert name not in V2_NAMES


def test_v2_deserialization_helpers_build_v2_types():
    location = models_v2.from_api_location(
        {"id": "l1", "name": "de", "active_workers_count": 2, "kind": "location"},
    )
    assert isinstance(location, models_v2.Location)
    assert location.name == "de"
