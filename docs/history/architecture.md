> [!WARNING]
> **HISTORICAL DOCUMENT � NOT CURRENT SOURCE OF TRUTH**
> This document represents earlier project planning and may contain requirements that have since changed.

# Clash of Clans Resource Farming Automation — Architecture

**Status:** Draft v1.0
**Date:** 2026-08-22

## 1. Architectural Principles

1. Perception must be separated from action execution.
2. Decisions must be generated from an explicit game-state model.
3. Every important action requires a precondition and verification step.
4. Configuration must be external to core business logic.
5. The runtime army must be discovered rather than permanently hard-coded.
6. Unexpected or low-confidence states must fail safely.
7. Screenshot replay must be possible without sending real input.

## 2. Recommended Stack

### Python

Python is the preferred implementation language for v1 because the project is dominated by computer vision, OCR, screenshot analysis, configuration, testing, and rapid iteration. Likely libraries include:

- OpenCV: image processing and template/shape matching
- NumPy: array operations
- Pillow: image loading/manipulation
- A desktop screenshot/input layer: implementation choice to be validated
- OCR engine: implementation choice to be benchmarked
- Pydantic or dataclasses: typed runtime models
- PyYAML or TOML/JSON: configuration
- SQLite: local persistence
- pytest: automated tests

C# is a credible alternative for a Windows-first production UI, but Python has the stronger combination of CV experimentation and iteration speed for this project. Java is workable but not the strongest fit for the dominant CV/OCR workflow. C++ is unnecessary for the first implementation.

## 3. High-Level Architecture

```text
┌───────────────────────┐
│ Screen Capture Layer  │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ Viewport Calibration  │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ Perception / CV Layer │
│ - UI state            │
│ - Resource OCR        │
│ - Army detector       │
│ - Battle indicators   │
│ - Wall detector       │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ Runtime Game State    │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ Decision Engine       │
│ - Target rules        │
│ - Exit rules          │
│ - Wall rules          │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ Action Planner        │
│ - Navigation          │
│ - Deployment          │
│ - Exit action         │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ UI Controller         │
└───────────┬───────────┘
            ↓
      Visible Game UI
```

## 4. Core Components

### 4.1 ScreenCapture

Captures the game viewport at a controlled rate. It must support:

- full-screen mode;
- viewport cropping;
- frame timestamps;
- optional save-on-failure.

### 4.2 ViewportCalibration

Locates the actual Clash of Clans viewport inside the Windows/Google Play Games window.

Inputs:

- screen resolution;
- current window geometry;
- visual anchors.

Outputs:

- viewport bounds;
- normalized coordinate transform;
- calibration confidence.

### 4.3 PerceptionEngine

Runs specialized detectors against the viewport.

Submodules:

```text
UIStateDetector
LootDetector
ArmyDetector
HeroDetector
BattleTimerDetector
DamageDetector
DialogDetector
WallDetector
StorageDetector
BuilderDetector
```

### 4.4 GameStateStore

The single runtime model representing the visible game state.

Example structure:

```text
GameState
  ui_state
  viewport
  candidate
  army
  heroes
  battle
  home
  walls
  confidence
  timestamps
```

### 4.5 TargetEvaluator

Evaluates candidate villages using an editable expression. It must not know anything about mouse coordinates.

### 4.6 DeploymentPlanner

Creates a sequence of abstract actions:

```text
Select Valkyrie
Deploy line region A
Deploy line region B
Deploy line region C
Select Hero 1
Deploy middle region
...
Select Log Launcher
Deploy configured region
Select Totem
Deploy outward point
Deploy inward point
...
```

The planner operates on abstract positions and units. The UI controller converts them into actual screen interactions.

### 4.7 ActionExecutor

Executes an action only when its precondition is satisfied. It reports success/failure and evidence.

### 4.8 StateMachine

Controls the overall workflow and timeouts.

### 4.9 SessionController

Controls mode selection, attack counts, pause/resume/stop, and high-level lifecycle.

### 4.10 WallManager

Checks Home Village wall conditions, detects wall candidates, selects wall batches, verifies upgrades, and loops until stopping conditions are met.

### 4.11 Persistence

Use SQLite for session history and JSON/YAML/TOML for user-editable configuration.

## 5. State Machine

Primary states:

```text
HOME
ATTACK_MENU
MULTIPLAYER
MATCHMAKING
CANDIDATE_SCAN
TARGET_ACCEPTED
BATTLE_PREPARATION
ARMY_RECOGNITION
TROOP_DEPLOYMENT
HERO_DEPLOYMENT
SIEGE_DEPLOYMENT
SPELL_DEPLOYMENT
ABILITY_PHASE
DEPLOYMENT_VERIFY
BATTLE_MONITORING
END_BATTLE_CONFIRM
SURRENDER_CONFIRM
RESULT_SCREEN
RETURN_HOME
WALL_CHECK
WALL_UPGRADE
WALL_VERIFY
PAUSED
ERROR_SAFE_STOP
```

Transitions should be driven by observed evidence, not fixed delays alone.

## 6. Runtime Army Model

```text
RuntimeArmyState
  troops[]
  spells[]
  siege[]
  heroes[]
  clan_castle
  total_capacity
  confidence
```

Each item should carry:

```text
type
quantity
slot
confidence
source_region
last_seen
```

## 7. Army Ledger

The Army Ledger is immutable for the initial expected quantity and mutable for deployed/remaining counts.

```text
ExpectedUnit
DeployedUnit
RemainingUnit
Status = EXPECTED | DEPLOYED | UNAVAILABLE | UNKNOWN
```

This provides a verification layer independent of the click sequence.

## 8. Coordinate Model

Use two coordinate spaces:

1. normalized game coordinates, 0–1;
2. calibrated pixel coordinates for execution.

Example:

```text
NormalizedPoint(x=0.50, y=0.15)
        ↓ calibration
PixelPoint(x=960, y=162)
```

Do not make gameplay decisions from raw desktop coordinates.

## 9. Vision Strategy

Start with deterministic methods before machine learning.

### Phase 1 techniques

- fixed/anchor-based region localization;
- template matching for stable buttons/icons;
- OCR for numeric resource/time/damage values;
- color/shape heuristics where robust;
- slot-based detection for the army bar.

Introduce learned models only if benchmark results show deterministic methods are insufficient.

## 10. Confidence and Evidence

Every detector should return:

```text
DetectionResult
  value
  confidence
  bounding_box
  source_frame
```

State changes should require a minimum evidence threshold.

Example:

```text
if attack_button.confidence < threshold:
    do not click
```

## 11. Deployment Architecture

The deployment planner is data-driven.

### Baseline pattern

```text
Selected Edge
 ├─ Upper line region
 ├─ Middle line region
 └─ Lower line region
```

Then:

```text
Heroes → middle region
Log Launcher → configured region
Totems → initial troop region, then progressively inward
```

The exact points should be configurable and expressed relative to the battle viewport.

## 12. Exit Monitor

The BattleMonitor continuously tracks:

- timer;
- total damage;
- battle UI state;
- whether an end/surrender action is available.

Decision priority:

```text
if damage >= 50%:
    END_BATTLE
elif time_remaining <= 60s:
    SURRENDER
else:
    WAIT
```

## 13. Safety Interlocks

Global interlocks:

- Pause freezes action execution.
- Stop terminates the session safely.
- Unknown state blocks non-emergency clicks.
- Low-confidence recognition blocks high-impact actions.
- Unexpected dialogs cause state re-evaluation.
- Repeated failed state transitions trigger safe stop.

## 14. Diagnostics

Save on failure:

- raw screenshot;
- cropped region;
- detector output;
- state;
- intended action;
- timestamp;
- confidence values.

## 15. Testing Architecture

The same state machine must be runnable against:

```text
LiveScreenAdapter
ReplayScreenAdapter
MockGameAdapter
```

The action layer should also support:

```text
RealInputExecutor
DryRunExecutor
```

Dry-run mode should log what it would click without generating real input.

## 16. Suggested Project Structure

```text
coc-farming-controller/
├── docs/
├── config/
├── assets/
│   ├── ui/
│   ├── army/
│   ├── walls/
│   └── test_cases/
├── src/
│   ├── capture/
│   ├── calibration/
│   ├── vision/
│   ├── state/
│   ├── rules/
│   ├── planning/
│   ├── control/
│   ├── walls/
│   ├── persistence/
│   └── app/
├── tests/
│   ├── unit/
│   ├── image/
│   ├── replay/
│   └── integration/
└── data/
```

