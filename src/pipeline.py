import json
from pathlib import Path

from src.models.app_state import AppState
from src.models.config import Config
from src.modules.load_data import load_data_main
from src.modules.render import render_main
from src.modules.video_edit.video_edit_main import video_edit_main
from src.utils.logger import log_err, log_info


def run_for_config(config: Config, project_root: Path):
    """Run the rendering process for a given configuration.

    Each Config has a corresponding AppState.
    """
    app_state: AppState = AppState(
        project_root=project_root,
        render_output_path=project_root / "output" / config["render"]["output"],
    )

    app_state.load_data = load_data_main.load_data_main(config, app_state)

    log_info("Data loaded successfully.")

    render_main.render_main(config, app_state)
    video_edit_main(config, app_state)

    # ui_mode = config.get("dev_settings", {}).get("ui_mode", False)

    # if config["render"]["is_both_mode"]:
    #     config["render"]["is_shorts_output"] = True
    #     trigger(config)
    #     config["render"]["is_shorts_output"] = False
    #     trigger(config)
    # else:
    #     trigger(config)


def get_config(file: Path) -> Config:
    """Load JSON configuration file and convert to Config TypedDict."""
    with open(file, "r") as f:
        data = json.load(f)
        return Config(data)


def run_single_mode(project_root: Path):
    """Load configuration and set up the environment for the rendering process."""
    config_file = project_root / "config" / "config.json"
    template_file = project_root / "config" / "config-template.json"

    config = (
        get_config(config_file) if config_file.exists() else get_config(template_file)
    )

    run_for_config(config, project_root)


def run_batch_mode(project_root: Path):
    """Run batch mode, meaning a group of configurations."""
    batch_configs_dir = project_root / "config" / "batch_configs"
    if not batch_configs_dir.exists():
        log_err(f"Batch configs directory not found: {batch_configs_dir}")
        return 1

    config_files = [f for f in batch_configs_dir.glob("*.json")]
    if not config_files:
        log_err(f"No config files found in {batch_configs_dir}")
        return 1

    for config_file in config_files:
        log_info(f"Processing config: {config_file.name}")
        with open(config_file, "r") as f:
            config = json.load(f)
        run_for_config(config, project_root)
    return 0


def run_pipeline(project_root: Path, is_batch_mode: bool):
    if is_batch_mode:
        return run_batch_mode(project_root)
    else:
        return run_single_mode(project_root)
