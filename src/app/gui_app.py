"""
Desktop Control Dashboard (CustomTkinter GUI).
Provides real-time state visualization, foreground window binding & protection,
voice & audio alerts, target rule editing, and live session telemetry.
"""

from __future__ import annotations
import os
import sys

# Silence macOS legacy Tk deprecation notice that can freeze/delay window painting
os.environ["TK_SILENCE_DEPRECATION"] = "1"

import time
import threading
import logging
import re
from datetime import datetime
import customtkinter as ctk

from src.persistence.config_manager import ConfigManager
from src.persistence.database import DatabaseManager
from src.control.session_controller import SessionController
from src.control.notifier import Notifier
from src.state.game_state import UIState, GameState
from src.rules.expression_parser import ExpressionEvaluator
from src.planning.troop_housing import (
    get_troop_space,
    get_spell_space,
    calculate_army_housing_space,
    calculate_spell_housing_space,
    TROOP_HOUSING_SPACE,
    SPELL_HOUSING_SPACE,
)

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def safe_text(text: str) -> str:
    """
    Sanitizes strings for macOS Tkinter.
    macOS Tcl/Tk (compiled with TCL_UTF_MAX=3) fails on non-BMP Unicode characters (>0xFFFF).
    Replaces 4-byte emojis with clean standard symbols on macOS while preserving rich styling on Windows.
    """
    if sys.platform != "darwin":
        return text
    replacements = {
        "⚔️": "[⚔]", "⚔": "[⚔]",
        "🏰": "[Home]", "🔨": "[Builder]",
        "🎯": "◎",
        "🛑": "[STOP]",
        "💰": "[$]",
        "📜": "[Logs]",
        "📋": "[Audit]",
        "🟡": "●",
        "🟣": "●",
        "⚫": "●",
        "⏱️": "⏱", "⏱": "⏱",
        "⚡": "⚡",
        "▶": "▶",
        "⏸": "⏸",
        "⏹": "⏹",
        "📍": "•",
        "⌨": "⌨",
        "⚠️": "[!]",
        "📊": "[Live]",
        "💾": "[Save]",
        "🛡️": "[Siege]", "🛡": "[Siege]",
        "👑": "[Hero]",
    }
    cleaned = text
    for emoji, repl in replacements.items():
        cleaned = cleaned.replace(emoji, repl)
    # Strip any remaining characters outside the Basic Multilingual Plane (U+0000 to U+FFFF)
    return "".join(c for c in cleaned if ord(c) <= 0xFFFF).strip()


UNIT_ASSET_MAP = {
    # 1. Regular Elixir Troops
    "Barbarian": "assets/army/cards/troops/barbarian_card.png",
    "Archer": "assets/army/cards/troops/archer_card.png",
    "Giant": "assets/army/cards/troops/giant_card.png",
    "Goblin": "assets/army/cards/troops/goblin_card.png",
    "Wall Breaker": "assets/army/cards/troops/wall_breaker_card.png",
    "Balloon": "assets/army/cards/troops/balloon_card.png",
    "Wizard": "assets/army/cards/troops/wizard_card.png",
    "Healer": "assets/army/cards/troops/healer_card.png",
    "Dragon": "assets/army/cards/troops/dragon_card.png",
    "P.E.K.K.A": "assets/army/cards/troops/pekka_card.png",
    "Baby Dragon": "assets/army/cards/troops/baby_dragon_card.png",
    "Miner": "assets/army/cards/troops/miner_card.png",
    "Electro Dragon": "assets/army/cards/troops/electro_dragon_card.png",
    "Yeti": "assets/army/cards/troops/yeti_card.png",
    "Dragon Rider": "assets/army/cards/troops/dragon_rider_card.png",
    "Electro Titan": "assets/army/cards/troops/electro_titan_card.png",
    "Root Rider": "assets/army/cards/troops/root_rider_card.png",
    "Thrower": "assets/army/cards/troops/thrower_card.png",

    # 2. Dark Elixir Troops
    "Minion": "assets/army/cards/troops/minion_card.png",
    "Hog Rider": "assets/army/cards/troops/hog_rider_card.png",
    "Valkyrie": "assets/army/cards/troops/valkyrie_card.png",
    "Golem": "assets/army/cards/troops/golem_card.png",
    "Witch": "assets/army/cards/troops/witch_card.png",
    "Lava Hound": "assets/army/cards/troops/lava_hound_card.png",
    "Bowler": "assets/army/cards/troops/bowler_card.png",
    "Ice Golem": "assets/army/cards/troops/ice_golem_card.png",
    "Headhunter": "assets/army/cards/troops/headhunter_card.png",
    "Apprentice Warden": "assets/army/cards/troops/apprentice_warden_card.png",
    "Druid": "assets/army/cards/troops/druid_card.png",
    "Furnace": "assets/army/cards/troops/furnace_card.png",
    "Momma": "assets/army/cards/troops/momma_card.png",
    "Ruin Witch": "assets/army/cards/troops/ruin_witch_card.png",
    "Meteor Golem": "assets/army/cards/troops/meteor_golem_card.png",

    # 3. Super Troops
    "Super Barbarian": "assets/army/cards/troops/super_barbarian_card.png",
    "Super Archer": "assets/army/cards/troops/super_archer_card.png",
    "Super Giant": "assets/army/cards/troops/super_giant_card.png",
    "Sneaky Goblin": "assets/army/cards/troops/sneaky_goblin_card.png",
    "Super Wall Breaker": "assets/army/cards/troops/super_wall_breaker_card.png",
    "Rocket Balloon": "assets/army/cards/troops/rocket_balloon_card.png",
    "Super Wizard": "assets/army/cards/troops/super_wizard_card.png",
    "Super Dragon": "assets/army/cards/troops/super_dragon_card.png",
    "Inferno Dragon": "assets/army/cards/troops/inferno_dragon_card.png",
    "Super Minion": "assets/army/cards/troops/super_minion_card.png",
    "Super Valkyrie": "assets/army/cards/troops/super_valkyrie_card.png",
    "Super Witch": "assets/army/cards/troops/super_witch_card.png",
    "Ice Hound": "assets/army/cards/troops/ice_hound_card.png",
    "Super Bowler": "assets/army/cards/troops/bowler_card.png",
    "Super Miner": "assets/army/cards/troops/super_miner_card.png",
    "Super Hog Rider": "assets/army/cards/troops/super_hog_rider_card.png",
    "Super Yeti": "assets/army/cards/troops/super_yeti_card.png",

    # 4. Siege Machines (Crisp, clean, verified)
    "Siege Barracks": "assets/siege/siege_barracks.png",
    "Battle Blimp": "assets/siege/battle_blimp.png",
    "Log Launcher": "assets/siege/log_launcher.png",
    "Flame Flinger": "assets/siege/flame_flinger.png",
    "Wall Wrecker": "assets/siege/wall_wrecker.png",
    "Stone Slammer": "assets/siege/stone_slammer.png",
    "Battle Drill": "assets/siege/battle_drill.png",
    "Troop Launcher": "assets/siege/troop_launcher.png",
    "Sky Wagon": "assets/siege/sky_wagon.png",

    # 5. Heroes (TH17 Complete 6 Hero Roster)
    "Barbarian King": "assets/heroes/barbarian_king.png",
    "Archer Queen": "assets/heroes/archer_queen.png",
    "Grand Warden": "assets/heroes/grand_warden.png",
    "Royal Champion": "assets/heroes/royal_champion.png",
    "Minion Prince": "assets/heroes/minion_prince.png",
    "Dragon Duke": "assets/heroes/dragon_duke.png",

    # 6. Spells (Crisp, clean, verified)
    "Totem Spell": "assets/spells/totem.png",
    "Totem": "assets/spells/totem.png",
    "Lightning": "assets/spells/lightning.png",
    "Rage": "assets/spells/rage.png",
    "Freeze": "assets/spells/freeze.png",
    "Jump": "assets/spells/jump.png",
    "Healing": "assets/spells/healing.png",
    "Heal Spell": "assets/spells/healing.png",
    "Invisibility": "assets/spells/invisibility.png",
    "Invisibility Spell": "assets/spells/invisibility.png",
    "Revive Spell": "assets/spells/revive.png",
    "Revive": "assets/spells/revive.png",
    "Clone": "assets/spells/clone.png",
    "Clone Spell": "assets/spells/clone.png",
    "Recall": "assets/spells/recall.png",
    "Recall Spell": "assets/spells/recall.png",
    "Poison": "assets/spells/poison.png",
    "Haste": "assets/spells/haste.png",
    "Bat": "assets/spells/bat.png",
    "Bat Spell": "assets/spells/bat.png",
    "Ice Block": "assets/spells/ice_block.png",
    "Ice Block Spell": "assets/spells/ice_block.png",
    "Earthquake": "assets/spells/earthquake.png",
    "Earthquake Spell": "assets/spells/earthquake.png",
    "Skeleton": "assets/spells/skeleton.png",
    "Overgrowth": "assets/spells/overgrowth.png",
}

TROOP_OPTIONS = [
    # Regular Elixir Troops
    "Barbarian", "Archer", "Giant", "Goblin", "Wall Breaker",
    "Balloon", "Wizard", "Healer", "Dragon", "P.E.K.K.A",
    "Baby Dragon", "Miner", "Electro Dragon", "Yeti", "Dragon Rider",
    "Electro Titan", "Root Rider", "Thrower",

    # Dark Elixir Troops
    "Minion", "Hog Rider", "Valkyrie", "Golem", "Witch",
    "Lava Hound", "Bowler", "Ice Golem", "Headhunter", "Apprentice Warden",
    "Druid", "Furnace", "Momma", "Ruin Witch", "Meteor Golem",

    # Super Troops
    "Super Barbarian", "Super Archer", "Super Giant", "Sneaky Goblin", "Super Wall Breaker",
    "Rocket Balloon", "Super Wizard", "Super Dragon", "Inferno Dragon", "Super Minion",
    "Super Valkyrie", "Super Witch", "Ice Hound", "Super Bowler", "Super Miner",
    "Super Hog Rider", "Super Yeti"
]

SIEGE_OPTIONS = [
    "Siege Barracks", "Battle Blimp", "Log Launcher", "Flame Flinger",
    "Wall Wrecker", "Stone Slammer", "Battle Drill", "Troop Launcher", "Sky Wagon"
]

SPELL_OPTIONS = [
    "Totem Spell", "Lightning", "Healing", "Rage", "Freeze", "Jump",
    "Invisibility", "Revive Spell", "Clone", "Recall", "Poison", "Haste",
    "Bat", "Ice Block", "Earthquake", "Skeleton", "Overgrowth"
]

PRIORITY_OPTIONS = [
    f"{i}{'st' if i==1 else 'nd' if i==2 else 'rd' if i==3 else 'th'} (Drop {'First' if i==1 else 'Second' if i==2 else 'Third' if i==3 else 'Fourth' if i==4 else f'#{i}'})"
    for i in range(1, 16)
]


class DashboardApp(ctk.CTk):
    """Main CustomTkinter application window."""

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.config = config_manager.config
        self.db = DatabaseManager(self.config.logging.database_file)
        self.notifier = Notifier(voice_enabled=True, sounds_enabled=True)

        self.title("CoC Auto Farm Dashboard — Version 1 (AI Hybrid Edition)")
        win_w = 1140 if sys.platform == "darwin" else 1080
        win_h = 760 if sys.platform == "darwin" else 720
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(1000, 660)

        self.controller = SessionController(
            config_manager=self.config_manager,
            db_manager=self.db,
            state_callback=self._on_state_update,
            notifier=self.notifier,
            window_bind_callback=lambda: self.after(0, self._bind_game_window_interactive),
            hotkey_start_callback=lambda: self.after(0, self._toggle_farming_session),
            hotkey_pause_callback=lambda: self.after(0, self._handle_pause_action),
            hotkey_stop_callback=lambda: self.after(0, self._handle_stop_action),
            verification_callback=lambda payload: self.after(0, lambda: self._show_deployment_verification_prompt(payload))
        )

        self._build_ui()
        self._bind_keyboard_shortcuts()
        self._poll_ui_telemetry()

        # macOS Tkinter initial render workaround (forces Cocoa window server to paint canvas & calculate layouts)
        if sys.platform == "darwin":
            self.after(100, self._macos_force_paint)
            self.after(300, self._macos_force_paint)

        # Pre-warm vision models (EasyOCR, YOLOv8) in background so session start is instant
        threading.Thread(target=self._prewarm_vision_models, daemon=True).start()

    def _macos_force_paint(self) -> None:
        """Forces macOS Cocoa window server to redraw widgets and recalculate scrollable canvas frames."""
        try:
            self.update_idletasks()
            self.deiconify()
            self.lift()
            if hasattr(self, "sidebar") and hasattr(self.sidebar, "_parent_canvas"):
                self.sidebar._parent_canvas.event_generate("<Configure>")
                self.sidebar._parent_canvas.yview_moveto(0)
            self.update()
        except Exception as e:
            logger.debug(f"macOS paint trigger: {e}")

    def _load_ctk_image(self, rel_path: str, size: Tuple[int, int] = (36, 48)) -> Optional[ctk.CTkImage]:
        """Loads and caches a CTkImage from a relative project asset path safely."""
        try:
            from PIL import Image
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            full_path = os.path.join(base_dir, rel_path.replace("/", os.sep))
            if os.path.exists(full_path):
                img = Image.open(full_path).convert("RGBA")
                return ctk.CTkImage(light_image=img, dark_image=img, size=size)
        except Exception as e:
            logger.debug(f"Image load notice for '{rel_path}': {e}")
        return None

    def _bind_keyboard_shortcuts(self) -> None:
        """Binds native macOS Command shortcuts and universal F-keys to dashboard actions."""
        # 1. Mac Command shortcuts (⌘R Start/Stop, ⌘P Pause, ⌘B Bind, Esc Safe Stop)
        self.bind_all("<Command-r>", lambda e: self._toggle_farming_session())
        self.bind_all("<Command-R>", lambda e: self._toggle_farming_session())
        self.bind_all("<Command-p>", lambda e: self._handle_pause_action())
        self.bind_all("<Command-P>", lambda e: self._handle_pause_action())
        self.bind_all("<Command-b>", lambda e: self._bind_game_window_interactive())
        self.bind_all("<Command-B>", lambda e: self._bind_game_window_interactive())
        self.bind_all("<Command-period>", lambda e: self._handle_stop_action())

        # 2. Universal Escape key (Immediate Emergency Safe Stop)
        self.bind_all("<Escape>", lambda e: self._handle_stop_action())

        # 3. Windows / PC Control shortcuts (Ctrl+R, Ctrl+P, Ctrl+B)
        self.bind_all("<Control-r>", lambda e: self._toggle_farming_session())
        self.bind_all("<Control-R>", lambda e: self._toggle_farming_session())
        self.bind_all("<Control-p>", lambda e: self._handle_pause_action())
        self.bind_all("<Control-P>", lambda e: self._handle_pause_action())
        self.bind_all("<Control-b>", lambda e: self._bind_game_window_interactive())
        self.bind_all("<Control-B>", lambda e: self._bind_game_window_interactive())

        # 4. Standard Function Keys (F7 Bind, F8 Start/Stop, F9 Pause, F10 Stop)
        self.bind_all("<F7>", lambda e: self._bind_game_window_interactive())
        self.bind_all("<F8>", lambda e: self._toggle_farming_session())
        self.bind_all("<F9>", lambda e: self._handle_pause_action())
        self.bind_all("<F10>", lambda e: self._handle_stop_action())

    def _prewarm_vision_models(self) -> None:
        try:
            logger.info("Pre-warming fast glyph and template perception models in background...")
            from src.vision.glyph_reader import SupercellGlyphReader
            reader = SupercellGlyphReader()
            logger.info(f"Deterministic Glyph perception engine pre-warmed successfully ({len(reader.templates)} digit templates loaded).")
        except Exception as e:
            logger.warning(f"Vision pre-warm notice: {e}")

    def _build_ui(self) -> None:
        sidebar_min_w = 340 if sys.platform == "darwin" else 320
        sidebar_w = 330 if sys.platform == "darwin" else 300
        self.grid_columnconfigure(0, weight=0, minsize=sidebar_min_w)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ----------------- SIDEBAR (Controls & Config - Scrollable) -----------------
        self.sidebar = ctk.CTkScrollableFrame(
            self,
            width=sidebar_w,
            corner_radius=10,
            fg_color="#1e1e24",
            scrollbar_button_color="#3f3f46",
            scrollbar_button_hover_color="#52525b"
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.sidebar.grid_columnconfigure(0, weight=1)
        sidebar = self.sidebar

        # App Title
        lbl_title = ctk.CTkLabel(sidebar, text=safe_text("⚔️ CoC Farm Controller"), font=ctk.CTkFont(size=20, weight="bold"))
        lbl_title.grid(row=0, column=0, pady=(16, 2), padx=16, sticky="w")
        lbl_sub = ctk.CTkLabel(sidebar, text="Google Play Games / BlueStacks / LDPlayer", font=ctk.CTkFont(size=12), text_color="#9ca3af")
        lbl_sub.grid(row=1, column=0, pady=(0, 10), padx=16, sticky="w")

        # Village Switcher: [ 🏰 Home Village ]  [ 🔨 Builder Base ]
        self.current_village = "home_village"
        self.bb_config_manager = None
        self.bb_controller = None

        home_opt = "Home Village" if sys.platform == "darwin" else "🏰 Home Village"
        bb_opt = "Builder Base" if sys.platform == "darwin" else "🔨 Builder Base"
        self.village_options = [home_opt, bb_opt]

        self.village_mode_var = ctk.StringVar(value=home_opt)
        self.village_switcher = ctk.CTkSegmentedButton(
            sidebar,
            values=self.village_options,
            variable=self.village_mode_var,
            command=self._on_village_mode_change,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.village_switcher.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="ew")

        # Window Binding Status Card
        win_card = ctk.CTkFrame(sidebar, fg_color="#27272a", corner_radius=8)
        win_card.grid(row=3, column=0, padx=16, pady=(0, 10), sticky="ew")
        win_card.grid_columnconfigure(0, weight=1)

        self.lbl_win_status = ctk.CTkLabel(
            win_card,
            text="Window: Auto-Detecting...",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_win_status.grid(row=0, column=0, padx=10, pady=(6, 2), sticky="w")

        bind_btn_txt = "◎ Bind Game Window (⌘B)" if sys.platform == "darwin" else "🎯 Bind Game Window (F7)"
        btn_bind_win = ctk.CTkButton(
            win_card,
            text=bind_btn_txt,
            height=28,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._bind_game_window_interactive
        )
        btn_bind_win.grid(row=1, column=0, padx=10, pady=(2, 6), sticky="ew")

        # =============================================================
        # 1. HOME VILLAGE CONTROLS CONTAINER
        # =============================================================
        self.home_controls_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        self.home_controls_frame.grid(row=4, column=0, sticky="ew")
        self.home_controls_frame.grid_columnconfigure(0, weight=1)

        # Mode Selection
        lbl_mode = ctk.CTkLabel(self.home_controls_frame, text="Operation Mode:", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_mode.grid(row=0, column=0, padx=16, pady=(2, 2), sticky="w")

        mode_val = self.config.mode if self.config.mode != "wall_plus_attack" else "fixed_attacks"
        self.mode_var = ctk.StringVar(value=mode_val)
        mode_opt = ctk.CTkOptionMenu(
            self.home_controls_frame,
            variable=self.mode_var,
            values=["fixed_attacks", "infinite"],
            command=self._on_mode_change
        )
        mode_opt.grid(row=1, column=0, padx=16, pady=(0, 6), sticky="ew")

        # Fixed Attack Count Container
        self.fixed_count_frame = ctk.CTkFrame(self.home_controls_frame, fg_color="#27272a", corner_radius=8)
        self.fixed_count_frame.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="ew")
        self.fixed_count_frame.grid_columnconfigure(1, weight=1)

        lbl_fc = ctk.CTkLabel(self.fixed_count_frame, text="Target Attacks:", font=ctk.CTkFont(size=12))
        lbl_fc.grid(row=0, column=0, padx=(10, 6), pady=6)

        btn_minus = ctk.CTkButton(self.fixed_count_frame, text="-", width=28, height=26, fg_color="#3f3f46", command=self._decrement_attack_count)
        btn_minus.grid(row=0, column=1, padx=2, pady=6, sticky="e")

        self.attack_count_var = ctk.StringVar(value=str(self.config.fixed_attack_count))
        self.entry_attack_count = ctk.CTkEntry(self.fixed_count_frame, textvariable=self.attack_count_var, width=44, height=26, justify="center")
        self.entry_attack_count.grid(row=0, column=2, padx=4, pady=6)
        self.entry_attack_count.bind("<FocusOut>", lambda e: self._save_attack_count())

        btn_plus = ctk.CTkButton(self.fixed_count_frame, text="+", width=28, height=26, fg_color="#3f3f46", command=self._increment_attack_count)
        btn_plus.grid(row=0, column=3, padx=(2, 10), pady=6, sticky="w")

        self._update_fixed_count_visibility()

        # Target Loot Criteria Card
        loot_card = ctk.CTkFrame(self.home_controls_frame, fg_color="#27272a", corner_radius=8)
        loot_card.grid(row=3, column=0, padx=16, pady=(2, 8), sticky="ew")
        loot_card.grid_columnconfigure(1, weight=1)

        lbl_loot_hdr = ctk.CTkLabel(loot_card, text=safe_text("🎯 Target Loot Criteria:"), font=ctk.CTkFont(size=13, weight="bold"))
        lbl_loot_hdr.grid(row=0, column=0, columnspan=2, padx=10, pady=(6, 2), sticky="w")

        curr_mode = getattr(self.config.target, "match_mode", "OR").upper()
        mode_val = "ALL (AND)" if curr_mode == "AND" else "ANY (OR)"
        self.match_mode_var = ctk.StringVar(value=mode_val)
        mode_seg = ctk.CTkSegmentedButton(
            loot_card,
            values=["ANY (OR)", "ALL (AND)"],
            variable=self.match_mode_var,
            command=self._on_loot_criteria_change,
            height=24
        )
        mode_seg.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 6), sticky="ew")

        # 1. Gold Checkbox & Entry
        self.chk_gold_var = ctk.BooleanVar(value=getattr(self.config.target, "watch_gold", True))
        self.chk_gold = ctk.CTkCheckBox(loot_card, text="Min Gold:", variable=self.chk_gold_var, command=self._on_loot_criteria_change, font=ctk.CTkFont(size=12))
        self.chk_gold.grid(row=2, column=0, padx=(10, 4), pady=2, sticky="w")
        self.ent_gold_var = ctk.StringVar(value=str(getattr(self.config.target, "min_gold", 500000)))
        self.ent_gold = ctk.CTkEntry(loot_card, textvariable=self.ent_gold_var, width=95, height=24, justify="right")
        self.ent_gold.grid(row=2, column=1, padx=(4, 10), pady=2, sticky="e")
        self.ent_gold.bind("<FocusOut>", lambda e: self._on_loot_criteria_change())

        # 2. Elixir Checkbox & Entry
        self.chk_elixir_var = ctk.BooleanVar(value=getattr(self.config.target, "watch_elixir", False))
        self.chk_elixir = ctk.CTkCheckBox(loot_card, text="Min Elixir:", variable=self.chk_elixir_var, command=self._on_loot_criteria_change, font=ctk.CTkFont(size=12))
        self.chk_elixir.grid(row=3, column=0, padx=(10, 4), pady=2, sticky="w")
        self.ent_elixir_var = ctk.StringVar(value=str(getattr(self.config.target, "min_elixir", 500000)))
        self.ent_elixir = ctk.CTkEntry(loot_card, textvariable=self.ent_elixir_var, width=95, height=24, justify="right")
        self.ent_elixir.grid(row=3, column=1, padx=(4, 10), pady=2, sticky="e")
        self.ent_elixir.bind("<FocusOut>", lambda e: self._on_loot_criteria_change())

        # 3. Dark Elixir Checkbox & Entry
        self.chk_de_var = ctk.BooleanVar(value=getattr(self.config.target, "watch_dark_elixir", False))
        self.chk_de = ctk.CTkCheckBox(loot_card, text="Min Dark Elixir:", variable=self.chk_de_var, command=self._on_loot_criteria_change, font=ctk.CTkFont(size=12))
        self.chk_de.grid(row=4, column=0, padx=(10, 4), pady=2, sticky="w")
        self.ent_de_var = ctk.StringVar(value=str(getattr(self.config.target, "min_dark_elixir", 5000)))
        self.ent_de = ctk.CTkEntry(loot_card, textvariable=self.ent_de_var, width=95, height=24, justify="right")
        self.ent_de.grid(row=4, column=1, padx=(4, 10), pady=2, sticky="e")
        self.ent_de.bind("<FocusOut>", lambda e: self._on_loot_criteria_change())

        # DE Prerequisite Gate (Prevents 10k DE from accepting low gold/elixir bases in OR mode)
        self.chk_de_gate_var = ctk.BooleanVar(value=getattr(self.config.target, "dark_elixir_as_gate", True))
        self.chk_de_gate = ctk.CTkCheckBox(
            loot_card,
            text="Gate: Require DE as (AND)",
            variable=self.chk_de_gate_var,
            command=self._on_loot_criteria_change,
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.chk_de_gate.grid(row=5, column=0, columnspan=2, padx=(24, 10), pady=(0, 2), sticky="w")

        # 4. Combined (Gold + Elixir) Checkbox & Entry
        self.chk_comb_var = ctk.BooleanVar(value=getattr(self.config.target, "watch_combined", True))
        self.chk_comb = ctk.CTkCheckBox(loot_card, text="Combined (G+E):", variable=self.chk_comb_var, command=self._on_loot_criteria_change, font=ctk.CTkFont(size=12))
        self.chk_comb.grid(row=6, column=0, padx=(10, 4), pady=2, sticky="w")
        self.ent_comb_var = ctk.StringVar(value=str(getattr(self.config.target, "min_combined", 1000000)))
        self.ent_comb = ctk.CTkEntry(loot_card, textvariable=self.ent_comb_var, width=95, height=24, justify="right")
        self.ent_comb.grid(row=6, column=1, padx=(4, 10), pady=2, sticky="e")
        self.ent_comb.bind("<FocusOut>", lambda e: self._on_loot_criteria_change())

        # Active Summary Label
        self.lbl_active_criteria = ctk.CTkLabel(
            loot_card,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38bdf8",
            wraplength=310,
            justify="left"
        )
        self.lbl_active_criteria.grid(row=7, column=0, columnspan=2, padx=10, pady=(2, 6), sticky="w")
        self._on_loot_criteria_change()

        # Combat Exit Criteria Card (Home)
        exit_card = ctk.CTkFrame(self.home_controls_frame, fg_color="#18181b", corner_radius=8)
        exit_card.grid(row=4, column=0, padx=16, pady=(4, 6), sticky="ew")
        exit_card.grid_columnconfigure(0, weight=1)
        exit_card.grid_columnconfigure(1, weight=0)

        lbl_exit_title = ctk.CTkLabel(exit_card, text=safe_text("⏱ Combat Exit Criteria:"), font=ctk.CTkFont(size=12, weight="bold"))
        lbl_exit_title.grid(row=0, column=0, columnspan=2, padx=(10, 4), pady=(6, 4), sticky="w")

        # 1. Timer
        lbl_timer = ctk.CTkLabel(exit_card, text="Max Time (s):", font=ctk.CTkFont(size=12))
        lbl_timer.grid(row=1, column=0, padx=(16, 4), pady=(2, 2), sticky="w")
        init_timer_val = getattr(self.config.exit, "combat_timer_seconds", 60)
        self.ent_timer_var = ctk.StringVar(value=f"{init_timer_val}")
        self.ent_timer = ctk.CTkEntry(exit_card, textvariable=self.ent_timer_var, width=60, height=24, justify="center")
        self.ent_timer.grid(row=1, column=1, padx=(4, 10), pady=(2, 2), sticky="e")
        self.ent_timer.bind("<FocusOut>", lambda e: self._on_exit_criteria_change())
        self.ent_timer.bind("<Return>", lambda e: self._on_exit_criteria_change())

        # 2. Damage %
        lbl_damage = ctk.CTkLabel(exit_card, text="Damage (%):", font=ctk.CTkFont(size=12))
        lbl_damage.grid(row=2, column=0, padx=(16, 4), pady=(2, 2), sticky="w")
        init_damage_val = getattr(self.config.exit, "damage_threshold_percent", 60.0)
        self.ent_damage_var = ctk.StringVar(value=f"{int(init_damage_val)}")
        self.ent_damage = ctk.CTkEntry(exit_card, textvariable=self.ent_damage_var, width=60, height=24, justify="center")
        self.ent_damage.grid(row=2, column=1, padx=(4, 10), pady=(2, 2), sticky="e")
        self.ent_damage.bind("<FocusOut>", lambda e: self._on_exit_criteria_change())
        self.ent_damage.bind("<Return>", lambda e: self._on_exit_criteria_change())

        # 3. Loot Collected %
        lbl_loot_pct = ctk.CTkLabel(exit_card, text="Loot Col. (%):", font=ctk.CTkFont(size=12))
        lbl_loot_pct.grid(row=3, column=0, padx=(16, 4), pady=(2, 2), sticky="w")
        init_loot_val = getattr(self.config.exit, "loot_collected_percent", 65.0)
        self.ent_loot_var = ctk.StringVar(value=f"{int(init_loot_val)}")
        self.ent_loot = ctk.CTkEntry(exit_card, textvariable=self.ent_loot_var, width=60, height=24, justify="center")
        self.ent_loot.grid(row=3, column=1, padx=(4, 10), pady=(2, 6), sticky="e")
        self.ent_loot.bind("<FocusOut>", lambda e: self._on_exit_criteria_change())
        self.ent_loot.bind("<Return>", lambda e: self._on_exit_criteria_change())

        self.lbl_exit_summary = ctk.CTkLabel(
            exit_card,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#a1a1aa"
        )
        self.lbl_exit_summary.grid(row=4, column=0, columnspan=2, padx=10, pady=(0, 6), sticky="w")
        self._update_exit_summary_text(init_timer_val, init_damage_val, init_loot_val)

        # Storage Capacity Limits Card (Auto-Stop on Full Storage)
        storage_card = ctk.CTkFrame(self.home_controls_frame, fg_color="#18181b", corner_radius=8)
        storage_card.grid(row=5, column=0, padx=16, pady=(4, 6), sticky="ew")
        storage_card.grid_columnconfigure(0, weight=1)
        storage_card.grid_columnconfigure(1, weight=0)

        lbl_storage_title = ctk.CTkLabel(storage_card, text=safe_text("🛑 Storage Limit (Auto-Stop):"), font=ctk.CTkFont(size=12, weight="bold"))
        lbl_storage_title.grid(row=0, column=0, columnspan=2, padx=(10, 4), pady=(6, 2), sticky="w")

        self.chk_storage_limit_var = ctk.BooleanVar(value=getattr(self.config.storage_limit, "enabled", True))
        chk_storage_limit = ctk.CTkCheckBox(
            storage_card,
            text="Stop attacks when storage full",
            variable=self.chk_storage_limit_var,
            command=self._on_storage_limit_change,
            font=ctk.CTkFont(size=11)
        )
        chk_storage_limit.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 4), sticky="w")

        # Stop Match Mode (ANY vs ALL)
        curr_smode = "ALL (AND)" if getattr(self.config.storage_limit, "match_mode", "OR").upper() == "AND" else "ANY (OR)"
        self.storage_match_mode_var = ctk.StringVar(value=curr_smode)
        storage_mode_seg = ctk.CTkSegmentedButton(
            storage_card,
            values=["ANY (OR)", "ALL (AND)"],
            variable=self.storage_match_mode_var,
            command=self._on_storage_limit_change,
            height=22
        )
        storage_mode_seg.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 4), sticky="ew")

        # 1. Max Gold Checkbox & Entry
        self.chk_storage_gold_var = ctk.BooleanVar(value=getattr(self.config.storage_limit, "check_gold", True))
        self.chk_storage_gold = ctk.CTkCheckBox(
            storage_card, text="Max Gold:", variable=self.chk_storage_gold_var,
            command=self._on_storage_limit_change, font=ctk.CTkFont(size=11)
        )
        self.chk_storage_gold.grid(row=3, column=0, padx=(10, 4), pady=2, sticky="w")
        init_max_gold = getattr(self.config.storage_limit, "max_gold", 31000000) or 31000000
        self.ent_max_gold_var = ctk.StringVar(value=f"{init_max_gold:,}")
        self.ent_max_gold = ctk.CTkEntry(storage_card, textvariable=self.ent_max_gold_var, width=95, height=24, justify="right")
        self.ent_max_gold.grid(row=3, column=1, padx=(4, 10), pady=2, sticky="e")
        self.ent_max_gold.bind("<FocusOut>", lambda e: self._commit_storage_entry("gold"))
        self.ent_max_gold.bind("<Return>", lambda e: self._commit_storage_entry("gold"))

        # 2. Max Elixir Checkbox & Entry
        self.chk_storage_elixir_var = ctk.BooleanVar(value=getattr(self.config.storage_limit, "check_elixir", True))
        self.chk_storage_elixir = ctk.CTkCheckBox(
            storage_card, text="Max Elixir:", variable=self.chk_storage_elixir_var,
            command=self._on_storage_limit_change, font=ctk.CTkFont(size=11)
        )
        self.chk_storage_elixir.grid(row=4, column=0, padx=(10, 4), pady=2, sticky="w")
        init_max_elixir = getattr(self.config.storage_limit, "max_elixir", 31000000) or 31000000
        self.ent_max_elixir_var = ctk.StringVar(value=f"{init_max_elixir:,}")
        self.ent_max_elixir = ctk.CTkEntry(storage_card, textvariable=self.ent_max_elixir_var, width=95, height=24, justify="right")
        self.ent_max_elixir.grid(row=4, column=1, padx=(4, 10), pady=2, sticky="e")
        self.ent_max_elixir.bind("<FocusOut>", lambda e: self._commit_storage_entry("elixir"))
        self.ent_max_elixir.bind("<Return>", lambda e: self._commit_storage_entry("elixir"))

        # 3. Max Dark Elixir Checkbox & Entry
        self.chk_storage_de_var = ctk.BooleanVar(value=getattr(self.config.storage_limit, "check_dark_elixir", False))
        self.chk_storage_de = ctk.CTkCheckBox(
            storage_card, text="Max DE:", variable=self.chk_storage_de_var,
            command=self._on_storage_limit_change, font=ctk.CTkFont(size=11)
        )
        self.chk_storage_de.grid(row=5, column=0, padx=(10, 4), pady=2, sticky="w")
        init_max_de = getattr(self.config.storage_limit, "max_dark_elixir", 350000) or 350000
        self.ent_max_de_var = ctk.StringVar(value=f"{init_max_de:,}")
        self.ent_max_de = ctk.CTkEntry(storage_card, textvariable=self.ent_max_de_var, width=95, height=24, justify="right")
        self.ent_max_de.grid(row=5, column=1, padx=(4, 10), pady=2, sticky="e")
        self.ent_max_de.bind("<FocusOut>", lambda e: self._commit_storage_entry("de"))
        self.ent_max_de.bind("<Return>", lambda e: self._commit_storage_entry("de"))

        # Summary / Status
        self.lbl_storage_summary = ctk.CTkLabel(
            storage_card,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="#38bdf8"
        )
        self.lbl_storage_summary.grid(row=6, column=0, columnspan=2, padx=10, pady=(2, 6), sticky="w")
        self._on_storage_limit_change()

        # Army & hero deployment settings are configured in the dedicated "Army Setup & Sequencer" tab
        curr_hero_count = getattr(self.config.deployment, "hero_count", 4)
        init_hero_str = f"{curr_hero_count} Heroes" if curr_hero_count != 1 else "1 Hero"
        self.hero_count_var = ctk.StringVar(value=init_hero_str)
        init_ability_delay = getattr(self.config.deployment, "hero_ability_delay_seconds", 6.0)
        self.ent_ability_delay_var = ctk.StringVar(value=f"{init_ability_delay:.1f}".rstrip('0').rstrip('.'))

        # =============================================================
        # 2. BUILDER BASE CONTROLS CONTAINER
        # =============================================================
        self.bb_controls_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        self.bb_controls_frame.grid_columnconfigure(0, weight=1)

        # BB Mode Selection
        lbl_bb_mode = ctk.CTkLabel(self.bb_controls_frame, text="Builder Base Mode:", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_bb_mode.grid(row=0, column=0, padx=16, pady=(2, 2), sticky="w")

        self.bb_mode_var = ctk.StringVar(value="infinite")
        bb_mode_opt = ctk.CTkOptionMenu(
            self.bb_controls_frame,
            variable=self.bb_mode_var,
            values=["infinite", "fixed_attacks"],
            command=self._on_bb_mode_change
        )
        bb_mode_opt.grid(row=1, column=0, padx=16, pady=(0, 6), sticky="ew")

        # BB Fixed Attack Count Container
        self.bb_fixed_count_frame = ctk.CTkFrame(self.bb_controls_frame, fg_color="#27272a", corner_radius=8)
        self.bb_fixed_count_frame.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="ew")
        self.bb_fixed_count_frame.grid_columnconfigure(1, weight=1)

        lbl_bb_fc = ctk.CTkLabel(self.bb_fixed_count_frame, text="Target BB Attacks:", font=ctk.CTkFont(size=12))
        lbl_bb_fc.grid(row=0, column=0, padx=(10, 6), pady=6)

        btn_bb_minus = ctk.CTkButton(self.bb_fixed_count_frame, text="-", width=28, height=26, fg_color="#3f3f46", command=self._decrement_bb_attack_count)
        btn_bb_minus.grid(row=0, column=1, padx=2, pady=6, sticky="e")

        self.bb_attack_count_var = ctk.StringVar(value="10")
        self.bb_entry_attack_count = ctk.CTkEntry(self.bb_fixed_count_frame, textvariable=self.bb_attack_count_var, width=44, height=26, justify="center")
        self.bb_entry_attack_count.grid(row=0, column=2, padx=4, pady=6)
        self.bb_entry_attack_count.bind("<FocusOut>", lambda e: self._save_bb_attack_count())

        btn_bb_plus = ctk.CTkButton(self.bb_fixed_count_frame, text="+", width=28, height=26, fg_color="#3f3f46", command=self._increment_bb_attack_count)
        btn_bb_plus.grid(row=0, column=3, padx=(2, 10), pady=6, sticky="w")
        self.bb_fixed_count_frame.grid_remove()

        # BB Deployment Strategy Info Card
        bb_info_card = ctk.CTkFrame(self.bb_controls_frame, fg_color="#27272a", corner_radius=8)
        bb_info_card.grid(row=3, column=0, padx=16, pady=(4, 6), sticky="ew")
        bb_info_card.grid_columnconfigure(0, weight=1)

        lbl_bb_deploy_info = ctk.CTkLabel(
            bb_info_card,
            text=safe_text("📍 Deployment Strategy:\n• Point: Top-Right Perimeter (0.776, 0.102)\n• Dynamic BH Army Slots (1..8 auto-scan)\n• Hero Ability Auto-Cadence (Battle Machine)\n• Multi-Stage 1 & 2 Auto-Advance"),
            font=ctk.CTkFont(size=11),
            text_color="#38bdf8",
            justify="left"
        )
        lbl_bb_deploy_info.grid(row=0, column=0, padx=10, pady=8, sticky="w")

        # BB Combat Exit Timer Card
        bb_timer_card = ctk.CTkFrame(self.bb_controls_frame, fg_color="#18181b", corner_radius=8)
        bb_timer_card.grid(row=4, column=0, padx=16, pady=(4, 6), sticky="ew")
        bb_timer_card.grid_columnconfigure(0, weight=1)
        bb_timer_card.grid_columnconfigure(1, weight=0)

        lbl_bb_timer_title = ctk.CTkLabel(bb_timer_card, text=safe_text("⏱️ BB Combat Exit Timer:"), font=ctk.CTkFont(size=12, weight="bold"))
        lbl_bb_timer_title.grid(row=0, column=0, padx=(10, 4), pady=(6, 2), sticky="w")

        self.bb_ent_timer_var = ctk.StringVar(value="60s")
        self.bb_ent_timer = ctk.CTkEntry(bb_timer_card, textvariable=self.bb_ent_timer_var, width=70, height=24, justify="center")
        self.bb_ent_timer.grid(row=0, column=1, padx=(4, 10), pady=(6, 2), sticky="e")
        self.bb_ent_timer.bind("<FocusOut>", lambda e: self._on_bb_timer_change())
        self.bb_ent_timer.bind("<Return>", lambda e: self._on_bb_timer_change())

        self.lbl_bb_timer_summary = ctk.CTkLabel(
            bb_timer_card,
            text="Exit limit: 1m 00s (Max: 2m 30s / 150s)",
            font=ctk.CTkFont(size=11),
            text_color="#a1a1aa"
        )
        self.lbl_bb_timer_summary.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 6), sticky="w")

        # BB Audit Log Button
        btn_bb_audit = ctk.CTkButton(
            self.bb_controls_frame,
            text=safe_text("📋 Open Builder Base Audit Log"),
            height=30,
            fg_color="#334155",
            hover_color="#1e293b",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._open_bb_audit_log
        )
        btn_bb_audit.grid(row=5, column=0, padx=16, pady=(6, 8), sticky="ew")

        # =============================================================
        # 3. GLOBAL CONTROLS & ACTION BUTTONS
        # =============================================================
        # Voice & Desktop Toast Switch
        self.voice_var = ctk.BooleanVar(value=True)
        sw_voice_text = "Voice & Desktop Toast Alerts" if sys.platform == "darwin" else "Voice & Windows Toast Alerts"
        sw_voice = ctk.CTkSwitch(sidebar, text=sw_voice_text, variable=self.voice_var, command=self._on_voice_toggle)
        sw_voice.grid(row=5, column=0, padx=16, pady=6, sticky="w")

        # Primary Action Buttons
        start_txt = safe_text("▶ START FARMING (⌘R)" if sys.platform == "darwin" else "▶ START FARMING (F8)")
        self.btn_start = ctk.CTkButton(
            sidebar,
            text=start_txt,
            height=42,
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._toggle_farming_session
        )
        self.btn_start.grid(row=6, column=0, padx=16, pady=(12, 6), sticky="ew")

        pause_txt = safe_text("⏸ PAUSE (⌘P)" if sys.platform == "darwin" else "⏸ PAUSE (F9)")
        self.btn_pause = ctk.CTkButton(
            sidebar,
            text=pause_txt,
            height=34,
            fg_color="#3f3f46",
            text_color="#9ca3af",
            state="disabled",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._handle_pause_action
        )
        self.btn_pause.grid(row=7, column=0, padx=16, pady=3, sticky="ew")

        stop_txt = safe_text("🛑 SAFE STOP (Esc)" if sys.platform == "darwin" else "🛑 EMERGENCY STOP (F10)")
        self.btn_stop = ctk.CTkButton(
            sidebar,
            text=stop_txt,
            height=34,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._handle_stop_action
        )
        self.btn_stop.grid(row=8, column=0, padx=16, pady=(3, 6), sticky="ew")

        btn_audit = ctk.CTkButton(
            sidebar,
            text=safe_text("📋 Open Decision Audit Log"),
            height=28,
            fg_color="#27272a",
            hover_color="#3f3f46",
            font=ctk.CTkFont(size=12),
            command=self._open_audit_log
        )
        btn_audit.grid(row=9, column=0, padx=16, pady=(0, 14), sticky="ew")




        # ----------------- MAIN VIEW (Tabbed Layout) -----------------
        main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#18181b")
        main_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 6), pady=(4, 6))
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=0)
        main_frame.grid_rowconfigure(1, weight=1)

        # Header with State, Shortcuts & Quick Action Buttons
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=8, pady=(4, 2), sticky="ew")

        # Left side: Active State Pill
        lbl_state_title = ctk.CTkLabel(header_frame, text="Active State:", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_state_title.pack(side="left", padx=(0, 6))

        self.state_pill = ctk.CTkLabel(
            header_frame,
            text="IDLE / READY",
            fg_color="#27272a",
            corner_radius=8,
            padx=10,
            pady=4,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#22c55e"
        )
        self.state_pill.pack(side="left", padx=(0, 8))

        # Header Quick Action Buttons (One-Click Convenience for Mac & Windows)
        self.btn_hdr_start = ctk.CTkButton(
            header_frame,
            text="▶ Start (⌘R)" if sys.platform == "darwin" else "▶ Start (F8)",
            width=92,
            height=28,
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._toggle_farming_session
        )
        self.btn_hdr_start.pack(side="left", padx=2)

        self.btn_hdr_pause = ctk.CTkButton(
            header_frame,
            text="⏸ Pause (⌘P)" if sys.platform == "darwin" else "⏸ Pause (F9)",
            width=92,
            height=28,
            fg_color="#3f3f46",
            text_color="#9ca3af",
            state="disabled",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._handle_pause_action
        )
        self.btn_hdr_pause.pack(side="left", padx=2)

        self.btn_hdr_stop = ctk.CTkButton(
            header_frame,
            text=safe_text("🛑 Stop (Esc)" if sys.platform == "darwin" else "🛑 Stop (F10)"),
            width=90,
            height=28,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._handle_stop_action
        )
        self.btn_hdr_stop.pack(side="left", padx=2)

        self.btn_hdr_bind = ctk.CTkButton(
            header_frame,
            text="◎ Bind (⌘B)" if sys.platform == "darwin" else "◎ Bind (F7)",
            width=86,
            height=28,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._bind_game_window_interactive
        )
        self.btn_hdr_bind.pack(side="left", padx=2)

        # Right side: Execution Mode Pill & Shortcut Badge
        exec_pill_label = "⚡ LIVE WIN32" if sys.platform == "win32" else "⚡ LIVE MOUSE"
        self.mode_pill = ctk.CTkLabel(
            header_frame,
            text=exec_pill_label,
            fg_color="#dc2626",
            corner_radius=8,
            padx=10,
            pady=4,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ffffff"
        )
        self.mode_pill.pack(side="right")

        shortcut_text = "⌨ ⌘R Start • ⌘P Pause • ⌘B Bind • Esc Stop" if sys.platform == "darwin" else "⌨ [F7] Bind • [F8] Start • [F9] Pause • [F10] Stop"
        lbl_shortcuts = ctk.CTkLabel(
            header_frame,
            text=shortcut_text,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#27272a",
            text_color="#9ca3af",
            corner_radius=8,
            padx=8,
            pady=4
        )
        lbl_shortcuts.pack(side="right", padx=(0, 6))

        # Main Tabview on Right Panel:
        # Tab 1: Live Telemetry & Feed
        # Tab 2: Army Setup & Drop Sequencer
        self.main_tabview = ctk.CTkTabview(main_frame, corner_radius=10, fg_color="#18181b")
        self.main_tabview.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 4))
        self.main_tabview.grid_columnconfigure(0, weight=1)
        self.main_tabview.grid_rowconfigure(0, weight=0)
        self.main_tabview.grid_rowconfigure(3, weight=1)

        tab_live_name = safe_text("📊 Telemetry & Live Feed")
        tab_army_name = safe_text("⚔️ Army Setup & Sequencer")
        tab_hist_name = safe_text("📜 Attack History")
        self.tab_live = self.main_tabview.add(tab_live_name)
        self.tab_army = self.main_tabview.add(tab_army_name)
        self.tab_hist = self.main_tabview.add(tab_hist_name)

        self.tab_live.grid_columnconfigure(0, weight=1)
        self.tab_live.grid_rowconfigure(2, weight=1)

        # ----------------- TAB 1: TELEMETRY & FEED -----------------
        # Telemetry Cards (Stats Grid - Attacks & Skips)
        telemetry_frame = ctk.CTkFrame(self.tab_live, fg_color="#222226", corner_radius=10)
        telemetry_frame.grid(row=0, column=0, padx=8, pady=(4, 6), sticky="ew")
        for i in range(2):
            telemetry_frame.grid_columnconfigure(i, weight=1)

        self.lbl_stat_attacks = self._create_stat_card(telemetry_frame, 0, "Attacks Completed", "0")
        self.lbl_stat_skips = self._create_stat_card(telemetry_frame, 1, "Skipped Bases", "0")

        # Loot Collected Section (Screenshot Verified)
        loot_section_frame = ctk.CTkFrame(self.tab_live, fg_color="#222226", corner_radius=10)
        loot_section_frame.grid(row=1, column=0, padx=8, pady=(0, 6), sticky="ew")
        loot_section_frame.grid_columnconfigure(0, weight=1)
        loot_section_frame.grid_columnconfigure(1, weight=1)
        loot_section_frame.grid_columnconfigure(2, weight=1)

        # Header for Loot Section
        lbl_loot_hdr = ctk.CTkLabel(
            loot_section_frame,
            text=safe_text("💰 Loot Collected (Screenshot Verified)"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e4e4e7"
        )
        lbl_loot_hdr.grid(row=0, column=0, columnspan=3, padx=12, pady=(6, 2), sticky="w")

        # Gold Card
        gold_card = ctk.CTkFrame(loot_section_frame, fg_color="#18181b", corner_radius=8)
        gold_card.grid(row=1, column=0, padx=8, pady=(2, 6), sticky="ew")
        gold_card.grid_columnconfigure(0, weight=1)
        lbl_g_t = ctk.CTkLabel(gold_card, text=safe_text("🟡 Gold"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#fbbf24")
        lbl_g_t.pack(pady=(4, 0))
        self.lbl_loot_gold_total = ctk.CTkLabel(gold_card, text="0", font=ctk.CTkFont(size=15, weight="bold"), text_color="#fef08a")
        self.lbl_loot_gold_total.pack(pady=(0, 0))
        self.lbl_loot_gold_last = ctk.CTkLabel(gold_card, text="Last: +0", font=ctk.CTkFont(size=10), text_color="#a1a1aa")
        self.lbl_loot_gold_last.pack(pady=(0, 4))

        # Elixir Card
        elixir_card = ctk.CTkFrame(loot_section_frame, fg_color="#18181b", corner_radius=8)
        elixir_card.grid(row=1, column=1, padx=8, pady=(2, 6), sticky="ew")
        elixir_card.grid_columnconfigure(0, weight=1)
        lbl_e_t = ctk.CTkLabel(elixir_card, text=safe_text("🟣 Elixir"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#d946ef")
        lbl_e_t.pack(pady=(4, 0))
        self.lbl_loot_elixir_total = ctk.CTkLabel(elixir_card, text="0", font=ctk.CTkFont(size=15, weight="bold"), text_color="#f5d0fe")
        self.lbl_loot_elixir_total.pack(pady=(0, 0))
        self.lbl_loot_elixir_last = ctk.CTkLabel(elixir_card, text="Last: +0", font=ctk.CTkFont(size=10), text_color="#a1a1aa")
        self.lbl_loot_elixir_last.pack(pady=(0, 4))

        # Dark Elixir Card
        de_card = ctk.CTkFrame(loot_section_frame, fg_color="#18181b", corner_radius=8)
        de_card.grid(row=1, column=2, padx=8, pady=(2, 6), sticky="ew")
        de_card.grid_columnconfigure(0, weight=1)
        lbl_de_t = ctk.CTkLabel(de_card, text=safe_text("⚫ Dark Elixir"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#38bdf8")
        lbl_de_t.pack(pady=(4, 0))
        self.lbl_loot_de_total = ctk.CTkLabel(de_card, text="0", font=ctk.CTkFont(size=15, weight="bold"), text_color="#e2e8f0")
        self.lbl_loot_de_total.pack(pady=(0, 0))
        self.lbl_loot_de_last = ctk.CTkLabel(de_card, text="Last: +0", font=ctk.CTkFont(size=10), text_color="#a1a1aa")
        self.lbl_loot_de_last.pack(pady=(0, 4))

        # Activity & Decision Feed
        feed_frame = ctk.CTkFrame(self.tab_live, fg_color="#222226", corner_radius=10)
        feed_frame.grid(row=2, column=0, padx=8, pady=(0, 8), sticky="nsew")
        feed_frame.grid_columnconfigure(0, weight=1)
        feed_frame.grid_rowconfigure(1, weight=1)

        lbl_feed_title = ctk.CTkLabel(feed_frame, text=safe_text("📜 Activity & Decision Feed"), font=ctk.CTkFont(size=13, weight="bold"))
        lbl_feed_title.grid(row=0, column=0, padx=12, pady=(8, 4), sticky="w")

        mono_family = "Menlo" if sys.platform == "darwin" else "Consolas"
        self.txt_logs = ctk.CTkTextbox(feed_frame, font=ctk.CTkFont(family=mono_family, size=12), fg_color="#18181b")
        self.txt_logs.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")

        # ----------------- TAB 2: ARMY SETUP & DROP SEQUENCER -----------------
        self._build_army_tab(self.tab_army)

        # ----------------- TAB 3: ATTACK HISTORY & RUN TOTALS -----------------
        self._build_history_tab(self.tab_hist)

        self.log_event("Application initialized. Ready to farm.")
        self.notifier.announce("Clash of Clans Farming Controller is ready", chime="ok")

        self._update_window_binding_ui()

    def _build_army_tab(self, parent) -> None:
        """Constructs the dedicated Army Configuration & Drop Sequencer tab."""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(
            parent,
            fg_color="transparent",
            scrollbar_button_color="#3f3f46",
            scrollbar_button_hover_color="#52525b"
        )
        scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=2)
        scroll.grid_columnconfigure(0, weight=1)

        self.army_scroll_frame = scroll
        self._enable_smooth_mousewheel_scrolling(scroll)

        # Header banner (tightened top padding)
        lbl_hdr = ctk.CTkLabel(
            scroll,
            text=safe_text("⚔️ Army Composition & Drop Sequencer (TH17 Ready)"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_hdr.grid(row=0, column=0, padx=6, pady=(2, 1), sticky="w")

        lbl_desc = ctk.CTkLabel(
            scroll,
            text="Configure dynamic army squad, siege machine, complete 6-hero lineup, and drop sequencer.\nUnits deploy in combat strictly according to your selected drop sequence order.",
            font=ctk.CTkFont(size=11),
            text_color="#9ca3af",
            justify="left"
        )
        lbl_desc.grid(row=1, column=0, padx=6, pady=(0, 6), sticky="w")

        # -------------------------------------------------------------
        # 0. ARMY HOUSING SPACE & CAPACITY SLIDERS (TH17 VERIFIED)
        # -------------------------------------------------------------
        card_capacity = ctk.CTkFrame(scroll, fg_color="#222226", corner_radius=10)
        card_capacity.grid(row=2, column=0, padx=6, pady=(0, 8), sticky="ew")
        card_capacity.grid_columnconfigure(0, weight=1)
        card_capacity.grid_columnconfigure(1, weight=1)

        cap_hdr_frame = ctk.CTkFrame(card_capacity, fg_color="transparent")
        cap_hdr_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=(8, 4), sticky="ew")
        cap_hdr_frame.grid_columnconfigure(0, weight=1)

        lbl_cap_hdr = ctk.CTkLabel(
            cap_hdr_frame,
            text=safe_text("⛺ Army Camp & Spell Storage Capacity:"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_cap_hdr.pack(side="left")

        # Live Troop Space Badge
        self.lbl_troop_cap_badge = ctk.CTkLabel(
            cap_hdr_frame,
            text="Troop Space: 352 / 352",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#22c55e",
            fg_color="#18181b",
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.lbl_troop_cap_badge.pack(side="right")

        # Live Spell Space Badge
        self.lbl_spell_cap_badge = ctk.CTkLabel(
            cap_hdr_frame,
            text="Spell Space: 11 / 11",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#a855f7",
            fg_color="#18181b",
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.lbl_spell_cap_badge.pack(side="right", padx=(0, 6))

        # Controls Row: Troop Capacity Slider & Entry
        cap_ctrl_frame = ctk.CTkFrame(card_capacity, fg_color="#18181b", corner_radius=8)
        cap_ctrl_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(2, 8), sticky="ew")
        cap_ctrl_frame.grid_columnconfigure(1, weight=1)

        # Troop Capacity
        lbl_tc = ctk.CTkLabel(cap_ctrl_frame, text="Troop Camp Limit:", font=ctk.CTkFont(size=11, weight="bold"))
        lbl_tc.grid(row=0, column=0, padx=(10, 6), pady=6, sticky="w")

        init_tc = int(getattr(self.config.deployment, "max_troop_capacity", 352))
        self.ent_troop_cap_var = ctk.StringVar(value=str(init_tc))
        self.ent_troop_cap = ctk.CTkEntry(cap_ctrl_frame, textvariable=self.ent_troop_cap_var, width=50, height=24, justify="center")
        self.ent_troop_cap.grid(row=0, column=1, padx=(0, 8), pady=6, sticky="w")

        self.slider_troop_cap = ctk.CTkSlider(
            cap_ctrl_frame,
            from_=50,
            to=400,
            number_of_steps=350,
            width=160,
            height=16,
            command=self._on_troop_capacity_slider_changed
        )
        self.slider_troop_cap.set(init_tc)
        self.slider_troop_cap.grid(row=0, column=2, padx=6, pady=6, sticky="w")

        self.ent_troop_cap.bind("<FocusOut>", lambda e: self._on_troop_capacity_entry_changed())
        self.ent_troop_cap.bind("<Return>", lambda e: self._on_troop_capacity_entry_changed())

        # Spell Capacity
        lbl_sc = ctk.CTkLabel(cap_ctrl_frame, text="Spell Storage Limit:", font=ctk.CTkFont(size=11, weight="bold"))
        lbl_sc.grid(row=0, column=3, padx=(16, 6), pady=6, sticky="w")

        init_sc = int(getattr(self.config.deployment, "max_spell_capacity", 11))
        self.ent_spell_cap_var = ctk.StringVar(value=str(init_sc))
        self.ent_spell_cap = ctk.CTkEntry(cap_ctrl_frame, textvariable=self.ent_spell_cap_var, width=40, height=24, justify="center")
        self.ent_spell_cap.grid(row=0, column=4, padx=(0, 8), pady=6, sticky="w")

        self.slider_spell_cap = ctk.CTkSlider(
            cap_ctrl_frame,
            from_=1,
            to=15,
            number_of_steps=14,
            width=100,
            height=16,
            command=self._on_spell_capacity_slider_changed
        )
        self.slider_spell_cap.set(init_sc)
        self.slider_spell_cap.grid(row=0, column=5, padx=(6, 10), pady=6, sticky="w")

        self.ent_spell_cap.bind("<FocusOut>", lambda e: self._on_spell_capacity_entry_changed())
        self.ent_spell_cap.bind("<Return>", lambda e: self._on_spell_capacity_entry_changed())

        # -------------------------------------------------------------
        # 1. DEPLOYMENT BAR SIZE & CALIBRATION LOCK
        # -------------------------------------------------------------
        card_ribbon = ctk.CTkFrame(scroll, fg_color="#222226", corner_radius=10)
        card_ribbon.grid(row=3, column=0, padx=6, pady=(0, 8), sticky="ew")
        card_ribbon.grid_columnconfigure(0, weight=1)
        card_ribbon.grid_columnconfigure(1, weight=1)

        r_hdr_frame = ctk.CTkFrame(card_ribbon, fg_color="transparent")
        r_hdr_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=(8, 4), sticky="ew")
        r_hdr_frame.grid_columnconfigure(0, weight=1)

        lbl_r_hdr = ctk.CTkLabel(
            r_hdr_frame,
            text=safe_text("📐 Deployment Ribbon Calibration & Bar Size:"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_r_hdr.pack(side="left")

        curr_mode = getattr(self.config.deployment, "ribbon_mode", "compact").lower()
        is_locked = getattr(self.config.deployment, "lock_ribbon_mode", True)
        is_verified = getattr(self.config.deployment, "deployment_verified", True)

        status_text = f"🔒 Locked ({curr_mode.title()} Bar)" if is_locked else "🔓 Dynamic Auto-Detect"
        status_color = "#22c55e" if is_locked else "#f59e0b"

        self.lbl_ribbon_status = ctk.CTkLabel(
            r_hdr_frame,
            text=status_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=status_color,
            fg_color="#18181b",
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.lbl_ribbon_status.pack(side="right")

        # Row 1: Mode selector, Lock checkbox, and Test Verify button
        r_ctrl_frame = ctk.CTkFrame(card_ribbon, fg_color="transparent")
        r_ctrl_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(2, 8), sticky="ew")

        lbl_mode_desc = ctk.CTkLabel(
            r_ctrl_frame,
            text="In-Game Bar Size:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#e2e8f0"
        )
        lbl_mode_desc.pack(side="left", padx=(0, 8))

        mode_disp_val = "Compact (Reduced Bar)" if curr_mode == "compact" else "Large (Standard Bar)"
        self.seg_ribbon_mode = ctk.CTkSegmentedButton(
            r_ctrl_frame,
            values=["Compact (Reduced Bar)", "Large (Standard Bar)"],
            command=self._on_gui_ribbon_mode_changed
        )
        self.seg_ribbon_mode.set(mode_disp_val)
        self.seg_ribbon_mode.pack(side="left", padx=(0, 12))

        self.chk_lock_ribbon_var = ctk.BooleanVar(value=is_locked)
        self.chk_lock_ribbon = ctk.CTkCheckBox(
            r_ctrl_frame,
            text="Lock Calibration (Prevents scenery interference)",
            variable=self.chk_lock_ribbon_var,
            font=ctk.CTkFont(size=11),
            command=self._on_gui_toggle_lock_ribbon
        )
        self.chk_lock_ribbon.pack(side="left", padx=(0, 12))

        self.btn_verify_req = ctk.CTkButton(
            r_ctrl_frame,
            text="🧪 Verify On Next Attack",
            width=150,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self._on_gui_request_verification
        )
        self.btn_verify_req.pack(side="right")

        # -------------------------------------------------------------
        # 2. DYNAMIC TROOPS SQUAD & HORIZONTAL SELECTOR RIBBON
        # -------------------------------------------------------------
        card_troops = ctk.CTkFrame(scroll, fg_color="#222226", corner_radius=10)
        card_troops.grid(row=4, column=0, padx=6, pady=(0, 8), sticky="ew")
        card_troops.grid_columnconfigure(0, weight=1)

        t_hdr_frame = ctk.CTkFrame(card_troops, fg_color="transparent")
        t_hdr_frame.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")
        t_hdr_frame.grid_columnconfigure(0, weight=1)

        lbl_t_hdr = ctk.CTkLabel(
            t_hdr_frame,
            text=safe_text("🎯 Troop Squads & Drop Sequence (Dynamic Slots):"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#fbbf24"
        )
        lbl_t_hdr.pack(side="left")

        btn_add_troop = ctk.CTkButton(
            t_hdr_frame,
            text="+ Add Troop Slot",
            width=130,
            height=26,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._add_troop_slot
        )
        btn_add_troop.pack(side="right")

        # Horizontal Quick Select Ribbon for All 52 Troops
        lbl_ribbon_hdr = ctk.CTkLabel(
            card_troops,
            text=safe_text("🎠 Quick Select Troop Ribbon (Click card to add or assign slot):"),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#94a3b8"
        )
        lbl_ribbon_hdr.grid(row=1, column=0, padx=10, pady=(2, 0), sticky="w")

        self.troop_carousel = ctk.CTkScrollableFrame(
            card_troops,
            orientation="horizontal",
            height=92,
            fg_color="#18181b",
            corner_radius=8,
            scrollbar_button_color="#3f3f46",
            scrollbar_button_hover_color="#52525b"
        )
        self.troop_carousel.grid(row=2, column=0, padx=8, pady=(2, 6), sticky="ew")

        # Populate carousel with all 52 troop cards
        for opt_troop in TROOP_OPTIONS:
            t_icon_path = UNIT_ASSET_MAP.get(opt_troop)
            t_img = self._load_ctk_image(t_icon_path, size=(32, 42)) if t_icon_path else None

            # Compact button text
            disp_short = opt_troop
            if len(disp_short) > 11:
                disp_short = disp_short.replace("Super ", "S.").replace("Electro ", "E-").replace("Apprentice ", "App.")

            btn_c = ctk.CTkButton(
                self.troop_carousel,
                text=disp_short,
                image=t_img,
                compound="top",
                width=56,
                height=80,
                fg_color="#222226",
                hover_color="#0284c7",
                text_color="#e2e8f0",
                font=ctk.CTkFont(size=9, weight="bold"),
                command=lambda u=opt_troop: self._on_carousel_troop_clicked(u)
            )
            btn_c.pack(side="left", padx=2, pady=2)

        self.troop_rows_frame = ctk.CTkFrame(card_troops, fg_color="transparent")
        self.troop_rows_frame.grid(row=3, column=0, padx=6, pady=(0, 6), sticky="ew")
        self.troop_rows_frame.grid_columnconfigure(0, weight=1)

        self.troop_slot_rows = []

        cfg_troops = getattr(self.config.deployment.army, "troops", [])
        if cfg_troops:
            for s_idx, cfg_t in enumerate(cfg_troops):
                t_en = getattr(cfg_t, "enabled", True)
                t_name_raw = getattr(cfg_t, "name", "valkyrie").replace("_", " ").title()
                t_qty = int(getattr(cfg_t, "expected_quantity", 20))
                prio_val = int(getattr(cfg_t, "priority", s_idx + 1))
                prio_idx = min(len(PRIORITY_OPTIONS) - 1, max(0, prio_val - 1))
                self._add_troop_slot(unit_name=t_name_raw, qty=t_qty, prio_idx=prio_idx, enabled=t_en)
        else:
            self._add_troop_slot(unit_name="Valkyrie", qty=24, prio_idx=0, enabled=True)
            self._add_troop_slot(unit_name="Super Wall Breaker", qty=4, prio_idx=1, enabled=True)

        # -------------------------------------------------------------
        # 3. SIEGE MACHINE (HORIZONTAL QUICK SELECTOR & DEPLOYMENT SLOT)
        # -------------------------------------------------------------
        card_siege = ctk.CTkFrame(scroll, fg_color="#222226", corner_radius=10)
        card_siege.grid(row=5, column=0, padx=6, pady=(0, 8), sticky="ew")
        card_siege.grid_columnconfigure(0, weight=1)

        s_hdr_frame = ctk.CTkFrame(card_siege, fg_color="transparent")
        s_hdr_frame.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")
        s_hdr_frame.grid_columnconfigure(0, weight=1)

        lbl_s_hdr = ctk.CTkLabel(
            s_hdr_frame,
            text=safe_text("🛡️ Siege Machine (Deployment Slot):"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_s_hdr.pack(side="left")

        curr_siege_name = "Siege Barracks"
        cfg_sieges = getattr(self.config.deployment.army, "siege", [])
        if cfg_sieges and getattr(cfg_sieges[0], "name", None):
            s_cand = cfg_sieges[0].name.replace("_", " ").title()
            for opt in SIEGE_OPTIONS:
                if opt.lower().replace(" ", "") == s_cand.lower().replace(" ", ""):
                    curr_siege_name = opt
                    break

        self.siege_unit_var = ctk.StringVar(value=curr_siege_name)

        self.lbl_active_siege_badge = ctk.CTkLabel(
            s_hdr_frame,
            text=f"Active: {curr_siege_name}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#38bdf8",
            fg_color="#1e293b",
            corner_radius=6,
            padx=8,
            pady=2
        )
        self.lbl_active_siege_badge.pack(side="right")

        self.chk_siege_var = ctk.BooleanVar(value=getattr(self.config.deployment, "deploy_siege", True))
        chk_siege = ctk.CTkCheckBox(
            card_siege,
            text="Deploy Siege Machine in Attack (single tap drop, never spammed as troop or triggered as hero ability)",
            variable=self.chk_siege_var,
            font=ctk.CTkFont(size=11)
        )
        chk_siege.grid(row=1, column=0, padx=10, pady=(0, 4), sticky="w")

        lbl_siege_ribbon_hdr = ctk.CTkLabel(
            card_siege,
            text=safe_text("🎠 Select Siege Machine (Click card to equip):"),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#94a3b8"
        )
        lbl_siege_ribbon_hdr.grid(row=2, column=0, padx=10, pady=(2, 0), sticky="w")

        # Horizontal Scrollable Ribbon for All 9 Siege Machines
        self.siege_carousel = ctk.CTkScrollableFrame(
            card_siege,
            orientation="horizontal",
            height=95,
            fg_color="#18181b",
            corner_radius=8,
            scrollbar_button_color="#3f3f46",
            scrollbar_button_hover_color="#52525b"
        )
        self.siege_carousel.grid(row=3, column=0, padx=8, pady=(2, 8), sticky="ew")

        self.siege_carousel_buttons = {}
        for opt_siege in SIEGE_OPTIONS:
            s_icon_path = UNIT_ASSET_MAP.get(opt_siege)
            s_img = self._load_ctk_image(s_icon_path, size=(38, 46)) if s_icon_path else None

            disp_short = opt_siege
            if len(disp_short) > 13:
                disp_short = disp_short.replace("Launcher", "Launch.").replace("Barracks", "Barr.")

            is_active = (opt_siege == curr_siege_name)
            btn_s = ctk.CTkButton(
                self.siege_carousel,
                text=disp_short,
                image=s_img,
                compound="top",
                width=68,
                height=84,
                fg_color="#1e293b" if is_active else "#222226",
                hover_color="#0284c7",
                border_color="#0284c7" if is_active else "#27272a",
                border_width=2 if is_active else 0,
                text_color="#38bdf8" if is_active else "#e2e8f0",
                font=ctk.CTkFont(size=9, weight="bold"),
                command=lambda s=opt_siege: self._on_siege_card_clicked(s)
            )
            btn_s.pack(side="left", padx=3, pady=2)
            self.siege_carousel_buttons[opt_siege] = btn_s

        self.lbl_siege_icon = ctk.CTkLabel(card_siege, text="", width=1, height=1)
        self._update_siege_icon_preview()

        # -------------------------------------------------------------
        # 4. HEROES (TH17 COMPLETE 6 HERO ROSTER, MAX 4 ACTIVE)
        # -------------------------------------------------------------
        card_heroes = ctk.CTkFrame(scroll, fg_color="#222226", corner_radius=10)
        card_heroes.grid(row=6, column=0, padx=6, pady=(0, 8), sticky="ew")
        for c_i in range(6):
            card_heroes.grid_columnconfigure(c_i, weight=1)

        self.lbl_h_hdr = ctk.CTkLabel(
            card_heroes,
            text=safe_text("👑 Active Heroes (Select up to 4 Heroes for Battle — Max 4 Allowed):"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f43f5e"
        )
        self.lbl_h_hdr.grid(row=0, column=0, columnspan=6, padx=10, pady=(8, 4), sticky="w")

        self.hero_vars = {}
        self.hero_frames = {}
        self._selected_heroes_order = []

        hero_defs = [
            ("barbarian_king", "Barbarian King", "assets/heroes/barbarian_king.png"),
            ("archer_queen", "Archer Queen", "assets/heroes/archer_queen.png"),
            ("grand_warden", "Grand Warden", "assets/heroes/grand_warden.png"),
            ("royal_champion", "Royal Champion", "assets/heroes/royal_champion.png"),
            ("minion_prince", "Minion Prince", "assets/heroes/minion_prince.png"),
            ("dragon_duke", "Dragon Duke", "assets/heroes/dragon_duke.png"),
        ]

        cfg_heroes = getattr(self.config.deployment.army, "heroes", [])
        cfg_hero_active_map = {}
        for h in cfg_heroes:
            h_name = h.name if hasattr(h, "name") else (h.get("name", "") if isinstance(h, dict) else "")
            h_en = getattr(h, "enabled", True) if hasattr(h, "enabled") else (h.get("enabled", True) if isinstance(h, dict) else True)
            if h_name:
                cfg_hero_active_map[h_name] = h_en

        for idx, (h_key, h_display, h_icon_path) in enumerate(hero_defs):
            h_frame = ctk.CTkFrame(card_heroes, fg_color="#18181b", corner_radius=8, border_width=1, border_color="#27272a")
            h_frame.grid(row=1, column=idx, padx=3, pady=(0, 6), sticky="ew")
            h_frame.grid_columnconfigure(0, weight=1)
            self.hero_frames[h_key] = h_frame

            # Rectangular attack ribbon card icon: 42x56
            h_img = self._load_ctk_image(h_icon_path, size=(42, 56))
            lbl_h_ico = ctk.CTkLabel(h_frame, text="", image=h_img)
            lbl_h_ico.grid(row=0, column=0, pady=(4, 2))

            # Enforce max 4 active heroes on initial load
            is_active = cfg_hero_active_map.get(h_key, (idx < 4))
            if is_active and len(self._selected_heroes_order) < 4:
                self._selected_heroes_order.append(h_key)
                init_val = True
            else:
                init_val = False

            h_var = ctk.BooleanVar(value=init_val)
            self.hero_vars[h_key] = h_var

            chk_h = ctk.CTkCheckBox(
                h_frame,
                text=h_display,
                variable=h_var,
                font=ctk.CTkFont(size=10, weight="bold"),
                command=lambda k=h_key: self._on_hero_toggled(k)
            )
            chk_h.grid(row=1, column=0, padx=2, pady=(0, 6))

            # Apply initial visual card styling
            self._update_hero_card_style(h_key, init_val)

        self._update_hero_header_text()

        # Hero Ability Delay
        delay_row = ctk.CTkFrame(card_heroes, fg_color="transparent")
        delay_row.grid(row=2, column=0, columnspan=6, padx=10, pady=(0, 6), sticky="ew")
        lbl_del = ctk.CTkLabel(delay_row, text="Ability Delay (s):", font=ctk.CTkFont(size=11, weight="bold"))
        lbl_del.pack(side="left", padx=(0, 6))

        init_delay = getattr(self.config.deployment, "hero_ability_delay_seconds", 6.0)
        self.ent_army_ability_delay_var = ctk.StringVar(value=f"{init_delay:.1f}".rstrip('0').rstrip('.'))
        ent_del = ctk.CTkEntry(delay_row, textvariable=self.ent_army_ability_delay_var, width=50, height=24, justify="center")
        ent_del.pack(side="left", padx=(0, 8))

        lbl_del_hint = ctk.CTkLabel(delay_row, text="Seconds after army drop to click hero ribbon slots and activate abilities.", font=ctk.CTkFont(size=10), text_color="#a1a1aa")
        lbl_del_hint.pack(side="left")

        # -------------------------------------------------------------
        # 5. SPELLS (DYNAMIC SPELL ARSENAL WITH HORIZONTAL QUICK SELECT)
        # -------------------------------------------------------------
        card_spells = ctk.CTkFrame(scroll, fg_color="#222226", corner_radius=10)
        card_spells.grid(row=7, column=0, padx=6, pady=(0, 8), sticky="ew")
        card_spells.grid_columnconfigure(0, weight=1)

        sp_hdr_frame = ctk.CTkFrame(card_spells, fg_color="transparent")
        sp_hdr_frame.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")
        sp_hdr_frame.grid_columnconfigure(0, weight=1)

        lbl_sp_hdr = ctk.CTkLabel(
            sp_hdr_frame,
            text=safe_text("⚡ Spell Arsenal (Dynamic Spell Slots):"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#a855f7"
        )
        lbl_sp_hdr.pack(side="left")

        btn_add_spell = ctk.CTkButton(
            sp_hdr_frame,
            text="+ Add Spell Slot",
            width=130,
            height=26,
            fg_color="#a855f7",
            hover_color="#9333ea",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._add_spell_slot
        )
        btn_add_spell.pack(side="right")

        self.chk_spells_var = ctk.BooleanVar(value=getattr(self.config.deployment, "deploy_spells", True))
        chk_sp = ctk.CTkCheckBox(card_spells, text="Deploy Spells in Attack", variable=self.chk_spells_var, font=ctk.CTkFont(size=11))
        chk_sp.grid(row=1, column=0, padx=10, pady=(0, 4), sticky="w")

        # Horizontal Quick Select Ribbon for All 17 Spells
        lbl_spell_ribbon_hdr = ctk.CTkLabel(
            card_spells,
            text=safe_text("🎠 Quick Select Spell Ribbon (Click card to add or assign slot):"),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#94a3b8"
        )
        lbl_spell_ribbon_hdr.grid(row=2, column=0, padx=10, pady=(2, 0), sticky="w")

        self.spell_carousel = ctk.CTkScrollableFrame(
            card_spells,
            orientation="horizontal",
            height=95,
            fg_color="#18181b",
            corner_radius=8,
            scrollbar_button_color="#3f3f46",
            scrollbar_button_hover_color="#52525b"
        )
        self.spell_carousel.grid(row=3, column=0, padx=8, pady=(2, 6), sticky="ew")

        # Populate carousel with all 17 spells
        for opt_sp in SPELL_OPTIONS:
            sp_icon_path = UNIT_ASSET_MAP.get(opt_sp)
            sp_img = self._load_ctk_image(sp_icon_path, size=(42, 44)) if sp_icon_path else None

            disp_short = opt_sp.replace(" Spell", "")

            btn_s = ctk.CTkButton(
                self.spell_carousel,
                text=disp_short,
                image=sp_img,
                compound="top",
                width=62,
                height=84,
                fg_color="#222226",
                hover_color="#a855f7",
                text_color="#e2e8f0",
                font=ctk.CTkFont(size=9, weight="bold"),
                command=lambda s=opt_sp: self._on_carousel_spell_clicked(s)
            )
            btn_s.pack(side="left", padx=2, pady=2)

        self.spell_rows_frame = ctk.CTkFrame(card_spells, fg_color="transparent")
        self.spell_rows_frame.grid(row=4, column=0, padx=6, pady=(0, 6), sticky="ew")
        self.spell_rows_frame.grid_columnconfigure(0, weight=1)

        self.spell_slot_rows = []

        cfg_spells = getattr(self.config.deployment.army, "spells", [])
        if cfg_spells:
            for s_idx, cfg_sp in enumerate(cfg_spells):
                sp_en = getattr(cfg_sp, "enabled", True)
                sp_name_raw = getattr(cfg_sp, "name", "totem_spell").replace("_", " ").title()
                if sp_name_raw.lower() in ("totem", "totem spell"):
                    sp_name_raw = "Totem Spell"
                sp_qty = int(getattr(cfg_sp, "expected_quantity", 11))
                self._add_spell_slot(spell_name=sp_name_raw, qty=sp_qty, enabled=sp_en)
        else:
            self._add_spell_slot(spell_name="Totem Spell", qty=11, enabled=True)

        # -------------------------------------------------------------
        # 5. SAVE & APPLY BUTTON
        # -------------------------------------------------------------
        btn_save = ctk.CTkButton(
            scroll,
            text=safe_text("💾 Save & Apply Army Configuration"),
            height=38,
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._save_army_configuration
        )
        btn_save.grid(row=8, column=0, padx=6, pady=(4, 12), sticky="ew")
        self._update_army_capacity_display()

    # -----------------------------------------------------------------
    # SMOOTH SCROLLING, HOUSING SPACE & ATTACK HISTORY
    # -----------------------------------------------------------------
    def _enable_smooth_mousewheel_scrolling(self, scrollable_frame) -> None:
        """
        Recursively binds <MouseWheel> events across all child widgets so mousewheel scrolling
        remains fluid, responsive, and stutter-free across all panels.
        """
        canvas = getattr(scrollable_frame, "_parent_canvas", None)
        if not canvas:
            return

        def _on_mousewheel(event):
            if sys.platform == "darwin":
                delta = -1 * int(event.delta)
            else:
                delta = -1 * int(event.delta / 120)
            canvas.yview_scroll(delta, "units")

        def _bind_widget(w):
            if isinstance(w, ctk.CTkScrollableFrame) and w != scrollable_frame:
                if getattr(w, "_orientation", "vertical") == "horizontal":
                    return
            try:
                w.bind("<MouseWheel>", _on_mousewheel, add="+")
            except Exception:
                pass
            for child in w.winfo_children():
                _bind_widget(child)

        self._bind_mousewheel_recursive = _bind_widget
        _bind_widget(scrollable_frame)

    def _on_troop_capacity_slider_changed(self, val: float) -> None:
        new_v = int(round(float(val)))
        if hasattr(self, "ent_troop_cap_var") and self.ent_troop_cap_var.get() != str(new_v):
            self.ent_troop_cap_var.set(str(new_v))
        self._update_army_capacity_display()

    def _on_troop_capacity_entry_changed(self) -> None:
        try:
            val = int(self.ent_troop_cap_var.get())
            val = max(50, min(400, val))
            self.ent_troop_cap_var.set(str(val))
            if hasattr(self, "slider_troop_cap"):
                self.slider_troop_cap.set(val)
        except ValueError:
            pass
        self._update_army_capacity_display()

    def _on_spell_capacity_slider_changed(self, val: float) -> None:
        new_v = int(round(float(val)))
        if hasattr(self, "ent_spell_cap_var") and self.ent_spell_cap_var.get() != str(new_v):
            self.ent_spell_cap_var.set(str(new_v))
        self._update_army_capacity_display()

    def _on_spell_capacity_entry_changed(self) -> None:
        try:
            val = int(self.ent_spell_cap_var.get())
            val = max(1, min(15, val))
            self.ent_spell_cap_var.set(str(val))
            if hasattr(self, "slider_spell_cap"):
                self.slider_spell_cap.set(val)
        except ValueError:
            pass
        self._update_army_capacity_display()

    def _update_army_capacity_display(self) -> None:
        """Calculates and refreshes current army and spell housing space against configured limits."""
        try:
            troops_data = []
            for r in getattr(self, "troop_slot_rows", []):
                u_name = r["unit_var"].get()
                try:
                    qty = int(r["qty_var"].get())
                except ValueError:
                    qty = 0
                en = r["en_var"].get()
                troops_data.append((u_name, qty, en))
                if "lbl_sp_hint" in r:
                    unit_sp = get_troop_space(u_name)
                    tot_sp = unit_sp * qty
                    r["lbl_sp_hint"].configure(text=f"({tot_sp} sp)")

            used_troop_sp, _ = calculate_army_housing_space(troops_data)

            spells_data = []
            for r in getattr(self, "spell_slot_rows", []):
                sp_name = r["unit_var"].get()
                try:
                    qty = int(r["qty_var"].get())
                except ValueError:
                    qty = 0
                en = r["en_var"].get()
                spells_data.append((sp_name, qty, en))
                if "lbl_sp_hint" in r:
                    unit_sp = get_spell_space(sp_name)
                    tot_sp = unit_sp * qty
                    r["lbl_sp_hint"].configure(text=f"({tot_sp} sp)")

            used_spell_sp, _ = calculate_spell_housing_space(spells_data)

            try:
                max_troop = int(self.ent_troop_cap_var.get())
            except (ValueError, AttributeError):
                max_troop = 352

            try:
                max_spell = int(self.ent_spell_cap_var.get())
            except (ValueError, AttributeError):
                max_spell = 11

            if hasattr(self, "lbl_troop_cap_badge"):
                if used_troop_sp > max_troop:
                    diff = used_troop_sp - max_troop
                    self.lbl_troop_cap_badge.configure(
                        text=f"⚠️ Over Capacity: {used_troop_sp}/{max_troop} (+{diff} sp)",
                        text_color="#ef4444"
                    )
                elif used_troop_sp == max_troop:
                    self.lbl_troop_cap_badge.configure(
                        text=f"✓ Full Army: {used_troop_sp}/{max_troop} sp (100%)",
                        text_color="#22c55e"
                    )
                else:
                    pct = round((used_troop_sp / max_troop) * 100) if max_troop > 0 else 0
                    self.lbl_troop_cap_badge.configure(
                        text=f"Troop Space: {used_troop_sp}/{max_troop} sp ({pct}%)",
                        text_color="#38bdf8"
                    )

            if hasattr(self, "lbl_spell_cap_badge"):
                if used_spell_sp > max_spell:
                    diff = used_spell_sp - max_spell
                    self.lbl_spell_cap_badge.configure(
                        text=f"⚠️ Over Spell Cap: {used_spell_sp}/{max_spell} (+{diff} sp)",
                        text_color="#ef4444"
                    )
                elif used_spell_sp == max_spell:
                    self.lbl_spell_cap_badge.configure(
                        text=f"✓ Full Spells: {used_spell_sp}/{max_spell} sp (100%)",
                        text_color="#a855f7"
                    )
                else:
                    self.lbl_spell_cap_badge.configure(
                        text=f"Spell Space: {used_spell_sp}/{max_spell} sp",
                        text_color="#c084fc"
                    )
        except Exception as e:
            logger.debug(f"Error updating capacity display: {e}")

    def _build_history_tab(self, parent) -> None:
        """Constructs the dedicated Attack History & Cumulative Run Totals tab."""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # 1. Lifetime Run Summary Card Grid
        summary_frame = ctk.CTkFrame(parent, fg_color="#222226", corner_radius=10)
        summary_frame.grid(row=0, column=0, padx=8, pady=(4, 6), sticky="ew")
        for i in range(4):
            summary_frame.grid_columnconfigure(i, weight=1)

        # Lifetime Gold
        c_g = ctk.CTkFrame(summary_frame, fg_color="#18181b", corner_radius=8)
        c_g.grid(row=0, column=0, padx=6, pady=6, sticky="ew")
        lbl_g_title = ctk.CTkLabel(c_g, text=safe_text("🟡 Total Gold Looted"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#fbbf24")
        lbl_g_title.pack(pady=(4, 0))
        self.lbl_hist_gold = ctk.CTkLabel(c_g, text="0", font=ctk.CTkFont(size=16, weight="bold"), text_color="#fef08a")
        self.lbl_hist_gold.pack(pady=(0, 4))

        # Lifetime Elixir
        c_e = ctk.CTkFrame(summary_frame, fg_color="#18181b", corner_radius=8)
        c_e.grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        lbl_e_title = ctk.CTkLabel(c_e, text=safe_text("🟣 Total Elixir Looted"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#d946ef")
        lbl_e_title.pack(pady=(4, 0))
        self.lbl_hist_elixir = ctk.CTkLabel(c_e, text="0", font=ctk.CTkFont(size=16, weight="bold"), text_color="#f5d0fe")
        self.lbl_hist_elixir.pack(pady=(0, 4))

        # Lifetime Dark Elixir
        c_de = ctk.CTkFrame(summary_frame, fg_color="#18181b", corner_radius=8)
        c_de.grid(row=0, column=2, padx=6, pady=6, sticky="ew")
        lbl_de_title = ctk.CTkLabel(c_de, text=safe_text("⚫ Total Dark Elixir"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#38bdf8")
        lbl_de_title.pack(pady=(4, 0))
        self.lbl_hist_de = ctk.CTkLabel(c_de, text="0", font=ctk.CTkFont(size=16, weight="bold"), text_color="#bae6fd")
        self.lbl_hist_de.pack(pady=(0, 4))

        # Lifetime Attacks
        c_att = ctk.CTkFrame(summary_frame, fg_color="#18181b", corner_radius=8)
        c_att.grid(row=0, column=3, padx=6, pady=6, sticky="ew")
        lbl_att_title = ctk.CTkLabel(c_att, text=safe_text("⚔️ Attacks (Run Total)"), font=ctk.CTkFont(size=11, weight="bold"), text_color="#22c55e")
        lbl_att_title.pack(pady=(4, 0))
        self.lbl_hist_attacks = ctk.CTkLabel(c_att, text="0", font=ctk.CTkFont(size=16, weight="bold"), text_color="#86efac")
        self.lbl_hist_attacks.pack(pady=(0, 4))

        # 2. Scrollable Attack History Table
        hist_table_card = ctk.CTkFrame(parent, fg_color="#222226", corner_radius=10)
        hist_table_card.grid(row=1, column=0, padx=8, pady=(0, 6), sticky="nsew")
        hist_table_card.grid_columnconfigure(0, weight=1)
        hist_table_card.grid_rowconfigure(2, weight=1)

        t_hdr = ctk.CTkFrame(hist_table_card, fg_color="transparent")
        t_hdr.grid(row=0, column=0, padx=10, pady=(8, 4), sticky="ew")
        lbl_t_title = ctk.CTkLabel(
            t_hdr,
            text=safe_text("📜 Attack Log (All Attacks During Program Run):"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#e2e8f0"
        )
        lbl_t_title.pack(side="left")

        # Table Column Headers
        col_hdr = ctk.CTkFrame(hist_table_card, fg_color="#18181b", corner_radius=6)
        col_hdr.grid(row=1, column=0, padx=10, pady=(0, 2), sticky="ew")
        cols = [("#", 35), ("Time", 65), ("Outcome", 80), ("Gold Looted", 110), ("Elixir Looted", 110), ("Dark Elixir", 90), ("Duration", 70)]
        for c_idx, (col_name, w) in enumerate(cols):
            lbl_c = ctk.CTkLabel(col_hdr, text=col_name, width=w, font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8")
            lbl_c.pack(side="left", padx=2, pady=4)

        # Scrollable rows container
        self.hist_scroll_rows = ctk.CTkScrollableFrame(
            hist_table_card,
            fg_color="#18181b",
            corner_radius=8,
            scrollbar_button_color="#3f3f46",
            scrollbar_button_hover_color="#52525b"
        )
        self.hist_scroll_rows.grid(row=2, column=0, padx=10, pady=(0, 8), sticky="nsew")

        self._enable_smooth_mousewheel_scrolling(self.hist_scroll_rows)
        self.rendered_history_count = 0

    def _render_history_table_row(self, index: int, record: dict) -> None:
        if not hasattr(self, "hist_scroll_rows"):
            return
        row_frame = ctk.CTkFrame(self.hist_scroll_rows, fg_color="#222226" if index % 2 == 0 else "#1c1c20", corner_radius=4)
        row_frame.pack(fill="x", padx=2, pady=1)

        t_time = record.get("timestamp", datetime.now().strftime("%H:%M:%S"))
        outcome = record.get("outcome", "VICTORY")
        g = record.get("target_gold", 0)
        e = record.get("target_elixir", 0)
        de = record.get("target_dark_elixir", 0)
        dur = int(record.get("duration_seconds", 60))

        out_color = "#22c55e" if outcome == "VICTORY" else "#ef4444"

        ctk.CTkLabel(row_frame, text=f"#{index}", width=35, font=ctk.CTkFont(size=10, weight="bold"), text_color="#a1a1aa").pack(side="left", padx=2, pady=3)
        ctk.CTkLabel(row_frame, text=t_time, width=65, font=ctk.CTkFont(size=10), text_color="#cbd5e1").pack(side="left", padx=2, pady=3)
        ctk.CTkLabel(row_frame, text=outcome, width=80, font=ctk.CTkFont(size=10, weight="bold"), text_color=out_color).pack(side="left", padx=2, pady=3)
        ctk.CTkLabel(row_frame, text=f"+{g:,}", width=110, font=ctk.CTkFont(size=10, weight="bold"), text_color="#fbbf24").pack(side="left", padx=2, pady=3)
        ctk.CTkLabel(row_frame, text=f"+{e:,}", width=110, font=ctk.CTkFont(size=10, weight="bold"), text_color="#d946ef").pack(side="left", padx=2, pady=3)
        ctk.CTkLabel(row_frame, text=f"+{de:,}", width=90, font=ctk.CTkFont(size=10, weight="bold"), text_color="#38bdf8").pack(side="left", padx=2, pady=3)
        ctk.CTkLabel(row_frame, text=f"{dur}s", width=70, font=ctk.CTkFont(size=10), text_color="#94a3b8").pack(side="left", padx=2, pady=3)

    # -----------------------------------------------------------------
    # DYNAMIC TROOP, SIEGE & SPELL MANAGEMENT
    # -----------------------------------------------------------------
    def _on_carousel_troop_clicked(self, troop_name: str) -> None:
        """Triggered when clicking a troop card in the horizontal ribbon."""
        for row in self.troop_slot_rows:
            if row["unit_var"].get().lower().replace(" ", "") == troop_name.lower().replace(" ", ""):
                try:
                    curr = int(row["qty_var"].get())
                except ValueError:
                    curr = 0
                new_q = curr + 5
                row["qty_var"].set(str(new_q))
                row["en_var"].set(True)
                if "slider_q" in row:
                    row["slider_q"].set(min(100, new_q))
                self.log_event(f"Incremented troop quantity: {troop_name} (+5 -> {new_q})")
                return
        self._add_troop_slot(unit_name=troop_name, qty=15, enabled=True)
        self.log_event(f"Added troop slot from ribbon: {troop_name} (x15)")

    def _on_siege_card_clicked(self, siege_name: str) -> None:
        """Triggered when clicking a siege machine card in the horizontal ribbon."""
        self.siege_unit_var.set(siege_name)
        self._update_siege_icon_preview()
        self._update_siege_carousel_highlight()
        self.log_event(f"Equipped siege machine: {siege_name}")

    def _update_siege_carousel_highlight(self) -> None:
        if not hasattr(self, "siege_unit_var"):
            return
        current = self.siege_unit_var.get()
        if hasattr(self, "lbl_active_siege_badge"):
            self.lbl_active_siege_badge.configure(text=f"Active: {current}")
        for s_name, btn in getattr(self, "siege_carousel_buttons", {}).items():
            if s_name == current:
                btn.configure(fg_color="#1e293b", border_color="#0284c7", border_width=2, text_color="#38bdf8")
            else:
                btn.configure(fg_color="#222226", border_color="#27272a", border_width=0, text_color="#e2e8f0")

    def _on_carousel_spell_clicked(self, spell_name: str) -> None:
        """Triggered when clicking a spell card in the horizontal ribbon."""
        for row in self.spell_slot_rows:
            if row["unit_var"].get().lower().replace(" ", "") == spell_name.lower().replace(" ", ""):
                try:
                    curr = int(row["qty_var"].get())
                except ValueError:
                    curr = 0
                new_q = min(12, curr + 1)
                row["qty_var"].set(str(new_q))
                if "slider_q" in row:
                    row["slider_q"].set(new_q)
                row["en_var"].set(True)
                self.log_event(f"Incremented spell quantity: {spell_name} (x{new_q})")
                return
        default_qty = 11 if "totem" in spell_name.lower() else 1
        self._add_spell_slot(spell_name=spell_name, qty=default_qty, enabled=True)
        self.log_event(f"Added spell slot from ribbon: {spell_name} (x{default_qty})")

    def _add_troop_slot(self, unit_name: str = "Valkyrie", qty: int = 20, prio_idx: Optional[int] = None, enabled: bool = True) -> None:
        idx = len(self.troop_slot_rows)
        row_frame = ctk.CTkFrame(self.troop_rows_frame, fg_color="#18181b", corner_radius=6)
        row_frame.pack(fill="x", padx=2, pady=2)
        row_frame.grid_columnconfigure(2, weight=0)
        row_frame.grid_columnconfigure(7, weight=1)

        en_var = ctk.BooleanVar(value=enabled)
        matched_unit = unit_name
        for opt in TROOP_OPTIONS:
            if opt.lower().replace(" ", "").replace("_", "") == unit_name.lower().replace(" ", "").replace("_", ""):
                matched_unit = opt
                break
        unit_var = ctk.StringVar(value=matched_unit)
        qty_var = ctk.StringVar(value=str(qty))

        if prio_idx is None:
            prio_idx = min(len(PRIORITY_OPTIONS) - 1, idx)
        prio_var = ctk.StringVar(value=PRIORITY_OPTIONS[prio_idx])

        chk_t = ctk.CTkCheckBox(
            row_frame,
            text=f"Slot {idx+1}:",
            variable=en_var,
            width=65,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._update_army_capacity_display
        )
        chk_t.grid(row=0, column=0, padx=(6, 2), pady=3, sticky="w")

        lbl_ico = ctk.CTkLabel(row_frame, text="", width=36, height=48)
        lbl_ico.grid(row=0, column=1, padx=3, pady=3)

        lbl_sp_hint = ctk.CTkLabel(row_frame, text="", font=ctk.CTkFont(size=10, weight="bold"), text_color="#38bdf8", width=58)

        row_data = {
            "frame": row_frame,
            "en_var": en_var,
            "unit_var": unit_var,
            "qty_var": qty_var,
            "prio_var": prio_var,
            "chk_t": chk_t,
            "lbl_ico": lbl_ico,
            "lbl_sp_hint": lbl_sp_hint,
        }

        opt_t = ctk.CTkOptionMenu(
            row_frame,
            variable=unit_var,
            values=TROOP_OPTIONS,
            width=150,
            height=26,
            command=lambda v, r=row_data: (self._update_troop_row_icon(r), self._update_army_capacity_display())
        )
        opt_t.grid(row=0, column=2, padx=3, pady=3, sticky="w")

        lbl_q = ctk.CTkLabel(row_frame, text="Qty:", font=ctk.CTkFont(size=11))
        lbl_q.grid(row=0, column=3, padx=(4, 2), pady=3, sticky="e")

        # Stepper [-]
        btn_minus = ctk.CTkButton(
            row_frame,
            text="-",
            width=22,
            height=24,
            fg_color="#27272a",
            hover_color="#3f3f46",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda r=row_data: self._step_troop_qty(r, -1)
        )
        btn_minus.grid(row=0, column=4, padx=1, pady=3)

        ent_q = ctk.CTkEntry(row_frame, textvariable=qty_var, width=38, height=24, justify="center")
        ent_q.grid(row=0, column=5, padx=1, pady=3)

        # Stepper [+]
        btn_plus = ctk.CTkButton(
            row_frame,
            text="+",
            width=22,
            height=24,
            fg_color="#27272a",
            hover_color="#3f3f46",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda r=row_data: self._step_troop_qty(r, +1)
        )
        btn_plus.grid(row=0, column=6, padx=1, pady=3)

        # Space label (e.g. (352 sp))
        lbl_sp_hint.grid(row=0, column=7, padx=(2, 4), pady=3)

        # Slider [===O===] (1 to 120)
        init_val = min(120, max(1, qty))
        slider_q = ctk.CTkSlider(
            row_frame,
            from_=1,
            to=120,
            number_of_steps=119,
            width=90,
            height=16,
            command=lambda val, r=row_data: self._on_troop_slider_changed(r, val)
        )
        slider_q.set(init_val)
        slider_q.grid(row=0, column=8, padx=(4, 6), pady=3)

        opt_p = ctk.CTkOptionMenu(
            row_frame,
            variable=prio_var,
            values=PRIORITY_OPTIONS,
            width=130,
            height=26
        )
        opt_p.grid(row=0, column=9, padx=3, pady=3, sticky="e")

        btn_del = ctk.CTkButton(
            row_frame,
            text="✕",
            width=26,
            height=26,
            fg_color="#3f3f46",
            hover_color="#ef4444",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda r=row_data: self._remove_troop_slot(r)
        )
        btn_del.grid(row=0, column=10, padx=(3, 6), pady=3)

        row_data["opt_t"] = opt_t
        row_data["btn_minus"] = btn_minus
        row_data["ent_q"] = ent_q
        row_data["btn_plus"] = btn_plus
        row_data["slider_q"] = slider_q
        row_data["opt_p"] = opt_p
        row_data["btn_del"] = btn_del

        # Bidirectional sync: entry -> slider & capacity display
        qty_var.trace_add("write", lambda *a, r=row_data: self._sync_troop_entry_to_slider(r))

        self.troop_slot_rows.append(row_data)
        self._update_troop_row_icon(row_data)
        self._rebuild_troop_slot_indices()

        if hasattr(self, "_bind_mousewheel_recursive"):
            self._bind_mousewheel_recursive(row_frame)
        self._update_army_capacity_display()

    def _step_troop_qty(self, row_data: dict, delta: int) -> None:
        try:
            curr = int(row_data["qty_var"].get())
        except ValueError:
            curr = 1
        new_v = max(1, min(120, curr + delta))
        row_data["qty_var"].set(str(new_v))
        row_data["slider_q"].set(new_v)
        self._update_army_capacity_display()

    def _on_troop_slider_changed(self, row_data: dict, val: float) -> None:
        new_v = int(round(float(val)))
        if row_data["qty_var"].get() != str(new_v):
            row_data["qty_var"].set(str(new_v))
        self._update_army_capacity_display()

    def _sync_troop_entry_to_slider(self, row_data: dict) -> None:
        val_str = row_data["qty_var"].get().strip()
        if val_str.isdigit():
            v = int(val_str)
            if 1 <= v <= 120:
                row_data["slider_q"].set(v)
        self._update_army_capacity_display()

    def _remove_troop_slot(self, row_data: dict) -> None:
        if row_data in self.troop_slot_rows:
            self.troop_slot_rows.remove(row_data)
            row_data["frame"].destroy()
            self._rebuild_troop_slot_indices()
            self._update_army_capacity_display()

    def _rebuild_troop_slot_indices(self) -> None:
        for idx, row in enumerate(self.troop_slot_rows):
            row["chk_t"].configure(text=f"Slot {idx+1}:")

    def _update_troop_row_icon(self, row_data: dict) -> None:
        unit_name = row_data["unit_var"].get()
        rel_path = UNIT_ASSET_MAP.get(unit_name)
        img = self._load_ctk_image(rel_path, size=(36, 48)) if rel_path else None
        row_data["lbl_ico"].configure(image=img)

    def _update_troop_icon_preview(self, idx: int) -> None:
        if 0 <= idx < len(self.troop_slot_rows):
            self._update_troop_row_icon(self.troop_slot_rows[idx])

    def _add_spell_slot(self, spell_name: str = "Earthquake", qty: int = 11, enabled: bool = True) -> None:
        idx = len(self.spell_slot_rows)
        row_frame = ctk.CTkFrame(self.spell_rows_frame, fg_color="#18181b", corner_radius=6)
        row_frame.pack(fill="x", padx=2, pady=2)
        row_frame.grid_columnconfigure(2, weight=0)
        row_frame.grid_columnconfigure(7, weight=1)

        en_var = ctk.BooleanVar(value=enabled)
        matched_sp = spell_name
        for opt in SPELL_OPTIONS:
            if opt.lower().replace(" ", "").replace("_", "") == spell_name.lower().replace(" ", "").replace("_", ""):
                matched_sp = opt
                break
        unit_var = ctk.StringVar(value=matched_sp)
        qty_var = ctk.StringVar(value=str(qty))

        chk_sp = ctk.CTkCheckBox(
            row_frame,
            text=f"Spell {idx+1}:",
            variable=en_var,
            width=75,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._update_army_capacity_display
        )
        chk_sp.grid(row=0, column=0, padx=(6, 2), pady=3, sticky="w")

        lbl_ico = ctk.CTkLabel(row_frame, text="", width=46, height=48)
        lbl_ico.grid(row=0, column=1, padx=3, pady=3)

        lbl_sp_hint = ctk.CTkLabel(row_frame, text="", font=ctk.CTkFont(size=10, weight="bold"), text_color="#c084fc", width=58)

        row_data = {
            "frame": row_frame,
            "en_var": en_var,
            "unit_var": unit_var,
            "qty_var": qty_var,
            "chk_sp": chk_sp,
            "lbl_ico": lbl_ico,
            "lbl_sp_hint": lbl_sp_hint,
        }

        opt_sp = ctk.CTkOptionMenu(
            row_frame,
            variable=unit_var,
            values=SPELL_OPTIONS,
            width=150,
            height=26,
            command=lambda v, r=row_data: (self._update_spell_row_icon(r), self._update_army_capacity_display())
        )
        opt_sp.grid(row=0, column=2, padx=3, pady=3, sticky="w")

        lbl_q = ctk.CTkLabel(row_frame, text="Qty:", font=ctk.CTkFont(size=11))
        lbl_q.grid(row=0, column=3, padx=(4, 2), pady=3, sticky="e")

        btn_minus = ctk.CTkButton(
            row_frame,
            text="-",
            width=22,
            height=24,
            fg_color="#27272a",
            hover_color="#3f3f46",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda r=row_data: self._step_spell_qty(r, -1)
        )
        btn_minus.grid(row=0, column=4, padx=1, pady=3)

        ent_q = ctk.CTkEntry(row_frame, textvariable=qty_var, width=38, height=24, justify="center")
        ent_q.grid(row=0, column=5, padx=1, pady=3)

        btn_plus = ctk.CTkButton(
            row_frame,
            text="+",
            width=22,
            height=24,
            fg_color="#27272a",
            hover_color="#3f3f46",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda r=row_data: self._step_spell_qty(r, +1)
        )
        btn_plus.grid(row=0, column=6, padx=1, pady=3)

        # Space label (e.g. (11 sp))
        lbl_sp_hint.grid(row=0, column=7, padx=(2, 4), pady=3)

        # Slider [===O===] (1 to 12)
        init_sp_val = min(12, max(1, qty))
        slider_q = ctk.CTkSlider(
            row_frame,
            from_=1,
            to=12,
            number_of_steps=11,
            width=90,
            height=16,
            command=lambda val, r=row_data: self._on_spell_slider_changed(r, val)
        )
        slider_q.set(init_sp_val)
        slider_q.grid(row=0, column=8, padx=(4, 6), pady=3)

        btn_del = ctk.CTkButton(
            row_frame,
            text="✕",
            width=26,
            height=26,
            fg_color="#3f3f46",
            hover_color="#ef4444",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda r=row_data: self._remove_spell_slot(r)
        )
        btn_del.grid(row=0, column=9, padx=(3, 6), pady=3)

        row_data["opt_sp"] = opt_sp
        row_data["btn_minus"] = btn_minus
        row_data["ent_q"] = ent_q
        row_data["btn_plus"] = btn_plus
        row_data["slider_q"] = slider_q
        row_data["btn_del"] = btn_del

        qty_var.trace_add("write", lambda *a, r=row_data: self._sync_spell_entry_to_slider(r))

        self.spell_slot_rows.append(row_data)
        self._update_spell_row_icon(row_data)
        self._rebuild_spell_slot_indices()

        if hasattr(self, "_bind_mousewheel_recursive"):
            self._bind_mousewheel_recursive(row_frame)
        self._update_army_capacity_display()

    def _step_spell_qty(self, row_data: dict, delta: int) -> None:
        try:
            curr = int(row_data["qty_var"].get())
        except ValueError:
            curr = 1
        new_v = max(1, min(12, curr + delta))
        row_data["qty_var"].set(str(new_v))
        row_data["slider_q"].set(new_v)
        self._update_army_capacity_display()

    def _on_spell_slider_changed(self, row_data: dict, val: float) -> None:
        new_v = int(round(float(val)))
        if row_data["qty_var"].get() != str(new_v):
            row_data["qty_var"].set(str(new_v))
        self._update_army_capacity_display()

    def _sync_spell_entry_to_slider(self, row_data: dict) -> None:
        val_str = row_data["qty_var"].get().strip()
        if val_str.isdigit():
            v = int(val_str)
            if 1 <= v <= 12:
                row_data["slider_q"].set(v)
        self._update_army_capacity_display()

    def _remove_spell_slot(self, row_data: dict) -> None:
        if row_data in self.spell_slot_rows:
            self.spell_slot_rows.remove(row_data)
            row_data["frame"].destroy()
            self._rebuild_spell_slot_indices()
            self._update_army_capacity_display()

    def _rebuild_spell_slot_indices(self) -> None:
        for idx, row in enumerate(self.spell_slot_rows):
            row["chk_sp"].configure(text=f"Spell {idx+1}:")

    def _update_spell_row_icon(self, row_data: dict) -> None:
        spell_name = row_data["unit_var"].get()
        rel_path = UNIT_ASSET_MAP.get(spell_name)
        img = self._load_ctk_image(rel_path, size=(46, 48)) if rel_path else None
        row_data["lbl_ico"].configure(image=img)

    def _update_spell_icon_preview(self, idx: int = 0) -> None:
        if 0 <= idx < len(self.spell_slot_rows):
            self._update_spell_row_icon(self.spell_slot_rows[idx])

    def _update_siege_icon_preview(self) -> None:
        if hasattr(self, "lbl_siege_icon") and hasattr(self, "siege_unit_var"):
            unit_name = self.siege_unit_var.get()
            rel_path = UNIT_ASSET_MAP.get(unit_name)
            img = self._load_ctk_image(rel_path, size=(40, 50)) if rel_path else None
            self.lbl_siege_icon.configure(image=img)
        self._update_siege_carousel_highlight()

    def _on_hero_toggled(self, h_key: str) -> None:
        """Enforces max 4 active heroes with FIFO auto-deselection rule."""
        is_checked = self.hero_vars[h_key].get()
        if is_checked:
            if h_key not in self._selected_heroes_order:
                self._selected_heroes_order.append(h_key)
            if len(self._selected_heroes_order) > 4:
                # FIFO: deselect the oldest selected hero
                oldest = self._selected_heroes_order.pop(0)
                self.hero_vars[oldest].set(False)
                self._update_hero_card_style(oldest, False)
            self._update_hero_card_style(h_key, True)
        else:
            if h_key in self._selected_heroes_order:
                self._selected_heroes_order.remove(h_key)
            self._update_hero_card_style(h_key, False)
        self._update_hero_header_text()

    def _update_hero_card_style(self, h_key: str, is_active: bool) -> None:
        if hasattr(self, "hero_frames") and h_key in self.hero_frames:
            f = self.hero_frames[h_key]
            if is_active:
                f.configure(fg_color="#1e293b", border_color="#0284c7", border_width=2)
            else:
                f.configure(fg_color="#18181b", border_color="#27272a", border_width=1)

    def _update_hero_header_text(self) -> None:
        if hasattr(self, "lbl_h_hdr") and hasattr(self, "_selected_heroes_order"):
            count = len(self._selected_heroes_order)
            color = "#10b981" if count == 4 else ("#f59e0b" if count > 0 else "#ef4444")
            self.lbl_h_hdr.configure(
                text=safe_text(f"👑 Active Heroes ({count}/4 Selected for Battle — Max 4 Allowed):"),
                text_color=color
            )

    # Backward compatibility properties for any scripts or test suites
    @property
    def troop_enabled_vars(self):
        return [r["en_var"] for r in self.troop_slot_rows]

    @property
    def troop_unit_vars(self):
        return [r["unit_var"] for r in self.troop_slot_rows]

    @property
    def troop_qty_vars(self):
        return [r["qty_var"] for r in self.troop_slot_rows]

    @property
    def troop_prio_vars(self):
        return [r["prio_var"] for r in self.troop_slot_rows]

    @property
    def troop_icon_labels(self):
        return [r["lbl_ico"] for r in self.troop_slot_rows]

    @property
    def spell_unit_var(self):
        return self.spell_slot_rows[0]["unit_var"] if self.spell_slot_rows else ctk.StringVar(value="Earthquake")

    @property
    def spell_qty_var(self):
        return self.spell_slot_rows[0]["qty_var"] if self.spell_slot_rows else ctk.StringVar(value="11")

    @property
    def lbl_spell_icon(self):
        return self.spell_slot_rows[0]["lbl_ico"] if self.spell_slot_rows else ctk.CTkLabel(self, text="")

    def _save_army_configuration(self) -> None:
        try:
            from src.persistence.config_manager import (
                TroopUnitConfig, SiegeUnitConfig, HeroUnitConfig, SpellUnitConfig, ArmyConfig
            )

            troops = []
            for idx, row in enumerate(self.troop_slot_rows):
                en = row["en_var"].get()
                uname = row["unit_var"].get()
                prio_str = row["prio_var"].get()
                try:
                    qty = int(row["qty_var"].get())
                except ValueError:
                    qty = 10
                prio_digits = re.findall(r"\d+", prio_str)
                prio = int(prio_digits[0]) if prio_digits else idx + 1
                norm_name = uname.lower().replace(" ", "_").replace(".", "")
                troops.append(TroopUnitConfig(name=norm_name, expected_quantity=qty, priority=prio, enabled=en))

            s_name = self.siege_unit_var.get()
            s_en = self.chk_siege_var.get()
            s_norm = s_name.lower().replace(" ", "_")
            siege = [SiegeUnitConfig(name=s_norm, expected_quantity=1, enabled=s_en)]

            heroes = []
            for h_key, h_var in self.hero_vars.items():
                heroes.append(HeroUnitConfig(name=h_key, enabled=h_var.get()))
            active_hero_count = len([h for h in heroes if h.enabled])

            try:
                ability_delay = float(self.ent_army_ability_delay_var.get())
            except ValueError:
                ability_delay = 6.0

            sp_en = self.chk_spells_var.get()
            spells = []
            for row in self.spell_slot_rows:
                row_en = row["en_var"].get() and sp_en
                sp_name = row["unit_var"].get()
                try:
                    sp_qty = int(row["qty_var"].get())
                except ValueError:
                    sp_qty = 1
                sp_norm = sp_name.lower().replace(" ", "_")
                spells.append(SpellUnitConfig(name=sp_norm, expected_quantity=sp_qty, enabled=row_en))

            new_army = ArmyConfig(
                troops=troops,
                spells=spells,
                siege=siege,
                heroes=heroes,
                clan_castle=False
            )
            self.config.deployment.army = new_army
            self.config.deployment.hero_count = active_hero_count
            self.config.deployment.hero_ability_delay_seconds = ability_delay
            self.config.deployment.deploy_siege = s_en
            self.config.deployment.deploy_spells = sp_en

            if hasattr(self, "ent_troop_cap_var"):
                try:
                    self.config.deployment.max_troop_capacity = int(self.ent_troop_cap_var.get())
                except ValueError:
                    pass
            if hasattr(self, "ent_spell_cap_var"):
                try:
                    self.config.deployment.max_spell_capacity = int(self.ent_spell_cap_var.get())
                except ValueError:
                    pass

            self.config_manager.save(self.config)

            if self.controller is not None and getattr(self.controller, "state_machine", None) is not None:
                self.controller.state_machine.config = self.config

            active_t_names = [t.name for t in troops if t.enabled]
            active_sp_names = [f"{sp.name}x{sp.expected_quantity}" for sp in spells if sp.enabled]
            self.log_event(f"Army saved: Troops={active_t_names}, Siege={'ON' if s_en else 'OFF'}, Heroes={active_hero_count}, Spells={active_sp_names}")
            self.notifier.announce("Army configuration saved and applied", chime="accept")

            # When army changes, schedule first-attack verification prompt
            if hasattr(self, "controller") and self.controller:
                self.controller.request_deployment_verification()
            if hasattr(self, "lbl_ribbon_status"):
                self.lbl_ribbon_status.configure(text="🧪 Verification Scheduled (Next Attack)", text_color="#38bdf8")
        except Exception as e:
            logger.error(f"Failed to save army configuration: {e}", exc_info=True)
            self.log_event(f"Error saving army configuration: {e}")

    def _on_gui_ribbon_mode_changed(self, mode_str: str) -> None:
        mode = "compact" if "compact" in mode_str.lower() else "large"
        locked = self.chk_lock_ribbon_var.get()
        self.controller.set_ribbon_mode(mode, locked=locked)
        self._update_ribbon_status_ui(locked, mode)
        self.log_event(f"Deployment ribbon mode changed to: {mode.upper()} (Locked={locked})")

    def _on_gui_toggle_lock_ribbon(self) -> None:
        locked = self.chk_lock_ribbon_var.get()
        mode = "compact" if "compact" in self.seg_ribbon_mode.get().lower() else "large"
        self.controller.set_ribbon_mode(mode, locked=locked)
        self._update_ribbon_status_ui(locked, mode)
        self.log_event(f"Ribbon calibration lock set to: {locked}")

    def _on_gui_request_verification(self) -> None:
        self.controller.request_deployment_verification()
        if hasattr(self, "lbl_ribbon_status"):
            self.lbl_ribbon_status.configure(
                text="🧪 Verification Pending Next Attack",
                text_color="#38bdf8"
            )
        self.log_event("Verification scheduled: The bot will pause after the next battle to confirm deployment.")
        self.notifier.announce("Verification scheduled for next battle.", chime="ok")

    def _update_ribbon_status_ui(self, locked: bool, mode: str) -> None:
        if not hasattr(self, "lbl_ribbon_status"):
            return
        if locked:
            disp = f"🔒 Locked ({mode.title()} Bar)"
            color = "#22c55e"
        else:
            disp = "🔓 Dynamic Auto-Detect"
            color = "#f59e0b"
        self.lbl_ribbon_status.configure(text=disp, text_color=color)

    def _show_deployment_verification_prompt(self, payload: dict) -> None:
        """
        Displays a user confirmation modal dialog after an attack to verify if troops,
        siege, heroes, and spells deployed properly. If confirmed, locks calibration.
        """
        dialog = ctk.CTkToplevel(self)
        dialog.title("Attack Completed — Deployment Verification")
        dialog.geometry("560x320")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        try:
            x = self.winfo_x() + (self.winfo_width() - 560) // 2
            y = self.winfo_y() + (self.winfo_height() - 320) // 2
            dialog.geometry(f"+{x}+{y}")
        except Exception:
            pass

        content = ctk.CTkFrame(dialog, fg_color="#18181b", corner_radius=10)
        content.pack(fill="both", expand=True, padx=12, pady=12)

        lbl_title = ctk.CTkLabel(
            content,
            text=safe_text("⚔️ First Attack Completed — Verify Deployment"),
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_title.pack(pady=(12, 6))

        outcome = payload.get("outcome", "BATTLE")
        loot_g = payload.get("actual_gold", 0)
        loot_e = payload.get("actual_elixir", 0)
        mode = payload.get("ribbon_mode", "compact").upper()

        info_text = (
            f"Battle Outcome: {outcome} | Loot Collected: {loot_g:,} Gold, {loot_e:,} Elixir\n"
            f"Active Deployment Bar Mode: {mode}\n\n"
            "Did ALL units deploy correctly (Troops, Siege, King, Queen, Warden, Duke, Spells)?\n"
            "• If YES: Deployment slot coordinates will be permanently locked so the bot\n"
            "  deploys in this exact pattern every single battle without scenery errors.\n"
            "• If NO: The session remains paused so you can adjust settings or toggle bar size."
        )

        lbl_msg = ctk.CTkLabel(
            content,
            text=info_text,
            font=ctk.CTkFont(size=11),
            text_color="#e2e8f0",
            justify="center"
        )
        lbl_msg.pack(padx=16, pady=(0, 16))

        btn_box = ctk.CTkFrame(content, fg_color="transparent")
        btn_box.pack(pady=(6, 12))

        def on_confirm_yes():
            self.controller.confirm_deployment_verification(True)
            self._update_ribbon_status_ui(True, "compact")
            self.log_event("Deployment verified and locked by user. Farming resumed.")
            dialog.destroy()

        def on_confirm_no():
            self.controller.confirm_deployment_verification(False)
            self.log_event("User reported deployment issue. Farming remains paused for inspection.")
            self.main_tabview.set(safe_text("⚔️ Army Setup & Sequencer"))
            dialog.destroy()

        btn_yes = ctk.CTkButton(
            btn_box,
            text="✓ Yes, Deployed Correctly (Lock & Resume)",
            width=230,
            height=34,
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=on_confirm_yes
        )
        btn_yes.pack(side="left", padx=8)

        btn_no = ctk.CTkButton(
            btn_box,
            text="✗ No, Issue Detected (Keep Paused)",
            width=210,
            height=34,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=on_confirm_no
        )
        btn_no.pack(side="left", padx=8)

    def _toggle_farming_session(self) -> None:
        """Starts or stops farming session for the active village mode."""
        if self.current_village == "builder_base":
            if self.bb_controller:
                if self.bb_controller.is_running:
                    self.bb_controller.stop_session()
                else:
                    self._on_bb_timer_change()
                    self.bb_controller.start_session()
        else:
            if self.controller.is_running:
                logger.info("Stopping session via GUI Start/Stop button...")
                self.controller.stop_session()
            else:
                logger.info("Starting session via GUI Start/Stop button...")
                self.controller.start_session()

    def _handle_pause_action(self) -> None:
        """Pauses or resumes the active session."""
        if self.current_village == "builder_base" and self.bb_controller:
            self.bb_controller.toggle_pause()
        else:
            self.controller.toggle_pause()

    def _handle_stop_action(self) -> None:
        """Stops the active session immediately."""
        if self.current_village == "builder_base" and self.bb_controller:
            self.bb_controller.stop_session()
        else:
            self.controller.stop_session()

    def _bind_game_window_interactive(self) -> None:
        """Prompts user to switch to Clash of Clans and binds directly."""
        self.log_event("Switching / focusing Clash of Clans window in 2 seconds...")
        self.notifier.announce("Please bring Clash of Clans to the foreground now", chime="ok", toast_title="Binding Window")

        def worker():
            time.sleep(2.0)
            geom = self.controller.calibrator.bind_foreground_window()
            self.after(0, lambda: self._on_window_bound(geom))

        threading.Thread(target=worker, daemon=True).start()

    def _on_window_bound(self, geom) -> None:
        title = geom.window_title or "Primary Screen"
        w = geom.window_width
        h = geom.window_height
        x = geom.window_x
        y = geom.window_y
        self.lbl_win_status.configure(
            text=f"Window: {title[:20]} ({w}x{h})",
            text_color="#22c55e"
        )
        self.log_event(f"🎯 Bound to Window: '{title}' ({w}x{h} at [{x}, {y}])")
        self.notifier.announce(f"Bound to {title}", chime="accept", toast_title="Window Bound")

    def _update_window_binding_ui(self) -> None:
        geom = self.controller.calibrator.calibrate_live_window()
        title = geom.window_title or "Primary Screen"
        w = geom.window_width
        h = geom.window_height
        color = "#22c55e" if geom.hwnd else "#38bdf8"
        self.lbl_win_status.configure(
            text=f"Window: {title[:20]} ({w}x{h})",
            text_color=color
        )
        self.log_event(f"Detected Window: '{title}' ({w}x{h})")

    def _create_stat_card(self, parent, col: int, title: str, initial_val: str) -> ctk.CTkLabel:
        card = ctk.CTkFrame(parent, fg_color="#18181b", corner_radius=8)
        card.grid(row=0, column=col, padx=8, pady=8, sticky="ew")
        lbl_t = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11), text_color="#8e8e93")
        lbl_t.pack(pady=(6, 0))
        lbl_v = ctk.CTkLabel(card, text=initial_val, font=ctk.CTkFont(size=15, weight="bold"))
        lbl_v.pack(pady=(0, 6))
        return lbl_v

    def log_event(self, msg: str) -> None:
        clean_msg = safe_text(msg)
        ts = datetime.now().strftime("%H:%M:%S")
        self.txt_logs.insert("end", f"[{ts}] {clean_msg}\n")
        self.txt_logs.see("end")

    def _update_fixed_count_visibility(self) -> None:
        if self.mode_var.get() == "fixed_attacks":
            self.fixed_count_frame.grid()
        else:
            self.fixed_count_frame.grid_remove()

    def _increment_attack_count(self) -> None:
        try:
            val = int(self.attack_count_var.get()) + 1
        except ValueError:
            val = 5
        self.attack_count_var.set(str(val))
        self._save_attack_count()

    def _decrement_attack_count(self) -> None:
        try:
            val = max(1, int(self.attack_count_var.get()) - 1)
        except ValueError:
            val = 5
        self.attack_count_var.set(str(val))
        self._save_attack_count()

    def _save_attack_count(self) -> None:
        try:
            val = max(1, int(self.attack_count_var.get()))
        except ValueError:
            val = 5
            self.attack_count_var.set("5")
        self.config.fixed_attack_count = val
        self.config_manager.save(self.config)
        self.log_event(f"Fixed attack limit set to {val} attacks.")

    def _on_mode_change(self, mode: str) -> None:
        self.config.mode = mode
        self._update_fixed_count_visibility()
        self.config_manager.save(self.config)
        self.log_event(f"Mode changed to: {mode}")
        self.notifier.announce(f"Mode changed to {mode}", chime="ok")

    def _on_voice_toggle(self) -> None:
        enabled = self.voice_var.get()
        self.notifier.voice_enabled = enabled
        self.notifier.sounds_enabled = enabled
        self.notifier.toasts_enabled = enabled
        if hasattr(self.controller, "state_machine"):
            self.controller.state_machine.notifier.voice_enabled = enabled
            self.controller.state_machine.notifier.sounds_enabled = enabled
            self.controller.state_machine.notifier.toasts_enabled = enabled
        self.log_event(f"Voice & Toast Alerts: {'ENABLED' if enabled else 'DISABLED'}")

    def _on_state_update(self, state: UIState, game_state: GameState) -> None:
        state_str = str(state.value) if hasattr(state, "value") else str(state)
        self.after(0, lambda: self._update_state_ui(state_str, game_state))

    def _update_state_ui(self, state_str: str, game_state: GameState) -> None:
        self.state_pill.configure(text=state_str)
        if "BATTLE" in state_str:
            self.state_pill.configure(text_color="#ef4444")
        elif "HOME" in state_str:
            self.state_pill.configure(text_color="#22c55e")
        elif "PAUSED" in state_str:
            self.state_pill.configure(text_color="#eab308")
        else:
            self.state_pill.configure(text_color="#3b82f6")

    def _on_village_mode_change(self, mode_str: str) -> None:
        """Switches between Home Village and Builder Base attack modes with graceful error handling."""
        if "Builder Base" in mode_str:
            try:
                from builderBase.src.bb_config_manager import BBConfigManager
                from builderBase.src.bb_session_controller import BBSessionController

                if self.bb_config_manager is None:
                    self.bb_config_manager = BBConfigManager()
                if self.bb_controller is None:
                    self.bb_controller = BBSessionController(
                        config_manager=self.bb_config_manager,
                        state_callback=self._on_bb_state_update,
                        notifier=self.notifier,
                        calibrator=self.controller.calibrator
                    )

                self.current_village = "builder_base"
                self.home_controls_frame.grid_forget()
                self.bb_controls_frame.grid(row=4, column=0, sticky="ew")

                # Sync BB UI fields
                bb_cfg = self.bb_config_manager.config
                self.bb_mode_var.set(bb_cfg.mode)
                self.bb_attack_count_var.set(str(bb_cfg.fixed_attack_count))
                self.bb_ent_timer_var.set(f"{bb_cfg.exit.combat_timer_seconds}s")
                self._update_bb_fixed_count_visibility()
                self._on_bb_timer_change()

                self.log_event("Switched to [🔨 Builder Base] attack mode.")
                self.notifier.announce("Builder Base mode active", chime="ok")
                self.state_pill.configure(text="BB_IDLE", text_color="#3b82f6")

            except Exception as e:
                logger.error(f"Could not load Builder Base module: {e}", exc_info=True)
                self.village_mode_var.set("🏰 Home Village")
                self.current_village = "home_village"
                self.home_controls_frame.grid(row=4, column=0, sticky="ew")
                self.bb_controls_frame.grid_forget()
                self.log_event(f"⚠️ Builder Base module not available ({e}). Reverting to Home Village.")
                self.notifier.announce("Builder Base module not found", chime="warning")
        else:
            self.current_village = "home_village"
            self.bb_controls_frame.grid_forget()
            self.home_controls_frame.grid(row=4, column=0, sticky="ew")
            self.log_event("Switched to [🏰 Home Village] attack mode.")
            self.notifier.announce("Home Village mode active", chime="ok")
            self.state_pill.configure(text="IDLE", text_color="#3b82f6")

    def _on_bb_state_update(self, state, details: dict) -> None:
        state_str = state.name if hasattr(state, "name") else str(state)
        self.after(0, lambda: self._update_bb_state_ui(state_str, details))

    def _update_bb_state_ui(self, state_str: str, details: dict) -> None:
        self.state_pill.configure(text=state_str)
        if "BATTLE" in state_str:
            self.state_pill.configure(text_color="#ef4444")
        elif "HOME" in state_str:
            self.state_pill.configure(text_color="#22c55e")
        elif "RESULT" in state_str:
            self.state_pill.configure(text_color="#a855f7")
        else:
            self.state_pill.configure(text_color="#3b82f6")

    def _on_bb_mode_change(self, mode: str) -> None:
        if self.bb_config_manager:
            self.bb_config_manager.config.mode = mode
            self.bb_config_manager.save(self.bb_config_manager.config)
        self._update_bb_fixed_count_visibility()
        self.log_event(f"Builder Base mode set to: {mode}")

    def _update_bb_fixed_count_visibility(self) -> None:
        if self.bb_mode_var.get() == "fixed_attacks":
            self.bb_fixed_count_frame.grid()
        else:
            self.bb_fixed_count_frame.grid_remove()

    def _increment_bb_attack_count(self) -> None:
        try:
            val = int(self.bb_attack_count_var.get()) + 1
        except ValueError:
            val = 5
        self.bb_attack_count_var.set(str(val))
        self._save_bb_attack_count()

    def _decrement_bb_attack_count(self) -> None:
        try:
            val = max(1, int(self.bb_attack_count_var.get()) - 1)
        except ValueError:
            val = 5
        self.bb_attack_count_var.set(str(val))
        self._save_bb_attack_count()

    def _save_bb_attack_count(self) -> None:
        try:
            val = max(1, int(self.bb_attack_count_var.get()))
        except ValueError:
            val = 5
            self.bb_attack_count_var.set("5")
        if self.bb_config_manager:
            self.bb_config_manager.config.fixed_attack_count = val
            self.bb_config_manager.save(self.bb_config_manager.config)
        self.log_event(f"Builder Base target attack limit set to {val} attacks.")

    def _on_bb_timer_change(self, *args) -> None:
        raw = self.bb_ent_timer_var.get()
        parsed_secs = self._parse_timer_input(raw)
        if self.bb_config_manager:
            self.bb_config_manager.config.exit.combat_timer_seconds = parsed_secs
            self.bb_config_manager.save(self.bb_config_manager.config)

        mins, secs = divmod(parsed_secs, 60)
        formatted = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"

        if hasattr(self, "lbl_bb_timer_summary"):
            self.lbl_bb_timer_summary.configure(
                text=f"Exit limit: {formatted} (Max allowed: 2m 30s)"
            )

    def _poll_ui_telemetry(self) -> None:
        # 1. Builder Base Active Telemetry
        if self.current_village == "builder_base" and self.bb_controller:
            sm = self.bb_controller.state_machine
            self.lbl_stat_attacks.configure(text=str(sm.attacks_completed))
            self.lbl_stat_skips.configure(text="N/A (Direct)")

            is_mac = sys.platform == "darwin"
            start_key = "⌘R" if is_mac else "F8"
            pause_key = "⌘P" if is_mac else "F9"

            if self.bb_controller.is_running:
                self.btn_start.configure(
                    text=f"⏹ STOP BB BOT ({start_key})",
                    fg_color="#dc2626",
                    hover_color="#b91c1c"
                )
                if hasattr(self, "btn_hdr_start"):
                    self.btn_hdr_start.configure(
                        text=f"⏹ Stop ({start_key})",
                        fg_color="#dc2626",
                        hover_color="#b91c1c"
                    )
                bb_paused = self.bb_controller.is_paused
                self.btn_pause.configure(
                    state="normal",
                    text=f"▶ RESUME ({pause_key})" if bb_paused else f"⏸ PAUSE ({pause_key})",
                    fg_color="#10b981" if bb_paused else "#eab308",
                    text_color="#ffffff" if bb_paused else "#000000",
                    hover_color="#059669" if bb_paused else "#ca8a04"
                )
                if hasattr(self, "btn_hdr_pause"):
                    self.btn_hdr_pause.configure(
                        state="normal",
                        text="▶ Resume" if bb_paused else "⏸ Pause",
                        fg_color="#10b981" if bb_paused else "#eab308",
                        text_color="#ffffff" if bb_paused else "#000000",
                        hover_color="#059669" if bb_paused else "#ca8a04"
                    )
            else:
                self.btn_start.configure(
                    text=f"▶ START BB BOT ({start_key})",
                    fg_color="#16a34a",
                    hover_color="#15803d"
                )
                if hasattr(self, "btn_hdr_start"):
                    self.btn_hdr_start.configure(
                        text=f"▶ Start ({start_key})",
                        fg_color="#16a34a",
                        hover_color="#15803d"
                    )
                self.btn_pause.configure(
                    state="disabled",
                    text=f"⏸ PAUSE ({pause_key})",
                    fg_color="#3f3f46",
                    text_color="#9ca3af"
                )
                if hasattr(self, "btn_hdr_pause"):
                    self.btn_hdr_pause.configure(
                        state="disabled",
                        text="⏸ Pause",
                        fg_color="#3f3f46",
                        text_color="#9ca3af"
                    )

        # 2. Home Village Active Telemetry
        else:
            is_mac = sys.platform == "darwin"
            start_key = "⌘R" if is_mac else "F8"
            pause_key = "⌘P" if is_mac else "F9"

            if hasattr(self.controller, "get_loot_stats"):
                loot_stats = self.controller.get_loot_stats()
                self.lbl_stat_attacks.configure(text=str(loot_stats.get("attacks_completed", 0)))
                self.lbl_stat_skips.configure(text=str(loot_stats.get("skips", 0)))
            elif hasattr(self.controller, "state_machine") and self.controller.state_machine:
                sm = self.controller.state_machine
                self.lbl_stat_attacks.configure(text=str(sm.attacks_completed))
                self.lbl_stat_skips.configure(text=str(sm.consecutive_skips))
            elif hasattr(self.controller, "db") and getattr(self.controller, "session_id", None):
                try:
                    stats = self.controller.db.get_session_stats(self.controller.session_id)
                    if stats:
                        self.lbl_stat_attacks.configure(text=str(stats.get("total_attacks", 0)))
                        self.lbl_stat_skips.configure(text=str(stats.get("total_skips", 0)))
                except Exception:
                    pass

            # Dynamic Start / Stop Button Updates for Home Village
            if self.controller.is_running:
                self.btn_start.configure(
                    text=f"⏹ STOP FARMING ({start_key})",
                    fg_color="#dc2626",
                    hover_color="#b91c1c"
                )
                if hasattr(self, "btn_hdr_start"):
                    self.btn_hdr_start.configure(
                        text=f"⏹ Stop ({start_key})",
                        fg_color="#dc2626",
                        hover_color="#b91c1c"
                    )
                is_p = self.controller.is_paused
                self.btn_pause.configure(
                    state="normal",
                    text=f"▶ RESUME ({pause_key})" if is_p else f"⏸ PAUSE ({pause_key})",
                    fg_color="#10b981" if is_p else "#eab308",
                    text_color="#ffffff" if is_p else "#000000",
                    hover_color="#059669" if is_p else "#ca8a04"
                )
                if hasattr(self, "btn_hdr_pause"):
                    self.btn_hdr_pause.configure(
                        state="normal",
                        text="▶ Resume" if is_p else "⏸ Pause",
                        fg_color="#10b981" if is_p else "#eab308",
                        text_color="#ffffff" if is_p else "#000000",
                        hover_color="#059669" if is_p else "#ca8a04"
                    )
            else:
                self.btn_start.configure(
                    text=f"▶ START FARMING ({start_key})",
                    fg_color="#16a34a",
                    hover_color="#15803d"
                )
                if hasattr(self, "btn_hdr_start"):
                    self.btn_hdr_start.configure(
                        text=f"▶ Start ({start_key})",
                        fg_color="#16a34a",
                        hover_color="#15803d"
                    )
                self.btn_pause.configure(
                    state="disabled",
                    text=f"⏸ PAUSE ({pause_key})",
                    fg_color="#3f3f46",
                    text_color="#9ca3af"
                )
                if hasattr(self, "btn_hdr_pause"):
                    self.btn_hdr_pause.configure(
                        state="disabled",
                        text="⏸ Pause",
                        fg_color="#3f3f46",
                        text_color="#9ca3af"
                    )

        # 3. Loot Collected Telemetry (Screenshot-Verified)
        if self.current_village == "builder_base":
            self.lbl_loot_gold_total.configure(text="N/A (BB)")
            self.lbl_loot_gold_last.configure(text="Last: -")
            self.lbl_loot_elixir_total.configure(text="N/A (BB)")
            self.lbl_loot_elixir_last.configure(text="Last: -")
            self.lbl_loot_de_total.configure(text="N/A (BB)")
            self.lbl_loot_de_last.configure(text="Last: -")
        else:
            loot_stats = self.controller.get_loot_stats() if hasattr(self.controller, "get_loot_stats") else {}
            g_tot = loot_stats.get("total_gold", 0)
            e_tot = loot_stats.get("total_elixir", 0)
            de_tot = loot_stats.get("total_dark_elixir", 0)
            g_last = loot_stats.get("last_gold", 0)
            e_last = loot_stats.get("last_elixir", 0)
            de_last = loot_stats.get("last_dark_elixir", 0)

            self.lbl_loot_gold_total.configure(text=f"{g_tot:,}")
            self.lbl_loot_gold_last.configure(text=f"Last: +{g_last:,}")
            self.lbl_loot_elixir_total.configure(text=f"{e_tot:,}")
            self.lbl_loot_elixir_last.configure(text=f"Last: +{e_last:,}")
            self.lbl_loot_de_total.configure(text=f"{de_tot:,}")
            self.lbl_loot_de_last.configure(text=f"Last: +{de_last:,}")

            # Update Attack History tab cards & table
            if hasattr(self, "lbl_hist_gold"):
                self.lbl_hist_gold.configure(text=f"{g_tot:,}")
                self.lbl_hist_elixir.configure(text=f"{e_tot:,}")
                self.lbl_hist_de.configure(text=f"{de_tot:,}")
                self.lbl_hist_attacks.configure(text=str(loot_stats.get("attacks_completed", 0)))

            if hasattr(self, "hist_scroll_rows") and hasattr(self.controller, "attack_history_records"):
                records = self.controller.attack_history_records
                while self.rendered_history_count < len(records):
                    rec = records[self.rendered_history_count]
                    self._render_history_table_row(self.rendered_history_count + 1, rec)
                    self.rendered_history_count += 1

        self.after(400, self._poll_ui_telemetry)

    def _fmt_k(self, amt: int) -> str:
        if amt >= 1_000_000:
            return f"{amt / 1_000_000:.1f}M"
        elif amt >= 1_000:
            return f"{amt // 1_000}K"
        return str(amt)

    def _on_loot_criteria_change(self, *args) -> None:
        try:
            self.config.target.watch_gold = self.chk_gold_var.get()
            self.config.target.min_gold = max(0, int(self.ent_gold_var.get().replace(",", "").replace("_", "").replace(" ", "")))
        except (ValueError, AttributeError):
            pass

        try:
            self.config.target.watch_elixir = self.chk_elixir_var.get()
            self.config.target.min_elixir = max(0, int(self.ent_elixir_var.get().replace(",", "").replace("_", "").replace(" ", "")))
        except (ValueError, AttributeError):
            pass

        try:
            self.config.target.watch_dark_elixir = self.chk_de_var.get()
            self.config.target.min_dark_elixir = max(0, int(self.ent_de_var.get().replace(",", "").replace("_", "").replace(" ", "")))
        except (ValueError, AttributeError):
            pass

        try:
            self.config.target.watch_combined = self.chk_comb_var.get()
            self.config.target.min_combined = max(0, int(self.ent_comb_var.get().replace(",", "").replace("_", "").replace(" ", "")))
        except (ValueError, AttributeError):
            pass

        de_as_gate = self.chk_de_gate_var.get() if hasattr(self, "chk_de_gate_var") else True
        self.config.target.dark_elixir_as_gate = de_as_gate

        mode_val = "AND" if "AND" in self.match_mode_var.get() else "OR"
        self.config.target.match_mode = mode_val

        primary_parts = []
        if self.config.target.watch_gold:
            primary_parts.append(f"Gold >= {self._fmt_k(self.config.target.min_gold)}")
        if self.config.target.watch_elixir:
            primary_parts.append(f"Elixir >= {self._fmt_k(self.config.target.min_elixir)}")
        if self.config.target.watch_combined:
            primary_parts.append(f"Combined(G+E) >= {self._fmt_k(self.config.target.min_combined)}")

        de_part = f"DE >= {self._fmt_k(self.config.target.min_dark_elixir)}" if self.config.target.watch_dark_elixir else None

        if primary_parts or de_part:
            if mode_val == "AND":
                all_p = list(primary_parts)
                if de_part:
                    all_p.append(de_part)
                summary = f"Filter: {' AND '.join(all_p)}"
            else:  # "OR"
                if de_as_gate and de_part and primary_parts:
                    summary = f"Filter: ({' OR '.join(primary_parts)}) AND {de_part}"
                else:
                    all_p = list(primary_parts)
                    if de_part:
                        all_p.append(de_part)
                    warn = " ⚠️ (DE alone attacks base!)" if (de_part and primary_parts) else ""
                    summary = f"Filter: {' OR '.join(all_p)}{warn}"
        else:
            summary = "Filter: (All bases accepted - no criteria selected)"

        if hasattr(self, "lbl_active_criteria"):
            self.lbl_active_criteria.configure(text=summary)

        self.config_manager.save(self.config)

        if hasattr(self.controller, "state_machine") and hasattr(self.controller.state_machine, "target_evaluator"):
            self.controller.state_machine.target_evaluator.config = self.config.target

    def _parse_timer_input(self, text: str) -> int:
        import re
        text = text.strip().lower()
        m_ms = re.search(r"(\d+)\s*m\s*(\d+)?\s*s?", text)
        if m_ms:
            mins = int(m_ms.group(1))
            secs = int(m_ms.group(2)) if m_ms.group(2) else 0
            total = mins * 60 + secs
            return max(5, min(150, total))

        m_colon = re.search(r"(\d+)\s*:\s*(\d+)", text)
        if m_colon:
            mins = int(m_colon.group(1))
            secs = int(m_colon.group(2))
            total = mins * 60 + secs
            return max(5, min(150, total))

        m_sec = re.sub(r"[^\d]", "", text)
        if m_sec:
            total = int(m_sec)
            return max(5, min(150, total))

        return 60

    def _update_exit_summary_text(self, timer_val: int, dmg_val: float, loot_val: float) -> None:
        mins, secs = divmod(timer_val, 60)
        formatted = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
        if hasattr(self, "lbl_exit_summary"):
            self.lbl_exit_summary.configure(
                text=f"Exit limit: {formatted}\nDmg: {int(dmg_val)}%, Loot: {int(loot_val)}%"
            )

    def _on_exit_criteria_change(self, *args) -> None:
        # Timer
        raw_timer = self.ent_timer_var.get()
        parsed_secs = self._parse_timer_input(raw_timer)
        self.config.exit.combat_timer_seconds = parsed_secs

        # Damage
        try:
            parsed_dmg = float(self.ent_damage_var.get())
        except ValueError:
            parsed_dmg = 60.0
        self.config.exit.damage_threshold_percent = parsed_dmg

        # Loot
        try:
            parsed_loot = float(self.ent_loot_var.get())
        except ValueError:
            parsed_loot = 65.0
        self.config.exit.loot_collected_percent = parsed_loot

        self._update_exit_summary_text(parsed_secs, parsed_dmg, parsed_loot)
        self.config_manager.save(self.config)
        if hasattr(self.controller, "state_machine") and hasattr(self.controller.state_machine, "exit_evaluator"):
            self.controller.state_machine.exit_evaluator.config = self.config.exit

    def _parse_resource_limit_input(self, text: str) -> int:
        """Robustly parses resource limits: handles 350k, 31m, 350,000, 0, or blank."""
        if not text:
            return 0
        raw = str(text).strip().lower().replace(" ", "")
        if raw in ("0", "none", "off", "disable", "disabled", "-", ""):
            return 0
        try:
            if raw.endswith("m"):
                val_str = raw[:-1].replace(",", "")
                return int(float(val_str) * 1_000_000)
            elif raw.endswith("k"):
                val_str = raw[:-1].replace(",", "")
                return int(float(val_str) * 1_000)

            clean = re.sub(r"[^\d]", "", raw)
            return int(clean) if clean else 0
        except Exception:
            return 0

    def _format_compact_num(self, val: int) -> str:
        if val >= 1_000_000:
            m = val / 1_000_000
            return f"{m:.1f}M".replace(".0M", "M")
        elif val >= 1_000:
            k = val / 1_000
            return f"{k:.1f}K".replace(".0K", "K")
        return str(val)

    def _format_storage_entry(self, entry_type: str) -> None:
        """Formats the input entry with comma thousands separators on blur/enter without overwriting active edits."""
        try:
            if entry_type == "gold":
                val = self._parse_resource_limit_input(self.ent_max_gold_var.get())
                self.ent_max_gold_var.set(f"{val:,}")
            elif entry_type == "elixir":
                val = self._parse_resource_limit_input(self.ent_max_elixir_var.get())
                self.ent_max_elixir_var.set(f"{val:,}")
            elif entry_type == "de":
                val = self._parse_resource_limit_input(self.ent_max_de_var.get())
                self.ent_max_de_var.set(f"{val:,}")
        except Exception:
            pass

    def _commit_storage_entry(self, entry_type: str) -> None:
        self._format_storage_entry(entry_type)
        self._on_storage_limit_change()

    def _on_storage_limit_change(self, *args) -> None:
        enabled = self.chk_storage_limit_var.get()
        gold_val = self._parse_resource_limit_input(self.ent_max_gold_var.get())
        elixir_val = self._parse_resource_limit_input(self.ent_max_elixir_var.get())
        de_val = self._parse_resource_limit_input(self.ent_max_de_var.get())

        chk_g = self.chk_storage_gold_var.get() if hasattr(self, "chk_storage_gold_var") else True
        chk_e = self.chk_storage_elixir_var.get() if hasattr(self, "chk_storage_elixir_var") else True
        chk_de = self.chk_storage_de_var.get() if hasattr(self, "chk_storage_de_var") else False
        mode_val = "AND" if hasattr(self, "storage_match_mode_var") and "AND" in self.storage_match_mode_var.get() else "OR"

        self.config.storage_limit.enabled = enabled
        self.config.storage_limit.stop_when_full = enabled
        self.config.storage_limit.match_mode = mode_val
        self.config.storage_limit.max_gold = gold_val
        self.config.storage_limit.max_elixir = elixir_val
        self.config.storage_limit.max_dark_elixir = de_val
        self.config.storage_limit.check_gold = chk_g and (gold_val > 0)
        self.config.storage_limit.check_elixir = chk_e and (elixir_val > 0)
        self.config.storage_limit.check_dark_elixir = chk_de and (de_val > 0)
        self.config_manager.save(self.config)

        # Update summary status label
        parts = []
        if chk_g and gold_val > 0:
            parts.append(f"Gold {self._format_compact_num(gold_val)}")
        if chk_e and elixir_val > 0:
            parts.append(f"Elixir {self._format_compact_num(elixir_val)}")
        if chk_de and de_val > 0:
            parts.append(f"DE {self._format_compact_num(de_val)}")

        delim = " & " if mode_val == "AND" else " | "
        status = f"Stop if [{mode_val}]: {delim.join(parts)}" if parts else "Stop limit: (No active resource selected)"
        if not enabled:
            status += " (Disabled)"

        if hasattr(self, "lbl_storage_summary"):
            self.lbl_storage_summary.configure(
                text=status,
                text_color="#38bdf8" if enabled else "#71717a"
            )

    def _on_deployment_settings_change(self, *args) -> None:
        if not hasattr(self, "hero_count_var") or not hasattr(self, "ent_ability_delay_var"):
            return

        raw_hero_str = self.hero_count_var.get()
        if "auto" in raw_hero_str.lower():
            h_count = -1
        else:
            try:
                h_count = int(raw_hero_str.split()[0])
            except (ValueError, IndexError):
                h_count = 2

        try:
            delay_sec = float(self.ent_ability_delay_var.get())
            delay_sec = max(1.0, min(60.0, delay_sec))
        except ValueError:
            delay_sec = 6.0

        self.config.deployment.hero_count = h_count
        self.config.deployment.hero_ability_delay_seconds = delay_sec
        self.config_manager.save(self.config)

        if hasattr(self, "lbl_deploy_summary"):
            if h_count == -1:
                layout_desc = f"Auto-Detect ribbon slots | Ability: {delay_sec:.1f}s"
            elif h_count == 0:
                layout_desc = f"S0=Troop, S1=Siege, S2=Spells (0 Heroes) | Ability: {delay_sec:.1f}s"
            elif h_count == 1:
                layout_desc = f"S0=Troop, S1=Siege, S2=Hero, S3=Spells | Ability: {delay_sec:.1f}s"
            elif h_count == 2:
                layout_desc = f"S0=Troop, S1=Siege, S2-3=Heroes, S4=Spells | Ability: {delay_sec:.1f}s"
            elif h_count == 3:
                layout_desc = f"S0=Troop, S1=Siege, S2-4=Heroes, S5=Spells | Ability: {delay_sec:.1f}s"
            else:
                layout_desc = f"S0=Troop, S1=Siege, S2-5=Heroes, S6=Spells | Ability: {delay_sec:.1f}s"

            self.lbl_deploy_summary.configure(
                text=layout_desc,
                text_color="#38bdf8"
            )

    def _start_session(self) -> None:
        self._on_loot_criteria_change()
        self._on_exit_criteria_change()
        self._on_storage_limit_change()
        self._on_deployment_settings_change()
        self.controller.calibrator.calibrate_live_window()
        self.controller.calibrator.focus_game_window()

        exec_type = "LIVE WIN32 EXECUTION" if sys.platform == "win32" else "LIVE MOUSE EXECUTION"
        self.log_event(f"Starting farming session in mode '{self.config.mode}' [{exec_type}]...")
        self.controller.start_session()

    def _open_audit_log(self) -> None:
        from src.utils.audit_logger import AUDIT_LOG_FILE
        try:
            if os.path.exists(AUDIT_LOG_FILE):
                if sys.platform == "win32":
                    os.startfile(AUDIT_LOG_FILE)
                elif sys.platform == "darwin":
                    subprocess.run(["open", AUDIT_LOG_FILE])
                else:
                    subprocess.run(["xdg-open", AUDIT_LOG_FILE])
            else:
                self.log_event("[AUDIT LOG] Log file will be generated on starting session.")
        except Exception as e:
            self.log_event(f"[AUDIT LOG ERROR] Could not open log: {e}")

    def _open_bb_audit_log(self) -> None:
        from builderBase.src.bb_audit_logger import BB_AUDIT_LOG_FILE
        try:
            if os.path.exists(BB_AUDIT_LOG_FILE):
                if sys.platform == "win32":
                    os.startfile(BB_AUDIT_LOG_FILE)
                elif sys.platform == "darwin":
                    subprocess.run(["open", BB_AUDIT_LOG_FILE])
                else:
                    subprocess.run(["xdg-open", BB_AUDIT_LOG_FILE])
            else:
                self.log_event("[BB AUDIT LOG] Log file will be generated on starting Builder Base attack.")
        except Exception as e:
            self.log_event(f"[BB AUDIT LOG ERROR] Could not open log: {e}")
