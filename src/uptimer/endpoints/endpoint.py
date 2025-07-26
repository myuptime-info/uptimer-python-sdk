from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uptimer.http import UptimerHttpLib


class BaseEndpoint:
    def __init__(
        self,
        http: UptimerHttpLib,
        segment: str,
        parent_segments: str | list[str] | None = None,
    ):
        self._http = http
        self._segment = segment
        if parent_segments is None:
            parent_segments = []
        if isinstance(parent_segments, str):
            parent_segments = [parent_segments]
        self._parent_segments = parent_segments

    @property
    def segment(self) -> str:
        return self._segment

    @property
    def http(self) -> UptimerHttpLib:
        return self._http

    @property
    def url(self) -> str:
        return self._http.build_url(self.path)

    @property
    def path(self) -> str:
        return "/".join([*self._parent_segments, self._segment])
