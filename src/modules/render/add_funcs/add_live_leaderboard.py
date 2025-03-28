"""Add a live leaderboard to the scene."""

import bpy
from mathutils import Vector

from py.render.add_funcs.add_driver_circle import DriverCircle
from py.utils.config import Config
from py.utils.logger import log_info
from py.utils.models import Driver
from py.utils.project_structure import Resources


class LiveLeaderboard:
    """Add a live leaderboard to the scene."""

    def __init__(
        self,
        config: Config,
        drivers_and_colors: list[tuple[Driver, str]],
        car_rankings: list[list[tuple[Driver, float]]],
        is_fancy_mode: bool,
        camera_obj: bpy.types.Object,
    ):
        """Create the live leaderboard.

        Args:
            config: Configuration dictionary with rendering settings
            drivers_and_colors: List of driver objects and colors (e.g., [(Driver, '#FF0000'), (Driver, '#00FF00')])
            car_rankings: List of rankings for each frame containing driver-time tuples
            is_fancy_mode: Whether to use fancy rendering mode with driver circles
            camera_obj: The camera object to parent the leaderboard to

        """
        log_info("Initializing LiveLeaderboard...")

        self.config = config
        self.drivers_and_colors = drivers_and_colors
        self.car_rankings = car_rankings
        self.is_fancy_mode = is_fancy_mode
        self.driver_objects: dict[
            Driver, bpy.types.Object
        ] = {}  # Store references to driver objects
        self.camera_obj = camera_obj

        if self.is_fancy_mode:
            self.spacing = 0.055
        else:
            self.spacing = 0.015  # Vertical spacing between elements

        # Create main collection
        self.collection = bpy.data.collections.new("LiveLeaderboard")
        scene = bpy.context.scene
        if not scene:
            raise ValueError("No active scene found")
        scene.collection.children.link(self.collection)  # pyright: ignore

        # Create empty parent object for camera-relative positioning
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))  # pyright: ignore
        parent_empty = bpy.context.active_object
        if not parent_empty:
            raise ValueError("Failed to create parent empty object")
        self.parent_empty = parent_empty
        # ensure the parent empty is not rendered and invisible in viewport
        self.parent_empty.hide_render = True
        self.parent_empty.hide_viewport = True
        self.parent_empty.name = "LeaderboardParent"

        self._parent_to_camera()

        # Initialize
        self.position_offsets = self._get_offsets_dict()
        self._build_initial_objs()
        self._update_driver_positions()

    def _update_driver_positions(self) -> None:
        start_buffer_frames = self.config["render"]["start_buffer_frames"]

        for frame, ranking in enumerate(self.car_rankings):
            if frame % 10 != 0 and frame != len(self.car_rankings) - 1:
                continue

            true_frame = frame + start_buffer_frames
            new_order = [x[0] for x in ranking]
            for idx, driver in enumerate(new_order):
                empty_parent_obj = self.driver_objects[driver]
                empty_parent_obj.location = self.position_offsets[idx + 1]
                empty_parent_obj.keyframe_insert(data_path="location", frame=true_frame)  # pyright: ignore

    def _parent_to_camera(self) -> None:
        """Parent the leaderboard to the camera."""
        self.parent_empty.parent = self.camera_obj

        if self.config["render"]["is_shorts_output"]:
            if self.is_fancy_mode:
                position = (-0.15, 0.29, -1)
            else:
                position = (-0.17, 0.29, -1)
        elif self.is_fancy_mode:
            position = (-0.33, 0.17, -1)
        else:
            position = (-0.35, 0.18, -1)

        self.parent_empty.location = Vector(position)
        self.parent_empty.rotation_euler = self.camera_obj.rotation_euler

    def _build_initial_objs(self) -> None:
        """Create initial objects for each driver in the leaderboard."""
        for idx, (driver, color) in enumerate(self.drivers_and_colors):
            position = idx + 1
            empty_obj = self._create_element_obj(driver, color)
            empty_obj.location = self.position_offsets[position]
            self.driver_objects[driver] = empty_obj

    def _create_element_obj(self, driver: Driver, color: str) -> bpy.types.Object:
        """Create an empty object as parent for the driver's text object.

        Args:
            driver: Driver object
            color: Hex color code for the driver

        Returns:
            bpy.types.Object: Empty object that parents the driver's text

        """
        # Create empty parent for text
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))  # pyright: ignore
        empty_obj = bpy.context.active_object
        if not empty_obj:
            raise ValueError("Failed to create empty object")

        empty_obj.name = f"Empty_{driver.abbrev}"
        empty_obj.hide_render = True
        empty_obj.hide_viewport = True
        empty_obj.parent = self.parent_empty

        # Create driver circle if in fancy mode
        if self.is_fancy_mode:
            self.driver_circle = DriverCircle(
                driver=driver,
                color=color,
                driver_car_obj=None,  # Using empty_obj as the parent
                camera_obj=None,
                pre_existing_empty=empty_obj,
            )
            self.driver_circle.circle_face.scale = (0.015, 0.015, 0.015)

        # Create text object
        if self.is_fancy_mode:
            text_loc = (0.03, -0.009, 0)
        else:
            text_loc = (0, 0, 0)

        bpy.ops.object.text_add(location=text_loc)  # pyright: ignore
        text_obj = bpy.context.active_object
        if not text_obj:
            raise ValueError("Failed to create text object")

        text_obj.name = f"Text_{driver.abbrev}"
        text_curve = text_obj.data
        if not isinstance(text_curve, bpy.types.TextCurve):
            raise TypeError("Expected text_obj.data to be of type bpy.types.TextCurve")

        text_obj.parent = empty_obj

        text_curve.font = bpy.data.fonts.load(str(Resources.get_bold_font()))

        text_curve.align_x = "LEFT"

        if self.is_fancy_mode:
            text_curve.body = driver.last_name.title()
            text_curve.size = 0.03
        else:
            text_curve.body = driver.abbrev
            text_curve.size = 0.02

        # Create material for text
        mat = bpy.data.materials.new(name=f"Material_{driver.abbrev}")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes  # pyright: ignore
        nodes["Principled BSDF"].inputs["Base Color"].default_value = self._hex_to_rgba(  # pyright: ignore
            color
        )
        # 26 and 27 are emission
        nodes["Principled BSDF"].inputs[26].default_value = self._hex_to_rgba(  # pyright: ignore
            color
        )
        nodes["Principled BSDF"].inputs[27].default_value = 0.1  # pyright: ignore

        # Assign material to text
        text_obj.data.materials.append(mat)  # pyright: ignore

        # Link both objects to the main collection
        for obj in [empty_obj, text_obj]:
            for col in obj.users_collection:
                col.objects.unlink(obj)  # pyright: ignore
            self.collection.objects.link(obj)  # pyright: ignore

        return empty_obj

    def _get_offsets_dict(self) -> dict[int, Vector]:
        """Calculate position offsets for each possible position.

        Returns:
            Dict[int, Vector]: Dictionary mapping position numbers to Vector locations

        """
        num_drivers = len(self.drivers_and_colors)
        offsets: dict[int, Vector] = {}
        for position in range(1, num_drivers + 1):
            # Calculate vertical offset (top to bottom)
            y_offset = -(position - 1) * self.spacing
            offsets[position] = Vector((0, y_offset, 0))
        return offsets

    @staticmethod
    def _hex_to_rgba(hex_color: str) -> tuple[float, float, float, float]:
        """Convert hex color to RGBA values."""
        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4))
        return (rgb[0], rgb[1], rgb[2], 1.0)  # Add alpha channel
