"""
Main Application Entry Point.
Launches the CustomTkinter GUI Dashboard or Headless CLI runner.
"""

from __future__ import annotations
import os
import sys

# Prevent OpenMP / MKL / BLAS multi-threading conflicts in Python 3.14 on Windows
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import argparse
import logging
import time

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.persistence.config_manager import ConfigManager
from src.control.session_controller import SessionController


def setup_logging(level_name: str = "INFO", log_file: str = "data/coc_farming.log") -> None:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    level = getattr(logging, level_name.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8")
        ]
    )


def run_cli_mode(config_mgr: ConfigManager, args: argparse.Namespace) -> None:
    logger = logging.getLogger("CLI_Runner")
    logger.info("Starting Clash of Clans Resource Farming Controller in Headless CLI Mode...")

    controller = SessionController(config_mgr)
    controller.start_session()

    try:
        while controller.is_running:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Ctrl+C received. Stopping controller...")
        controller.stop_session()


def main():
    parser = argparse.ArgumentParser(description="Clash of Clans Resource Farming Automation")
    parser.add_argument("--cli", action="store_true", help="Run in headless CLI mode instead of GUI")
    parser.add_argument("--mode", type=str, choices=["wall_plus_attack", "fixed_attacks", "infinite"], help="Override operation mode")
    parser.add_argument("--edge", type=str, choices=["top", "bottom", "left", "right"], help="Override attack deployment edge")
    parser.add_argument("--expression", type=str, help="Override target loot expression")
    parser.add_argument("--config", type=str, default=None, help="Path to custom config YAML file")

    args = parser.parse_args()

    # Load configuration
    config_mgr = ConfigManager(args.config)
    config = config_mgr.config

    if args.mode:
        config.mode = args.mode
    if args.edge:
        config.deployment.selected_edge = args.edge
    if args.expression:
        config.target.expression = args.expression

    setup_logging(config.logging.level, config.logging.log_file)

    if args.cli:
        run_cli_mode(config_mgr, args)
    else:
        # Launch GUI Dashboard
        from src.app.gui_app import DashboardApp
        app = DashboardApp(config_mgr)
        app.mainloop()


if __name__ == "__main__":
    main()
