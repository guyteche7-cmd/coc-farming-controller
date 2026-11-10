> [!WARNING]
> **HISTORICAL DOCUMENT � NOT CURRENT SOURCE OF TRUTH**
> This document is a historical progress report (v1). Please refer to CURRENT_SPEC.md and CURRENT_ARCHITECTURE.md for the current source of truth.

# 🛡️ Clash of Clans Autonomous Farming & Battle Controller
## Comprehensive Master Technical Specification & Architecture Handover Report ("Done So Far")

> **Document Version**: 2.4.0  
> **Target Platforms**: Windows 10 / 11, LDPlayer 9, BlueStacks 5 (1920×1080 Landscape)  
> **Runtime Environment**: Python 3.10+ (PyTorch, OpenCV, EasyOCR, YOLOv8, CustomTkinter, PyWin32)  
> **Document Purpose**: This document serves as an exhaustive technical specification, system design guide, and historical changelog for the Clash of Clans Automation Suite. It is structured for software engineers, automation specialists, and project stakeholders to understand the entire architecture, underlying mathematical algorithms, computer vision pipelines, state machines, and solved operational challenges.

---

## 📑 Table of Contents
1. [Executive Summary & High-Level Architecture](#1-executive-summary--high-level-architecture)
2. [Complete Directory & Module Anatomy](#2-complete-directory--module-anatomy)
3. [Mathematical & Perception Foundations](#3-mathematical--perception-foundations)
4. [Subsystem 1: Builder Base 2.0 Auto-Battler Engine](#4-subsystem-1-builder-base-20-auto-battler-engine)
5. [Subsystem 2: Main Home Village Auto-Farmer Engine](#5-subsystem-2-main-home-village-auto-farmer-engine)
6. [Subsystem 3: GUI, Hotkeys & User Experience](#6-subsystem-3-gui-hotkeys--user-experience)
7. [Subsystem 4: Audit Logging & Visual Anomaly Diagnostics](#7-subsystem-4-audit-logging--visual-anomaly-diagnostics)
8. [Comprehensive Root-Cause Changelog (Problems Solved)](#8-comprehensive-root-cause-changelog-problems-solved)
9. [Automated Verification & Diagnostic Health Benchmarks](#9-automated-verification--diagnostic-health-benchmarks)
10. [Standard Operating Procedures (How to Run & Configure)](#10-standard-operating-procedures-how-to-run--configure)

---

## 1. Executive Summary & High-Level Architecture

The **Clash of Clans Autonomous Controller** is a dual-pipeline computer vision and input automation platform designed to operate on Windows alongside Android emulators. Unlike simple clicker bots, this system employs:
- **Multi-Modal Perception**: Combines YOLOv8 deep learning object detection, multi-scale normalized OpenCV template matching, and EasyOCR text extraction.
- **Normalized Coordinate Space**: Operates on a resolution-invariant $[0.0, 1.0]$ coordinate grid, mapping dynamically to any emulator resolution (1080p, 720p, 575p).
- **Humanized Kinematics**: Generates Gaussian-jittered click distributions and variable timing cadences to emulate real human finger taps.
- **Dual Village Automation**:
  - **🏰 Main Village Auto-Farmer**: Analyzes enemy loot, executes 4-finger perimeter tactical attacks, manages builder queues, and performs auto-wall upgrades.
  - **🔨 Builder Base 2.0 Auto-Battler**: Handles matchmaking, pre-battle countdown isolation, zero-ability cascade deployment, star/damage evaluation, surrender timing, and rapid attack cycling.

### High-Level System Architecture
```
                                ┌───────────────────────────┐
                                │   Android Emulator Window │
                                │   (LDPlayer / BlueStacks) │
                                └─────────────┬─────────────┘
                                              │ (Win32 BitBlt / Desktop Duplication)
                                              ▼
                                ┌───────────────────────────┐
                                │  High-FPS Screen Capture  │
                                └─────────────┬─────────────┘
                                              │ (BGR Frame Matrix)
                                              ▼
                ┌───────────────────────────────────────────────────────────┐
                │             Hybrid Computer Vision Engine                 │
                │  - Multi-Scale OpenCV Template Matching                   │
                │  - EasyOCR Text Extraction (Gold, Elixir, Timers)         │
                │  - Dynamic Bounding Box & Anchor Extraction               │
                └─────────────┬───────────────────────────────┬─────────────┘
                              │                               │
             (Home Village UI │                               │ (Builder Base UI)
                              ▼                               ▼
       ┌──────────────────────────────┐              ┌──────────────────────────────┐
       │   HV State Machine (9 S)     │              │   BB State Machine (8 S)     │
       │  - HOME                      │              │  - BB_HOME                   │
       │  - ATTACK_MENU               │              │  - BB_START_ATTACK_MODAL     │
       │  - MY_ARMY_SCREEN            │              │  - BB_MATCHMAKING            │
       │  - MATCHMAKING (Clouds)      │              │  - BB_BATTLE_COUNTDOWN       │
       │  - CANDIDATE_BATTLE (Loot)   │              │  - BB_STAGE1_BATTLE          │
       │  - ACTIVE_BATTLE             │              │  - BB_STAGE2_BATTLE          │
       │  - SURRENDER_DIALOG          │              │  - BB_CONFIRM_DIALOG         │
       │  - VICTORY / DEFEAT_RESULT   │              │  - BB_RESULT_SCREEN          │
       └──────────────┬───────────────┘              └──────────────┬───────────────┘
                      │                                             │
                      ▼                                             ▼
       ┌──────────────────────────────┐              ┌──────────────────────────────┐
       │ HV Tactical Deployment &     │              │ BB Safe Cascade Deployment   │
       │ Wall Upgrader Planning       │              │ (Zero Ability Activations)   │
       └──────────────┬───────────────┘              └──────────────┬───────────────┘
                      │                                             │
                      └───────────────────────┬─────────────────────┘
                                              │ (Normalized Clicks & Delays)
                                              ▼
                                ┌───────────────────────────┐
                                │  Humanized Input Engine   │
                                │  (Win32 SendInput/Jitter) │
                                └─────────────┬─────────────┘
                                              │
                                              ▼
                                ┌───────────────────────────┐
                                │  Audit Logger & Snapshots │
                                │  (data/logs/ + snapshots/)│
                                └───────────────────────────┘
```

---

## 2. Complete Directory & Module Anatomy

```
coc-farming-controller/
├── run.py                             # Main application launcher (GUI entry point)
├── DONE_SO_FAR.md                     # This technical specification document
│
├── assets/                            # Visual assets for Home Village
│   ├── army/                          # Hero & troop icons (Barb King, Queen, Valkyrie, etc.)
│   ├── templates/                     # Pre-processed matching templates
│   ├── test_cases/                    # Benchmark screenshots for 9 Home Village states
│   ├── ui/                            # Buttons (Attack, Next, Surrender, Dialogs, HUDs)
│   └── walls/                         # Wall level templates (L15 – L19)
│
├── builderBase/                       # Builder Base 2.0 Subsystem
│   ├── assets/
│   │   ├── heroes/                    # Battle Machine & Battle Copter icons
│   │   ├── troops/                    # Builder Base troops (P.E.K.K.A, Bomber, Minion, etc.)
│   │   └── ui/                        # Boost pills, Attack button, Return Home template
│   └── src/
│       ├── __init__.py                # Package descriptor
│       ├── bb_audit_logger.py         # Tagged audit logger & anomaly snapshot capturer
│       ├── bb_battle_evaluator.py     # Combat duration timer & exit evaluator
│       ├── bb_deployment_planner.py   # Safe continuous cascade deployment generator
│       ├── bb_session_controller.py   # Threaded worker loop with 5s countdown & focus lock
│       ├── bb_state_detector.py       # Resolution-invariant 8-state UI detector
│       └── bb_state_machine.py        # Deterministic finite automaton for Builder Base
│
├── src/                               # Main Home Village Core Subsystem
│   ├── app/
│   │   ├── gui_app.py                 # Modern compact GUI (980x640, CustomTkinter)
│   │   └── main.py                    # Headless CLI entry point
│   ├── calibration/
│   │   └── viewport.py                # Win32 client area calibration & coordinate mapper
│   ├── capture/
│   │   ├── screen_capture.py          # Fast frame capture via BitBlt & Desktop Duplication
│   │   └── replay_adapter.py          # Offline video/frame replay adapter
│   ├── control/
│   │   ├── action_executor.py         # Humanized micro-jitter click executor
│   │   ├── input_adapter.py           # Win32 PostMessage/SendInput driver
│   │   ├── notifier.py                # Text-to-speech voice and audio synthesizer
│   │   ├── session_controller.py      # Home Village worker thread & pause lock
│   │   └── state_machine.py           # Home Village 9-state farming automaton
│   ├── persistence/
│   │   ├── config_manager.py          # JSON config persistence with schema validation
│   │   └── database.py                # SQLite database interface (`farming.db`)
│   ├── planning/
│   │   ├── deployment_planner.py      # 4-edge tactical army placement planner
│   │   └── wall_planner.py            # Wall segment identifier & upgrade coordinator
│   ├── rules/
│   │   ├── battle_exit_evaluator.py   # Loot gain & star exit evaluation
│   │   ├── expression_parser.py       # Dynamic rule parser for custom loot criteria
│   │   └── wall_evaluator.py          # Resource reserve calculation engine
│   ├── state/
│   │   ├── army_ledger.py             # Army composition tracker
│   │   └── game_state.py              # Pydantic data models for UI state & detections
│   ├── utils/
│   │   └── audit_logger.py            # Home Village decision & anomaly snapshot logger
│   └── vision/
│       ├── ai_detector.py             # YOLOv8 object detection wrapper
│       ├── army_detector.py           # Home Village army slot detector
│       ├── battle_detector.py         # Battle timer and star parser
│       ├── loot_detector.py           # EasyOCR number extractor for Gold/Elixir/DE
│       ├── ocr_engine.py              # OCR preprocessing & text normalization
│       ├── state_detector.py          # Hybrid YOLOv8 + OpenCV state detector
│       └── wall_detector.py           # Wall segment locator & level classifier
│
├── data/                              # Persistent data & runtime logs
│   ├── config.json                    # User settings (loot targets, limits, timings)
│   ├── farming.db                     # SQLite attack records & loot history
│   └── logs/
│       ├── coc_farming.log            # Main application log
│       ├── builder_base_audit.log     # Builder Base tagged audit trail
│       ├── decision_audit.log         # Home Village decision audit trail
│       └── snapshots/                 # Diagnostic JPEG frames from detected anomalies
│
└── tools/                             # Diagnostics, calibration, and test utilities
```

---

## 3. Mathematical & Perception Foundations

### 3.1. Resolution Invariance ($[0.0, 1.0]$ Space)
All UI elements, slot coordinates, buttons, and deployment spots are defined as **normalized coordinates** $(x_{\text{norm}}, y_{\text{norm}}) \in [0.0, 1.0] \times [0.0, 1.0]$.

When interacting with an active emulator window of dimensions $(W, H)$ at client offset $(X_{\text{origin}}, Y_{\text{origin}})$:
$$\text{Pixel}_X = X_{\text{origin}} + \lfloor x_{\text{norm}} \times W \rfloor$$
$$\text{Pixel}_Y = Y_{\text{origin}} + \lfloor y_{\text{norm}} \times H \rfloor$$

### 3.2. Proportional Template Scaling
When matching a reference template $T$ cropped from a standard $1080\text{p}$ frame against a live frame of height $H_{\text{frame}}$:
$$\text{Scale Factor } s = \frac{H_{\text{frame}}}{1080.0}$$
$$T_{\text{scaled}} = \text{cv2.resize}\left(T, (\lfloor W_T \times s \rfloor, \lfloor H_T \times s \rfloor)\right)$$
This enables matching at $720\text{p}$, $575\text{p}$, or high-DPI emulator scalings without creating separate template sets.

### 3.3. Humanized Input Jitter
To prevent anti-cheat heuristic detection, every tap applies a 2D Gaussian random offset $(\Delta x, \Delta y)$ and variable hold duration:
$$\Delta x \sim \mathcal{N}(0, \sigma_x^2), \quad \Delta y \sim \mathcal{N}(0, \sigma_y^2), \quad \text{where } \sigma_x = 0.003 \cdot W, \; \sigma_y = 0.003 \cdot H$$
$$\text{Tap Hold Duration } t_{\text{hold}} \sim \mathcal{U}(35\text{ms}, 65\text{ms})$$

---

## 4. Subsystem 1: Builder Base 2.0 Auto-Battler Engine

### 4.1. State Machine Deterministic Flow
The Builder Base state machine (`BBStateMachine`) cycles through 8 distinct UI states:

```
                  ┌──────────────┐
                  │   BB_HOME    │◄──────────────────────────────────┐
                  └──────┬───────┘                                   │
                         │ Click Attack! Button                      │
                         ▼                                           │
              ┌──────────────────────┐                               │
              │BB_START_ATTACK_MODAL │                               │
              └──────────┬───────────┘                               │
                         │ Click Find Now!                           │
                         ▼                                           │
              ┌──────────────────────┐                               │
              │    BB_MATCHMAKING    │                               │
              └──────────┬───────────┘                               │
                         │ Match Found                               │
                         ▼                                           │
              ┌──────────────────────┐                               │
              │ BB_BATTLE_COUNTDOWN  │                               │
              └──────────┬───────────┘                               │
                         │ 0s Countdown (Dual-Pills disappear)       │
                         ▼                                           │
              ┌──────────────────────┐                               │
              │   BB_STAGE1_BATTLE   │                               │
              └──────────┬───────────┘                               │
                         │ Timer > 60s / 100% Destruction            │
                         ▼                                           │
              ┌──────────────────────┐                               │
              │  BB_CONFIRM_DIALOG   │                               │
              └──────────┬───────────┘                               │
                         │ Click Okay                                │
                         ▼                                           │
              ┌──────────────────────┐                               │
              │   BB_RESULT_SCREEN   │───────────────────────────────┘
              └──────────────────────┘ (Click Return Home at Y=0.850)
```

### 4.2. Breakthrough: Zero-Ability Cascade Deployment
- **The Problem**: In Clash of Clans Builder Base 2.0, units with 1-unit camps (e.g. Power P.E.K.K.A) auto-advance to the next slot when placed. If the bot clicked Slot 2, 3, or 4 after deploying the army, the game registered those clicks as **"Activate Ability"** (triggering Overcharge explosion prematurely).
- **The Solution**: Implemented **Safe Cascade Deployment**:
  1. **Slot 0 (Hero)**: Click Slot 0 $(0.098, 0.833) \rightarrow$ Tap battlefield $(0.776, 0.102)$ 1 time.
  2. **Slot 1 (Troops)**: Click Slot 1 $(0.188, 0.833) \rightarrow$ Tap battlefield continuously 24 times at a relaxed `0.20s` delay.
  3. **Zero Touches to Slot Bar**: The bot **never touches the bottom slot bar again**. The game automatically empties Camp 1, advances to Camp 2, empties Camp 2, advances to Camp 3, etc., deploying all camps with zero ability activations!

### 4.3. Breakthrough: Pre-Battle Countdown Isolation
- **The Problem**: Entering a match presents a 60-second preparation countdown (`"Battle starts in: Xs"`). During this window, the game rejects troop placements. If the bot deployed during countdown, all clicks were discarded, and when the battle actually started, the bot deployed nothing.
- **The Solution**:
  - Detects `bb_boost_army_pill` (purple) and `bb_boost_heroes_pill` (silver) with **`92%` confidence**.
  - Enters `BB_BATTLE_COUNTDOWN` and waits in non-blocking 1.0s ticks.
  - When the countdown hits 0s and the battle begins, it adds a **5.5s stabilization buffer** for camera and UI animations to settle, then executes the deployment plan.

### 4.4. Breakthrough: Precise Return Home Sub-Pixel Anchoring
- **The Problem**: The previous template was cropped too high, causing clicks to hit empty space at $Y = 0.782$ ($Y = 845\text{px}$ in 1080p), missing the green button at $Y = 0.850$ ($Y = 915\text{px}$).
- **The Solution**: Re-cropped `return_home_button.png` to the exact button borders and anchored to **`Norm: (0.501, 0.850)`**, dismissing the result screen immediately on the first tap.

---

## 5. Subsystem 2: Main Home Village Auto-Farmer Engine

### 5.1. Dead Base & Loot Evaluation
1. **Loot Region Extraction**: Crops Gold, Elixir, and Dark Elixir text regions from the top-left HUD.
2. **EasyOCR Pipeline**: Preprocesses crops via adaptive thresholding and morphology, parsing integer loot values.
3. **Decision Rule**: Compares against user-configured targets:
   $$\text{Accept Match } \iff (\text{Gold} \ge \text{MinGold}) \land (\text{Elixir} \ge \text{MinElixir}) \land (\text{DarkElixir} \ge \text{MinDE})$$
   If condition fails, clicks "Next" $(0.90, 0.82)$ to continue searching.

### 5.2. Tactical 4-Edge Perimeter Deployment
- Drops Tank units along the perimeter line closest to high-loot collectors.
- Spreads DPS and cleanup troops in parallel 4-tap waves with Gaussian spatial dispersion.

### 5.3. Autonomous Wall Upgrader
- Queries storage fill percentages via HUD visual color ratio.
- If Builder count $\ge 1$ and resource reserves exceed safety thresholds:
  1. Identifies wall segment candidates matching selected wall level templates (L15 – L19).
  2. Selects wall row and confirms upgrade transaction.

---

## 6. Subsystem 3: GUI, Hotkeys & User Experience

### 6.1. Compact Window Layout (`src/app/gui_app.py`)
- Standardized default geometry to **`980×640`** (minimum `880×560`).
- Compact 320px sidebar with dedicated cards for Session Control, Attack Counter, Loot Telemetry, and Live Preview Feed.
- Seamless tab switching between **`🏰 Main Village`** and **`🔨 Builder Base`**.

### 6.2. 5-Second Preparation Countdown
- When starting via **`F8`** or the GUI **Start** button, the bot announces:
  `"⏳ Starting in 5s... Focus Clash of Clans!"`, counting down `4s... 3s... 2s... 1s...` before executing mouse clicks.

### 6.3. Focus Guard & Global Hotkeys
- **`F8`**: Start / Resume active session.
- **`F9`**: Pause session.
- **`F10`**: Emergency Safe Stop (instantly unhooks mouse/keyboard and terminates worker threads).
- **`FocusGuard`**: Win32 window monitor that automatically halts click dispatches if the emulator loses active window focus, preventing clicks from hitting other desktop applications.

---

## 7. Subsystem 4: Audit Logging & Visual Anomaly Diagnostics

### 7.1. Tagged Audit Logs
Every decision and physical screen tap is logged with millisecond precision:
- **`data/logs/builder_base_audit.log`**:
  ```
  [2026-08-25 00:01:05.120] [DETECTION  ] UI State: 'BB_STAGE1_BATTLE' (92% confidence) | Active Troop Slots: [1, 2, 3, 4, 5, 6].
  [2026-08-25 00:01:10.650] [DEPLOYMENT ] Deploying Select Hero (Slot 0) -> Tap 1/27 at Norm (0.098, 0.833) [Pixel: (188, 900)].
  [2026-08-25 00:01:11.030] [DEPLOYMENT ] Deploying Deploy Hero at (0.776, 0.102) -> Tap 2/27 at Norm (0.778, 0.108) [Pixel: (1494, 117)].
  [2026-08-25 00:01:11.350] [DEPLOYMENT ] Deploying Select Troop Slot 1 -> Tap 3/27 at Norm (0.188, 0.833) [Pixel: (361, 900)].
  [2026-08-25 00:01:11.600] [DEPLOYMENT ] Deploying Cascade Deploy Army (Tap 1/24) -> Tap 4/27 at Norm (0.776, 0.102) [Pixel: (1490, 110)].
  ```
- **`data/logs/decision_audit.log`**:
  ```
  [2026-08-25 00:00:12.440] [LOOT_EVAL   ] Base Scanned: G=650k, E=720k, DE=4.2k -> Decision: ACCEPT MATCH.
  [2026-08-25 00:00:15.800] [DEPLOY_PLAN ] Generated 4-edge deployment wave (32 units).
  ```

### 7.2. Automated Visual Anomaly Capture
- Implemented `log_anomaly_snapshot()` in both audit loggers.
- Whenever an unexpected state transition or timeout occurs, a timestamped JPEG is automatically saved to `data/logs/snapshots/` for visual verification.

---

## 8. Comprehensive Root-Cause Changelog (Problems Solved)

| # | Issue | Symptoms | Root Cause | Code Fix Applied |
|---|---|---|---|---|
| 1 | **Troop Ability Premature Trigger** | Units (Power P.E.K.K.A) exploding and wasting abilities immediately upon drop. | In 1-unit camps, dropping a troop empties the camp and auto-selects the next slot. The old loop clicked slots 2, 3, 4, which the game interpreted as "Trigger Ability" on deployed units. | Rewrote `BBDeploymentPlanner` to use **Safe Cascade Deployment**: Click Slot 0 $\rightarrow$ 1 tap $\rightarrow$ Click Slot 1 $\rightarrow$ 24 continuous taps. Never click slots 2..6. |
| 2 | **Troops Not Deploying at Match Start** | Program enters battle but drops 0 troops; sits idle until combat timeout. | The 60s preparation countdown ("Battle starts in: Xs") locks deployment. A strict detection threshold caused the detector to classify the countdown as active battle and drop army clicks into the locked screen. | Created dual-pill Boost Army/Heroes templates (`92%` match). Added `BB_BATTLE_COUNTDOWN` state that waits for 0s countdown, followed by a **5.5s stabilization buffer**. |
| 3 | **Stuck on Battle Result Screen** | Endless loop clicking "Return Home" without returning to village. | The template was cropped too high ($Y = 845\text{px}$), missing the actual green button at $Y = 915\text{px}$ ($Y_{\text{norm}} = 0.850$). | Re-cropped template to exact button borders, updated anchor to `Norm: (0.501, 0.850)`, and added proportional scaling. |
| 4 | **Oversized GUI Window** | Window opened at `1240x820` with huge empty space in the center. | Rigid grid spacing and excessive paddings. | Compacted window geometry to `980x640` (minsize `880x560`) with 320px sidebar and 8px padding. |
| 5 | **Stray Desktop Clicks** | Clicking outside the emulator if window lost focus. | Input dispatcher fired clicks regardless of window foreground state. | Implemented Win32 `FocusGuard` in `BBSessionController` and `SessionController`. |

---

## 9. Automated Verification & Diagnostic Health Benchmarks

A full automated checkup was executed across the entire codebase with the following results:

```
======================================================================
=== COMPLETE CLASH OF CLANS AUTOMATION SYSTEM HEALTH CHECKUP ===
======================================================================

[1/5] Checking UI & Army Asset Files...
  Found 103 image assets.
  [OK]   All 103 image assets read cleanly with OpenCV (0 corrupted).

[2/5] Testing Builder Base State Detector...
  Loaded 14 BB templates.
  [OK]   Modal Start Attack        -> BB_START_ATTACK_MODAL  (Confidence: 1.00)
  [OK]   Home Village              -> BB_HOME                (Confidence: 1.00)
  [OK]   Matchmaking Search        -> BB_MATCHMAKING         (Confidence: 1.00)
  [OK]   Countdown (43s)           -> BB_BATTLE_COUNTDOWN    (Confidence: 0.92)
  [OK]   Countdown (19s)           -> BB_BATTLE_COUNTDOWN    (Confidence: 0.92)
  [OK]   Countdown (53s)           -> BB_BATTLE_COUNTDOWN    (Confidence: 0.94)
  [OK]   Stage 2 Battle            -> BB_STAGE2_BATTLE       (Confidence: 0.99)
  [OK]   Stage 1 Battle            -> BB_STAGE1_BATTLE       (Confidence: 0.92)
  [OK]   Result Screen 1           -> BB_RESULT_SCREEN       (Confidence: 1.00)
  [OK]   Result Screen 2           -> BB_RESULT_SCREEN       (Confidence: 0.94)
  [OK]   Surrender Dialog          -> BB_CONFIRM_DIALOG      (Confidence: 1.00)
  [OK]   End Battle Dialog         -> BB_CONFIRM_DIALOG      (Confidence: 1.00)

[3/5] Testing Home Village State Detector...
  Loaded 33 HV templates.
  [OK]   HV Home                   -> HOME                   (Confidence: 0.96)
  [OK]   HV Attack Menu            -> ATTACK_MENU            (Confidence: 0.95)
  [OK]   HV Army Screen            -> MY_ARMY_SCREEN         (Confidence: 0.95)
  [OK]   HV Clouds                 -> MATCHMAKING            (Confidence: 0.94)
  [OK]   HV Candidate Enemy        -> CANDIDATE_BATTLE       (Confidence: 0.95)
  [OK]   HV Active Battle          -> ACTIVE_BATTLE          (Confidence: 0.92)
  [OK]   HV Surrender Dialog       -> SURRENDER_DIALOG       (Confidence: 0.95)
  [OK]   HV Defeat Result          -> DEFEAT_RESULT          (Confidence: 0.96)
  [OK]   HV Victory Result         -> VICTORY_RESULT         (Confidence: 0.96)

[4/5] Checking Log Directories & Anomaly Capture...
  [OK]   Log directory ready: data/logs
  [OK]   Snapshot directory ready: data/logs/snapshots

[5/5] DIAGNOSTIC SUMMARY:
  Total Errors:   0
  Total Warnings: 0

  >>> FULL SYSTEM HEALTH STATUS: 100% OPERATIONAL & PERFECT! <<<
```

---

## 10. Standard Operating Procedures (How to Run & Configure)

### 10.1. Prerequisites
1. **Operating System**: Windows 10 / 11 (64-bit).
2. **Android Emulator**: LDPlayer 9 or BlueStacks 5.
   - Resolution: **1920×1080 (Landscape)**.
   - DPI: **240 or 320 DPI**.
3. **Python Environment**: Python 3.10+ with dependencies installed.

### 10.2. Launching the Controller
Run the launcher from PowerShell or Command Prompt:
```powershell
python run.py
```

### 10.3. Operator Instructions
1. Open Clash of Clans in the emulator and navigate to either the Home Village or Builder Base.
2. In the GUI:
   - Select the **`🏰 Main Village`** or **`🔨 Builder Base`** tab.
   - Set your target attack count or loot requirements.
3. Click **Start Session** (or press **`F8`**).
4. Focus the Clash of Clans emulator window during the **5-second countdown**.
5. To pause, press **`F9`**. For an emergency safe stop, press **`F10`**.

