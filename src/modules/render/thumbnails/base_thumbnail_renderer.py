import bpy

from src.models.app_state import AppState
from src.models.config import Config
from src.modules.render.add_funcs import add_light, add_track
from src.modules.render.render_animation import setup_ui_mode_viewport
from src.utils.logger import log_info


class BaseThumbnailRenderer:
    def __init__(self, config: Config, state: AppState, output_path: str):
        self.config = config
        self.state = state
        self.output_path = output_path

        # Common setup
        add_light.main()

        thumbnail_track_data = self.state.thumbnail_track_data
        assert thumbnail_track_data is not None
        add_track.main(thumbnail_track_data, None)

        # These will be implemented by subclasses
        self._add_objects()
        self._add_camera()

        if config["dev_settings"]["ui_mode"]:
            setup_ui_mode_viewport(config)
        else:
            self._render_cycles()

    def _render_cycles(self):
        """Render the thumbnail using Cycles."""
        log_info(f"Rendering thumbnail and saving to {self.output_path}")
        scene = bpy.context.scene
        if not scene:
            raise ValueError("No active scene found")

        scene.render.engine = "CYCLES"
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = self.output_path

        scene.display_settings.display_device = "sRGB"
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
        scene.view_settings.gamma = 0.95

        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.resolution_percentage = 100

        # GPU rendering
        scene.cycles.device = "GPU"
        bpy.context.preferences.addons[
            "cycles"
        ].preferences.compute_device_type = "CUDA"

        bpy.ops.render.render(write_still=True)

    def _add_objects(self):
        """Add objects to the scene - to be implemented by subclasses."""
        raise NotImplementedError

    def _add_camera(self):
        """Add camera to the scene - to be implemented by subclasses."""
        raise NotImplementedError
