"""Add social media links and other outro elements at the end of the video."""

import math
import os

import bpy
from bpy.types import Object
from mathutils import Vector

from src.models.config import Config
from src.utils import file_utils
from src.utils.logger import log_err, log_info


class Outro:
    """Add social media links and other outro elements at the end of the video."""

    def __init__(self, config: Config, camera_obj: Object, num_frames: int):
        """Add social media links and other outro elements at the end of the video."""
        log_info("Initializing Outro...")
        self.config = config
        self.camera_obj = camera_obj
        self.num_frames = num_frames

        # Create a collection to store all outro objects
        self.outro_collection = bpy.data.collections.new("Outro_Elements")
        bpy.context.scene.collection.children.link(self.outro_collection)  # pyright: ignore

        # Create parent empty object
        self.parent_empty = bpy.data.objects.new("Outro_Parent", None)
        self.outro_collection.objects.link(self.parent_empty)  # pyright: ignore
        self.parent_empty.hide_viewport = True
        self.parent_empty.hide_render = True
        self._parent_to_camera(self.camera_obj, self.parent_empty)
        self.parent_empty.scale = Vector((0.05, 0.05, 0.05))

        self.text_material = self._create_text_material()

        self._create_all_outro_elements()

    def _create_text_material(self):
        """Create a shared white text material."""
        material = bpy.data.materials.new(name="Shared_Text_Material")
        material.use_nodes = True
        nodes = material.node_tree.nodes  # pyright: ignore
        nodes["Principled BSDF"].inputs["Base Color"].default_value = (  # pyright: ignore
            0.95,
            0.95,
            0.95,
            1,
        )
        nodes["Principled BSDF"].inputs["Metallic"].default_value = 1.0  # pyright: ignore
        material.shadow_method = "NONE"  # pyright: ignore
        return material

    def _add_formula_viz_icon(self, location):
        bpy.ops.preferences.addon_enable(module="io_import_images_as_planes")
        image_path = str(file_utils.project_paths.FORMULA_VIZ_ICON_PATH)

        # Check if the file exists
        if not os.path.exists(image_path):
            log_err(f"Formula viz icon not found at {image_path}")
            return None

        # the emission here is of the image pixels themselves, so making the image brighter
        bpy.ops.import_image.to_plane(  # pyright: ignore
            files=[{"name": image_path}],
            shader="EMISSION",  # Use emission shader
            emit_strength=0.8,  # Set emission strength to 1.0
        )
        formula_viz_icon = bpy.context.selected_objects[0]
        formula_viz_icon.name = "FormulaVizIcon"
        formula_viz_icon.location = location
        formula_viz_icon.scale = (0.3, 0.3, 0.3)

        formula_viz_icon.data.materials[0].shadow_method = "NONE"  # pyright: ignore
        formula_viz_icon.parent = self.parent_empty

        return formula_viz_icon

    def _create_social_element(
        self, offset: Vector, image_path: str, title: str, platform: str
    ):
        """Create a social media element with platform icon and username."""
        # Enable import images as planes addon
        bpy.ops.preferences.addon_enable(module="io_import_images_as_planes")  # pyright: ignore

        # Import image as plane
        bpy.ops.import_image.to_plane(files=[{"name": image_path}])  # pyright: ignore
        icon_plane = bpy.context.selected_objects[0]
        icon_plane.name = f"Icon_{platform}"
        # set rotation in degrees
        icon_plane.rotation_euler = Vector(  # pyright: ignore
            (math.radians(180), math.radians(180), math.radians(180))
        )  # pyright: ignore

        # Create text for username/handle
        text_curve = bpy.data.curves.new(name=f"Text_{platform}", type="FONT")
        text_obj = bpy.data.objects.new(name=f"Text_{platform}", object_data=text_curve)
        self.outro_collection.objects.link(text_obj)  # pyright: ignore

        text_obj.data.body = title  # pyright: ignore
        text_obj.data.align_x = "LEFT"  # pyright: ignore
        text_obj.data.align_y = "CENTER"  # pyright: ignore
        text_obj.data.font = bpy.data.fonts.load(
            str(file_utils.project_paths.MAIN_FONT)
        )  # pyright: ignore
        text_obj.data.size = 0.5  # pyright: ignore

        # Assign shared text material
        text_obj.data.materials.append(self.text_material)  # pyright: ignore

        # Create empty to group icon and text
        group_empty = bpy.data.objects.new(f"Social_{platform}", None)
        self.outro_collection.objects.link(group_empty)  # pyright: ignore
        group_empty.hide_viewport = True
        group_empty.hide_render = True

        # Parent icon and text to group empty
        icon_plane.parent = group_empty
        text_obj.parent = group_empty

        # Position elements relative to each other
        icon_plane.location = Vector((0, 0, 0))
        text_obj.location = Vector((0.7, 0, 0))  # Offset text to right of icon

        # Parent group to main outro parent and apply offset
        group_empty.parent = self.parent_empty
        group_empty.location = offset

        return group_empty

    def _create_solid_background_plane(self, color=(0.000116, 0, 0.004111, 1)):
        """Create a plain background plane with solid color.

        Args:
            color: RGBA color tuple with values from 0-1, defaults to black

        Returns:
            The created background plane object

        """
        bpy.ops.mesh.primitive_plane_add(size=11.0)  # pyright: ignore
        bg_plane = bpy.context.active_object
        bg_plane.name = "SolidOutroBackground"  # pyright: ignore

        # Create solid color material
        bg_mat = bpy.data.materials.new(name="SolidOutroBackgroundMaterial")
        bg_mat.use_nodes = True
        nodes = bg_mat.node_tree.nodes  # pyright: ignore

        # Set the color of the principled BSDF shader
        principled = nodes.get("Principled BSDF")
        if principled:
            principled.inputs["Base Color"].default_value = color  # pyright: ignore
            principled.inputs["Roughness"].default_value = 1.0  # pyright: ignore

        bg_plane.data.materials.append(bg_mat)  # pyright: ignore
        bg_plane.parent = self.parent_empty  # pyright: ignore

        # Position it slightly behind other elements
        bg_plane.location = Vector((0, 0, -1))  # pyright: ignore
        if self.config["render"]["is_shorts_output"]:
            bg_plane.scale = (1.47, 0.83, 0)  # pyright: ignore
        else:
            bg_plane.scale = (1.12, 0.64, 0)  # pyright: ignore

        return bg_plane

    def _create_background_plane(self):
        """Create a semi-transparent black background plane."""
        bpy.ops.mesh.primitive_plane_add(size=11.0)  # pyright: ignore
        bg_plane = bpy.context.active_object
        bg_plane.name = "Outro_Background"  # pyright: ignore

        # Create semi-transparent black material
        bg_mat = bpy.data.materials.new(name="Outro_Background_Material")
        bg_mat.use_nodes = True
        bg_mat.blend_method = "BLEND"  # Enable transparency
        nodes = bg_mat.node_tree.nodes  # pyright: ignore
        links = bg_mat.node_tree.links  # pyright: ignore
        nodes.clear()  # pyright: ignore

        # Set up principled shader with transparency
        principled = nodes.new("ShaderNodeBsdfPrincipled")
        output = nodes.new("ShaderNodeOutputMaterial")

        # Set to black with transparency
        principled.inputs["Base Color"].default_value = (0.000076, 0, 0.00262, 1)  # pyright: ignore
        principled.inputs["Alpha"].default_value = 0.95  # pyright: ignore

        links.new(principled.outputs[0], output.inputs[0])

        bg_plane.data.materials.append(bg_mat)  # pyright: ignore
        bg_plane.parent = self.parent_empty  # pyright: ignore

        # Position it slightly behind other elements
        bg_plane.location = Vector((0, 0, -1))  # pyright: ignore
        if self.config["render"]["is_shorts_output"]:
            bg_plane.scale = (0.64, 1.13, 0)  # pyright: ignore
        else:
            bg_plane.scale = (1.12, 0.64, 0)  # pyright: ignore

        return bg_plane

    def _create_text(self, text: str, name: str, size: float, location: Vector):
        """Create bottom text element."""
        text_curve = bpy.data.curves.new(name=name, type="FONT")
        text_obj = bpy.data.objects.new(name, object_data=text_curve)
        self.outro_collection.objects.link(text_obj)  # pyright: ignore

        text_obj.data.body = text  # pyright: ignore
        text_obj.data.align_x = "CENTER"  # pyright: ignore
        text_obj.data.align_y = "CENTER"  # pyright: ignore
        text_obj.data.font = bpy.data.fonts.load(
            str(file_utils.project_paths.MAIN_FONT)
        )  # pyright: ignore
        text_obj.data.size = size  # pyright: ignore

        # Assign shared text material
        text_obj.data.materials.append(self.text_material)  # pyright: ignore

        text_obj.parent = self.parent_empty
        text_obj.location = location

        return text_obj

    def _create_all_outro_elements(self):
        """Create all outro elements with visibility animation."""
        # self._create_solid_background_plane()
        self._create_background_plane()

        self._add_formula_viz_icon(Vector((-0.65, 0.4, 0)))
        self._create_text(
            "formula-viz", "FormulaVizOutroText", 0.4, Vector((0.2, 0.4, 0))
        )

        self._create_text(
            "Uploading every formula 1 qualifying session",
            "UploadingOutroText",
            0.3,
            Vector((0, -0.33, 0)),
        )

        self._create_text(
            "Join the discord to make suggestions",
            "JoinDiscordOutroText",
            0.3,
            Vector((0, -0.68, 0)),
        )

        # # Create social media elements
        # cur_loc = Vector((0, -1.5, 0))
        # offset = Vector((0, 1.5, 0))

        # # Add bottom text at the end
        # self._create_social_element(
        #     cur_loc, str(DISCORD_ICON_PATH), "discord.gg/formula-viz", "discord"
        # )

        # cur_loc += offset
        # self._create_social_element(
        #     cur_loc, str(TIKTOK_ICON_PATH), "@formula-viz", "tiktok"
        # )

        # cur_loc += offset
        # self._create_social_element(
        #     cur_loc, str(INSTAGRAM_ICON_PATH), "@formula-viz", "instagram"
        # )

        # cur_loc += offset
        # self._create_social_element(
        #     cur_loc, str(YOUTUBE_ICON_PATH), "youtube.com/formula-viz", "youtube"
        # )

    def _parent_to_camera(self, camera_obj: Object, element_obj: Object) -> None:
        """Parent the outro element to the camera."""
        element_obj.parent = camera_obj
        end_buffer = self.config["render"]["end_buffer_frames"]

        if self.config["render"]["is_shorts_output"]:
            final_position = (0.0, 0.0, -0.8)
            start_position = (0.0, 2.0, -0.8)
        else:
            # TODO, modify to support 4k landscape mode
            final_position = (0.0, 0.0, -0.8)
            start_position = (0.0, 5.0, -0.8)

        # Set initial position
        element_obj.location = Vector(start_position)
        element_obj.keyframe_insert(data_path="location", frame=0)  # pyright: ignore

        element_obj.keyframe_insert(  # pyright: ignore
            data_path="location", frame=self.num_frames - end_buffer - 20
        )

        # Animate to final position
        element_obj.location = Vector(final_position)
        element_obj.keyframe_insert(  # pyright: ignore
            data_path="location", frame=self.num_frames - end_buffer + 30
        )

        element_obj.rotation_euler = camera_obj.rotation_euler
