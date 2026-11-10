# Instructions for AI Coding Agents

Welcome to the Clash of Clans Autonomous Farming Controller project.
If you are an AI agent or a developer beginning work on this project, **YOU MUST READ THIS FILE FIRST.**

## Documentation Authority Hierarchy

This project has evolved significantly from its original design. Do not treat original planning documents as the current requirements. The strict documentation hierarchy is:

1. **AGENTS.md** (This file) - Meta-instructions for you.
2. **docs/CURRENT_SPEC.md** - The ultimate source of truth for what the system SHOULD currently do.
3. **docs/CURRENT_ARCHITECTURE.md** - The ultimate source of truth for HOW the system is currently designed.
4. **docs/IMPLEMENTATION_STATUS.md** - The verified status of what has actually been implemented and tested in the codebase.
5. **docs/CHANGELOG.md** - A record of important design decisions and deviations from the original plan.
6. **docs/OPERATOR_GUIDE.md** - User-facing instructions on how to run the bot.
7. **docs/research/** - Research notes, visual findings, and game observations.
8. **docs/history/** - Original planning documents (e.g., old PRDs, design docs). **Do NOT treat these as current requirements.**

## Rules for AI Agents

1. **Never Silently Override Current Specs:** If you find a contradiction between docs/history/ and the actual source code or CURRENT_SPEC.md, **the code and CURRENT_SPEC.md win.** The project has changed intentionally (e.g., moving from Valkyries to Electro Dragons, adding Builder Base).
2. **Do Not Invent Missing Requirements:** If the current specification is ambiguous or lacks details, state clearly that it is UNRESOLVED or NEEDS CONFIRMATION. Do not guess or silently choose a behavior.
3. **Evidence-Based Completion:** When updating IMPLEMENTATION_STATUS.md, only mark things as IMPLEMENTED or VERIFIED if the code explicitly supports it. Do not use vague terms like "100% complete" without proof.
4. **Update Documentation on Change:** If you write code that changes how the bot behaves (e.g., modifying the deployment strategy, adding a new exit condition), you MUST update CURRENT_SPEC.md, CURRENT_ARCHITECTURE.md, and CHANGELOG.md to reflect this change.
5. **Preserve History:** Never rewrite historical documents in docs/history/ to make them match the current implementation. They must remain as historical records.
6. **Ask for Clarification:** If you are asked to implement a feature that contradicts CURRENT_SPEC.md, point out the contradiction to the user before making sweeping architectural changes.
