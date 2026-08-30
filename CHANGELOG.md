## 1.6.0-rc.0 (2026-08-30)

### Feat

- **api**: post custom observations via client.v2 subjects/signals

## 1.5.0 (2026-08-20)

### BREAKING CHANGE

- Targets Uptimer **API v2 only**. The `client.v1` namespace, its models and its
  kinds are gone. Code written against 0.4.x keeps working **against the
  server** — API v1 is unchanged and supported — but must pin
  `uptimer-python-sdk<1`.
- The version now tracks the uptimer release it targets, so this is 1.5.0 rather
  than 1.0.0: 1.5.x speaks to uptimer 1.5.0 and later. Patch numbers stay
  independent (product Decision 0013).

### Feat

- `client.v2.workspaces`, `client.v2.locations`, `client.v2.incidents` and
  `client.v2.monitoring.websites` replace the v1 namespace. The API version stays
  visible in the SDK, as it was in 0.4.x — there are no root-level aliases.
- **Types are versioned too:** import them from `uptimer.models.v2`
  (`Location`, `Incident`, `Workspace`, the website-monitor classes, the
  `AGREEMENT_*` / `STATUS_*` constants and the `from_api*` helpers). They are no
  longer exported from `uptimer.models`, and there are no flat aliases. The
  deserialization exceptions stay on `uptimer.models`, being
  version-independent.
- `client.v2.incidents` reads **open** incidents, with the same five status words
  the Uptimer screens use — `problem`, `pending`, `recovering`, `no_data`, `ok`.
  `pending` means failing but inside the confirm hold: nobody has been notified
  yet.
- Website monitors carry `agreement` (`any`, `majority`, `all`) — how many
  locations must report a problem before the monitor does. Omitting it on update
  keeps the stored value.
- `client.check_compatibility()` refuses a server that predates API v2 with a
  message naming the fix, instead of a bare 404 on the first call.

### Migration

| 0.4.x | 1.5.0 |
|---|---|
| `client.v1.workspaces` | `client.v2.workspaces` |
| `client.v1.regions` | `client.v2.locations` |
| `client.v1.rules` | `client.v2.monitoring.websites` |
| `Region` | `Location` |
| `Rule` / `CreateRuleRequest` | `WebsiteMonitor` / `CreateWebsiteMonitorRequest` |
| `regions=[...]` | `locations=[...]` |
| — | `agreement=...`, `client.v2.incidents` |
| `from uptimer.models import …` | `from uptimer.models.v2 import …` |

`client.version()` and the compatibility helpers are unchanged and stay on the
client itself: `/version` is a shared global endpoint, not a versioned one.

## 0.4.0 (2026-07-15)

### Feat

- assign regions (by name) when creating or updating a rule via `rules.create`/`rules.update`; rules now expose a `regions` field

## 0.3.0 (2025-08-19)

### Feat

- self-hosted client now requires a base_url, added cloud client, updated docs

## 0.2.0 (2025-08-10)

### Feat

- create/update/delete rule methods.
- added method to get all rules
- added regions and get rule API
- added getting workspace list
- add Cursor IDE configuration for testing and development

### Fix

- fixed dependencies in pyproject.toml
