import os
import pickle
import subprocess

from src.models.app_state import AppState
from src.models.config import Config
from src.modules.thumbnail.abstract import ImageMode, ThumbnailInput
from src.utils import file_utils
from src.utils.logger import log_info


def encode_to_pickle_and_run_blender(thumbnail_input: ThumbnailInput, is_ui_mode: bool):
    thumbnail_temp_dir = file_utils.project_paths.THUMBNAIL_MODULE_TMP
    os.makedirs(thumbnail_temp_dir, exist_ok=True)

    pickle_path = os.path.join(thumbnail_temp_dir, "thumbnail_input.pickle")

    with open(pickle_path, "wb") as f:
        pickle.dump(thumbnail_input, f)

    blender_script_path = os.path.join(
        file_utils.project_paths.PROJECT_ROOT, "src/modules/thumbnail/blender_entry.py"
    )

    cmd = ["blender"]
    if not is_ui_mode:
        cmd.append("-b")
    cmd.extend(["--python", blender_script_path, "--", pickle_path])

    subprocess.run(cmd, check=True)


def main(config: Config, app_state: AppState):
    """Entry point for thumbnail generation.
    This function runs outside of Blender, pickles the configuration objects,
    and then launches Blender with a script that will generate the thumbnail.

    Args:
        config: Application configuration
        app_state: Current application state

    """
    log_info("Starting thumbnail generation process")

    load_data = app_state.load_data
    assert load_data is not None
    drivers = load_data.run_drivers.drivers
    focused_driver = load_data.run_drivers.focused_driver

    # Sort drivers by position and find first non-focused driver
    sorted_drivers = sorted(drivers, key=lambda d: d.position)
    second_driver = next((d for d in sorted_drivers if d != focused_driver), None)
    assert second_driver is not None

    thumbnail_input = ThumbnailInput(
        ui_mode=False,
        should_render=True,
        should_post_process=True,
        image_mode=ImageMode.TWO_IMAGES,
        drivers=drivers,
        driver_for_img_one=focused_driver,
        driver_for_img_two=second_driver,
    )
    encode_to_pickle_and_run_blender(thumbnail_input, is_ui_mode=False)
