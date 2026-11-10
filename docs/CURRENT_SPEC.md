# Current Specification (CURRENT_SPEC.md)

This document is the **Primary Source of Truth** for what the Clash of Clans Autonomous Farming Controller SHOULD currently do. It overrides all historical planning documents.

## 1. Project Purpose & Scope
- **Purpose**: Autonomous farming bot for Clash of Clans on Windows PC.
- **Scope**: Supports both **Main Home Village** (auto-farming loot/walls) and **Builder Base 2.0** (auto-battling for loot/stars).
- **Out of Scope**: Advanced base-specific path planning, defense-by-defense targeting, network packet inspection, memory injection, Clan Castle troop automation, dodging anti-bot mechanisms.
- **Supported Environment**: Windows 10/11 running LDPlayer 9, BlueStacks 5, or Google Play Games PC. Must run at **1920x1080** resolution in Landscape mode.

## 2. Main Home Village Requirements
### Target Selection
- **Target Extraction**: Extract Gold, Elixir, and Dark Elixir from the top-left HUD using OCR.
- **Evaluation Criteria**: Configurable logic supporting ANY (OR) or ALL (AND) logic against user-defined minimum thresholds.
- **Skip Behavior**: Automatically clicks 'Next' if criteria are not met.

### Army Configuration
- **Current Baseline**: Electro Dragons (16), Battle Blimp / Log Launcher (1), Heroes (Barbarian King, Archer Queen, Grand Warden, Dragon Duke/Minion Prince), Earthquake Spells (11).
- **Clan Castle**: Clan Castle troops are explicitly NOT used in the current version. The system MUST NOT assume Clan Castle troops are available, and the absence of Clan Castle deployment MUST NOT be treated as a deployment failure. Future implementation is planned.
- **Deployment Behavior**:
  1. **Probe/Test**: Planners execute smart troop probe deployment to find valid placement (e.g., beside 'Battle ends in:' on top grass).
  2. **Dump/Deployment**: Once location is confirmed, dump all remaining troops at that exact spot. Deploy Siege and Heroes with exactly 1 click each.
  3. **Spells**: Cast 11 Earthquake Spells across randomized target points with micro-jitter.
  4. **Abilities**: Pause briefly for units to march, then activate all Hero Abilities with 1 click each.
- **Historical Note**: Original PRD specified Valkyries/Totems via a 4-edge perimeter spread. This was intentionally changed to Electro Dragons and single-spot dump deployment.

### Battle Exit Behavior
- Monitor damage percentage and time remaining.
- Exit at >= 50% damage by clicking End Battle, OR at <= 60 seconds remaining if damage is < 50% by clicking Surrender.

### Wall Upgrade Behavior (Auto-Wall)
- Check storage capacity via visual color ratio when returning to Home Village.
- Check if Builder count is >= 1.
- Locate valid wall segments matching selected levels (L15-L19) and upgrade if resource reserves exceed safety minimums.

## 3. Builder Base 2.0 Requirements
### Battle Flow & State Machine
- Transition from Home -> Attack Modal -> Matchmaking -> Pre-Battle Countdown -> Stage 1 Battle.
- **Pre-Battle Countdown**: Must detect the 60s preparation countdown (using Boost Army / Boost Heroes pills) and wait in non-blocking ticks to prevent clicks dropping into a locked screen.
- **Stabilization Buffer**: Wait exactly **5.5 seconds** after the countdown reaches 0s before deploying units to allow camera animations to settle.

### Deployment Behavior (Cascade Deployment)
- **Objective**: Prevent premature activation of unit abilities (e.g., Power P.E.K.K.A overcharge).
- **Behavior**:
  - Select Hero (Slot 0) -> Tap battlefield once.
  - Select Troop (Slot 1) -> Tap battlefield continuously (e.g., 24 times) at a 0.20s cadence with micro-jitter.
  - **CRITICAL**: The bot must NEVER touch the bottom slot bar again. The game will auto-cascade empty camps.

### Battle Exit Behavior
- Wait for 100% destruction or combat timer > 60s before attempting to exit.
- Handle Surrender confirmation dialogs and precise sub-pixel anchoring (Norm: (0.501, 0.850)) for clicking the green 'Return Home' button on result screens.

## 4. Input & Safety Requirements
- **Humanized Kinematics**: Every tap must apply a 2D Gaussian random offset and a variable hold duration (e.g., 35ms - 65ms).
- **Pause/Stop**: Must support Global Hotkeys (F8 Start/Resume, F9 Pause, F10 Emergency Stop).
- **Focus Guard**: Instantly halt click dispatches if the emulator loses active window focus to prevent stray desktop clicks.

## 5. Vision & Detection Requirements
- Must use normalized coordinates [0.0, 1.0] mapping dynamically to the emulator window.
- Must support proportional template scaling (scaling 1080p templates to fit the live frame height).
- YOLOv8 and multi-scale OpenCV template matching handle state detection.

## 6. Unresolved / Open Questions
- *None currently identified. The current specification strictly matches implemented functionality.*
