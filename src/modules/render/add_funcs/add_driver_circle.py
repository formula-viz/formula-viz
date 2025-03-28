"""Create a circle above the driver with their face."""

import math
from typing import Optional

import bpy
from mathutils import Vector

from src.models.driver import Driver
from src.utils import file_utils
from src.utils.colors import hex_to_blender_rgb
from src.utils.logger import log_info


class DriverCircle:
    """Create a circle above the driver with their face."""

    def __init__(
        self,
        driver: Driver,
        color: str,  # color will be hex
        driver_car_obj: Optional[bpy.types.Object] = None,
        camera_obj: Optional[bpy.types.Object] = None,
        pre_existing_empty: Optional[bpy.types.Object] = None,
    ):
        """Initialize the DriverCircle object."""
        self.driver = driver
        self.driver_car_obj = driver_car_obj
        self.camera_obj = camera_obj
        self.color = color

        log_info(f"Initializing DriverCircle for {driver.last_name}...")

        if pre_existing_empty:
            parent_empty = pre_existing_empty
        else:
            bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))  # pyright: ignore
            parent_empty = bpy.context.active_object
            parent_empty.hide_render = True  # pyright: ignore
            parent_empty.hide_viewport = True  # pyright: ignore
            parent_empty.name = f"{driver.abbrev}CircleParent"  # pyright: ignore

        if not parent_empty:
            raise ValueError("Failed to create parent empty")

        self._setup(parent_empty)

    def _setup(self, parent_empty: bpy.types.Object):
        self.circle_face = self._create_circle_face()
        outline = self._create_outline()

        # Parent outline to circle face
        outline.parent = self.circle_face
        # Parent circle to empty
        self.circle_face.parent = parent_empty

        # if these are not given, then assume this is in isolated mode
        # we will handle the relative parenting later
        if self.camera_obj and self.driver_car_obj:
            # Parent empty to car
            self._parent_to_car(parent_empty)
            # Add track to camera constraint
            self._add_camera_tracking(parent_empty)

    def _create_circle_face(self) -> bpy.types.Object:
        # Create circular face for the image
        bpy.ops.mesh.primitive_circle_add(radius=1.5, vertices=32, fill_type="NGON")  # pyright: ignore
        circle_obj = bpy.context.active_object
        if not circle_obj:
            raise ValueError("Failed to create circle object")

        circle_obj.name = f"{self.driver.abbrev}CircleFace"

        circle_obj.rotation_euler.z = math.radians(-75)

        # Disable shadow casting, no shadow on the car
        circle_obj.visible_shadow = False
        circle_obj.display.show_shadows = False

        # Create material for the face
        face_mat = bpy.data.materials.new(
            name=f"{self.driver.abbrev}CircleFaceMaterial"
        )
        face_mat.use_nodes = True
        nodes = face_mat.node_tree.nodes  # pyright: ignore
        face_mat.shadow_method = "NONE"  # pyright: ignore
        nodes.clear()  # pyright: ignore

        # Create nodes for image texture
        node_emission = nodes.new("ShaderNodeEmission")
        node_tex = nodes.new("ShaderNodeTexImage")
        node_output = nodes.new("ShaderNodeOutputMaterial")

        # Add UV Map node
        node_uvmap = nodes.new("ShaderNodeUVMap")

        # Load and assign the image
        image_path = file_utils.project_paths.get_driver_image_path(self.driver)
        image = bpy.data.images.load(str(image_path))
        node_tex.image = image  # pyright: ignore

        # Set emission strength
        node_emission.inputs["Strength"].default_value = 1.0  # pyright: ignore

        # Link nodes
        links = face_mat.node_tree.links  # pyright: ignore
        # UV to Image Texture
        links.new(node_uvmap.outputs[0], node_tex.inputs[0])
        # Color to emission
        links.new(node_tex.outputs[0], node_emission.inputs[0])
        links.new(node_emission.outputs[0], node_output.inputs[0])

        # Add material to object
        circle_obj.data.materials.append(face_mat)  # pyright: ignore

        # Ensure proper UV mapping
        bpy.context.view_layer.objects.active = circle_obj  # pyright: ignore
        bpy.ops.object.mode_set(mode="EDIT")  # pyright: ignore
        bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.001)  # pyright: ignore
        bpy.ops.object.mode_set(mode="OBJECT")  # pyright: ignore

        return circle_obj

    def _create_outline(self) -> bpy.types.Object:
        # Create torus for the outline
        bpy.ops.mesh.primitive_torus_add(  # pyright: ignore
            major_radius=1.5,  # Radius of the circle
            minor_radius=0.03,  # Thickness of the outline
            major_segments=128,  # Segments of the circle
            minor_segments=32,  # Segments of the tube
        )
        outline = bpy.context.active_object
        if not outline:
            raise ValueError("Failed to create outline object")

        outline.name = f"{self.driver.abbrev}CircleOutline"

        # Disable shadow casting, no shadow on the car
        outline.visible_shadow = False
        outline.display.show_shadows = False

        # Create material for the outline
        outline_mat = bpy.data.materials.new(
            name=f"{self.driver.abbrev}CircleOutlineMaterial"
        )
        outline_mat.use_nodes = True
        nodes = outline_mat.node_tree.nodes  # pyright: ignore
        outline_mat.shadow_method = "NONE"  # pyright: ignore
        nodes.clear()  # pyright: ignore

        # Create emission node
        node_emission = nodes.new("ShaderNodeEmission")
        node_output = nodes.new("ShaderNodeOutputMaterial")

        # Set emission color and strength
        node_emission.inputs["Color"].default_value = (  # pyright: ignore
            *hex_to_blender_rgb(self.color),
            1,
        )
        node_emission.inputs["Strength"].default_value = 0.4  # pyright: ignore

        # Link nodes
        links = outline_mat.node_tree.links  # pyright: ignore
        links.new(node_emission.outputs[0], node_output.inputs[0])

        outline.data.materials.append(outline_mat)  # pyright: ignore
        return outline

    def _parent_to_car(self, parent_empty: bpy.types.Object) -> None:
        """Parent the circle to the car and position it above."""
        parent_empty.parent = self.driver_car_obj
        parent_empty.location = Vector((0, 0, 3.5))

    def _add_camera_tracking(self, parent_empty: bpy.types.Object) -> None:
        """Add constraint to make circle face camera."""
        constraint = parent_empty.constraints.new("TRACK_TO")
        constraint.target = self.camera_obj  # pyright: ignore
        constraint.track_axis = "TRACK_Z"  # pyright: ignore
        constraint.up_axis = "UP_Y"  # pyright: ignore
