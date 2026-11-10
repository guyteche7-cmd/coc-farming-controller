"""
Desktop Control Dashboard (CustomTkinter GUI).
Provides real-time state visualization, foreground window binding & protection,
voice & audio alerts, target rule editing, and live session telemetry.
"""

from __future__ import annotations
import os
import sys
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

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class DashboardApp(ctk.CTk):
    """Main CustomTkinter application window."""

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.config = config_manager.config
        self.db = DatabaseManager(self.config.logging.database_file)
        self.notifier = Notifier(voice_enabled=True, sounds_enabled=True)

        self.title("CoC Auto Farm Dashboard — Version 1 (AI Hybrid Edition)")
        self.geometry("1020x700")
        self.minsize(920, 620)

        self.controller = SessionController(
            config_manager=self.config_manager,
            db_manager=self.db,
            state_callback=self._on_state_update,
            notifier=self.notifier,
            window_bind_callback=lambda: self.after(0, self._bind_game_window_interactive),
            hotkey_start_callback=lambda: self.after(0, self._toggle_farming_session),
            hotkey_pause_callback=lambda: self.after(0, self._handle_pause_action),
            hotkey_stop_callback=lambda: self.after(0, self._handle_stop_action)
        )

        self._build_ui()
        self._poll_ui_telemetry()

        # macOS Tkinter initial render workaround (forces Cocoa window server to paint canvas)
        if sys.platform == "darwin":
            self.after(100, self._macos_force_paint)

        # Pre-warm vision models (EasyOCR, YOLOv8) in background so session start is instant
        threading.Thread(target=self._prewarm_vision_models, daemon=True).start()

    def _macos_force_paint(self) -> None:
        """Forces macOS Cocoa window server to redraw widgets instead of staying blank/black."""
        try:
            self.update_idletasks()
            self.lift()
            self.attributes('-topmost', True)
            self.after(20, lambda: self.attributes('-topmost', False))
            # Minor geometry toggle to trigger Cocoa buffer swap
            w, h = self.winfo_width(), self.winfo_height()
            if w > 10 and h > 10:
                self.geometry(f"{w+1}x{h}")
                self.after(10, lambda: self.geometry(f"{w}x{h}"))
        except Exception as e:
            logger.debug(f"macOS paint trigger: {e}")

    def _prewarm_vision_models(self) -> None:
        try:
            logger.info("Pre-warming fast glyph and template perception models in background...")
            from src.vision.glyph_reader import SupercellGlyphReader
            reader = SupercellGlyphReader()
            logger.info(f"Deterministic Glyph perception engine pre-warmed successfully ({len(reader.templates)} digit templates loaded).")
        except Exception as e:
            logger.warning(f"Vision pre-warm notice: {e}")

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0, minsize=320)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ----------------- SIDEBAR (Controls & Config - Scrollable) -----------------
        sidebar = ctk.CTkScrollableFrame(
            self,
            width=300,
            corner_radius=10,
            fg_color="#1e1e24",
            scrollbar_button_color="#3f3f46",
            scrollbar_button_hover_color="#52525b"
        )
        sidebar.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        sidebar.grid_columnconfigure(0, weight=1)


        # App Title
        lbl_title = ctk.CTkLabel(sidebar, text="⚔️ CoC Farm Controller", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_title.grid(row=0, column=0, pady=(16, 2), padx=16, sticky="w")
        lbl_sub = ctk.CTkLabel(sidebar, text="Google Play Games on PC (Client Area Mode)", font=ctk.CTkFont(size=12), text_color="#9ca3af")
        lbl_sub.grid(row=1, column=0, pady=(0, 10), padx=16, sticky="w")

        # Village Switcher: [ 🏰 Home Village ]  [ 🔨 Builder Base ]
        self.current_village = "home_village"
        self.bb_config_manager = None
        self.bb_controller = None

        self.village_mode_var = ctk.StringVar(value="🏰 Home Village")
        self.village_switcher = ctk.CTkSegmentedButton(
            sidebar,
            values=["🏰 Home Village", "🔨 Builder Base"],
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

        btn_bind_win = ctk.CTkButton(
            win_card,
            text="🎯 Bind Game Window (F7)",
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

        lbl_loot_hdr = ctk.CTkLabel(loot_card, text="🎯 Target Loot Criteria:", font=ctk.CTkFont(size=13, weight="bold"))
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

        # 4. Combined (Gold + Elixir) Checkbox & Entry
        self.chk_comb_var = ctk.BooleanVar(value=getattr(self.config.target, "watch_combined", True))
        self.chk_comb = ctk.CTkCheckBox(loot_card, text="Combined (G+E):", variable=self.chk_comb_var, command=self._on_loot_criteria_change, font=ctk.CTkFont(size=12))
        self.chk_comb.grid(row=5, column=0, padx=(10, 4), pady=2, sticky="w")
        self.ent_comb_var = ctk.StringVar(value=str(getattr(self.config.target, "min_combined", 1000000)))
        self.ent_comb = ctk.CTkEntry(loot_card, textvariable=self.ent_comb_var, width=95, height=24, justify="right")
        self.ent_comb.grid(row=5, column=1, padx=(4, 10), pady=2, sticky="e")
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
        self.lbl_active_criteria.grid(row=6, column=0, columnspan=2, padx=10, pady=(2, 6), sticky="w")
        self._on_loot_criteria_change()

        # Combat Exit Criteria Card (Home)
        exit_card = ctk.CTkFrame(self.home_controls_frame, fg_color="#18181b", corner_radius=8)
        exit_card.grid(row=4, column=0, padx=16, pady=(4, 6), sticky="ew")
        exit_card.grid_columnconfigure(0, weight=1)
        exit_card.grid_columnconfigure(1, weight=0)

        lbl_exit_title = ctk.CTkLabel(exit_card, text=" Combat Exit Criteria:", font=ctk.CTkFont(size=12, weight="bold"))
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

        lbl_storage_title = ctk.CTkLabel(storage_card, text="🛑 Storage Limit (Auto-Stop):", font=ctk.CTkFont(size=12, weight="bold"))
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

        # Army Deployment & Heroes Configuration Card (Home)
        deploy_card = ctk.CTkFrame(self.home_controls_frame, fg_color="#18181b", corner_radius=8)
        deploy_card.grid(row=6, column=0, padx=16, pady=(4, 8), sticky="ew")
        deploy_card.grid_columnconfigure(0, weight=1)
        deploy_card.grid_columnconfigure(1, weight=0)

        lbl_deploy_title = ctk.CTkLabel(deploy_card, text="⚔ Army & Heroes Setup:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_deploy_title.grid(row=0, column=0, columnspan=2, padx=(10, 4), pady=(6, 2), sticky="w")

        # 1. Hero Count Selector
        lbl_heroes = ctk.CTkLabel(deploy_card, text="Heroes in Army:", font=ctk.CTkFont(size=12))
        lbl_heroes.grid(row=1, column=0, padx=(16, 4), pady=2, sticky="w")

        curr_hero_count = getattr(self.config.deployment, "hero_count", 2)
        hero_options = ["Auto-Detect", "0 Heroes", "1 Hero", "2 Heroes", "3 Heroes", "4 Heroes"]
        if curr_hero_count == -1:
            init_hero_str = "Auto-Detect"
        else:
            init_hero_str = f"{curr_hero_count} Heroes" if curr_hero_count != 1 else "1 Hero"
            if init_hero_str not in hero_options:
                init_hero_str = "2 Heroes"

        self.hero_count_var = ctk.StringVar(value=init_hero_str)
        self.opt_heroes = ctk.CTkOptionMenu(
            deploy_card,
            variable=self.hero_count_var,
            values=hero_options,
            command=lambda v: self._on_deployment_settings_change(),
            width=115,
            height=24
        )
        self.opt_heroes.grid(row=1, column=1, padx=(4, 10), pady=2, sticky="e")

        # 2. Hero Ability Delay (User requested 6s)
        lbl_ability_delay = ctk.CTkLabel(deploy_card, text="Ability Delay (s):", font=ctk.CTkFont(size=12))
        lbl_ability_delay.grid(row=2, column=0, padx=(16, 4), pady=2, sticky="w")
        init_ability_delay = getattr(self.config.deployment, "hero_ability_delay_seconds", 6.0)
        self.ent_ability_delay_var = ctk.StringVar(value=f"{init_ability_delay:.1f}".rstrip('0').rstrip('.'))
        self.ent_ability_delay = ctk.CTkEntry(deploy_card, textvariable=self.ent_ability_delay_var, width=60, height=24, justify="center")
        self.ent_ability_delay.grid(row=2, column=1, padx=(4, 10), pady=2, sticky="e")
        self.ent_ability_delay.bind("<FocusOut>", lambda e: self._on_deployment_settings_change())
        self.ent_ability_delay.bind("<Return>", lambda e: self._on_deployment_settings_change())

        # Summary label
        self.lbl_deploy_summary = ctk.CTkLabel(
            deploy_card,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="#a1a1aa"
        )
        self.lbl_deploy_summary.grid(row=3, column=0, columnspan=2, padx=10, pady=(2, 6), sticky="w")
        self._on_deployment_settings_change()

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
            text="📍 Deployment Strategy:\n• Point: Top-Right Perimeter (0.776, 0.102)\n• Dynamic BH Army Slots (1..8 auto-scan)\n• Hero Ability Auto-Cadence (Battle Machine)\n• Multi-Stage 1 & 2 Auto-Advance",
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

        lbl_bb_timer_title = ctk.CTkLabel(bb_timer_card, text="⏱️ BB Combat Exit Timer:", font=ctk.CTkFont(size=12, weight="bold"))
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
            text="📋 Open Builder Base Audit Log",
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
        sw_voice = ctk.CTkSwitch(sidebar, text="Voice & Windows Toast Alerts", variable=self.voice_var, command=self._on_voice_toggle)
        sw_voice.grid(row=5, column=0, padx=16, pady=6, sticky="w")

        # Primary Action Buttons
        self.btn_start = ctk.CTkButton(
            sidebar,
            text="▶ START FARMING (F8)",
            height=42,
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._toggle_farming_session
        )
        self.btn_start.grid(row=6, column=0, padx=16, pady=(12, 6), sticky="ew")

        self.btn_pause = ctk.CTkButton(
            sidebar,
            text="⏸ PAUSE (F9)",
            height=34,
            fg_color="#3f3f46",
            text_color="#9ca3af",
            state="disabled",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._handle_pause_action
        )
        self.btn_pause.grid(row=7, column=0, padx=16, pady=3, sticky="ew")

        self.btn_stop = ctk.CTkButton(
            sidebar,
            text="🛑 EMERGENCY STOP (F10)",
            height=34,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._handle_stop_action
        )
        self.btn_stop.grid(row=8, column=0, padx=16, pady=(3, 6), sticky="ew")

        btn_audit = ctk.CTkButton(
            sidebar,
            text="📋 Open Decision Audit Log",
            height=28,
            fg_color="#27272a",
            hover_color="#3f3f46",
            font=ctk.CTkFont(size=12),
            command=self._open_audit_log
        )
        btn_audit.grid(row=9, column=0, padx=16, pady=(0, 14), sticky="ew")




        # ----------------- MAIN VIEW (Telemetry & Feed) -----------------
        main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#18181b")
        main_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(3, weight=1)

        # Header with State, Shortcuts & Mode badges
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=16, pady=(14, 10), sticky="ew")

        lbl_state_title = ctk.CTkLabel(header_frame, text="Active State:", font=ctk.CTkFont(size=14))
        lbl_state_title.pack(side="left", padx=(0, 8))

        self.state_pill = ctk.CTkLabel(
            header_frame,
            text="IDLE / READY",
            fg_color="#27272a",
            corner_radius=8,
            padx=12,
            pady=4,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#22c55e"
        )
        self.state_pill.pack(side="left")

        # Quick Help & Shortcuts (Moved directly beside Active State)
        lbl_shortcuts = ctk.CTkLabel(
            header_frame,
            text="⌨ [F7] Bind  •  [F8] Start/Stop  •  [F9] Pause  •  [F10] Safe Stop",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#27272a",
            text_color="#9ca3af",
            corner_radius=8,
            padx=12,
            pady=4
        )
        lbl_shortcuts.pack(side="left", padx=(12, 0))

        exec_pill_label = "⚡ LIVE WIN32 MOUSE EXECUTION" if sys.platform == "win32" else "⚡ LIVE MOUSE EXECUTION"
        self.mode_pill = ctk.CTkLabel(
            header_frame,
            text=exec_pill_label,
            fg_color="#dc2626",
            corner_radius=8,
            padx=12,
            pady=4,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffffff"
        )
        self.mode_pill.pack(side="right")

        # Telemetry Cards (Stats Grid - Attacks & Skips)
        telemetry_frame = ctk.CTkFrame(main_frame, fg_color="#222226", corner_radius=10)
        telemetry_frame.grid(row=1, column=0, padx=16, pady=(0, 8), sticky="ew")
        for i in range(2):
            telemetry_frame.grid_columnconfigure(i, weight=1)

        self.lbl_stat_attacks = self._create_stat_card(telemetry_frame, 0, "Attacks Completed", "0")
        self.lbl_stat_skips = self._create_stat_card(telemetry_frame, 1, "Skipped Bases", "0")

        # Loot Collected Section (Screenshot Verified)
        loot_section_frame = ctk.CTkFrame(main_frame, fg_color="#222226", corner_radius=10)
        loot_section_frame.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="ew")
        loot_section_frame.grid_columnconfigure(0, weight=1)
        loot_section_frame.grid_columnconfigure(1, weight=1)
        loot_section_frame.grid_columnconfigure(2, weight=1)

        # Header for Loot Section
        lbl_loot_hdr = ctk.CTkLabel(
            loot_section_frame,
            text="💰 Loot Collected (Screenshot Verified)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e4e4e7"
        )
        lbl_loot_hdr.grid(row=0, column=0, columnspan=3, padx=12, pady=(6, 2), sticky="w")

        # Gold Card
        gold_card = ctk.CTkFrame(loot_section_frame, fg_color="#18181b", corner_radius=8)
        gold_card.grid(row=1, column=0, padx=8, pady=(2, 8), sticky="ew")
        gold_card.grid_columnconfigure(0, weight=1)
        lbl_g_t = ctk.CTkLabel(gold_card, text="🟡 Gold", font=ctk.CTkFont(size=11, weight="bold"), text_color="#fbbf24")
        lbl_g_t.pack(pady=(4, 0))
        self.lbl_loot_gold_total = ctk.CTkLabel(gold_card, text="0", font=ctk.CTkFont(size=15, weight="bold"), text_color="#fef08a")
        self.lbl_loot_gold_total.pack(pady=(0, 0))
        self.lbl_loot_gold_last = ctk.CTkLabel(gold_card, text="Last: +0", font=ctk.CTkFont(size=10), text_color="#a1a1aa")
        self.lbl_loot_gold_last.pack(pady=(0, 4))

        # Elixir Card
        elixir_card = ctk.CTkFrame(loot_section_frame, fg_color="#18181b", corner_radius=8)
        elixir_card.grid(row=1, column=1, padx=8, pady=(2, 8), sticky="ew")
        elixir_card.grid_columnconfigure(0, weight=1)
        lbl_e_t = ctk.CTkLabel(elixir_card, text="🟣 Elixir", font=ctk.CTkFont(size=11, weight="bold"), text_color="#d946ef")
        lbl_e_t.pack(pady=(4, 0))
        self.lbl_loot_elixir_total = ctk.CTkLabel(elixir_card, text="0", font=ctk.CTkFont(size=15, weight="bold"), text_color="#f5d0fe")
        self.lbl_loot_elixir_total.pack(pady=(0, 0))
        self.lbl_loot_elixir_last = ctk.CTkLabel(elixir_card, text="Last: +0", font=ctk.CTkFont(size=10), text_color="#a1a1aa")
        self.lbl_loot_elixir_last.pack(pady=(0, 4))

        # Dark Elixir Card
        de_card = ctk.CTkFrame(loot_section_frame, fg_color="#18181b", corner_radius=8)
        de_card.grid(row=1, column=2, padx=8, pady=(2, 8), sticky="ew")
        de_card.grid_columnconfigure(0, weight=1)
        lbl_de_t = ctk.CTkLabel(de_card, text="⚫ Dark Elixir", font=ctk.CTkFont(size=11, weight="bold"), text_color="#38bdf8")
        lbl_de_t.pack(pady=(4, 0))
        self.lbl_loot_de_total = ctk.CTkLabel(de_card, text="0", font=ctk.CTkFont(size=15, weight="bold"), text_color="#e2e8f0")
        self.lbl_loot_de_total.pack(pady=(0, 0))
        self.lbl_loot_de_last = ctk.CTkLabel(de_card, text="Last: +0", font=ctk.CTkFont(size=10), text_color="#a1a1aa")
        self.lbl_loot_de_last.pack(pady=(0, 4))

        # Activity & Decision Feed
        feed_frame = ctk.CTkFrame(main_frame, fg_color="#222226", corner_radius=10)
        feed_frame.grid(row=3, column=0, padx=16, pady=(0, 14), sticky="nsew")
        feed_frame.grid_columnconfigure(0, weight=1)
        feed_frame.grid_rowconfigure(1, weight=1)

        lbl_feed_title = ctk.CTkLabel(feed_frame, text="📜 Activity & Decision Feed", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_feed_title.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        self.txt_logs = ctk.CTkTextbox(feed_frame, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#18181b")
        self.txt_logs.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")

        self.log_event("Application initialized. Ready to farm.")
        self.notifier.announce("Clash of Clans Farming Controller is ready", chime="ok")

        self._update_window_binding_ui()

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
        ts = datetime.now().strftime("%H:%M:%S")
        self.txt_logs.insert("end", f"[{ts}] {msg}\n")
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

            if self.bb_controller.is_running:
                self.btn_start.configure(
                    text="⏹ STOP BB BOT (F8)",
                    fg_color="#dc2626",
                    hover_color="#b91c1c"
                )
                self.btn_pause.configure(
                    state="normal",
                    text="▶ RESUME (F9)" if self.bb_controller.is_paused else "⏸ PAUSE (F9)",
                    fg_color="#10b981" if self.bb_controller.is_paused else "#eab308",
                    text_color="#ffffff" if self.bb_controller.is_paused else "#000000",
                    hover_color="#059669" if self.bb_controller.is_paused else "#ca8a04"
                )
            else:
                self.btn_start.configure(
                    text="▶ START BB BOT (F8)",
                    fg_color="#16a34a",
                    hover_color="#15803d"
                )
                self.btn_pause.configure(
                    state="disabled",
                    text="⏸ PAUSE (F9)",
                    fg_color="#3f3f46",
                    text_color="#9ca3af"
                )

        # 2. Home Village Active Telemetry
        else:
            if hasattr(self.controller, "state_machine") and self.controller.state_machine:
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
                    text="⏹ STOP FARMING (F8)",
                    fg_color="#dc2626",
                    hover_color="#b91c1c"
                )
                self.btn_pause.configure(
                    state="normal",
                    text="▶ RESUME (F9)" if self.controller.is_paused else "⏸ PAUSE (F9)",
                    fg_color="#10b981" if self.controller.is_paused else "#eab308",
                    text_color="#ffffff" if self.controller.is_paused else "#000000",
                    hover_color="#059669" if self.controller.is_paused else "#ca8a04"
                )
            else:
                self.btn_start.configure(
                    text="▶ START FARMING (F8)",
                    fg_color="#16a34a",
                    hover_color="#15803d"
                )
                self.btn_pause.configure(
                    state="disabled",
                    text="⏸ PAUSE (F9)",
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

        mode_val = "AND" if "AND" in self.match_mode_var.get() else "OR"
        self.config.target.match_mode = mode_val

        parts = []
        if self.config.target.watch_gold:
            parts.append(f"Gold >= {self._fmt_k(self.config.target.min_gold)}")
        if self.config.target.watch_elixir:
            parts.append(f"Elixir >= {self._fmt_k(self.config.target.min_elixir)}")
        if self.config.target.watch_dark_elixir:
            parts.append(f"DE >= {self._fmt_k(self.config.target.min_dark_elixir)}")
        if self.config.target.watch_combined:
            parts.append(f"Combined(G+E) >= {self._fmt_k(self.config.target.min_combined)}")

        if parts:
            joiner = f" {mode_val} "
            summary = f"Filter: {joiner.join(parts)}"
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
