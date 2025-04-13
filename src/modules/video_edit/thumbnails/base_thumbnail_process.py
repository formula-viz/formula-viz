"""Base class for thumbnail processing operations in Formula Viz.

Handles common operations like setup, color borders, and icon placement.
"""

from abc import ABC, abstractmethod

import bpy

from src.models.app_state import AppState
from src.models.config import Config
from src.utils import file_utils


class ThumbnailProcess(ABC):
    """Base class for thumbnail processing operations in Formula Viz.

    Handles common operations like setup, color borders, and icon placement.
    """

    def __init__(
        self, config: Config, app_state: AppState, raw_path: str, output_path: str
    ):
        """Initialize the ThumbnailProcess class.

        Args:
            config (Config): The configuration object.
            app_state (AppState): The application state object.
            raw_path (str): The path to the raw input image file.
            output_path (str): The path where the processed thumbnail will be saved.

        """
        self.config = config
        self.app_state = app_state
        self.seq_editor = bpy.context.scene.sequence_editor
        self.cur_channel = 1
        self.raw_path = raw_path
        self.output_path = output_path

        # Assign colors and icon paths based on sort section
        self.base_color, self.circle_icon_path = self._assign_color()

        self._setup_scene()
        self._process()
        self._save()

    def _assign_color(self):
        """Determine the base color and icon path based on the sort section.

        Returns:
            tuple: A tuple containing (base_color, circle_icon_path)

        """
        if self.config["sort_section"] == "standard":
            return (
                0,
                1,
                1,
            ), file_utils.project_paths.FORMULA_VIZ_CIRCLE_ICON_PATH  # Cyan
        elif self.config["sort_section"] == "historical":
            return (
                1,
                0.5,
                0,
            ), file_utils.project_paths.FORMULA_VIZ_CIRCLE_ICON_PATH_ORANGE  # Orange
        elif self.config["sort_section"] == "recap":
            return (
                0.9,
                0,
                0.9,
            ), file_utils.project_paths.FORMULA_VIZ_CIRCLE_ICON_PATH_PURPLE  # Purple
        else:
            raise ValueError("Invalid sort section")

    def _setup_scene(self):
        """Set up the scene with proper resolution."""
        bpy.context.scene.render.resolution_x = 1920
        bpy.context.scene.render.resolution_y = 1080
        bpy.context.scene.render.resolution_percentage = 80

    def _process(self):
        """Process."""
        self._add_raw()
        self._add_specific_elements()  # Abstract method to be implemented by subclasses
        self._add_color_border()
        self._add_formula_viz_circle_icon()

    def _save(self):
        """Render and save the thumbnail."""
        scene = bpy.context.scene
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = self.output_path

        # Render the current frame
        bpy.ops.render.render(write_still=True)

    def _add_raw(self):
        """Add the raw base image."""
        self.seq_editor.sequences.new_image(
            name="RawImage",
            filepath=self.raw_path,
            channel=self.cur_channel,
            frame_start=1,
        )
        self.cur_channel += 1

    def _add_color_border(self):
        """Add color border around the thumbnail."""

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

        left.transform.offset_x = -937
        right.transform.offset_x = 937
        left.transform.scale_x = 0.03
        right.transform.scale_x = 0.03

        top.transform.scale_y = 0.045
        bottom.transform.scale_y = 0.045
        top.transform.offset_y = 522
        bottom.transform.offset_y = -522

        left.color = self.base_color
        right.color = self.base_color
        top.color = self.base_color
        bottom.color = self.base_color

    def _add_formula_viz_circle_icon(self):
        """Add the Formula Viz circle icon."""
        circle_icon = self.seq_editor.sequences.new_image(
            name="CircleIcon",
            filepath=str(self.circle_icon_path),
            channel=self.cur_channel,
            frame_start=1,
        )
        self.cur_channel += 1

        # Adjust position and scale as needed
        circle_icon.transform.scale_x = 0.15
        circle_icon.transform.scale_y = 0.15

        circle_icon.transform.offset_x = -730
        circle_icon.transform.offset_y = 310

    @abstractmethod
    def _add_specific_elements(self):
        """Add thumbnail-specific elements - to be implemented by subclasses."""
        pass
