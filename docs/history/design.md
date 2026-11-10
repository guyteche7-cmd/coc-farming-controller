> [!WARNING]
> **HISTORICAL DOCUMENT � NOT CURRENT SOURCE OF TRUTH**
> This document represents earlier project planning and may contain requirements that have since changed.

# Clash of Clans Resource Farming Automation — Detailed Design

**Status:** Draft v1.0
**Date:** 2026-08-22

## 1. Design Goals

- Observable behavior.
- Deterministic rules.
- Data-driven deployment.
- Low-coupling CV and control.
- Replayable tests.
- Strong failure containment.

## 2. State Model

Each loop iteration should produce:

```text
Frame → Detections → GameState → Decision → ActionPlan → ActionResult → Verification
```

### GameState example

```yaml
ui_state: CANDIDATE_SCAN
viewport:
  confidence: 0.99
candidate:
  gold: 1245000
  elixir: 912000
  dark_elixir: 5000
  confidence: 0.96
army:
  confidence: 0.98
battle:
  damage_percent: null
  time_remaining_seconds: null
```

## 3. Detector Contracts

Each detector returns a common result type:

```text
DetectionResult[T]
  value: T | None
  confidence: float
  bbox: BoundingBox | None
  timestamp: datetime
  source_frame_id: string
  errors: list[str]
```

## 4. UI State Detector

Primary states to recognize:

```text
HOME
ATTACK_MENU
MATCHMAKING
CANDIDATE_BATTLE
ACTIVE_BATTLE
END_BATTLE_DIALOG
SURRENDER_DIALOG
VICTORY_RESULT
DEFEAT_RESULT
ARMY_SCREEN
WALL_SCREEN
UNKNOWN
```

State classification should use multiple cues where possible rather than one pixel/template.

## 5. Resource Detector

### Region

The candidate battle screenshot has the loot panel in the upper-left.

### Pipeline

```text
Locate loot panel
   ↓
Crop Gold row
   ↓
OCR / recognition
   ↓
Normalize spaces/separators
   ↓
Integer parse
   ↓
Confidence
```

Repeat for Elixir and Dark Elixir.

### Sanity checks

- integer value must be non-negative;
- glyph recognition must be internally consistent;
- impossible parse results are rejected;
- sudden frame-to-frame changes should be flagged.

## 6. Army Detector

The army bar is slot-based. Each slot should be modeled as:

```text
slot_index
icon_class
quantity
special marker/ability indicator
confidence
```

The detector should identify the unit type by template/model and quantity by OCR or digit recognition.

For Heroes, distinguish Hero identity from troop slots.

## 7. Army Ledger Design

```text
ArmyLedger
  expected[]
  deployed[]
  remaining[]
  status_by_unit
  last_verified_at
```

The ledger must support repeated verification after deployment actions.

## 8. Deployment Pattern Design

### Edge selection

Store the chosen edge as a configuration enum:

```text
TOP
BOTTOM
LEFT
RIGHT
```

v1 may use a fixed selected edge.

### Valkyrie line

The edge is divided into upper/middle/lower deployment zones. The deployment planner produces ordered positions distributed along a line.

Example abstraction:

```text
upper_points[]
middle_points[]
lower_points[]
```

### Heroes

Heroes use a middle anchor region.

### Log Launcher

Uses a configured siege anchor on the same broad attack side.

### Totems

Totem points are generated from an outward anchor toward an inward target region.

```text
P1 = troop start region
P2 = slightly inward
P3 = deeper inward
...
```

The number of points/placements must be computed from runtime Totem quantity and configuration rather than assumed to be 11 forever.

## 9. Action Planner

Represent actions in a neutral schema:

```text
Action
  type
  target
  precondition
  expected_effect
  timeout_ms
  retry_policy
```

Examples:

```text
CLICK_ATTACK_BUTTON
CLICK_FIND_MATCH
CLICK_NEXT
SELECT_UNIT(Valkyrie)
DEPLOY_POINT(x,y)
SELECT_HERO(ArcherQueen)
SELECT_SIEGE(LogLauncher)
SELECT_SPELL(Totem)
CLICK_END_BATTLE
CLICK_SURRENDER
CLICK_CONFIRM_OKAY
```

## 10. Verification

Every high-impact action needs observable evidence.

Example:

```text
Before:
  state = ATTACK_MENU

Action:
  CLICK_FIND_MATCH

Expected:
  state = CANDIDATE_BATTLE or MATCHMAKING

Verify:
  UIStateDetector confirms transition
```

## 11. Battle Monitor

Poll only as fast as required to detect exit conditions without creating unnecessary input or CPU load.

Inputs:

- damage percent;
- time remaining;
- battle-active indicator.

Rule order:

```text
if damage >= 50:
    end battle
elif time_remaining <= 60:
    surrender
else:
    continue monitoring
```

## 12. Result Parser

### Victory result

Extract where available:

- result;
- damage;
- stars;
- Gold;
- Elixir;
- Dark Elixir;
- bonus;
- visible troop-expended list.

### Defeat result

Extract:

- result;
- damage;
- visible rewards;
- troop-expended list.

The result parser should not require every field to exist.

## 13. Wall Design

### Home condition detector

Detect:

- free/occupied builder state;
- Gold storage fill;
- Elixir storage fill;
- wall presence;
- wall level/style candidates;
- wall-upgrade UI.

### Wall selection

Prefer batch selection when the current UI exposes the same-level multi-wall function.

### Verification

Confirm at least one of:

- upgrade confirmation appears;
- selected wall state changes;
- resource amount decreases consistently;
- upgrade queue/indicator changes.

## 14. Pause/Stop Design

### Pause

Set `session_status = PAUSED`. ActionExecutor rejects new actions except internal status operations.

### Resume

Re-detect current state. Do not blindly resume a stale click sequence.

### Stop

Set `session_status = STOP_REQUESTED`, clear pending actions, and exit to a safe non-clicking loop. The UI should display stopped state.

## 15. Configuration Design

Example conceptual configuration:

```yaml
mode: infinite

window:
  resolution: [1920, 1080]
  scaling: 1.0
  fullscreen: true

target:
  expression: "gold >= 1000000 OR gold + elixir >= 1500000"
  dark_elixir:
    enabled: false
    minimum: 0

deployment:
  edge: top
  troop_pattern: line
  hero_region: center
  siege_type: log_launcher
  spell_type: totem
  spell_pattern: outward_to_inward

exit:
  damage_percent: 50
  surrender_seconds: 60

walls:
  enabled: true
  builder_required: true
  storage_threshold_percent: 80
```

## 16. Logging Design

Structured JSONL logs are recommended for per-event logging.

Example event:

```json
{"ts":"2026-08-22T21:40:00+05:30","state":"CANDIDATE_SCAN","gold":1245000,"elixir":912000,"accepted":true}
```

## 17. Replay Design

A replay case is a timestamped sequence of screenshots and expected states.

```text
case_001/
  frame_0001.png
  frame_0002.png
  frame_0003.png
  expected.json
```

The state machine must run against this without generating real input.

## 18. Asset Design

Reference screenshots should be organized by semantic state:

```text
assets/
  ui/
    home/
    attack_menu/
    matchmaking/
    battle/
    dialogs/
    results/
  army/
  walls/
```

Wall reference images should include metadata:

```text
wall level
crop coordinates
source screenshot
screen resolution
research date
confidence
```

## 19. Error Recovery Design

Use bounded retries by state, not infinite click loops.

Example:

```text
DETECT_BUTTON
  ├─ confidence high → click
  ├─ confidence medium → wait/reacquire
  └─ confidence low → safe stop
```

Repeated failure should always create a diagnostic capture.

