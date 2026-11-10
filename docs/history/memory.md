> [!WARNING]
> **HISTORICAL DOCUMENT — NOT CURRENT SOURCE OF TRUTH**
> This document represents earlier project planning and may contain requirements that have since changed.

# Clash of Clans Resource Farming Automation â€” Memory and Persistence

**Status:** Draft v1.0
**Date:** 2026-08-22

## 1. Purpose

This document defines what the application should persist between sessions. It is intentionally small: persistent memory should support reliability and configuration, not attempt to become an external copy of game state.

## 2. Persisted Configuration

Store:

- operation mode;
- target expression;
- optional Dark Elixir settings;
- deployment edge;
- deployment pattern;
- baseline/selected army configuration;
- wall-upgrade toggle;
- wall storage threshold;
- builder requirement preference;
- pause/stop UI preferences;
- logging level;
- viewport calibration data.

## 3. Calibration Memory

Store the last known viewport configuration:

```text
screen resolution
window/fullscreen mode
viewport bounds
normalized-coordinate transform
calibration confidence
timestamp
```

Calibration should be revalidated at application startup rather than blindly trusted.

## 4. Reference Asset Memory

Store metadata for screenshot assets and wall reference images.

Example:

```text
asset_id
category
file_path
state
wall_level_if_known
resolution
created_at
source_case
notes
```

## 5. Session Memory

Store high-level session metrics:

- session start/end;
- selected mode;
- attacks started;
- attacks completed;
- candidates skipped;
- accepted targets;
- average target resources;
- victory/defeat outcomes;
- average damage;
- wall upgrades performed;
- errors and safe stops.

## 6. Short-Term Runtime Memory

The following should remain in memory only for the active session unless explicitly persisted for diagnostics:

- current GameState;
- current candidate;
- current Army Ledger;
- pending ActionPlan;
- current state-machine state;
- pause/stop status;
- current detection confidence.

## 7. Failure Memory

Persist a compact failure record:

```text
failure_id
timestamp
state
intended_action
error_code
screenshot_path
confidence_summary
recovery_result
```

Do not silently accumulate unlimited data. Use configurable retention.

## 8. What Must Not Be Stored

Do not store:

- passwords;
- authentication tokens;
- Supercell ID credentials;
- payment details;
- unrelated personal information;
- network secrets;
- game memory dumps;
- network packet captures intended to reproduce internal game state.

## 9. Persistent Learnings

The application may remember engineering metadata such as:

- detector performance statistics;
- known screenshot failure patterns;
- calibrated UI template versions;
- asset validation status.

It should not automatically rewrite behavioral rules based on one unexpected live-game event. Rule changes must remain explicit and reviewable.

## 10. Versioning

Persisted configuration should have a schema version.

Example:

```json
{"schema_version":1,"mode":"infinite","target_expression":"gold >= 1000000 OR gold + elixir >= 1500000"}
```

On incompatible schema changes, migrate or fail clearly rather than partially loading settings.

