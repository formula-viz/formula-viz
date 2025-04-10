import math

import bpy
import numpy as np
from pandas import DataFrame, Timedelta

from src.models.config import Config
from src.utils import file_utils


def add_frame_counter(
    config: Config,
    sped_point_df_with_times: DataFrame,
    focused_driver_total_time: Timedelta,
    start_frame=1,
    channel=1,
):
    """Add a frame counter that increments every frame in the VSE using individual text strips.

    Args:
        start_frame: First frame to start counting from
        end_frame: Last frame (defaults to scene end frame if None)
        channel: VSE channel to place the counter
        position: Counter position ('TOP_LEFT', 'TOP_RIGHT', 'BOTTOM_LEFT', 'BOTTOM_RIGHT', 'CENTER')

    Returns:
        List of created text strips

    """
    scene = bpy.context.scene

    # Create a text strip for each frame
    if not scene.sequence_editor:
        scene.sequence_editor_create()

    text_strips = []

    # Convert focused_driver_total_time (Timedelta) to string in format 0:00.000
    total_seconds = focused_driver_total_time.total_seconds()
    total_minutes = int(total_seconds // 60)
    remaining_seconds = total_seconds % 60
    total_time_str = f"{total_minutes}:{remaining_seconds:06.3f}"

    is_before = True
    for i, row in enumerate(sped_point_df_with_times.itertuples()):
        # Calculate start and end frames for this text strip
        frame = i + 1
        strip_start = frame
        strip_end = frame + 1

        # Create the text strip
        text_strip = scene.sequence_editor.sequences.new_effect(
            name=f"FrameCounter_{frame}",
            type="TEXT",
            channel=channel,
            frame_start=strip_start,
            frame_end=strip_end,
        )

        text_strip.font = bpy.data.fonts.load(
            str(
                file_utils.project_paths.FONTS_DIR
                / "Azeret_Mono/static/AzeretMono-ExtraBold.ttf"
            )
        )

        # text_strip.font = bpy.data.fonts.load(str(file_utils.project_paths.IMPACT_FONT))
        text_strip.color = (1, 1, 1, 1)  # White text
        text_strip.use_shadow = True
        text_strip.shadow_color = (0, 0, 0, 1)  # Black shadow

        if config["render"]["is_shorts_output"]:
            text_strip.location = (0.26, 0.85)
            text_strip.font_size = 90
        else:
            text_strip.location = (0.5, 0.14)
            text_strip.font_size = 100

        # Set the text based on the current frame
        # For a counter display that's consistent across frames
        # we'll use the first frame number of this strip
        # Convert frame to seconds and format as 0:00.000
        # Check if row.Time is NaN

        if isinstance(row.Time, float) and (math.isnan(row.Time) or np.isnan(row.Time)):
            if not is_before:
                text_strip.text = ""
            else:
                text_strip.text = "0:00.000"

        elif frame <= config["render"]["start_buffer_frames"]:
            text_strip.text = "0:00.000"
        else:
            time_float = float(row.Time)
            minutes = int(time_float // 60)
            remaining_seconds = time_float % 60
            text_strip.text = f"{minutes}:{remaining_seconds:06.3f}"
            is_before = False

        text_strips.append(text_strip)

    return text_strips
