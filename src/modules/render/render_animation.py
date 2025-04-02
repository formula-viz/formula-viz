"""Set up blender's render settings based on config.

Configures resolution, frame rate, and rendering settings based on the provided
configuration, then initiates either Cycles or Eevee rendering process.

Conditionally does not start the render process if in development settings ui_mode.
"""

import bpy

from src.models.config import Config
from src.utils import file_utils
from src.utils.logger import log_info, log_warn


def configure_output(config: Config) -> str:
    """Configure ffmpeg mp4 output settings."""
    scene = bpy.context.scene
    if not scene:
        raise ValueError("Scene not found")

    output_path = str(file_utils.project_paths.get_render_output(config))
    scene.render.filepath = output_path

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"  # pyright: ignore
    scene.render.ffmpeg.codec = "H264"  # pyright: ignore
    scene.render.ffmpeg.constant_rate_factor = "PERC_LOSSLESS"  # pyright: ignore

    return output_path


def eevee_render(config: Config, num_frames: int, is_ui_mode: bool):
    """Incorporate all possible settings for Eevee rendering."""
    log_info(f"Starting Eevee render of {num_frames} with preview_mode={is_ui_mode}...")

    scene = bpy.data.scenes["Scene"]
    scene.render.engine = "BLENDER_EEVEE"  # type: ignore

    eevee = scene.eevee
    if not eevee:
        raise ValueError("Eevee settings not found")

    # Sampling
    eevee.taa_render_samples = config["render"]["samples"]
    # only affects viewport
    eevee.taa_samples = config["render"]["samples"]

    # Ambient Occlusion
    # I don't see a visual impact of ambient occlusion, I'm leaving it out

    # Bloom, bright pixels produce a glowing effect, mimicking real cameras
    # This adds depth to the cars, I like it.
    eevee.use_bloom = True  # type: ignore

    # Depth of Field
    # I don't see a visual impact of depth of field, I'm not editing the defaults

    # Subsurface scattering is too technical to matter

    # Screen Space Reflections
    eevee.use_ssr = True  # type: ignore
    # this gets technical, I'm just going to enable and leave with the defaults

    # Motion Blur
    eevee.use_motion_blur = True  # type: ignore
    eevee.motion_blur_shutter = 0.75  # type: ignore

    # Leaving Volumetrics Off, it seems to be for mist or fog

    # Not Touching Performance, Curves

    # Shadows, really affect the visuals. maxing this out
    eevee.shadow_cube_size = "4096"  # type: ignore
    eevee.shadow_cascade_size = "4096"  # type: ignore
    eevee.use_shadow_high_bitdepth = True  # type: ignore
    eevee.use_soft_shadows = True  # type: ignore

    # Not touching Indirect Lighting

    # Film, having a filter value over 1.0 really smooths the fine lines
    # Makes it look sharp, professional at the cost of a small level of detail
    scene.render.filter_size = 2.5

    # Simplify, I actually don't think this makes it look worse,
    # TODO: may be worth it to have this for quicker renders, especially
    # if I eventually transition to eevee

    # Not touching Grease Pencil or Freestyle

    # Color Management, this is very important for aesthetics
    scene.display_settings.display_device = "sRGB"  # type: ignore
    scene.view_settings.view_transform = "AgX"  # type: ignore
    scene.view_settings.look = "AgX - Base Contrast"  # type: ignore
    scene.view_settings.gamma = 0.95  # pyright: ignore

    if not is_ui_mode:
        bpy.ops.render.render(animation=True)  # pyright: ignore
        log_info("Render complete")


# def cycles_render(config, num_frames, is_ui_mode):
#     """TODO, needs proper config"""
#     scene = bpy.context.scene
#     if not scene:
#         raise ValueError("Scene not found")

#     scene.render.engine = "CYCLES"  # type: ignore

#     scene.cycles.samples = config["render"]["samples"]
#     scene.cycles.use_denoising = True

#     if not is_ui_mode:
#         log_info(f"Starting Cycles Render of {num_frames}")
#         bpy.ops.render.render(animation=True)
#         log_info("Cycles render complete")


def setup_ui_mode_viewport(config: Config):
    """Configure viewport for viewing in the development ui_mode.

    Saves time by automated the setup like removing overlays, setting shader mode.
    """
    window = bpy.context.window
    if not window:
        raise ValueError("Window not found")

    screen = window.screen
    for area in screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.overlay.show_overlays = False  # type: ignore
                    space.overlay.show_relationship_lines = False  # type: ignore
                    space.overlay.show_outline_selected = False  # type: ignore
                    space.overlay.show_object_origins = False  # type: ignore

                    space.shading.type = "RENDERED"  # type: ignore

                    space.region_3d.view_perspective = "CAMERA"  # type: ignore

    # go to frame 10 to ensure everything is positioned properly
    bpy.context.scene.frame_set(10)  # type: ignore


def main(config: Config, num_frames: int):
    """Set up blender's render settings based on config.

    Configures resolution, frame rate, and rendering settings based on the provided
    configuration, then initiates either Cycles or Eevee rendering process.

    Conditionally does not start the render process if in development settings ui_mode.

    Args:
        config: Configuration object containing rendering and development settings
        num_frames: Total number of frames to render in the animation

    """
    scene = bpy.context.scene
    if not scene:
        raise ValueError("Scene not found")

    # configure the resolution before quitting in the case of
    # preview render mode to properly preview mobile/desktop viewports
    if config["render"]["is_shorts_output"]:
        log_info("Setting to shorts/phone resolution...")
        scene.render.resolution_x = 1080
        scene.render.resolution_y = 1920

        scene.cycles.tile_x = 1080  # pyright: ignore
        scene.cycles.tile_y = 1920  # pyright: ignore
    else:
        log_info("Setting to 4k desktop resolution...")
        scene.render.resolution_x = 3840
        scene.render.resolution_y = 2160

        # it is better to use 1 tile because gpu has 12GB+ of memory
        scene.cycles.tile_x = 3840  # pyright: ignore
        scene.cycles.tile_y = 2160  # pyright: ignore

    scene.render.fps = config["render"]["fps"]
    scene.frame_end = num_frames

    if config["dev_settings"]["limited_frames_mode"]:
        scene.frame_end = 100

    if config["dev_settings"]["ui_mode"]:
        setup_ui_mode_viewport(config)

    output_path = configure_output(config)
    if config["render"]["engine"] == "cycles":
        # cycles_render(config, num_frames, config["dev_settings"]["ui_mode"])
        log_warn("Cycles rendering not configured")
    else:
        eevee_render(config, num_frames, config["dev_settings"]["ui_mode"])
    return output_path
