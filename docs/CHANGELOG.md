# Architectural Changelog & Decision History (CHANGELOG.md)

This document records important decisions and changes where the project direction intentionally diverged from original planning documents.

---

## CHANGE-003
**Title:** Implementation of Builder Base 2.0 Subsystem
**Date:** Post-PRD
**Original:**
The original PRD (PRD.md) scoped the project strictly to the Main Home Village.
**Current:**
A complete, fully isolated Builder Base 2.0 Auto-Battler engine was built in the uilderBase/ directory.
**Reason:**
Builder Base farming (for Builder Gold/Elixir and Stars) is an incredibly high-value, repetitive task with fewer variables (no loot skipping, fixed deployment logic). It offers a highly reliable farming loop.
**Affected systems:**
- Created uilderBase/ module.
- Added Dual-Tab support to GUI.
**Status:** ACCEPTED & IMPLEMENTED

---

## CHANGE-002
**Title:** Builder Base Troop Ability Triggering -> Cascade Deployment
**Original:**
The BB deployment loop clicked every troop slot to deploy units.
**Current:**
The BB deployment planner uses "Safe Cascade Deployment": it clicks Slot 0 (Hero), then clicks Slot 1 multiple times. It *never* clicks slots 2-6.
**Reason:**
In Builder Base 2.0, deploying a 1-unit camp (e.g., Power P.E.K.K.A) automatically shifts the next camp into the active slot. Clicking slots 2, 3, or 4 afterward registered as an "Activate Ability" click on the already deployed troops, causing premature explosions.
**Affected systems:**
- uilderBase/src/bb_deployment_planner.py
**Status:** ACCEPTED & IMPLEMENTED

---

## CHANGE-001
**Title:** Main Village Army Strategy & Deployment Pattern Change
**Original:**
The PRD defined the baseline army as "44 Valkyries, 11 Totems, one Log Launcher, four Heroes". It required a "1-edge line pattern" deployment spreading Valkyries and Totems inward.
**Current:**
The code (src/planning/deployment_planner.py) and Operator Guide rely on: Electro Dragons (16), Battle Blimp (1), Heroes (4), Earthquake Spells (11). Deployment uses a "Single-Spot Dump" after probing for a valid coordinate on the top grass, followed by random 11-point Earthquake casts.
**Reason:**
Electro Dragons with Blimps provide higher consistency for securing 50% damage with a single dump coordinate, greatly simplifying the kinematic requirements compared to dragging a continuous line of Valkyries across an edge.
**Affected systems:**
- src/planning/deployment_planner.py
- docs/OPERATOR_GUIDE.md
**Status:** ACCEPTED & IMPLEMENTED
