"""Given necessary data and setup, will setup the scene, generate the thumbnail, then reset the scene."""

from typing import Optional

import bpy

from py.render.add_funcs import add_formula_viz_car
from py.render.add_funcs.add_driver_objects import (
    create_null_base,
    create_driver_from_base,
    create_team_base,
    set_color,
)
from py.render.add_funcs.add_track import create_material, create_planes
from py.render.render_animation import setup_ui_mode_viewport
from py.render.thumbnail.thumbnail_layouts.abstract_layout import LayoutConfigurer
from py.render.thumbnail.thumbnail_layouts.landscape import LandscapeConfigurer
from py.render.thumbnail.thumbnail_layouts.shorts import ShortsConfigurer
from py.utils.colors import CurbColor, MainTrackColor, hex_to_blender_rgb
from py.utils.config import Config
from py.utils.logger import log_info
from py.utils.models import Driver
from py.utils.project_structure import DriverDataPS


class ThumbnailGenerator:
    """Generate thumbnail images for race visualizations."""

    def __init__(
        self, config: Config, drivers_in_color_order: list[Driver], colors: list[str]
    ):
        """Initialize the ThumbnailGenerator with configuration and driver data.

        Args:
            config: Configuration object containing render settings and other parameters
            drivers_in_color_order: List of Driver objects in the order they should appear in the thumbnail
            colors: List of color hex codes to use for the drivers and visual elements

        Note:
            Currently, thumbnail generation for shorts output is not implemented.

        """
        self.config: Config = config
        self.drivers_in_color_order: list[Driver] = drivers_in_color_order
        self.colors: list[str] = colors

        self.dy = 1.5
        self.dx = -3

        layout_configurer: Optional[LayoutConfigurer] = None
        if config["render"]["is_shorts_output"]:
            layout_configurer = ShortsConfigurer()
        else:
            layout_configurer = LandscapeConfigurer()

        self.camera = self._add_thumbnail_camera()
        layout_configurer.position_camera(self.camera)

        self.cars = self._add_cars()
        layout_configurer.position_cars(self.cars)

        self.formula_viz_car = self._add_formula_viz_car()
        layout_configurer.position_formula_viz_car(self.formula_viz_car)

        self._add_sample_track()

        self.driver_plane = self._add_driver_image()
        layout_configurer.position_driver_image(self.driver_plane)

        self._add_color_background()

        scene = bpy.context.scene
        if not scene:
            raise ValueError("No active scene found")
        if self.config["render"]["is_shorts_output"]:
            scene.render.resolution_x = 1080
            scene.render.resolution_y = 1920
        else:
            scene.render.resolution_x = 3840
            scene.render.resolution_y = 2160

        self._setup_render()
        if config["dev_settings"]["ui_mode"]:
            setup_ui_mode_viewport(config)
        else:
            self._render()

    def _render(self):
        """Render the thumbnail image using Eevee and save it to output/thumbnail.png."""
        log_info("Rendering thumbnail and saving to output/thumbnail.png")
        scene = bpy.context.scene
        if not scene:
            raise ValueError("No active scene found")

        scene.render.engine = "BLENDER_EEVEE"  # pyright: ignore
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = "output/thumbnail.png"

        scene.render.resolution_percentage = 100

        # Render the image
        bpy.ops.render.render(write_still=True)  # pyright: ignore

    def _setup_render(self):
        scene = bpy.context.scene
        if not scene:
            raise ValueError("No active scene found")

        scene.display_settings.display_device = "sRGB"  # type: ignore
        scene.view_settings.view_transform = "AgX"  # type: ignore
        scene.view_settings.look = "AgX - Very High Contrast"  # type: ignore
        scene.view_settings.gamma = 1.3

    def _add_driver_image(self) -> bpy.types.Object:
        # Enable import images as planes addon
        bpy.ops.preferences.addon_enable(module="io_import_images_as_planes")
        image_path = str(
            DriverDataPS.get_driver_image_path(self.drivers_in_color_order[0])
        )

        # the emission here is of the image pixels themselves, so making the image brighter
        bpy.ops.import_image.to_plane(  # pyright: ignore
            files=[{"name": image_path}],
            shader="EMISSION",  # Use emission shader
            emit_strength=0.8,  # Set emission strength to 1.0
        )
        driver_plane = bpy.context.selected_objects[0]
        driver_plane.name = "Driver Image"

        driver_plane.parent = self.camera

        return driver_plane

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

        bpy.context.scene.camera = camera_obj  # pyright: ignore
        return camera_obj

    def _add_formula_viz_car(self) -> bpy.types.Object:
        formula_viz_car_obj = add_formula_viz_car.import_car_collections(None)

        # for child in formula_viz_car_obj.children_recursive:
        #     if child.type == "MESH" and child.data.materials:
        #         for material in child.data.materials:
        #             if material.name == "CAR BASE COLOR" and material.use_nodes:
        #                 principled_bsdf = material.node_tree.nodes.get(
        #                     "Principled BSDF"
        #                 )
        #                 if principled_bsdf:
        #                     principled_bsdf.inputs["Base Color"].default_value = (
        #                         *hex_to_blender_rgb(self.colors[0]),
        #                         1.0,
        #                     )
        formula_viz_car_obj.parent = self.camera
        return formula_viz_car_obj

    def _add_color_background(self):
        """Add a colored background plane for the thumbnail."""
        bpy.ops.mesh.primitive_plane_add(size=2)
        color_plane = bpy.context.active_object
        if not color_plane:
            raise ValueError("Color plane creation failed")
        color_plane.name = "BackgroundColorPlane"

        # Create a new material for the plane
        mat = bpy.data.materials.new(name="BackgroundMaterial")
        mat.use_nodes = True
        node_tree = mat.node_tree
        if not node_tree:
            raise ValueError("Material node tree is None")
        nodes = node_tree.nodes

        # Clear existing nodes and create new emission shader
        nodes.clear()  # pyright: ignore
        emission_node = nodes.new(type="ShaderNodeEmission")
        output_node = nodes.new(type="ShaderNodeOutputMaterial")

        # Set the emission color using the first color from the colors list
        emission_node.inputs["Color"].default_value = (  # pyright: ignore
            *hex_to_blender_rgb(self.colors[0]),
            1.0,
        )
        emission_node.inputs["Strength"].default_value = 1.0  # pyright: ignore

        # Link nodes
        links = node_tree.links
        links.new(emission_node.outputs[0], output_node.inputs[0])

        # Ensure we have a mesh data object with materials
        mesh_data = color_plane.data
        if not mesh_data or not hasattr(mesh_data, "materials"):
            raise ValueError("Color plane data is None or has no materials attribute")

        # Type-check for mesh data with proper materials
        from bpy.types import Mesh

        if not isinstance(mesh_data, Mesh):
            raise TypeError(f"Expected Mesh type, got {type(mesh_data).__name__}")

        mesh_data.materials.append(mat)  # pyright: ignore

        # Set as child of camera and position
        color_plane.parent = self.camera  # pyright: ignore
        color_plane.location = (1, 0, -500)  # pyright: ignore
        color_plane.scale = (1001, 1000, 1000)  # pyright: ignore

    def _add_cars(self) -> list[bpy.types.Object]:
        base_empty_objs_by_team: dict[str, bpy.types.Object] = {}

        cars: list[bpy.types.Object] = []
        for driver, color in zip(self.drivers_in_color_order, self.colors):
            if len(cars) == 3:
                break

            if driver.team in base_empty_objs_by_team:
                base_empty_obj = base_empty_objs_by_team[driver.team]
            else:
                base_empty_obj = create_team_base(driver.team)
                base_empty_objs_by_team[driver.team] = base_empty_obj

            driver_obj = create_driver_from_base(driver.last_name, base_empty_obj)
            set_color(driver_obj, color, driver.abbrev)
            cars.append(driver_obj)
        return cars
