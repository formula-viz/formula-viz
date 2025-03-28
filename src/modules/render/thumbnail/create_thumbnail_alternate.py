"""Given necessary data and setup, will setup the scene, generate the thumbnail, then reset the scene."""

import math

import bpy

from py.render.add_funcs import add_formula_viz_car
from py.render.add_funcs.add_driver_circle import DriverCircle
from py.render.add_funcs.add_driver_objects import (
    create_base_driver_obj,
    create_driver_from_base,
    set_color,
)
from py.render.add_funcs.add_track import create_material, create_planes
from py.utils.colors import CurbColor, MainTrackColor, hex_to_blender_rgb
from py.utils.config import Config
from py.utils.models import Driver
from py.utils.project_structure import IMPACT_FONT


class ThumbnailGenerator:
    def __init__(
        self, config: Config, drivers_in_color_order: list[Driver], colors: list[str]
    ):
        self.config: Config = config
        self.drivers_in_color_order: list[Driver] = drivers_in_color_order
        self.colors: list[str] = colors

        self.dy = 1.5
        self.dx = -3

        self.camera = self._add_thumbnail_camera()
        self._add_cars()
        self._add_titles()
        self._add_formula_viz_car()
        self._add_sample_track()

    def _add_sample_track(self):
        """Add a track element for the thumbnail based on the necessary width."""
        close_points = [(1.5, -1000.0, 0.0), (1.5, 1000.0, 0.0)]

        # here, the first car is actually placed at the origin, so it starts at +1 not 0
        if self.config["type"] == "head-to-head":
            total_width_covered = (len(self.drivers_in_color_order) - 1) * abs(self.dx)

            far_points = [
                (-total_width_covered - 1.5, -1000.0, 0.0),
                (-total_width_covered - 1.5, 1000.0, 0.0),
            ]
        else:
            # there will be 10 drivers across for the 2 rows. 20 drivers total in a quali
            total_width_covered = abs(self.dx) * 3

            far_points = [
                (-total_width_covered - 1.5, -1000.0, 0.0),
                (-total_width_covered - 1.5, 1000.0, 0.0),
            ]

        close_curb_points = [
            (point[0] + 1, point[1], point[2]) for point in close_points
        ]
        far_curb_points = [(point[0] - 1, point[1], point[2]) for point in far_points]

        track_mat = create_material(MainTrackColor.get_scene_rgb(), "ThumbnailMain")
        curb_mat = create_material(CurbColor.get_scene_rgb(), "ThumbnailCurb")

        create_planes(close_points, close_curb_points, "ThumbnailInnerCurb", curb_mat)
        create_planes(far_points, far_curb_points, "ThumbnailOuterCurb", curb_mat)
        create_planes(close_points, far_points, "ThumbnailMain", track_mat)

    def _add_thumbnail_camera(self):
        """Add a camera pointing at the origin (0, 0, 0) for thumbnail rendering."""
        camera_data = bpy.data.cameras.new(name="ThumbnailCamera")
        camera_obj = bpy.data.objects.new("ThumbnailCamera", camera_data)
        bpy.context.scene.collection.objects.link(camera_obj)  # pyright: ignore

        camera_obj.location = (5, -20, 5)
        camera_obj.rotation_euler = (
            math.radians(82),
            0,
            math.radians(26),
        )

        bpy.context.scene.camera = camera_obj  # pyright: ignore
        return camera_obj

    def _add_formula_viz_car(self):
        formula_viz_car_obj = add_formula_viz_car.import_car_collections(None)

        formula_viz_car_obj.location = (-0.16, -0.16, -1)
        formula_viz_car_obj.scale = (0.015, 0.015, 0.015)
        formula_viz_car_obj.rotation_euler = (math.radians(-90), math.radians(44), 0)

        for child in formula_viz_car_obj.children_recursive:
            if child.type == "MESH" and child.data.materials:
                for material in child.data.materials:
                    if material.name == "CAR BASE COLOR" and material.use_nodes:
                        principled_bsdf = material.node_tree.nodes.get(
                            "Principled BSDF"
                        )
                        if principled_bsdf:
                            principled_bsdf.inputs["Base Color"].default_value = (
                                *hex_to_blender_rgb(self.colors[0]),
                                1.0,
                            )

        formula_viz_car_obj.parent = self.camera

    def _add_titles(self):
        """Add title text as a child of the camera for easy positioning."""
        bpy.ops.object.text_add()
        main_title_obj = bpy.context.active_object
        main_title_obj.name = "MainTitle"
        main_title_obj.data.body = self.config["track"]
        main_title_obj.scale = (0.15, 0.15, 0.15)
        main_title_obj.data.align_x = "LEFT"
        main_title_obj.data.font = bpy.data.fonts.load(str(IMPACT_FONT))
        main_title_obj.parent = self.camera
        main_title_obj.location = (-0.34, 0.1, -1)

        sub_title_obj = bpy.ops.object.text_add()
        sub_title_obj = bpy.context.active_object
        sub_title_obj.name = "SubTitle"
        sub_title_obj.data.body = str(self.config["year"])
        sub_title_obj.scale = (0.12, 0.12, 0.12)
        sub_title_obj.data.align_x = "LEFT"
        sub_title_obj.data.font = bpy.data.fonts.load(str(IMPACT_FONT))
        sub_title_obj.parent = self.camera
        sub_title_obj.location = (-0.34, 0.02, -1)

        mat = bpy.data.materials.new("TextMaterial")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes  # pyright: ignore
        nodes.clear()

        # Create emission node
        node_emission = nodes.new("ShaderNodeEmission")
        node_output = nodes.new("ShaderNodeOutputMaterial")

        # Set emission color and strength
        node_emission.inputs["Color"].default_value = (  # pyright: ignore
            *hex_to_blender_rgb(self.colors[0]),
            1,
        )
        node_emission.inputs["Strength"].default_value = 0.4  # pyright: ignore

        # Link nodes
        links = mat.node_tree.links  # pyright: ignore
        links.new(node_emission.outputs[0], node_output.inputs[0])

        main_title_obj.data.materials.append(mat)  # pyright: ignore
        sub_title_obj.data.materials.append(mat)  # pyright: ignore

        return main_title_obj

    def _add_cars(self):
        base_empty_obj = create_base_driver_obj()
        cur_x_offset = 0
        cur_y_offset = 0

        print(f"Drivers in color order: {self.drivers_in_color_order}")
        print(f"Colors: {self.colors}")

        is_first = True
        num = 0
        for driver, color in zip(self.drivers_in_color_order, self.colors):
            if num % 4 == 0 and num != 0:
                cur_x_offset = 0
                cur_y_offset = 10 * num / 4

            driver_obj = create_driver_from_base(driver.last_name, base_empty_obj)
            driver_obj.location = (cur_x_offset, cur_y_offset, 0)

            set_color(driver_obj, color, driver.abbrev)
            if is_first or self.config["type"] == "head-to-head":
                DriverCircle(driver, color, driver_obj, self.camera)

            cur_x_offset += self.dx
            cur_y_offset += self.dy
            is_first = False
            num += 1
