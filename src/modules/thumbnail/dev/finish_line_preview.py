import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.append(project_root)

from src.models.driver import Driver
from src.modules.thumbnail.abstract import ImageMode, ThumbnailInput
from src.modules.thumbnail.main import encode_to_pickle_and_run_blender

if __name__ == "__main__":
    # Get ui_mode from command line argument
    ui_mode = True if len(sys.argv) <= 1 else sys.argv[1].lower() == "true"
    should_render = True if len(sys.argv) <= 2 else sys.argv[2].lower() == "true"
    should_post_process = True if len(sys.argv) <= 3 else sys.argv[3].lower() == "true"

    verstappen = Driver(
        "Verstappen", "VER", "", 2025, "Q", "RedBullRacing", "#0600ef", 1
    )
    leclerc = Driver("Leclerc", "LEC", "", 2025, "Q", "Ferrari", "#f70d1a", 2)
    alonso = Driver("Alonso", "ALO", "", 2025, "Q", "AstonMartin", "#0090ff", 3)

    thumbnail_input = ThumbnailInput(
        ui_mode=ui_mode,
        should_render=should_render,
        should_post_process=should_post_process,
        image_mode=ImageMode.TWO_IMAGES,
        drivers=[verstappen, leclerc, alonso],
        driver_for_img_one=verstappen,
        driver_for_img_two=leclerc,
    )
    encode_to_pickle_and_run_blender(thumbnail_input, is_ui_mode=ui_mode)
