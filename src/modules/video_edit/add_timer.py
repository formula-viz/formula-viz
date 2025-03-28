import bpy

from src.models.config import Config
from src.utils import file_utils


def add_frame_counter(config: Config, end_frame, start_frame=1, channel=1):
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

    for frame in range(
        1,
        end_frame
        + config["render"]["end_buffer_frames"]
        + config["render"]["start_buffer_frames"],
    ):
        # Calculate start and end frames for this text strip
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

        # Configure text display
        text_strip.font_size = 70
        text_strip.font = bpy.data.fonts.load(str(file_utils.project_paths.BOLD_FONT))
        # text_strip.font = bpy.data.fonts.load(str(file_utils.project_paths.IMPACT_FONT))
        text_strip.color = (1, 1, 1, 1)  # White text
        text_strip.use_shadow = True
        text_strip.shadow_color = (0, 0, 0, 1)  # Black shadow
        text_strip.location = (0.08, 0.85)
        text_strip.align_x = "LEFT"

        # Set the text based on the current frame
        # For a counter display that's consistent across frames
        # we'll use the first frame number of this strip
        # Convert frame to seconds and format as 0:00.000
        seconds = strip_start / 30
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60

        if frame <= config["render"]["start_buffer_frames"]:
            text_strip.text = "0:00.000"
        else:
            text_strip.text = f"{minutes}:{remaining_seconds:06.3f}"

        text_strips.append(text_strip)

    return text_strips
