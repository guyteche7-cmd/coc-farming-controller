> [!WARNING]
> **HISTORICAL DOCUMENT � NOT CURRENT SOURCE OF TRUTH**
> This document represents earlier project planning and may contain requirements that have since changed.

# Clash of Clans Resource Farming Automation — Development Phases

**Status:** Draft v1.0
**Date:** 2026-08-22

## Phase 0 — Research and Specification

### Objective
Lock down game mechanics, user behavior, UI states, constraints, and policy boundaries.

### Deliverables
- PRD.md
- architecture.md
- rules.md
- design.md
- memory.md
- research/source log

### Exit criteria
No critical requirement remains ambiguous.

## Phase 1 — Screenshot and UI Dataset

### Objective
Create a structured dataset from supplied and newly captured screenshots.

### Required classes
- Home Village
- Attack menu
- Multiplayer
- Candidate battle
- Active battle
- End Battle dialog
- Surrender dialog
- Victory result
- Defeat result
- Army screen
- Wall UI
- Builder/resource status

### Exit criteria
Every required state has representative screenshots under normal and failure conditions.

## Phase 2 — Viewport Calibration

### Objective
Locate the Clash of Clans viewport at 1920×1080/100% in the maximized/full-screen PC environment.

### Tests
- normal full-screen;
- maximized non-F11;
- game reopened;
- minor window movement where applicable.

### Exit criteria
Stable normalized coordinate transform with confidence score.

## Phase 3 — UI State Recognition

### Objective
Detect the current game state from screenshots.

### Exit criteria
Replay tests achieve high-confidence classification on the reference dataset with explicit failure handling.

## Phase 4 — Resource Recognition

### Objective
Read Gold, Elixir, and optional Dark Elixir from the candidate loot panel.

### Exit criteria
Known screenshot values parse correctly and low-confidence values are rejected rather than guessed.

## Phase 5 — Configurable Target Engine

### Objective
Implement editable resource expressions.

### Exit criteria
Unit tests cover examples such as:

```text
gold >= 1000000
gold + elixir >= 1500000
gold >= 1000000 OR gold + elixir >= 1500000
dark_elixir >= 10000
gold + elixir >= 1500000 OR dark_elixir >= 10000
```

## Phase 6 — Army Recognition and Ledger

### Objective
Detect runtime troops/spells/siege/Heroes from the army UI and maintain an Army Ledger.

### Exit criteria
Current baseline army is detected correctly on multiple screenshots and the ledger can represent different future army compositions.

## Phase 7 — Action Planning in Dry Run

### Objective
Generate the full navigation/deployment/exit plan without sending real mouse input.

### Exit criteria
The planner generates deterministic actions for the baseline scenario and reports all intended coordinates/targets.

## Phase 8 — Real UI Controller

### Objective
Implement visible mouse/keyboard interaction behind a controlled interface.

### Exit criteria
Each action has a precondition, execution, and verification result.

## Phase 9 — Baseline Attack Workflow

### Objective
Complete one end-to-end attack using the current baseline army.

### Workflow
Home → Multiplayer → Find Match → Candidate Scan → Accept → Deploy → Verify → Monitor → Exit → Result → Return Home.

### Exit criteria
The workflow completes with diagnostic logs and no unsafe random actions.

## Phase 10 — Exit Logic

### Objective
Implement and test:

- ≥50% → End Battle;
- <50% and ≤60s → Surrender.

### Exit criteria
Both dialog paths are recognized and confirmed correctly from screenshots/replay.

## Phase 11 — Operating Modes

### Objective
Add:

- Wall + Attack;
- Fixed Number of Attacks;
- Infinite.

Add Pause and Stop.

### Exit criteria
Mode counters and control behavior are deterministic and logged.

## Phase 12 — Wall Recognition and Upgrade

### Objective
Detect wall-upgrade eligibility and use current wall batch-selection UI when available.

### Exit criteria
The system can safely perform a wall-upgrade loop under mock/replay conditions and stop at all defined boundaries.

## Phase 13 — Reliability Hardening

### Objective
Improve recovery from:

- delayed transitions;
- animations;
- overlays;
- OCR failures;
- unexpected dialogs;
- window focus changes;
- game updates.

### Exit criteria
Repeated replay and long-duration tests show predictable behavior and safe stops.

## Phase 14 — Live Controlled Test

### Objective
Use the live game only after dry-run/replay tests pass.

### Guardrails
- visible UI only;
- no memory or network manipulation;
- emergency Stop available;
- conservative timeouts;
- screenshots/logging enabled.

### Exit criteria
Only if the user accepts the policy/account risk and the software remains within the defined technical boundary.

