import os

import bpy

from src.models.app_state import AppState
from src.models.config import Config
from src.models.driver import Driver


def _add_gimp_dash(
    driver: Driver, x: int, y: int, scale_x: float, scale_y: float, cur_channel: int
):
    widget_pngs_dir = f"output/driver_widgets/{driver.last_name}"

    seq_editor = bpy.context.scene.sequence_editor

    # Get all PNG files and sort them by frame number to ensure proper order
    png_files = [f for f in os.listdir(widget_pngs_dir) if f.endswith(".png")]
    png_files.sort(
        key=lambda x: int(x.split("_")[1].split(".")[0])
    )  # Sort by frame number

    # Import all PNGs from the driver's widget directory into VSE in correct order
    for i, png_file in enumerate(png_files):
        filepath = os.path.join(widget_pngs_dir, png_file)
        # Create the image strip
        image_strip = seq_editor.sequences.new_image(
            name=png_file,
            filepath=filepath,
            channel=cur_channel,
            frame_start=i + 1,
        )

        # Set position and scale
        image_strip.transform.offset_x = x
        image_strip.transform.offset_y = y
        image_strip.transform.scale_x = scale_x
        image_strip.transform.scale_y = scale_y

    return cur_channel + 1


def add_gimp_dashes(config: Config, app_state: AppState, cur_channel: int):
    """Import all PNG images from driver widgets directory into Blender's Video Sequence Editor.
    Places each driver's widgets at the current channel and increments the channel for each driver.

    Args:
        config: Application configuration
        app_state: Current application state
        cur_channel: Starting channel number for sequence placement

    Returns:
        Updated channel number after all imports

    """
    load_data = app_state.load_data
    assert load_data is not None

    run_drivers = load_data.run_drivers
    drivers = run_drivers.drivers

    # Define common parameters
    X_OFFSET = 1568
    Y_OFFSET = -654
    SCALE = 0.7

    if config["render"]["is_shorts_output"]:
        if len(drivers) == 2:
            cur_channel = _add_gimp_dash(
                drivers[0], -X_OFFSET, Y_OFFSET, SCALE, SCALE, cur_channel
            )
            cur_channel = _add_gimp_dash(
                drivers[1], X_OFFSET, Y_OFFSET, SCALE, SCALE, cur_channel
            )
        else:
            cur_channel = _add_gimp_dash(
                run_drivers.focused_driver,
                X_OFFSET,
                Y_OFFSET,
                SCALE,
                SCALE,
                cur_channel,
            )
    elif len(drivers) == 2:
        cur_channel = _add_gimp_dash(
            drivers[0], -X_OFFSET, Y_OFFSET, SCALE, SCALE, cur_channel
        )
        cur_channel = _add_gimp_dash(
            drivers[1], X_OFFSET, Y_OFFSET, SCALE, SCALE, cur_channel
        )
    else:
        cur_channel = _add_gimp_dash(
            run_drivers.focused_driver, X_OFFSET, Y_OFFSET, SCALE, SCALE, cur_channel
        )

    return cur_channel
