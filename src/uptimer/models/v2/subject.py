from __future__ import annotations

from dataclasses import dataclass

# How a subject is configured, and therefore what may be done to it.
#
# A WEBSITE subject is the simple path: Uptimer's own probe watches a URL, and
# the check form owns its signal and its rule. A CUSTOM subject is yours —
# you add heartbeat and event signals and report to them yourself.
#
# This is not the object's `kind`. Every v2 object carries `kind` to say WHAT it
# is ("subject"); `subject_kind` says how this particular one is configured. The
# two are separate fields on purpose, so a client switching on `kind` keeps
# working when a third subject kind arrives.
SUBJECT_KIND_WEBSITE = "website"
SUBJECT_KIND_CUSTOM = "custom"


@dataclass
class CreateSubjectRequest:
    """
    One empty Custom subject to create.

    A name and a workspace is the whole of it. The subject arrives with nothing
    under it — no signal, no rule, no HTTP probe — because what it is made of is
    yours to add afterwards, through the signals it will own.

    Website monitoring is NOT created this way: it needs a URL, an interval and
    locations, and it has its own request
    (`client.v2.monitoring.websites.create`). `subject_kind` may only say
    "custom", and the server refuses anything else with a message pointing at
    that method.
    """

    name: str
    workspace_id: str
    subject_kind: str = SUBJECT_KIND_CUSTOM


@dataclass
class Subject:
    """
    One monitored subject.

    `id` is the subject's SLUG, which is what the API addresses it by: it is the
    first half of the observation route, and a rename never moves it. There is
    no database id in the payload.

    `signal_count` and `rule_count` are how much is under the subject. They are
    here because there is no signals or rules collection in this release, so
    they are the only way to see that a subject you just created really is
    empty.
    """

    id: str
    name: str
    subject_kind: str
    workspace_id: str
    signal_count: int = 0
    rule_count: int = 0
    kind: str = "subject"

    @property
    def is_custom(self) -> bool:
        """Whether this subject is operator-configured."""
        return self.subject_kind == SUBJECT_KIND_CUSTOM

    @property
    def is_website(self) -> bool:
        """Whether this subject is website monitoring."""
        return self.subject_kind == SUBJECT_KIND_WEBSITE
