import math

import bpy

from src.models.app_state import AppState
from src.models.config import Config
from src.modules.render.add_funcs import add_track
from src.modules.render.add_funcs.add_driver_objects import create_car_obj
from src.modules.render.render_animation import setup_ui_mode_viewport
from src.utils.logger import log_info


class CarSideThumbnail:
    def __init__(self, config: Config, state: AppState):
        self.config = config
        self.state = state

        self.output_path = "output/car-side-thumbnail-raw.png"

        thumbnail_track_data = self.state.thumbnail_track_data
        assert thumbnail_track_data is not None
        add_track.main(thumbnail_track_data, None)

        self._add_driver_obj()
        self._add_camera()

        if config["dev_settings"]["ui_mode"]:
            setup_ui_mode_viewport(config)
        else:
            self._render_cycles()

    def _render_cycles(self):
        """Render the thumbnail image using Cycles and save it to output/thumbnail.png."""
        log_info(f"Rendering thumbnail and saving to {self.output_path}")
        scene = bpy.context.scene
        if not scene:
            raise ValueError("No active scene found")

        scene.render.engine = "CYCLES"  # pyright: ignore
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = self.output_path

        scene.display_settings.display_device = "sRGB"  # type: ignore
        scene.view_settings.view_transform = "AgX"  # type: ignore
        scene.view_settings.look = "AgX - Base Contrast"  # type: ignore
        scene.view_settings.gamma = 0.95  # pyright: ignore

        scene.render.resolution_x = 3840  # 4K width
        scene.render.resolution_y = 2160  # 4K height
        scene.render.resolution_percentage = 100

        # Set to GPU rendering
        scene.cycles.device = "GPU"
        bpy.context.preferences.addons[
            "cycles"
        ].preferences.compute_device_type = "CUDA"

        bpy.ops.render.render(write_still=True)  # pyright: ignore

    def _render_eevee(self):
        """Render the thumbnail image using Eevee and save it to output/thumbnail.png."""
        log_info(f"Rendering thumbnail and saving to {self.output_path}")
        scene = bpy.context.scene
        if not scene:
            raise ValueError("No active scene found")

        scene.render.engine = "BLENDER_EEVEE"  # pyright: ignore
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = self.output_path

        scene.render.resolution_x = 3840  # 4K width
        scene.render.resolution_y = 2160  # 4K height
        scene.render.resolution_percentage = 100
        bpy.ops.render.render(write_still=True)  # pyright: ignore

    def _add_driver_obj(self):
        load_data = self.state.load_data
        assert load_data is not None
        focused_driver = load_data.run_drivers.focused_driver

        driver_obj, _ = create_car_obj(focused_driver.team, focused_driver.last_name)

        driver_obj.location = (-126.8, 3.58, 91.97)
        driver_obj.rotation_euler = (
            math.radians(-4),
            math.radians(-6),
            math.radians(-90),
        )

    def _add_camera(self):
        camera = bpy.data.cameras.new(name="CarSideThumbnail Camera")
        camera_obj = bpy.data.objects.new(
            name="CarSideThumbnail Camera", object_data=camera
        )
        bpy.context.scene.camera = camera_obj
        bpy.context.scene.collection.objects.link(camera_obj)

        camera_obj.location = (-130.2, 13.227, 95.456)
        camera_obj.rotation_euler = (
            math.radians(-105),
            math.radians(-180),
            math.radians(0),
        )
        camera.lens = 31
