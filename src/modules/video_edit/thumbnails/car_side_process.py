import bpy

from src.models.app_state import AppState
from src.models.config import Config
from src.utils import file_utils
from src.utils.colors import hex_to_blender_rgb


class CarSideProcess:
    def __init__(self, config: Config, app_state: AppState):
        self.config = config
        self.app_state = app_state
        self.seq_editor = bpy.context.scene.sequence_editor
        self.cur_channel = 1

        self.raw_path = "output/car-side-thumbnail-raw.png"
        self.output_path = "output/car-side-thumbnail.png"

        self._add_raw()
        # self._add_driver_images()
        self._add_color_border()
        self._add_formula_viz_circle_icon()

        self._save()

    def _save(self):
        scene = bpy.context.scene
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = self.output_path

        # Render the current frame
        bpy.ops.render.render(write_still=True)

    def _add_raw(self):
        # Set scene resolution to 4K (3840x2160)
        bpy.context.scene.render.resolution_x = 3840
        bpy.context.scene.render.resolution_y = 2160
        bpy.context.scene.render.resolution_percentage = 100

        # Add raw image strip
        raw_image_strip = self.seq_editor.sequences.new_image(
            name="RawImage",
            filepath=self.raw_path,
            channel=self.cur_channel,
            frame_start=1,
        )
        self.cur_channel += 1

    def _add_color_border(self):
        def add_color_strip(i):
            color_strip = self.seq_editor.sequences.new_effect(
                name=f"ColorBorder{i}",
                type="COLOR",
                channel=self.cur_channel,
                frame_start=1,
                frame_end=10,
            )
            self.cur_channel += 1
            return color_strip

        left = add_color_strip(1)
        right = add_color_strip(2)
        top = add_color_strip(3)
        bottom = add_color_strip(4)

        left.transform.offset_x = -1868
        right.transform.offset_x = 1868
        left.transform.scale_x = 0.03
        right.transform.scale_x = 0.03

        top.transform.scale_y = 0.045
        bottom.transform.scale_y = 0.045
        top.transform.offset_y = 1036
        bottom.transform.offset_y = -1036

        load_data = self.app_state.load_data
        assert load_data is not None
        run_drivers = load_data.run_drivers

        color = run_drivers.driver_applied_colors[run_drivers.focused_driver]
        rgb_color = hex_to_blender_rgb(color)

        rgb_color = (0, 1, 1)

        left.color = rgb_color
        right.color = rgb_color
        top.color = rgb_color
        bottom.color = rgb_color

    def _add_formula_viz_circle_icon(self):
        circle_icon_path = file_utils.project_paths.FORMULA_VIZ_CIRCLE_ICON_PATH
        circle_icon = self.seq_editor.sequences.new_image(
            name="CircleIcon",
            filepath=str(circle_icon_path),
            channel=self.cur_channel,
            frame_start=1,
        )
        self.cur_channel += 1

        # Adjust position and scale as needed
        circle_icon.transform.scale_x = 0.35
        circle_icon.transform.scale_y = 0.35

        circle_icon.transform.offset_x = -1393
        circle_icon.transform.offset_y = 541

    def _add_driver_images(self):
        load_data = self.app_state.load_data
        assert load_data is not None
        if self.config["type"] == "head-to-head":
            drivers = load_data.run_drivers.drivers
            if len(drivers) == 2:
                # if there are 2 drivers in the head to head, then we want to have one image on the left, one on the right
                for i, driver in enumerate(drivers):
                    driver_image_path = file_utils.project_paths.get_driver_image_path(
                        driver
                    )

                    # Create an image strip for the fast forward indicator
                    driver_image_strip = self.seq_editor.sequences.new_image(
                        name="FastForwardIndicator",
                        filepath=str(driver_image_path),
                        channel=self.cur_channel,  # Place it one channel above the current channel
                        frame_start=1,
                    )
                    self.cur_channel += 1

                    driver_image_strip.transform.offset_x = -1300 if i == 0 else 1300
                    driver_image_strip.transform.offset_y = -500
                    driver_image_strip.transform.scale_x = 1.5
                    driver_image_strip.transform.scale_y = 1.5
        else:
            pass
