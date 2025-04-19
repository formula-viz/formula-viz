import os

import bpy

from src.modules.render.add_funcs.add_driver_objects import create_car_obj
from src.modules.thumbnail.abstract import (
    ImageMode,
    ThumbnailAbstract,
    ThumbnailInput,
    ThumbnailType,
)
from src.utils import file_utils
from src.utils.colors import hex_to_blender_rgb
from src.utils.logger import log_err, log_info


class FinishLine(ThumbnailAbstract):
    def __init__(self, thumbnail_input: ThumbnailInput):
        """Take only the arguments which are required for the Gen."""
        super().__init__(thumbnail_input, ThumbnailType.FINISH_LINE)
        self.thumbnail_input = thumbnail_input

    def setup_scene(self):
        """Set up the finish line thumbnail scene by loading a pre-built Blender file."""
        scene_path = file_utils.project_paths.FINISH_LINE_SCENE_PATH

        if not os.path.exists(scene_path):
            log_err(f"Scene file not found: {scene_path}")
            raise FileNotFoundError(f"Scene file not found: {scene_path}")

        log_info(f"Loading finish line scene from: {scene_path}")

        bpy.ops.wm.open_mainfile(filepath=str(scene_path))

        if self.image_mode == ImageMode.NO_IMAGE:
            bpy.context.scene.camera = bpy.data.objects["CameraNoImage"]
        elif self.image_mode == ImageMode.ONE_IMAGE:
            bpy.context.scene.camera = bpy.data.objects["CameraOneImage"]
        elif self.image_mode == ImageMode.TWO_IMAGES:
            bpy.context.scene.camera = bpy.data.objects["CameraTwoImages"]

        self._setup_drivers_in_scene()
        log_info("Finish line scene setup complete")

    def render(self):
        """Render the finish line scene using Cycles."""
        super()._cycles_render()

    def _setup_drivers_in_scene(self):
        """Place driver objects/models in the scene based on the provided driver list."""
        # This method will contain the scene-specific setup code for drivers
        log_info(f"Setting up {len(self.thumbnail_input.drivers)} drivers in the scene")

        # Sort drivers by position (lowest numbers first)
        sorted_drivers = sorted(
            self.thumbnail_input.drivers, key=lambda driver: driver.position
        )

        # Create a new collection for cars
        cars_collection = bpy.data.collections.new("CarsCollection")
        bpy.context.scene.collection.children.link(cars_collection)

        first = sorted_drivers[0]
        first_obj, _ = create_car_obj(
            first.team, first.last_name, first.default_driver_color, cars_collection
        )
        first_obj.location = (-1.45, 8.41, 0)
        # Get the car trail material and set its color
        car_one_trail_mat = bpy.data.materials.get("CarOneTrailMat")
        car_one_trail_mat.node_tree.nodes["Emission"].inputs[0].default_value = (
            *hex_to_blender_rgb(first.default_driver_color),
            1,
        )

        if len(sorted_drivers) > 1:
            second = sorted_drivers[1]
            second_obj, _ = create_car_obj(
                second.team,
                second.last_name,
                second.default_driver_color,
                cars_collection,
            )
            second_obj.location = (1.94, 12.1, 0)
            car_two_trail_mat = bpy.data.materials.get("CarTwoTrailMat")
            car_two_trail_mat.node_tree.nodes["Emission"].inputs[0].default_value = (
                *hex_to_blender_rgb(second.default_driver_color),
                1,
            )
        else:
            # Delete CarTwoTrail if no second driver
            car_two_trail = bpy.data.objects.get("CarTwoTrail")
            if car_two_trail:
                bpy.data.objects.remove(car_two_trail, do_unlink=True)

        if len(sorted_drivers) > 2:
            third = sorted_drivers[2]
            third_obj, _ = create_car_obj(
                third.team, third.last_name, third.default_driver_color, cars_collection
            )
            third_obj.location = (-4.44, 13.88, 0)
            car_three_trail_mat = bpy.data.materials.get("CarThreeTrailMat")
            car_three_trail_mat.node_tree.nodes["Emission"].inputs[0].default_value = (
                *hex_to_blender_rgb(third.default_driver_color),
                1,
            )
        else:
            # Delete CarThreeTrail if no third driver
            car_three_trail = bpy.data.objects.get("CarThreeTrail")
            if car_three_trail:
                bpy.data.objects.remove(car_three_trail, do_unlink=True)
