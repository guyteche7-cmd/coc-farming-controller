# Future Implementation Plan: Dynamic Deployment Engine

This document describes a future architectural direction for the deployment subsystem.

The goal is to replace fixed army-specific deployment logic with a robust,
runtime-driven deployment system that can safely handle changing army
compositions without requiring the core deployment code to be rewritten.

## 1. CORE PROBLEM
The army composition changes frequently during development and normal use.
Therefore, deployment logic MUST NOT be built around fixed assumptions such as:
- 40 Valkyries
- 10 Dragons
- 11 Totems
- a fixed number of clicks for a troop
- a fixed number of available spells
- a permanently fixed army layout

The deployment system must derive deployment quantities from the CURRENT RUNTIME ARMY.

## 2. ARCHITECTURAL PRINCIPLE
Army composition is runtime data. It is NOT hard-coded business logic.
The system should conceptually operate as:
    Screen -> Army Recognition -> Runtime Army State -> Deployment Policy -> Dynamic Deployment Planner -> Abstract Actions -> Input/Motion Layer -> Deployment Verification

## 3. CURRENT STRATEGY VS DEPLOYMENT ENGINE
The current Main Village strategy is: Electro Dragons + Earthquake.
This is the CURRENT STRATEGY, not the permanent architecture of the deployment engine.
The deployment engine must remain capable of supporting future army configurations without rewriting the core planner.

## 4. RUNTIME ARMY RECOGNITION
Before generating a deployment plan, the system should determine the currently available army from the visible game UI.
The runtime army model should contain, where applicable: troop type, spell type, siege type, hero type, quantity, slot, availability, confidence, source region, timestamp.
The planner must reason about the dynamic quantities detected (e.g., 10 Electro Dragons or 40 Valkyries). The previous runtime army must never leak into the new attack.

## 5. QUANTITY MUST BE DYNAMIC
Deployment policies should not require hard-coded troop quantities unless a strategy explicitly requests one.
Consider supporting quantity modes such as: ALL_AVAILABLE, FIXED, PERCENTAGE, REMAINING, UNTIL_CONDITION.

## 6. NO SILENT UNIT SUBSTITUTION
If a deployment policy requests a specific unit type and that unit is not detected in the current army, the planner must NOT silently replace it with another unit.
The system should stop/re-evaluate/re-plan according to the defined recovery behavior.

## 7. CONFIDENCE REQUIREMENTS
Runtime army recognition must include confidence. High-impact deployment actions must not rely on an uncertain army recognition result.
Uncertain classification should trigger re-observation or safe recovery rather than blindly deploying the wrong unit.

## 8. DEPLOYMENT POLICY
Separate WHAT should be deployed from HOW many units happen to exist.
A deployment policy should describe concepts such as unit type, quantity mode, deployment region, formation, ordering, conditions, dependencies, verification requirements.
It should NOT permanently encode the current army quantity.

## 9. PLAN INVALIDATION
A generated deployment plan must be tied to the runtime army state from which it was created.
If the runtime army changes significantly before execution, the plan should be invalidated and regenerated.

## 10. DEPLOYMENT ACCOUNTING
The deployment engine should maintain an accounting model such as: expected/currently available, planned, attempted, successfully deployed, remaining, unavailable, unknown.
The system should not equate number of mouse clicks with number of successfully deployed units. Verification must be based on observed game state where practical.

## 11. ABSTRACT ACTIONS
The deployment planner should produce abstract actions rather than direct screen-input commands. (e.g., "Select Electro Dragon", "Deploy formation at region A").
The input layer is responsible for translating those actions into actual UI interaction.

## 12. FUTURE NATURALISTIC MOTION SYSTEM
Future work may introduce a separate Naturalistic Motion / Input layer to provide smooth, non-rigid, physically plausible interaction while preserving deterministic safety and verification.
Possible techniques: Cubic Bézier trajectories, controlled micro-variation, smooth acceleration/deceleration, logistic timing functions, Fitts's Law.
These techniques are an input/motion implementation detail, not part of the deployment planner. The motion layer must never determine gameplay decisions, nor bypass anti-bot detection.

## 13. MOTION LAYER MUST REMAIN REPLACEABLE
The architecture should allow multiple input executors (e.g., DryRunExecutor, DeterministicInputExecutor, NaturalisticMotionExecutor).

## 14. CLAN CASTLE
Clan Castle deployment is NOT a current blocking requirement. It should be treated as a FUTURE IMPROVEMENT.
Until that feature is implemented and verified, the system must not blindly assume that Clan Castle troops are available.

## 15. CURRENT STRATEGY
The current Main Village strategy is: Electro Dragons + Earthquake.
Do not turn this current strategy into hard-coded assumptions inside the core deployment subsystem.

## 16. FUTURE DEVELOPMENT ORDER
Phase 1: Runtime army recognition
Phase 2: Runtime army data model
Phase 3: Dynamic quantity resolution
Phase 4: Deployment policy abstraction
Phase 5: Dynamic deployment planner
Phase 6: Deployment accounting
Phase 7: Deployment verification
Phase 8: Plan invalidation/re-planning
Phase 9: Replay and regression testing
Phase 10: Optional naturalistic motion layer
Phase 11: Future Clan Castle support

## 17. TESTING REQUIREMENTS
The future system must be tested against changing army compositions (different troop quantities, missing expected troops, partially detected armies, etc.).
Critical regression test: Previous attack (Valkyrie x 40) vs Current attack (Electro Dragon x 10). It must NOT execute the previous Valkyrie quantity.

## 18. SUCCESS CRITERIA
1. No core deployment logic depends on a fixed troop quantity.
2. Runtime army composition is detected before deployment.
3. Deployment quantities are resolved from runtime state.
4. Different army compositions can use the same deployment engine.
5. Old army state cannot leak into a new attack.
6. Low-confidence army recognition prevents unsafe deployment.
7. Deployment plans can be invalidated and regenerated.
8. Click count is not treated as proof of successful deployment.
9. Deployment decisions are separated from input/motion execution.
10. Clan Castle remains an explicit future feature.
11. Naturalistic motion remains an independent future feature.
12. The system remains testable in replay/dry-run mode.

## 19. DOCUMENTATION REQUIREMENT
When implemented, update: CURRENT_SPEC.md, CURRENT_ARCHITECTURE.md, IMPLEMENTATION_STATUS.md, CHANGELOG.md.
Do not modify historical documents to make them appear as though dynamic deployment was part of the original design.
