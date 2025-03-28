"""Entrypoint for the python blender rendering application. Handles conditional triggering of different ports of the application for development and testing purposes."""

import json
import pickle
import sys
from typing import cast

from src.models.app_state import AppState
from src.models.config import Config
from src.modules.render.renderers import HeadToHeadRenderer, RestOfFieldRenderer
from src.utils.logger import log_info

if __name__ == "__main__":
    config_path = sys.argv[-2]
    app_state_path = sys.argv[-1]

    with open(config_path, "r") as f:
        raw_config = json.load(f)
    config = cast(Config, raw_config)

    with open(app_state_path, "rb") as f:
        app_state: AppState = pickle.load(f)

    video_type = config["type"]

    renderer = (
        HeadToHeadRenderer(config, app_state)
        if video_type == "head-to-head"
        else RestOfFieldRenderer(config, app_state)
    )
    log_info(
        f"Starting Render with Config: {config['track']}, {config['year']}, {config['type']}"
    )
    output_path = renderer.render()
