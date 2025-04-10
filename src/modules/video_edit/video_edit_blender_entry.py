import json
import pickle
import sys
from typing import cast

import bpy

from src.models.app_state import AppState
from src.models.config import Config
from src.modules.video_edit import (
    add_background_music,
    add_driver_dash_new,
    add_fast_forward_indicator,
    add_timer,
)
from src.modules.video_edit.thumbnails import process_thumbnails
from src.utils import file_utils
from src.utils.logger import log_info


def edit_video(config: Config, app_state: AppState):
    """Switch to Blender's video editing workspace and sequence editor."""
    # Switch to the Video Editing workspace
    if "Video Editing" in bpy.data.workspaces:
        for window in bpy.context.window_manager.windows:
            window.workspace = bpy.data.workspaces["Video Editing"]
    else:
        log_info("Video Editing workspace not found in Blender")

    # Ensure we're in the sequence editor
    for area in bpy.context.screen.areas:
        if area.type == "SEQUENCE_EDITOR":
            override = {"area": area}
            bpy.ops.sequencer.view_all(override)
            break
        elif area.type == "VIEW_3D":  # If no sequence editor found, change a 3D view
            area.type = "SEQUENCE_EDITOR"
            break

    log_info("Successfully switched to Blender video edit mode")

    log_info("Processing thumbnails first...")
    process_thumbnails.process_thumbnails(config, app_state)
    if config["dev_settings"]["ui_mode"] and config["dev_settings"]["thumbnail_mode"]:
        return

    if bpy.context.scene.sequence_editor:
        for sequence in bpy.context.scene.sequence_editor.sequences_all:
            bpy.context.scene.sequence_editor.sequences.remove(sequence)
    else:
        bpy.context.scene.sequence_editor_create()
    log_info("Done processing thumbnails")

    # Set frames per second based on config
    bpy.context.scene.render.fps = config["render"]["fps"]

    if config["render"]["is_shorts_output"]:
        # Set to 1080x1920 resolution for shorts
        bpy.context.scene.render.resolution_x = 1080
        bpy.context.scene.render.resolution_y = 1920
    else:
        # Set to 4K resolution (3840x2160)
        bpy.context.scene.render.resolution_x = 3840
        bpy.context.scene.render.resolution_y = 2160

    # Add the video file as a movie strip
    sequences = bpy.context.scene.sequence_editor.sequences
    video_strip = sequences.new_movie(
        name="Formula Viz Video",
        filepath=str(file_utils.project_paths.OUTPUT_DIR / config["render"]["output"]),
        channel=1,
        frame_start=1,
    )

    # Set scene frame range to match the video
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = video_strip.frame_final_duration

    log_info(
        f"Added video file: {file_utils.project_paths.OUTPUT_DIR / config['render']['output']}, with frames: {video_strip.frame_final_duration}"
    )

    load_data = app_state.load_data
    assert load_data is not None
    run_drivers = load_data.run_drivers

    focused_driver_run_data = run_drivers.driver_run_data[run_drivers.focused_driver]

    focused_driver_sector_times = run_drivers.driver_sector_times[
        run_drivers.focused_driver
    ]
    focused_driver_total_time = (
        focused_driver_sector_times.sector1
        + focused_driver_sector_times.sector2
        + focused_driver_sector_times.sector3
    )

    sped_point_df_with_times = focused_driver_run_data.sped_point_df

    cur_channel = 2
    driver_dash = add_driver_dash_new.DriverDash(
        app_state,
        config,
        run_drivers,
        cur_channel,
    )
    cur_channel = driver_dash.cur_channel + 1

    add_timer.add_frame_counter(
        config=config,
        sped_point_df_with_times=sped_point_df_with_times,
        focused_driver_total_time=focused_driver_total_time,
        start_frame=1,
        channel=cur_channel,
    )
    cur_channel += 1

    add_fast_forward_indicator.add_fast_forward_indicator(
        run_drivers=run_drivers, cur_channel=cur_channel
    )
    cur_channel += 1

    add_background_music.add_background_music(
        audio_path=file_utils.project_paths.BACKGROUND_MUSIC_PATH,
        channel=cur_channel,
        scene_end_frame=video_strip.frame_final_duration,
    )

    # Set output file path for the final video
    output_file = file_utils.project_paths.OUTPUT_DIR / config["post_process"]["output"]

    scene = bpy.context.scene
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"  # pyright: ignore
    scene.render.ffmpeg.codec = "H264"  # pyright: ignore
    scene.render.ffmpeg.constant_rate_factor = "PERC_LOSSLESS"  # pyright: ignore
    scene.render.ffmpeg.audio_codec = "AAC"  # pyright: ignore
    scene.render.ffmpeg.audio_bitrate = 192
    scene.render.filepath = str(output_file)

    if not config["dev_settings"]["ui_mode"]:
        log_info(f"Starting render to: {output_file}")
        bpy.ops.render.render(animation=True)
        log_info(f"Render completed: {output_file}")


if __name__ == "__main__":
    config_path = sys.argv[-2]
    app_state_path = sys.argv[-1]

    with open(config_path, "r") as f:
        raw_config = json.load(f)
    config = cast(Config, raw_config)
    with open(app_state_path, "rb") as f:
        app_state: AppState = pickle.load(f)

    log_info("Starting video edit.")
    edit_video(config, app_state)
