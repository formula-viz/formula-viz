"""Add a country flag corresponding to the current track."""

import os
from typing import Optional

import bpy
from bpy.types import Object

from src.models.config import Config
from src.utils.logger import log_info


def add_flag(config: Config, camera_obj: Optional[Object] = None, scale: float = 0.05):
    """Add a country flag corresponding to the current track.

    Returns:
        bpy.types.Object: The added flag object or None if the flag image is not found.

    """
    country = config["track"].title()
    log_info(f"Adding {country} flag")

    bpy.ops.preferences.addon_enable(module="io_import_images_as_planes")
    image_path = str(f"csv_repo/track_images/{country}.png")

    # Check if the file exists
    if not os.path.exists(image_path):
        log_info(f"Flag image for {country} not found at {image_path}")
        return None

    # the emission here is of the image pixels themselves, so making the image brighter
    bpy.ops.import_image.to_plane(  # pyright: ignore
        files=[{"name": image_path}],
        shader="EMISSION",  # Use emission shader
        emit_strength=0.8,  # Set emission strength to 1.0
    )
    flag_plane = bpy.context.selected_objects[0]
    flag_plane.name = f"{country} Flag"
    flag_plane.location = (0, 0, -1)
    flag_plane.scale = (scale, scale, scale)

    if camera_obj:
        flag_plane.parent = camera_obj

    return flag_plane
