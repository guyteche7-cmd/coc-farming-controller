# ⚔️ Clash of Clans Autonomous Farming Controller — Complete Documentation

An advanced, computer-vision and AI-powered autonomous farming bot for **Clash of Clans** on Windows PC (Google Play Games PC, LDPlayer, BlueStacks, Nox).

---

## 📋 Table of Contents
1. [System Requirements](#-system-requirements)
2. [Quick Installation & Setup](#-quick-installation--setup)
3. [How to Run the Bot](#-how-to-run-the-bot)
4. [In-Game Setup & Army Configuration](#-in-game-setup--army-configuration)
5. [Target Loot Criteria Filtering](#-target-loot-criteria-filtering)
6. [Combat Strategy & Deployment Flow](#-combat-strategy--deployment-flow)
7. [Combat Exit Conditions](#-combat-exit-conditions)
8. [Global Keyboard Hotkeys](#-global-keyboard-hotkeys)
9. [GUI Overview & Features](#-gui-overview--features)
10. [Troubleshooting & FAQs](#-troubleshooting--faqs)

---

## 💻 System Requirements

- **Operating System**: Windows 10 or Windows 11 (64-bit).
- **Python**: Python 3.10, 3.11, 3.12, 3.13, or 3.14.
- **Game Client**: Clash of Clans running on:
  - **Google Play Games for PC** (Recommended)
  - **LDPlayer 9** (1920x1080 resolution recommended)
  - **BlueStacks 5** (1920x1080 resolution recommended)
- **Display**: Any 1080p, 1440p, or 4K monitor.

---

## 🚀 Quick Installation & Setup

### 1-Click Launch (Recommended)
1. Extract this zip / clone this repository to any folder on your PC.
2. Double-click **
un_bot.bat**.
3. It will automatically detect Python, install any missing dependencies on first launch, and open the dashboard!

### Manual Installation (Alternative)
If you prefer installing dependencies manually via terminal:
`powershell
pip install -r requirements.txt
python -m src.app.main
```

---

## 🎮 How to Run the Bot

1. Open Clash of Clans on your PC and stay in your Home Village.
2. Double-click **`run_coc_bot.bat`** (or run `python -m src.app.main`).
3. In the GUI:
   - Click **`🎯 Bind Game Window (F7)`** (or press **F7**). The bot will automatically lock onto your game client.
   - Adjust your desired **Target Loot Criteria**, **Combat Exit Timer**, and **Operation Mode**.
4. Press **`F8`** or click **`▶ START FARMING (F8)`**.

---

## 🪖 In-Game Setup & Army Configuration

The bot uses the following high-efficiency farming army composition:

| Slot # | Unit Type | Unit Name | Quantity | Keybinding | Deployment Role |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **0** | Troop | **Electro Dragon** | 16 | `1` | 50% deployed at start along chosen edge; remaining 50% deployed after heroes |
| **1** | Siege | **Battle Blimp / Log Launcher** | 1 | `Z` | Deployed at center of the chosen deployment edge |
| **2** | Hero | **Dragon Duke / Minion Prince** | Hero 1 | `Q` | Deployed grouped at center edge |
| **3** | Hero | **Archer Queen** | Hero 2 | `W` | Deployed grouped at center edge |
| **4** | Hero | **Grand Warden** | Hero 3 | `E` | Deployed grouped at center edge |
| **5** | Hero | **Barbarian King** | Hero 4 | `R` | Deployed grouped at center edge |
| **6** | Spell | **Earthquake Spell** | 11 | `A` | Cast across 11 randomized base target points with micro-jitter |

---

## 🎯 Target Loot Criteria Filtering

In the GUI sidebar **Target Loot Criteria** card:
1. Choose Match Logic:
   - **`ANY (OR)`**: Attacks if **ANY** selected checkbox meets the minimum threshold.
   - **`ALL (AND)`**: Attacks only if **ALL** selected checkboxes meet the minimum threshold.
2. Select parameters to watch:
   - ☑️ **Min Gold**: e.g. `1,000,000`
   - ☑️ **Min Elixir**: e.g. `1,000,000`
   - ☑️ **Min Dark Elixir**: e.g. `5,000`
   - ☑️ **Combined (G+E)**: e.g. `1,600,000` (Gold + Elixir combined total)
3. Bases not meeting your criteria will be automatically skipped (`Next` button).

---

## ⚔️ Combat Strategy & Deployment Flow

When an acceptable enemy base is found, the bot executes:
1. **Wave 1 (50% Electro Dragons)**: Deploys the first 8 Electro Dragons evenly along the configured edge.
2. **Wave 2 (Siege Machine)**: Deploys the Battle Blimp / Log Launcher at the center of the edge.
3. **Wave 3 (Heroes)**: Rapidly deploys all 4 Heroes at the center of the edge.
4. **Wave 4 (Remaining Dragons)**: Deploys the remaining 8 Electro Dragons.
5. **Wave 5 (Randomized Earthquake Spells)**: Casts 11 Earthquake Spells across 11 key base coordinates until the spell slot is completely greyed out.
6. **10-Second Combat Pause**: Waits exactly 10 seconds for units to advance into the base.
7. **Hero Ability Activation**: Triggers all 4 hero abilities in rapid succession.
8. **Internal Combat Clock Starts**: Begins live monitoring of damage, loot collected, and the custom timer.

---

## 🛑 Combat Exit Conditions

The bot monitors active combat in real-time and exits the battle immediately when **ANY** of the following 3 conditions is met:

1. **⏱️ Internal Post-Deployment Timer**:
   - Customizable in the GUI (e.g. `45s`, `60s`, `90s`, `1m 30s`).
   - Hard capped at **$2\text{m } 30\text{s}$ ($150\text{s}$)** maximum.
   - Counted strictly by the bot's internal timer after full deployment.
2. **💥 Overall Damage $\ge 60\%$**:
   - OCR reads destruction percentage every second and exits immediately upon reaching $\ge 60\%$.
3. **💰 Loot Collected $\ge 65\%$**:
   - Exits once $65\%$ of initial Gold + Elixir is looted (remaining loot $\le 35\%$).

**Confirmation Dialog**: When an exit condition is met, the bot automatically clicks `End Battle` (or `Surrender`) and instantly confirms the `Okay` modal dialog to collect your loot.

---

## ⌨️ Global Keyboard Hotkeys

The controller registers hardware-level global hotkeys that work even when Clash of Clans is in the background:

| Hotkey | Action | Function |
| :---: | :---: | :--- |
| **`F7`** | **Bind Window** | Auto-detects and locks coordinates to Google Play Games / Emulator client area. |
| **`F8`** | **Start / Stop** | Toggles the autonomous farming loop on and off. |
| **`F9`** | **Pause / Resume** | Freezes the state machine temporarily (e.g. if you need to take over). |
| **`F10`** | **Emergency Stop** | Instantly halts all mouse clicks and background threads safely. |

---

## 🛡️ Safety & Focus Guard

- **Focus Guard**: The bot checks window foreground state before every mouse click. If you Alt-Tab away from Clash of Clans, mouse clicks are immediately halted until the game is focused again.
- **Humanized Jitter**: Action coordinates include organic human-like micro-delays and pixel jitter.

---

## 🔧 Troubleshooting & FAQs

### Q: The bot says "Window: Not Found" or clicks off-screen.
- **Fix**: Open Clash of Clans on your screen and press **`F7`**. Verify that the green badge in the GUI updates to `Window: Found (1920x1080)`.

### Q: EasyOCR is downloading models on first launch.
- **Fix**: EasyOCR downloads small recognition models (~80MB) on first start into `~/.EasyOCR`. This only happens once.

### Q: How do I run on GPU / CUDA?
- If you have an NVIDIA GPU, PyTorch will automatically use CUDA acceleration. If not, it runs smoothly on standard CPU.

---
*Created by CoC Automation Suite. Happy Farming!*
