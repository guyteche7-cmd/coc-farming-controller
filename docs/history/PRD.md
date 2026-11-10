> [!WARNING]
> **HISTORICAL DOCUMENT � NOT CURRENT SOURCE OF TRUTH**
> This document represents earlier project planning and may contain requirements that have since changed.

# Clash of Clans Resource Farming Automation — PRD

**Status:** Draft v1.0
**Date:** 2026-08-22
**Target Platform:** Windows PC, Clash of Clans via Google Play Games
**Primary language candidate:** Python

## 1. Product Summary

This project explores a screen-based computer-vision and UI-automation controller for a Clash of Clans farming workflow. The application observes the visible game UI, identifies the current state, evaluates candidate villages against editable resource rules, performs a deliberately simple attack deployment pattern, verifies deployment, exits the attack using explicit thresholds, returns home, and optionally performs wall upgrades.

The architecture is intentionally state-driven rather than a hard-coded macro. Perception, decision-making, action planning, UI execution, and verification are separate responsibilities.

## 2. Important Policy Boundary

This project must not be represented as permitted by Supercell. Supercell's current support guidance explicitly identifies bots, gameplay automation scripts, third-party software that gives an unfair advantage, and similar automation as unacceptable behavior and states that penalties may be applied. Therefore, use of the system against a live account carries account-risk and policy-compliance risk. The project must not include anti-bot evasion, memory modification, network manipulation, code injection, game-file modification, or vulnerability exploitation.

Development should still use normal visible UI observation and input only. A screenshot-replay/mock environment remains the preferred engineering test harness even though the user intends to test on the live PC game.

## 3. Goals

### Must

- Detect the current game UI state from screenshots/screen capture.
- Navigate from Home Village to Multiplayer matchmaking.
- Read visible Gold and Elixir loot from candidate villages.
- Support an editable target expression.
- Default target rule: `Gold >= 1,000,000 OR Gold + Elixir >= 1,500,000`.
- Optionally include a Dark Elixir threshold.
- Skip candidate villages until the configured target requirement is met.
- Detect the runtime army instead of hard-coding one permanent army composition.
- Support the current baseline army: 44 Valkyries, 11 Totems, one Log Launcher, four Heroes, no Clan Castle troops.
- Deploy Valkyries in a line along one configured edge.
- Deploy Heroes around the middle of that edge.
- Deploy the Log Launcher after the Heroes.
- Deploy Totems beginning near the troop deployment region and progressing inward toward the base.
- Verify that no configured deployable unit remains unintentionally undeployed.
- Exit at `>= 50%` damage by using End Battle, or at `<= 60 seconds` remaining when damage is still below 50% by using Surrender.
- Support three operation modes: Wall + Attack, Fixed Number of Attacks, Infinite.
- Provide global Pause and Stop controls.
- After returning Home, evaluate wall-upgrade conditions and upgrade eligible walls while conditions remain satisfied.
- Log decisions, state transitions, recognition confidence, errors, and attack results.

### Should

- Automatically locate/calibrate the Clash of Clans viewport inside the Google Play Games window.
- Use normalized coordinates and visual anchors rather than fixed absolute screen coordinates where practical.
- Save screenshots on recognition and state-transition failures.
- Maintain attack/session statistics.
- Support configuration without source-code edits.

### May

- Add better target scoring beyond the initial resource rule.
- Add adaptive deployment edge selection.
- Add richer Hero ability timing.
- Add wall-image classification across levels.

## 4. Non-Goals for v1

- Advanced attack strategy or guaranteed high-star outcomes.
- Defense-by-defense path planning.
- Town Hall sniping.
- Anti-bot detection or evasion.
- Memory inspection or game-state extraction outside the visible UI.
- Network packet inspection or modification.
- Game binary/file modification.
- Clan Castle troop automation; baseline configuration contains no Clan Castle troops.
- Full automation of every possible army type before the baseline flow is reliable.

## 5. Initial User Configuration

### Display

- Resolution: 1920x1080
- Windows scaling: 100%
- Game: maximized/full-screen style, including F11 full-screen mode

### Army

- 44 × Valkyrie
- 11 × Totem Spell
- 1 × Log Launcher
- 1 × Archer Queen
- 1 × Barbarian King
- 1 × Grand Warden
- 1 × Dragon Duke
- 0 Clan Castle troops

### Equipment reference

- Archer Queen: Action Figure, Magic Mirror
- Barbarian King: Spiky Ball, Earthquake Boots
- Grand Warden: Rage Gem, Heroic Torch
- Dragon Duke: Electro Fangs, Fire Heart

Equipment is configuration/reference data in v1; ability automation is a separate subsystem.

## 6. Target Selection Requirements

The target evaluator must use a configurable expression. Examples that must be supported by the rules engine include:

- `gold >= 1000000`
- `gold + elixir >= 1500000`
- `gold >= 1000000 OR gold + elixir >= 1500000`
- `gold + elixir >= 1500000 OR dark_elixir >= 10000`

Dark Elixir is ignored by default, but an optional threshold must be available.

A candidate with unreadable or low-confidence resource data must not be silently accepted.

## 7. Attack Requirements

### Navigation

Home Village → Attack → Multiplayer → Find a Match → Candidate Scan.

### Candidate scan

1. Detect candidate battle screen.
2. Read Gold, Elixir, and optionally Dark Elixir.
3. Evaluate the configured target expression.
4. If rejected, select Next and repeat.
5. Continue until accepted, stopped, paused, or an unrecoverable state occurs.

### Deployment

1. Detect battlefield and deployment UI.
2. Discover the runtime army.
3. Create an Army Ledger.
4. Deploy all Valkyries using a one-edge line pattern.
5. Deploy all available Heroes around the middle of the same edge.
6. Deploy the Log Launcher.
7. Deploy all configured Totems from the troop start area inward toward the base according to the configured pattern.
8. Verify remaining army state.
9. Enter wait/exit monitoring.

The deployment engine must not assume that all future armies will be Valkyries/Totems. The current army is the first test case.

## 8. Exit Requirements

The application shall continuously monitor attack time and visible total damage.

Priority:

1. If total damage reaches or exceeds 50%, use End Battle, confirm the dialog, and process the result screen.
2. Otherwise, when time remaining reaches or falls below 60 seconds, use Surrender, confirm the dialog, and process the defeat result.

The result screen must be recorded regardless of outcome.

## 9. Operating Modes

### Mode A — Wall + Attack

Return Home → Check wall conditions → Upgrade walls while eligible → Start next farming cycle.

### Mode B — Fixed Number of Attacks

Run until the requested number of attacks has completed. Skipped candidate villages do not count as attacks.

### Mode C — Infinite

Repeat until the user stops the session.

All modes have Pause and Stop controls.

## 10. Wall Upgrade Requirements

User-selected default behavior:

- Check walls after returning Home from an attack.
- Wall mode is active only when enabled.
- Preferred trigger: either Gold storage or Elixir storage is at least 80% full.
- User preference currently treats a free builder as part of the trigger; implementation must verify current wall UI/mechanics instead of assuming walls consume a normal builder slot.
- Continue upgrading while eligible walls and sufficient resources remain.
- Stop on insufficient resources, no eligible walls, failed verification, or changed resource/builder condition.

The current game supports adding multiple walls of the same level to a wall-upgrade selection, so the design should consider batch selection rather than assuming one-wall-at-a-time behavior. [Source: Supercell, “A new Update is here!”](https://supercell.com/en/games/clashofclans/blog/news/get-geared-up-for-the-latest-update--3/)

## 11. UI and Environment Requirements

The user plays at 1920×1080 and 100% Windows scaling. The game may be maximized and then placed into full-screen with F11. The automation must locate the actual game viewport rather than assuming the monitor is entirely the game.

Supercell officially supports Clash of Clans on Windows through Google Play Games, with mouse controls and gameplay equivalent to mobile. [Source: Supercell, “Clash of Clans and Clash Royale Are Now Officially Available on PC!”](https://supercell.com/en/news/clash-games-live-on-pc/)

## 12. Success Criteria

The first production-quality milestone is reached when the system can reliably:

- recognize all required states in the supplied screenshot dataset;
- identify the resource panel and parse target values with acceptable confidence;
- skip and accept targets according to configuration;
- detect the configured army at runtime;
- execute the baseline deployment sequence;
- verify the deployment result;
- exit using the correct 50% / 60-second rule;
- return Home safely;
- run wall checks without erroneous clicks;
- pause/resume/stop without corrupting state;
- capture enough diagnostics to investigate failures.

## 13. Acceptance Criteria

A test run is considered successful only if every major action has both a precondition and a postcondition. Unexpected screens, low-confidence recognition, missing buttons, or contradictory UI evidence must cause safe recovery or stop rather than random clicking.

## 14. Risks

- Game UI may change without notice.
- Visual recognition can fail under animations, effects, overlays, and different village layouts.
- Current game mechanics may change after the research date.
- Live automation may violate Supercell policy and risk account sanctions.
- Hero, spell, and wall mechanics can be version-sensitive.

## 15. Research Baseline

Research date: 2026-08-22.

Current research confirms that Dragon Duke is a Home Village Hero for Town Hall 15+, that attacking Heroes are selected from up to four slots, and that Heroes have battle abilities. [Supercell Support: About Heroes & Pets](https://support.supercell.com/clash-of-clans/en/articles/about-heroes-pets-9.html)

Totem is a real Clash of Clans spell introduced with Town Hall 18-era content; its February 2026 balance update changed its radius from 6 tiles to 5 and its damage from 70–100 to 0. [Supercell: The February Update has escaped!](https://supercell.com/en/games/clashofclans/blog/release-notes/the-february-update-has-escaped/)

Supercell's current fair-play guidance identifies bots, scripts, and gameplay automation as prohibited behavior. [Supercell Support: List of Unacceptable Behavior](https://support.supercell.com/clash-of-clans/en/articles/list-of-unacceptable-behavior.html)

