import os
import sys
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent.absolute()

# Add project root to Python's module search path
sys.path.insert(0, str(project_root))

from src.models.app_state import AppState
from src.modules.load_data import load_data_main
from src.pipeline import get_config


def main():
    project_root = Path(__file__).parent.parent.absolute()

    os.environ["PYTHONPATH"] = (
        f"{project_root}:{project_root}/py:{os.environ.get('PYTHONPATH', '')}"
    )

    config_file = project_root / "config" / "config.json"
    template_file = project_root / "config" / "config-template.json"

    config = (
        get_config(config_file) if config_file.exists() else get_config(template_file)
    )

    app_state: AppState = AppState(
        project_root=project_root,
        render_output_path=project_root / "output" / config["render"]["output"],
    )

    app_state.load_data = load_data_main.load_data_main(config, app_state)


if __name__ == "__main__":
    main()
