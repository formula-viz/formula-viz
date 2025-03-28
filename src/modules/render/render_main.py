import json
import os
import pickle
import subprocess
import tempfile

from src.models.app_state import AppState
from src.models.config import Config


def render_main(config: Config, app_state: AppState):
    ui_mode = config["dev_settings"]["ui_mode"]

    app_state.render_output_path = (
        app_state.project_root / "assets" / "dev" / "render-output.mp4"
    )

    try:
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as app_state_file:
            app_state_path = app_state_file.name
            pickle.dump(app_state, app_state_file)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as config_file:
            config_path = config_file.name
            with open(config_path, "w") as f:
                json.dump(config, f)

        cmd = ["blender"]
        if not ui_mode:
            cmd.append("-b")  # Background mode if not UI mode

        cmd.extend(
            [
                "--python",
                f"{app_state.project_root}/src/modules/render/render_blender_entry.py",
                "--",
                config_path,
                app_state_path,
            ]
        )

        subprocess.run(cmd, check=True)

        # Clean up temporary files
        os.unlink(config_path)
        os.unlink(app_state_path)

        return 0
    except subprocess.CalledProcessError as e:
        # Clean up temporary files in case of error
        config_path_exists = "config_path" in locals()
        app_state_path_exists = "app_state_path" in locals()

        if config_path_exists:
            try:
                os.unlink(locals()["config_path"])
            except (OSError, FileNotFoundError):
                pass

        if app_state_path_exists:
            try:
                os.unlink(locals()["app_state_path"])
            except (OSError, FileNotFoundError):
                pass

        return e.returncode
