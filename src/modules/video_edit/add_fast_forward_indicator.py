import bpy

from src.models.driver import RunDrivers
from src.utils import file_utils


def add_fast_forward_indicator(run_drivers: RunDrivers, cur_channel):
    """Add and animate a fast forward indicator image.

    This function adds a fast forward image object to the specified channel
    and animates its visibility based on FastForward status.

    Args:
        run_drivers: RunDrivers object containing driver data
        cur_channel: The channel to add the fast forward indicator to

    """
    focused_driver = run_drivers.focused_driver
    focused_driver_run_data = run_drivers.driver_run_data[focused_driver]

    focused_sped_df = focused_driver_run_data.sped_point_df
    focused_absolute_df = focused_driver_run_data.point_df
    sped_frame_to_absolute_frame = focused_driver_run_data.sped_frame_to_absolute_frame

    # Create a sequence in the Video Sequence Editor for fast forward indicator
    # ff_image_path = str(file_utils.project_paths.IMAGES_DIR / "ff-gray.png")
    ff_image_path = str(file_utils.project_paths.IMAGES_DIR / "ff-white-from-svg.png")

    # Get the sequence editor
    if not bpy.context.scene.sequence_editor:
        bpy.context.scene.sequence_editor_create()
    seq_editor = bpy.context.scene.sequence_editor

    # Create an image strip for the fast forward indicator
    ff_strip = seq_editor.sequences.new_image(
        name="FastForwardIndicator",
        filepath=ff_image_path,
        channel=cur_channel + 1,  # Place it one channel above the current channel
        frame_start=1,
    )

    ff_strip.transform.offset_x = 0
    ff_strip.transform.offset_y = 492
    ff_strip.transform.scale_x = 0.25
    ff_strip.transform.scale_y = 0.25

    # Set initial properties for the strip
    ff_strip.blend_type = "ALPHA_OVER"
    ff_strip.frame_final_end = (
        len(focused_sped_df) + 1
    )  # Make strip span the entire timeline

    # Initially hide the indicator by setting opacity to 0
    ff_strip.blend_alpha = 0
    ff_strip.keyframe_insert(data_path="blend_alpha", frame=1)

    # Animate the visibility based on FastForward status
    for i in range(len(focused_sped_df)):
        frame = i + 1
        absolute_frame = sped_frame_to_absolute_frame[i]

        # Check if there is a row with FastForward = True within 20 points
        in_fast_forward_zone = False
        check_range_start = max(0, absolute_frame - 3)
        check_range_end = min(len(focused_absolute_df), absolute_frame + 3)

        for check_frame in range(check_range_start, check_range_end):
            if focused_absolute_df.iloc[check_frame].get("FastForward", False):
                in_fast_forward_zone = True
                break

        # Set visibility based on fast forward status
        ff_strip.blend_alpha = 1.0 if in_fast_forward_zone else 0.0
        ff_strip.keyframe_insert(data_path="blend_alpha", frame=frame)
