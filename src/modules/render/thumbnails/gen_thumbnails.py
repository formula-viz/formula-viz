import time

import bpy

from src.models.app_state import AppState
from src.models.config import Config
from src.modules.render.thumbnails.car_side import CarSideThumbnail
from src.modules.render.thumbnails.two_car import TwoCarThumbnail
from src.utils.logger import log_info


def clear_scene():
    for collection in bpy.data.collections:
        bpy.data.collections.remove(collection, do_unlink=True)  # type: ignore
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)  # type: ignore
    for material in bpy.data.materials:
        bpy.data.materials.remove(material, do_unlink=True)  # type: ignore


def gen_thumbnails(config: Config, state: AppState):
    """Generate thumbnails for the app."""
    log_info("Generating thumbnails...")
    start_time = time.time()

    car_side_thumbnail = CarSideThumbnail(
        config, state, "output/car-side-thumbnail-raw.png"
    )
    clear_scene()
    two_car_thumbnail = TwoCarThumbnail(
        config, state, "output/two-car-thumbnail-raw.png"
    )

    log_info(f"Thumbnails generated in {time.time() - start_time:.2f} seconds")
