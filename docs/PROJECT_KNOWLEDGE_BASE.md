# Clash of Clans Autonomous Controller — Permanent Project Knowledge Base & Memory

> **Note**: This file serves as the permanent, cumulative memory for Antigravity and developers. All architectural decisions, known game mechanics, visual invariants, hardware profiles, and strategic plans are permanently recorded here so nothing is ever forgotten across sessions.

---

## 1. Hardware Profile & Compute Environment
- **Host CPU**: AMD Ryzen 5 7235HS
- **Host GPU**: NVIDIA GeForce RTX 4050 Laptop GPU (6GB GDDR6 VRAM, Ada Lovelace architecture, 4th Gen Tensor Cores)
- **Primary Game Environment**: LDPlayer / Android Emulator on Windows (Client Area Window Mode)
- **Secondary Environment**: macOS (Python 3.12+ via start.sh, hotkey bindings F7-F10)
- **Local Python Path**: `C:\Users\ayush\AppData\Local\Python\bin\python.exe`
- **Repository**: `https://github.com/guyteche7-cmd/coc-farming-controller.git`

---

## 2. Clash of Clans Game Invariants & Ribbon Mechanics
1. **Ribbon Order Hierarchy**:
   - Supercell strictly sorts ribbon cards by internal game order, **NOT** the order troops were trained in:
     `[Regular Troops] -> [Super Troops] -> [Siege Machines (max 1)] -> [Heroes (max 4)] -> [Spells (1..N)]`
   - Troop order on ribbon is fixed by Supercell's unit IDs (e.g. Barbarian < Archer < Goblin < Wall Breaker < Valkyrie < Healer).
   - If user brings Valkyries + Wall Breakers + Healers, the position is deterministic by troop ID, but can differ from user's preferred drop sequence.
   - **Solution**: Identify cards by visual icon templates (64x64 icon matching). Map slot index -> troop type, then follow user's custom deployment sequence (`Valkyries first, then Healers, then Wall Breakers`).
2. **Hero Limits**:
   - A player can bring at most 4 heroes into combat.
   - Hero cards have black square level badges in the bottom-left corner and flaming ability borders when active.
   - Never activate ability on non-hero cards.
3. **Siege Machine Limit**:
   - At most 1 siege machine slot per match. Positioned immediately between troops and heroes.
4. **Spells**:
   - Positioned strictly to the right of all heroes. Bottle shape with quantity badge.

---

## 3. Anti-Gem & Economic Safety Directives (CRITICAL)
- **Zero-Gem Expenditure**: The bot must NEVER spend Gems, purchase gems, or confirm upgrade modals with green gem icons.
- **Resource Verification**: Before triggering wall or building upgrades:
  $$\text{Current Storage} \ge \text{Upgrade Cost} + \text{Safety Reserve Threshold}$$
- **Dismiss on Gem Popup**: If a popup contains "Buy with Gems" or a Gem icon, immediately cancel by clicking the red 'X' or tapping outside the dialog.

---

## 4. Vision & Machine Learning Architecture
- **Perception Architecture**:
  - Phase 1 (Heuristic + OCR): Pixel glyph matching for loot/timers + RapidOCR DBNet for text + template matching for ribbon icons.
  - Phase 2 (Edge Deep Learning): Custom YOLOv8-nano (YOLOv8n) trained on user screenshots:
    - 8 Classes: `town_hall`, `gold_storage`, `elixir_storage`, `dark_elixir_storage`, `gold_mine`, `elixir_collector`, `dark_elixir_drill`, `wall`.
    - Real-time inference: ~7–9ms on RTX 4050 via ONNXRuntime / TensorRT.
- **Zoom & Map Visibility**:
  - LDPlayer pinch-to-zoom out (`Ctrl + Scroll Down` or ADB two-finger pinch) at battle start to reveal the entire base and 4 corner compartments.

---

## 5. Deployment Strategies
- **Mode 1: Single-Point Probe & Funnel** (Historical, default for Sneaky Goblins).
- **Mode 2: 4-Side Perimeter Deployment** (Valkyries, Barbarian/Archer Squads spread evenly across the 4 diamond edges).
- **Mode 3: Core Breach Funnel** (Wall breakers crack outer compartment nearest high-value storage/Town Hall $\to$ Heroes funnel into core $\to$ Equipment abilities fired $\to$ Spells saturate core).

---

## 6. Multi-Agent Validation Protocol
- Antigravity can validate complex code, plans, and game logic using built-in **subagents** (`invoke_subagent`), **swarms** (`swarm` board collaboration), or external LLMs (via Gemini API plugin).
