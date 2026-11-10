> [!WARNING]
> **HISTORICAL DOCUMENT � NOT CURRENT SOURCE OF TRUTH**
> This document represents earlier project planning and may contain requirements that have since changed.

# Clash of Clans Resource Farming Automation — Rules

**Status:** Draft v1.0
**Date:** 2026-08-22

## 1. Rule Principles

Rules describe what the system should decide, not how the clicks are implemented.

## 2. Target Rules

### Default expression

```text
Gold >= 1,000,000 OR Gold + Elixir >= 1,500,000
```

### Editable expressions

The system must support user-editable expressions containing:

- `gold`
- `elixir`
- `dark_elixir`
- numeric thresholds
- arithmetic `+`
- comparison operators `>=`, `>`, `<=`, `<`, `==`
- boolean operators `AND`, `OR`
- parentheses

### Dark Elixir

Default: ignored.

Optional examples:

```text
dark_elixir >= 10000
```

or

```text
gold + elixir >= 1500000 OR dark_elixir >= 10000
```

## 3. Candidate Village Rules

1. Candidate must be recognized as a valid multiplayer battle screen.
2. Resource values must be recognized with acceptable confidence.
3. If the configured expression evaluates true, accept.
4. Otherwise choose Next and scan again.
5. There is no default maximum skip count.
6. Skips are not counted as attacks.

## 4. Army Rules

1. Discover the current army at runtime.
2. Record expected quantities in the Army Ledger.
3. Do not assume the baseline army remains unchanged between sessions.
4. If the runtime army cannot be confidently recognized, do not begin deployment.
5. No Clan Castle troops are expected in the baseline test configuration.

## 5. Troop Deployment Rules

### Baseline troops

Deploy Valkyries in a line pattern along one selected edge.

The line has upper, middle, and lower regions to distribute the deployment.

### Hero deployment

Deploy all available attacking Heroes around the middle region of the chosen edge.

Do not assume all Heroes behave identically.

### Siege

Deploy the Log Launcher after the Heroes, using a configured position associated with the same attacking side.

### Spells

Deploy Totems beginning near the region where the army started deployment and progress inward toward the base.

The exact number and spacing of Totem placements must be derived from runtime quantity and configurable pattern parameters.

## 6. Ability Rules

Hero deployment and Hero ability activation are separate phases.

v1 must not require equipment-specific optimization.

Where ability activation is enabled, the ability controller must verify that the relevant Hero is active and the ability control is visible before acting.

## 7. Deployment Completeness Rules

After planned deployment:

1. Re-read the army bar.
2. Compare expected vs remaining quantities.
3. Mark each unit as `DEPLOYED`, `UNDEPLOYED`, `UNAVAILABLE`, or `UNKNOWN`.
4. If an expected unit remains undeployed and is still deployable, attempt the missing deployment.
5. If the state cannot be determined, enter `DEPLOYMENT_UNCERTAIN`.
6. Do not mark the phase complete from a low-confidence read.

## 8. Battle Exit Rules

### Rule A — Damage threshold

If:

```text
total_damage >= 50%
```

then:

```text
click End Battle
confirm Okay
process result
```

### Rule B — Time threshold

If:

```text
total_damage < 50%
AND
remaining_time <= 60 seconds
```

then:

```text
click Surrender
confirm Okay
process result
```

### Priority

Damage threshold takes priority whenever it is reached.

## 9. Result Rules

Every completed battle must produce a structured session record containing, where visible:

- outcome: victory/defeat;
- total damage;
- loot obtained;
- star result;
- troops expended/visible result details;
- timestamp;
- target resource values at the time of acceptance.

## 10. Wall Rules

### Trigger

Wall mode is enabled by configuration.

Preferred current user rule:

```text
Gold storage >= 80% OR Elixir storage >= 80%
```

Builder requirement is configurable and currently defaults to `true` for the user's preferred mode.

### Upgrade loop

After returning Home:

1. Check builder/resource conditions.
2. Scan for eligible wall levels.
3. Select an eligible wall or wall batch.
4. Confirm the upgrade UI.
5. Execute the upgrade.
6. Verify resource change or upgrade confirmation.
7. Repeat while eligible.

### Stop wall upgrading when

- no eligible walls remain;
- the relevant resource condition is no longer satisfied;
- the next upgrade is unaffordable;
- detection becomes uncertain;
- the expected wall UI is absent;
- the user pauses/stops.

Current game documentation indicates multiple walls of the same level can be selected for an upgrade batch, so the wall planner should prefer batch selection when the UI confirms that option. [Supercell update](https://supercell.com/en/games/clashofclans/blog/news/get-geared-up-for-the-latest-update--3/)

## 11. Operation Mode Rules

### Wall + Attack

Return Home → Wall Check → Wall Upgrade Loop → Attack Cycle.

### Fixed Attack Count

Stop after the configured number of attacks has completed.

Skipped candidates do not count.

### Infinite

Continue until the user selects Stop.

## 12. Pause Rules

Pause freezes the action executor.

While paused:

- no clicks are generated;
- no deployment actions are generated;
- the current logical state is retained;
- the screen may still be observed for status display.

Resume continues from the current state only if the observed UI still matches the saved state expectations; otherwise re-enter state detection.

## 13. Stop Rules

Stop must be safe and immediate for future action generation.

The application must not issue new gameplay actions after Stop is asserted.

## 14. Error Rules

Unknown state → stop or recover through a safe state transition.

Low-confidence resource OCR → do not accept target.

Button missing → re-scan before clicking.

Unexpected dialog → detect and classify before acting.

Repeated state-transition failure → safe stop.

## 15. Configuration Rules

No farming threshold, attack-count mode, wall toggle, or pause behavior should require editing Python source code.

