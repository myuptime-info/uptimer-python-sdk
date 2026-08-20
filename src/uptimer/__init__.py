"""
Uptimer Python SDK.

Targets Uptimer API v2 only. Code written against 0.4.x keeps working against
the server — API v1 is unchanged and supported — but must stay on the 0.4.x SDK.

The version tracks the uptimer release this SDK targets: 1.5.x speaks to
uptimer 1.5.0 and later. Patch numbers are independent, so an SDK fix can ship
without a server release. See product Decision 0013.
"""

__version__ = "1.5.0"
