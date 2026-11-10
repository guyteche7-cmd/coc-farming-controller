"""
Builder Base Configuration Manager.
Loads and saves configuration for the Builder Base automation module.
"""

from __future__ import annotations
import os
import yaml
import logging
from typing import List, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "bb_config.yaml")


class BBDeploymentConfig(BaseModel):
    default_point: List[float] = Field(default_factory=lambda: [0.776, 0.102])
    tap_delay_seconds: float = 0.1
    slot_delay_seconds: float = 0.3
    hero_ability_check_interval: float = 2.5


class BBExitConfig(BaseModel):
    combat_timer_seconds: int = 60
    max_combat_timer_seconds: int = 150
    auto_exit_on_destruction: bool = True


class BBSafetyConfig(BaseModel):
    humanize_mouse_movement: bool = True
    emergency_stop_hotkey: str = "f10"
    pause_resume_hotkey: str = "f9"


class BBConfig(BaseModel):
    mode: Literal["infinite", "fixed_attacks"] = "infinite"
    fixed_attack_count: int = 10
    deployment: BBDeploymentConfig = Field(default_factory=BBDeploymentConfig)
    exit: BBExitConfig = Field(default_factory=BBExitConfig)
    safety: BBSafetyConfig = Field(default_factory=BBSafetyConfig)


class BBConfigManager:
    """Manages loading, validation, and persisting of Builder Base settings."""

    def __init__(self, config_path: str = CONFIG_PATH):
        self.config_path = os.path.abspath(config_path)
        self.config = self.load()

    def load(self) -> BBConfig:
        if not os.path.exists(self.config_path):
            logger.info("Builder Base config file not found, creating default...")
            self.config = BBConfig()
            self.save(self.config)
            return self.config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self.config = BBConfig(**data)
            return self.config
        except Exception as e:
            logger.error(f"Error loading Builder Base config: {e}. Using defaults.")
            self.config = BBConfig()
            return self.config

    def save(self, config: BBConfig) -> None:
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)
            self.config = config
        except Exception as e:
            logger.error(f"Error saving Builder Base config: {e}")
