# Implementation Status (IMPLEMENTATION_STATUS.md)

This document describes what is ACTUALLY implemented, tested, and verified in the codebase. Do not update this document with planned features until the code exists and functions.

## Core Systems Status

| Component | Intended | Implemented | Tested | Verified | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Screen Capture** | Win32 BitBlt / Duplication | Yes | Yes | **VERIFIED** | Fast capture running smoothly. |
| **Window Detection** | Find emulator HWND | Yes | Yes | **VERIFIED** | Locks to LDPlayer / BlueStacks. |
| **Viewport Calibration** | Normalize window rect | Yes | Yes | **VERIFIED** | [0.0, 1.0] coordinate mapping works. |
| **GUI Framework** | CustomTkinter interface | Yes | Yes | **VERIFIED** | Dual tab layout (980x640) functional. |
| **Focus Guard Safety** | Halt clicks if unfocused | Yes | Yes | **VERIFIED** | Prevents stray desktop clicks. |
| **Diagnostic Logging** | Audit logs & Snapshots | Yes | Yes | **VERIFIED** | Tags anomalous states & saves JPEGs. |

## Main Home Village (HV)

| Component | Intended | Implemented | Tested | Verified | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **State Detection (HV)** | 9 UI States | Yes | Yes | **VERIFIED** | Automated test suite passes 9/9 states at 0.92+ conf. |
| **Loot OCR** | EasyOCR Gold/Elixir/DE | Yes | Yes | **VERIFIED** | Preprocessing + parsing handles numbers accurately. |
| **Decision Engine** | ANY/ALL target filtering | Yes | Yes | **VERIFIED** | Skips bases under threshold. |
| **Deployment Planner** | E-Drag/Blimp/Spells | Yes | Yes | **VERIFIED** | Probes 1 spot, dumps troops, casts 11 Earthquakes. |
| **Action Executor** | Humanized micro-jitter | Yes | Yes | **VERIFIED** | Gaussian distribution on click vectors. |
| **Auto-Wall Upgrader** | Check storage & upgrade | Yes | Yes | **VERIFIED** | Uses color ratio and template matching (L15-L19). |
| **Battle Monitor/Exit** | 50% dmg or 60s timer | Yes | Yes | **VERIFIED** | Successfully clicks End Battle / Surrender. |

## Builder Base 2.0 (BB)

| Component | Intended | Implemented | Tested | Verified | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **State Detection (BB)** | 8 UI States | Yes | Yes | **VERIFIED** | Automated test suite passes 12/12 test cases at 0.92+ conf. |
| **Countdown Detection** | 60s Pre-Battle Isolation | Yes | Yes | **VERIFIED** | Senses Boost Pills to pause inputs during lockout. |
| **Stabilization Buffer** | 5.5s delay after countdown | Yes | Yes | **VERIFIED** | Delays deployment perfectly to avoid animation glitches. |
| **Cascade Deployment** | Zero-ability drop logic | Yes | Yes | **VERIFIED** | Clicks slot 1 repeatedly; never touches slots 2-6. |
| **Return Home Flow** | Precise exit button anchor | Yes | Yes | **VERIFIED** | Uses (0.501, 0.850) norm to perfectly hit the green button. |

## Known Limitations / Missing Features
- **Clan Castle Automation**: Planned for future implementation. The current verified deployment system intentionally ignores Clan Castle troops. The system must not assume they are available, and their absence is NOT a deployment failure.
- **Dynamic Adaptive Deployment**: Currently relies on static spot probing and specific Army composition rather than a fully dynamic pathfinding approach.
- **Advanced Target Evaluation**: Does not currently evaluate defensive layout, only resource counts.
