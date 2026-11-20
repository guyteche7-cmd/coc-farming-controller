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
  - In-game setting: User reduces "Deploy Bar Size" in Clash of Clans Settings $\to$ More Settings.
  - Battle-Start Choreography:
    1. Automated pinch-out gesture (`Ctrl + Scroll Down` or dual touch) for 0.4s to reset zoom.
    2. Subtle vertical micro-pan (mouse drag `y=0.45` to `0.55`) to center the base diamond and bring both top and bottom corner compartments into full view.

---

## 5. Deployment Strategies & Meta Evolution
- **Deterministic Ribbon Mapping**:
  - User defines army structure: $N_{\text{troops}}$ troop types, 1 siege machine, $N_{\text{heroes}}$ heroes, $N_{\text{spells}}$ spells.
  - Slots `0..(N-1)`: Strictly troops. Icon matched to identify exact unit type (Valkyrie, Wall Breaker, Healer, Barbarian/Archer Squad).
  - Slot `N`: Strictly Siege Machine. Tapped once to deploy, never for ability.
  - Slots `N+1..N+H`: Strictly Heroes.
  - Trailing slots: Strictly Spells.
  - Bot deploys in user-configured sequence (e.g. Valkyrie first, Healer second, Wall Breaker third), completely ignoring Supercell's ribbon sorting!
- **Mode 1: Single-Point Probe & Funnel** (Historical, default for Sneaky Goblins).
- **Mode 2: 4-Side Diamond Perimeter Deployment** (Valkyries, Barbarian/Archer Squads spread evenly across the 4 diamond edges).
- **Mode 3: Core Breach Funnel** (Wall breakers crack outer compartment nearest high-value storage/Town Hall $\to$ Heroes funnel into core $\to$ Equipment abilities fired $\to$ Spells saturate core).
- **Mode 4: Active Attack Engine (Future Milestone)**: Real-time visual feedback loop monitoring destroyed buildings and adjusting unit waves on the fly.

---

## 6. Multi-Agent Validation Protocol
- Antigravity can validate complex code, plans, and game logic using built-in **subagents** (`invoke_subagent`), **swarms** (`swarm` board collaboration), or external LLMs (via Gemini API plugin).

---

## 7. Dataset Collection & Auto-Labeling Pipeline
- **Auto-Collector**: Captures full-resolution battle and village frames every 5s into `dataset/raw_frames/`.
- **Pre-Labeling Engine**: Local Florence-2 / template matching script generates standard YOLO `.txt` bounding boxes.
- **Offline Review Option**: LabelImg / AnyLabeling runs 100% locally on Windows without cloud accounts. Optional Roboflow/CVAT export.

---

## 8. Asset Library & Town Hall 17 Notes
- **Hero Icons (`assets/heroes/`)**: Sourced directly from in-battle attack ribbon crops for exact aspect ratio matching (King, Queen, Warden, Minion Prince / Royal Champion).
- **Siege Machines (`assets/siege/`)**: All 8 siege machines cropped from camp screen (Wall Wrecker, Blimp, Slammer, Barracks, Log Launcher, Flame Flinger, Drill, Balloon).
- **Spells (`assets/spells/`)**: Cropped from spell selection screen (Earthquake, Lightning, Rage, Freeze, Jump, Poison, Haste, Healing, Skeleton).
- **Troops (`assets/troops/`)**: Super Troops and Regular Elixir troops.
- **TH17 Update (Nov 16)**: Squad Barracks (Barbarian/Archer Squads) and Heroic Spell placeholders are used until visual assets are exported.
