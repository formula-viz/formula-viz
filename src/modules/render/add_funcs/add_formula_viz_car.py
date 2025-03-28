"""Places the formula-viz channel car in the scene as a watermark."""

import colorsys
import math
import time
from typing import Optional

import bpy

from src.utils import file_utils
from src.utils.logger import log_info


def import_car_collections(animated_color_mat: Optional[bpy.types.Material]):
    """Import car collections from the external blend file."""
    with bpy.data.libraries.load(
        str(file_utils.project_paths.FORMULA_VIZ_CAR_PATH)
    ) as (data_from, data_to):
        data_to.collections = ["FORMULA VIZ CAR BODY", "FORMULA VIZ CAR DETAILS"]

    scene = bpy.context.scene
    if scene is None:
        raise ValueError("No active scene found")

    # Create a parent collection for Formula Viz Car
    parent_collection = bpy.data.collections.new("FormulaVizCar")
    scene.collection.children.link(parent_collection)

    # Link imported collections as children to the parent collection instead
    for collection in data_to.collections:
        if collection is not None:
            if isinstance(collection, bpy.types.Collection):
                parent_collection.children.link(collection)

    car_obj = bpy.data.objects.get("FORMULA VIZ CAR")
    if car_obj is None:
        raise ValueError(
            "Could not find the FORMULA VIZ CAR object in the imported file"
        )

    if animated_color_mat:
        car_obj.data.materials[0] = animated_color_mat  # pyright: ignore

        wing1 = bpy.data.objects.get("WING 1")
        wing1.data.materials[0] = animated_color_mat  # pyright: ignore

        wing2 = bpy.data.objects.get("WING 2")
        wing2.data.materials[0] = animated_color_mat  # pyright: ignore

    car_obj.location = (-0.02, 0, 0)
    car_obj.scale = (0.003, 0.003, 0.003)

    return car_obj


def create_parent_empty(
    camera_obj: bpy.types.Object, is_shorts_output: bool
) -> bpy.types.Object:
    """Create an empty parent object for positioning."""
    if is_shorts_output:
        location = (-0.15, 0.28, -1)
        scale = (0.8, 0.8, 0.8)
    else:
        location = (-0.04, -0.12, -1)
        scale = (0.7, 0.7, 0.7)

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=location)
    empty_parent = bpy.context.active_object
    if not isinstance(empty_parent, bpy.types.Object):
        raise ValueError("Failed to create empty parent object")

    empty_parent.name = "CarAndTextParent"
    empty_parent.scale = scale

    empty_parent.hide_viewport = True
    empty_parent.hide_render = True

    empty_parent.parent = camera_obj
    return empty_parent


def create_text_object(animated_color_mat: bpy.types.Material):
    """Create and configure text object for the scene."""
    bpy.ops.object.text_add(location=(0.015, 0, 0))
    text_obj = bpy.context.active_object
    if not isinstance(text_obj, bpy.types.Object):
        raise ValueError("Failed to create text object")

    text_obj.name = "FormulaVizText"

    text_data = text_obj.data
    if not isinstance(text_data, bpy.types.TextCurve):
        raise ValueError("Failed to create text object: data is not a TextCurve")

    text_data.body = "formula-viz"
    text_data.font = bpy.data.fonts.load(str(file_utils.project_paths.IMPACT_FONT))
    text_data.size = 0.05

    text_obj.data.materials.append(animated_color_mat)  # pyright: ignore

    return text_obj


def setup_car_animation(car_obj: bpy.types.Object, is_shorts_output: bool):
    """Set up rotation animation for the car with continuous back-and-forth motion."""
    start_y_rotation = math.radians(21)
    middle_y_rotation = math.radians(-15)

    if is_shorts_output:
        x_rot = math.radians(-70)
    else:
        x_rot = math.radians(-86)

    car_obj.rotation_euler = (x_rot, start_y_rotation, 0)

    start_frame = 1
    cycle_length = 120

    # Create multiple keyframes for continuous animation
    for i in range(4):
        current_frame = start_frame + (i * cycle_length)
        car_obj.rotation_euler = (x_rot, start_y_rotation, 0)
        car_obj.keyframe_insert(data_path="rotation_euler", frame=current_frame)

        middle_frame = current_frame + (cycle_length // 2)
        car_obj.rotation_euler = (x_rot, middle_y_rotation, 0)
        car_obj.keyframe_insert(data_path="rotation_euler", frame=middle_frame)

    final_frame = start_frame + (4 * cycle_length)
    car_obj.rotation_euler = (x_rot, start_y_rotation, 0)
    car_obj.keyframe_insert(data_path="rotation_euler", frame=final_frame)

    # Make the animation cycle by setting up a modifier
    if car_obj.animation_data and car_obj.animation_data.action:
        action = car_obj.animation_data.action
        for fcurve in action.fcurves:
            if (
                fcurve.data_path == "rotation_euler" and fcurve.array_index == 1
            ):  # Y rotation
                # Set interpolation to bezier for smooth motion
                for keyframe in fcurve.keyframe_points:
                    keyframe.interpolation = "BEZIER"
                    keyframe.easing = "EASE_IN_OUT"

                # Add cyclic modifier to make the animation repeat indefinitely
                modifier = fcurve.modifiers.new("CYCLES")
                # The type system doesn't recognize mode_before/mode_after properties,
                # but they exist at runtime in Blender's Python API
                modifier.mode_before = "REPEAT_OFFSET"  # type: ignore
                modifier.mode_after = "REPEAT_OFFSET"  # type: ignore

    # Reset to initial rotation for rendering
    car_obj.rotation_euler = (x_rot, start_y_rotation, 0)


def create_animated_color() -> bpy.types.Material:
    """Create an animated material with color cycling."""
    material = bpy.data.materials.new(name="AnimatedColorMaterial")
    material.use_nodes = True

    principled_bsdf = material.node_tree.nodes.get("Principled BSDF")  # pyright: ignore
    if principled_bsdf:
        # Get the Base Color input
        base_color_input = principled_bsdf.inputs["Base Color"]
        metallic = principled_bsdf.inputs[1]
        metallic.default_value = 0.5  # pyright: ignore
        # emission = principled_bsdf.inputs[26]
        # principled_bsdf.inputs[27].default_value = 0.3  # pyright: ignore

        # Set keyframes for color cycling - use a shorter cycle for color
        color_cycle_length = 240  # Complete color cycle in 240 frames
        max_expected_frames = 3000

        # Create a series of keyframes for color cycling
        for frame in range(1, max_expected_frames, 30):
            # Calculate hue value based on frame (0-1 range)
            # Using a different cycle length than rotation for visual interest
            hue = ((frame - 1) % color_cycle_length) / color_cycle_length

            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)

            # Set current frame
            bpy.context.scene.frame_set(frame)  # pyright: ignore

            # Set color and create keyframe
            base_color_input.default_value = (r, g, b, 1.0)  # pyright: ignore
            # emission.default_value = (r, g, b, 1.0)  # pyright: ignore
            base_color_input.keyframe_insert("default_value", frame=frame)

    return material


def main(camera_obj: bpy.types.Object, is_shorts_output: bool):
    """Import formula-viz car from blend file and position it in front of the camera.

    Args:
        camera_obj: The Blender camera object to parent the car to
        is_shorts_output: Whether the output is phone resolution or not

    Returns:
        The imported car object

    """
    log_info("Adding formula viz car watermark.")
    start_time = time.time()

    empty_parent = create_parent_empty(camera_obj, is_shorts_output)

    animated_color_mat = create_animated_color()
    car_obj = import_car_collections(animated_color_mat)
    text_obj = create_text_object(animated_color_mat)

    car_obj.parent = empty_parent
    text_obj.parent = empty_parent

    setup_car_animation(car_obj, is_shorts_output)

    log_info(
        f"Formula viz car watermark added in {time.time() - start_time:.2f} seconds"
    )
    return car_obj
