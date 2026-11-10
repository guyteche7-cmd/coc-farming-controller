"""
Configuration Manager for Clash of Clans Farming Controller.
Validates and manages YAML configuration with typed Pydantic models.
"""

from __future__ import annotations
import os
import yaml
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class WindowConfig(BaseModel):
    title_pattern: str = "Google Play Games|Clash of Clans|BlueStacks|LDPlayer|Nox|MuMu|HD-Player"
    target_resolution: List[int] = Field(default_factory=lambda: [1920, 1080])
    expected_scaling: float = 1.0
    fullscreen_preferred: bool = True
    auto_focus: bool = True


class DarkElixirConfig(BaseModel):
    enabled: bool = False
    minimum: int = 10000


class TargetConfig(BaseModel):
    expression: str = "gold >= 500000 OR gold + elixir >= 1000000"
    match_mode: str = "OR" # "OR" (Match Any) or "AND" (Match All)
    watch_gold: bool = True
    min_gold: int = 500000
    watch_elixir: bool = False
    min_elixir: int = 500000
    watch_dark_elixir: bool = False
    min_dark_elixir: int = 5000
    watch_combined: bool = True
    min_combined: int = 1000000
    dark_elixir: DarkElixirConfig = Field(default_factory=DarkElixirConfig)
    max_consecutive_skips: int = 500
    skip_delay_seconds: float = 1.2
    min_ocr_confidence: float = 0.70



class TroopUnitConfig(BaseModel):
    name: str = "electro_dragon"
    expected_quantity: int = 16
    pattern: str = "line_distribute"


class SpellUnitConfig(BaseModel):
    name: str = "earthquake"
    expected_quantity: int = 11
    pattern: str = "randomized_targets"



class SiegeUnitConfig(BaseModel):
    name: str = "battle_blimp"
    expected_quantity: int = 1


class ArmyConfig(BaseModel):
    troops: List[TroopUnitConfig] = Field(default_factory=lambda: [TroopUnitConfig()])
    spells: List[SpellUnitConfig] = Field(default_factory=lambda: [SpellUnitConfig()])
    siege: List[SiegeUnitConfig] = Field(default_factory=lambda: [SiegeUnitConfig()])
    heroes: List[dict] = Field(default_factory=lambda: [
        {"name": "dragon_duke"},
        {"name": "archer_queen"},
        {"name": "grand_warden"},
        {"name": "minion_prince"}
    ])
    clan_castle: bool = False



class DeploymentConfig(BaseModel):
    selected_edge: Literal["top", "bottom", "left", "right"] = "top"
    tap_delay_seconds: float = 0.05
    hero_tap_delay_seconds: float = 0.3
    spell_tap_delay_seconds: float = 0.2
    army: ArmyConfig = Field(default_factory=ArmyConfig)
    hero_count: int = 2  # -1 for Auto-Detect, or 0, 1, 2, 3, 4
    hero_ability_delay_seconds: float = 6.0  # Reduced to 6s
    deploy_siege: bool = True
    deploy_spells: bool = True


class ExitConfig(BaseModel):
    combat_timer_seconds: int = 60
    max_combat_timer_seconds: int = 150
    damage_threshold_percent: float = 60.0
    loot_collected_percent: float = 65.0
    surrender_threshold_seconds: int = 60
    poll_interval_seconds: float = 1.0



class WallConfig(BaseModel):
    enabled: bool = False
    builder_required: bool = True
    storage_threshold_percent: float = 80.0
    prefer_batch_selection: bool = True
    max_upgrades_per_cycle: int = 50


class StorageLimitConfig(BaseModel):
    enabled: bool = True
    stop_when_full: bool = True
    match_mode: str = "OR"  # "OR" (Stop if Any selected full) or "AND" (Stop if All selected full)
    max_gold: int = 31000000
    max_elixir: int = 31000000
    max_dark_elixir: int = 350000
    check_gold: bool = True
    check_elixir: bool = True
    check_dark_elixir: bool = False
    full_threshold_percent: float = 98.0
    require_both_full: bool = True


class SafetyConfig(BaseModel):
    humanize_mouse_movement: bool = True
    emergency_stop_hotkey: str = "f10"
    pause_resume_hotkey: str = "f9"
    save_failure_screenshots: bool = True
    failure_screenshot_dir: str = "data/diagnostics"
    state_transition_timeout_seconds: float = 15.0


class LoggingConfig(BaseModel):
    level: str = "INFO"
    log_to_file: bool = True
    log_file: str = "data/coc_farming.log"
    database_file: str = "data/farming_history.db"


class AppConfig(BaseModel):
    version: int = 1
    mode: Literal["wall_plus_attack", "fixed_attacks", "infinite"] = "fixed_attacks"
    fixed_attack_count: int = 25
    window: WindowConfig = Field(default_factory=WindowConfig)
    target: TargetConfig = Field(default_factory=TargetConfig)
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig)
    exit: ExitConfig = Field(default_factory=ExitConfig)
    walls: WallConfig = Field(default_factory=WallConfig)
    storage_limit: StorageLimitConfig = Field(default_factory=StorageLimitConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class ConfigManager:
    """Manages loading, validation, and persisting of configuration files."""

    def __init__(self, config_path: Optional[str] = "config/default_config.yaml"):
        self.config_path = config_path or "config/default_config.yaml"
        self.config: AppConfig = self.load()

    def load(self) -> AppConfig:
        if not os.path.exists(self.config_path):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            config = AppConfig()
            self.save(config)
            return config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return AppConfig(**data)
        except Exception as e:
            print(f"Warning: Failed to load config from {self.config_path} ({e}). Using defaults.")
            return AppConfig()

    def save(self, config: Optional[AppConfig] = None) -> None:
        if config is not None:
            self.config = config
        data = self.config.model_dump()
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)


# Backward compatibility alias
RuntimeConfig = AppConfig

