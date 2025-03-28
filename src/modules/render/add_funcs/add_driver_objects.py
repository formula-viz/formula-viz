"""Create all drivers and return a dictionary mapping driver abbreviations to their objects given the driver data."""

import math
import os
import time
from typing import Optional

import bpy
import mathutils
import numpy as np
import pandas as pd
from PIL import Image

from src.models.driver import Driver
from src.utils import file_utils
from src.utils.colors import hex_to_blender_rgb, hex_to_normal_rgb
from src.utils.logger import log_info


def scale_and_position_car(empty_obj: bpy.types.Object):
    # Calculate the bounds of all objects together
    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")

    for obj in empty_obj.children_recursive:
        # Calculate object bounds in world space
        for v in obj.bound_box:
            world_v = obj.matrix_world @ mathutils.Vector(v)
            min_x = min(min_x, world_v.x)
            max_x = max(max_x, world_v.x)
            min_y = min(min_y, world_v.y)
            max_y = max(max_y, world_v.y)
            min_z = min(min_z, world_v.z)
            max_z = max(max_z, world_v.z)

    # Calculate center of bounds, but keep bottom at z=0
    center_x = (min_x + max_x) / 2
    center_y = max_y  # Place back of the car at y=0 for finish start line sync
    center_z = min_z  # Set z-offset to min_z to place bottom at z=0

    # Calculate current width and scaling factor
    current_width = max_x - min_x
    scale_factor = 3.0 / current_width if current_width > 0 else 1.0

    for child in empty_obj.children:
        cur_scale = child.scale
        child.scale = (
            cur_scale[0] * scale_factor,
            cur_scale[1] * scale_factor,
            cur_scale[2] * scale_factor,
        )
        cur_loc = child.location
        child.location = (
            (cur_loc[0] - center_x) * scale_factor,
            (cur_loc[1] - center_y) * scale_factor,
            (cur_loc[2] - center_z) * scale_factor,
        )


def create_car_obj(team_id: str, driver_last_name: str):
    """Create a base F1 car object that will be used as a template for this team."""
    # Create empty object to serve as parent
    bpy.ops.object.empty_add(type="PLAIN_AXES")
    empty_obj = bpy.context.object
    if empty_obj is None:
        raise ValueError("Failed to create empty object")
    empty_obj.name = f"{driver_last_name}{team_id}Car"
    empty_obj.hide_viewport = True
    empty_obj.hide_render = True

    blend_file_path = (
        f"{file_utils.project_paths.BLENDER_DIR}/f1-2025-cars/{team_id}.blend"
    )
    with bpy.data.libraries.load(blend_file_path) as (data_from, data_to):
        data_to.objects = data_from.objects

    # First link all objects to scene to preserve relationships
    for obj in data_to.objects:
        if obj is not None:
            bpy.context.scene.collection.objects.link(obj)

    # Now handle parenting after all objects exist in scene
    for obj in data_to.objects:
        obj.name = f"{driver_last_name}-{obj.name}"
        if obj is not None and obj.parent is None:
            # Top level objects become children of empty
            obj.parent = empty_obj

    scale_and_position_car(empty_obj)
    if team_id == "Williams":
        for child in empty_obj.children:
            child.location = (
                child.location[0],
                child.location[1],
                child.location[2] - 0.13,
            )

    return empty_obj


def create_team_base(team_id: str):
    """Create a base F1 car object that will be used as a template for this team."""
    # Create empty object to serve as parent
    bpy.ops.object.empty_add(type="PLAIN_AXES")
    empty_obj = bpy.context.object
    if empty_obj is None:
        raise ValueError("Failed to create empty object")
    empty_obj.name = f"Team{team_id}EmptyCar"
    empty_obj.hide_viewport = True
    empty_obj.hide_render = True

    blend_file_path = (
        f"{file_utils.project_paths.BLENDER_DIR}/f1-2025-cars/{team_id}.blend"
    )
    with bpy.data.libraries.load(blend_file_path) as (data_from, data_to):
        data_to.objects = data_from.objects

    # First link all objects to scene to preserve relationships
    for obj in data_to.objects:
        if obj is not None:
            bpy.context.scene.collection.objects.link(obj)

    # Now handle parenting after all objects exist in scene
    for obj in data_to.objects:
        if obj is not None and obj.parent is None:
            # Top level objects become children of empty
            obj.parent = empty_obj

    scale_and_position_car(empty_obj)
    return empty_obj


def create_null_base():
    """Create a base F1 car object that will be used as a template for all drivers."""
    bpy.ops.object.empty_add(type="PLAIN_AXES")
    empty_obj = bpy.context.object
    if empty_obj is None:
        raise ValueError("Failed to create empty object")

    empty_obj.name = "MasterEmptyCar"
    empty_obj.hide_viewport = True
    empty_obj.hide_render = True

    with bpy.data.libraries.load(
        str(file_utils.project_paths.BLENDER_DIR / "f1-2024-generic.blend")
    ) as (data_from, data_to):
        data_to.objects = data_from.objects

    for obj in data_to.objects:
        obj.parent = empty_obj

    scale_and_position_car(empty_obj)
    # Im not sure why this is necessary, but this fixes the floating car problem
    for obj in empty_obj.children:
        cur_loc = obj.location
        obj.location = cur_loc + mathutils.Vector((0, 0, -0.8))
    return empty_obj


def create_driver_from_base(driver_abbrev: str, base_empty_obj: bpy.types.Object):
    """Create a driver object by copying the base empty object and its children."""
    driver_collection = bpy.data.collections.new(f"{driver_abbrev.title()}CarObject")
    bpy.context.scene.collection.children.link(driver_collection)

    def copy_object_and_children(src_obj, parent_obj):
        new_obj = src_obj.copy()
        if src_obj.data:
            new_obj.data = src_obj.data.copy()

        new_obj.name = f"{driver_abbrev.title()}Car-{src_obj.name}"
        driver_collection.objects.link(new_obj)

        new_obj.parent = parent_obj
        # Ensure transforms are properly copied
        new_obj.matrix_local = src_obj.matrix_local.copy()
        new_obj.matrix_parent_inverse = src_obj.matrix_parent_inverse.copy()

        # # Copy constraints if any
        # for constraint in src_obj.constraints:
        #     new_constraint = new_obj.constraints.new(constraint.type)
        #     # Copy constraint properties
        #     for prop in constraint.bl_rna.properties:
        #         if not prop.is_readonly:
        #             setattr(
        #                 new_constraint,
        #                 prop.identifier,
        #                 getattr(constraint, prop.identifier),
        #             )

        # # Handle materials if needed
        # if new_obj.material_slots:
        #     for i, slot in enumerate(new_obj.material_slots):
        #         if slot.material:
        #             # Create a deep copy of the material
        #             new_material = slot.material.copy()
        #             new_material.name = f"{driver_abbrev.title()}-{slot.material.name}"
        #             new_obj.material_slots[i].material = new_material

        # Recursively handle children
        for child in src_obj.children:
            copy_object_and_children(child, new_obj)

        return new_obj

    # Create new empty and copy its properties
    new_empty = base_empty_obj.copy()
    new_empty.name = f"{driver_abbrev.title()}MasterEmpty"
    if base_empty_obj.data:
        new_empty.data = base_empty_obj.data.copy()
    driver_collection.objects.link(new_empty)

    new_empty.matrix_world = base_empty_obj.matrix_world.copy()

    for obj in base_empty_obj.children:
        copy_object_and_children(obj, new_empty)

    return new_empty


# Time,X,Y,Z,RotW,RotX,RotY,RotZ
def add_driver_keyframes(driver_obj, df):
    """Add keyframes to driver object based on dataframe values."""
    # Pre-fetch all the data we'll need to avoid repeated lookups
    x_values = df["X"]
    y_values = df["Y"]
    rot_w = df["RotW"]
    rot_x = df["RotX"]
    rot_y = df["RotY"]
    rot_z = df["RotZ"]
    tire_rot = df["TireRot"]
    # harsher_rot_z = df["HarsherRotZ"]

    # Prepare driver keyframes
    driver_loc_keyframes = []
    driver_rot_keyframes = []
    for i in range(len(df)):
        frame = i + 1
        point = mathutils.Vector((x_values[i], y_values[i], 0))

        rot_quat = mathutils.Quaternion((rot_w[i], rot_x[i], rot_y[i], rot_z[i]))
        rot_eul = rot_quat.to_euler()

        driver_loc_keyframes.append((point, frame))
        driver_rot_keyframes.append((rot_eul, frame))

    # Apply driver keyframes in batch
    for point, frame in driver_loc_keyframes:
        driver_obj.location = point
        driver_obj.keyframe_insert(data_path="location", frame=frame)

    for rot_eul, frame in driver_rot_keyframes:
        driver_obj.rotation_euler = rot_eul
        driver_obj.keyframe_insert(data_path="rotation_euler", frame=frame)

    # Find and animate all pyrotate objects recursively
    def animate_pyrotate_objects(obj):
        for child in obj.children:
            if "pyrotate" in child.name.lower():
                for i in range(len(df)):
                    frame = i + 1
                    child.rotation_euler.x = tire_rot[i]
                    # child.rotation_euler.z = harsher_rot_z[i]
                    child.keyframe_insert(data_path="rotation_euler", frame=frame)
            animate_pyrotate_objects(child)

    animate_pyrotate_objects(driver_obj)


def add_driver_trail(driver_obj, df, driver, trail_color, trail_length=30):
    """Create a trailing effect behind a driver object using an animated curve.

    Args:
        driver_obj: The driver's object
        df: DataFrame with position data
        driver: Driver information
        trail_color: Hex color code for the trail
        trail_length: Maximum length of trail in frames

    Returns:
        The curve object for the trail

    """
    # Create a curve for the trail
    curve_data = bpy.data.curves.new(f"{driver.abbrev}Trail", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 12
    curve_data.bevel_depth = 0.16  # Thickness of trail
    curve_data.bevel_resolution = 4  # Smoothness of the bevel
    curve_data.fill_mode = "FULL"

    # Create the curve object and link it to the scene
    trail_obj = bpy.data.objects.new(f"{driver.abbrev}Trail", curve_data)
    bpy.context.scene.collection.objects.link(trail_obj)

    # Create material with emission for the glow effect
    trail_mat = bpy.data.materials.new(name=f"{driver.abbrev}TrailMaterial")
    trail_mat.use_nodes = True
    nodes = trail_mat.node_tree.nodes
    links = trail_mat.node_tree.links

    # Clear the default nodes
    nodes.clear()

    # Create new nodes
    output = nodes.new(type="ShaderNodeOutputMaterial")
    mix_shader = nodes.new(type="ShaderNodeMixShader")
    transparent = nodes.new(type="ShaderNodeBsdfTransparent")
    emission = nodes.new(type="ShaderNodeEmission")
    color_ramp = nodes.new(type="ShaderNodeValToRGB")

    # Position nodes
    output.location = (300, 0)
    mix_shader.location = (100, 0)
    transparent.location = (-100, 100)
    emission.location = (-100, -100)
    color_ramp.location = (-300, 0)

    # Connect nodes
    links.new(mix_shader.outputs[0], output.inputs[0])
    links.new(transparent.outputs[0], mix_shader.inputs[1])
    links.new(emission.outputs[0], mix_shader.inputs[2])
    links.new(color_ramp.outputs[0], mix_shader.inputs[0])

    # Set the color ramp to fade from 1 to 0
    color_ramp.color_ramp.elements[0].position = 0.0
    color_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    color_ramp.color_ramp.elements[1].position = 1.0
    color_ramp.color_ramp.elements[1].color = (0, 0, 0, 0)

    # Set emission color
    rgb_color = hex_to_blender_rgb(trail_color)
    emission.inputs[0].default_value = (*rgb_color, 1.0)
    emission.inputs[1].default_value = 2.0  # Emission strength

    # Setup material
    trail_mat.blend_method = "BLEND"
    trail_obj.data.materials.append(trail_mat)

    # Add curve coordinates driver for material animation
    driver = color_ramp.inputs[0].driver_add("default_value").driver
    driver.type = "SCRIPTED"
    var = driver.variables.new()
    var.name = "spline_coordinate"
    var.type = "SINGLE_PROP"
    var.targets[0].id_type = "OBJECT"
    var.targets[0].id = trail_obj
    var.targets[
        0
    ].data_path = "data.splines[0].points.point_duplication"  # This path just ensures the driver updates
    driver.expression = "spline_coordinate"

    # Create a spline in the curve
    spline = curve_data.splines.new("NURBS")

    # Get positions from dataframe
    x_values = df["X"].values
    y_values = df["Y"].values
    z_value = 0.11

    # Set initial points (only one point, the trail grows as animation proceeds)
    spline.points.add(1)
    spline.points[0].co = (
        x_values[0],
        y_values[0],
        z_value,
        1,
    )  # Slightly above ground
    spline.points[1].co = (x_values[0], y_values[0], z_value, 1)

    # Animate the trail
    total_frames = len(df)
    stride = 3

    # Start with a minimal trail
    for frame in range(1, min(trail_length, total_frames), stride):
        # Record current frame for animation
        bpy.context.scene.frame_set(frame)

        # Determine how many points should be in the trail at this frame
        num_points = min(frame + 1, trail_length)

        # Ensure we have enough points
        while len(spline.points) < num_points + 1:  # +1 for initial point
            spline.points.add(1)

        # Update each point's position based on the car's past positions
        for i in range(num_points):
            # Get the position from i frames ago
            history_frame = frame - i * stride
            if history_frame >= 0 and history_frame < total_frames:
                x = x_values[history_frame]
                y = y_values[history_frame]
                # Set the point position (W=1 for NURBS weight)
                spline.points[i].co = (x, y, z_value, 1)
                spline.points[i].keyframe_insert(data_path="co", frame=frame)

    for frame in range(trail_length, total_frames + 1, stride):
        # Record current frame for animation
        bpy.context.scene.frame_set(frame)

        # Update each point's position
        for i in range(trail_length):
            # Get the position from i frames ago
            history_frame = frame - i * stride
            if history_frame >= 0 and history_frame < total_frames:
                x = x_values[history_frame]
                y = y_values[history_frame]
                # Set the point position
                spline.points[i].co = (x, y, z_value, 1)
                spline.points[i].keyframe_insert(data_path="co", frame=frame)

    # Reset to frame 1
    bpy.context.scene.frame_set(1)

    return trail_obj


def add_driver_trail_test(
    driver_obj, df, driver, base_color, trail_length=240, stride=5
):
    """Create a trailing effect behind a driver object using an animated curve.

    The trail color changes based on driver inputs:
    - Red when braking
    - Yellow to Green scale based on throttle amount (0-100%)
    - Base color when neither braking nor throttling

    Args:
        driver_obj: The driver's object
        df: DataFrame with position data
        driver: Driver information
        trail_color: Hex color code for the base trail color
        trail_length: Maximum length of trail in frames
        stride: Process every Nth frame for efficiency

    Returns:
        The curve object for the trail

    """

    # Define color constants for use throughout the function
    def define_color_constants():
        """Define the color constants used for the trail."""
        red_rgb = (0.5, 0.0, 0.0)
        yellow_rgb = (1.0, 1.0, 0.0)
        green_rgb = (0.0, 0.5, 0.0)
        return red_rgb, yellow_rgb, green_rgb

    def get_color_for_frame(
        frame_idx, throttle_array, brake_array, red_rgb, yellow_rgb, green_rgb
    ):
        """Determine the appropriate color based on throttle and brake values."""
        if frame_idx < len(brake_array) and brake_array[frame_idx] > 0:
            # Braking - red
            return red_rgb
        elif frame_idx < len(throttle_array) and throttle_array[frame_idx] > 0:
            # Throttle - yellow to green based on amount
            throttle_percent = throttle_array[frame_idx]
            # Interpolate from yellow to green
            r = yellow_rgb[0] * (1 - throttle_percent) + green_rgb[0] * throttle_percent
            g = yellow_rgb[1] * (1 - throttle_percent) + green_rgb[1] * throttle_percent
            b = yellow_rgb[2] * (1 - throttle_percent) + green_rgb[2] * throttle_percent
            return (r, g, b)
        else:
            # Neither braking nor throttle - use base color
            return yellow_rgb

    def apply_color_keyframe(emission_node, color, frame):
        """Apply a color keyframe to the emission node."""
        emission_node.inputs["Color"].default_value = (*color, 1.0)
        emission_node.inputs["Color"].keyframe_insert(
            data_path="default_value", frame=frame
        )

    def setup_curve_object():
        """Create and setup the curve object for the trail."""
        curve_data = bpy.data.curves.new(f"{driver.abbrev}Trail", type="CURVE")
        curve_data.dimensions = "3D"
        curve_data.resolution_u = 12
        curve_data.bevel_depth = 0.15  # Thickness of trail
        curve_data.bevel_resolution = 3  # Reduced for better performance
        curve_data.fill_mode = "FULL"

        trail_obj = bpy.data.objects.new(f"{driver.abbrev}Trail", curve_data)
        bpy.context.scene.collection.objects.link(trail_obj)
        return trail_obj, curve_data

    def setup_material(trail_obj):
        """Setup the emission material for the trail."""
        trail_mat = bpy.data.materials.new(name=f"{driver.abbrev}TrailMaterial")
        trail_mat.use_nodes = True
        nodes = trail_mat.node_tree.nodes
        links = trail_mat.node_tree.links

        # Clear default nodes
        nodes.clear()

        # Create simple emission shader
        output = nodes.new(type="ShaderNodeOutputMaterial")
        emission = nodes.new(type="ShaderNodeEmission")

        # Connect nodes
        links.new(emission.outputs[0], output.inputs[0])

        # Set base values
        emission.inputs["Strength"].default_value = 5.0  # Emission strength

        # Apply material
        trail_mat.blend_method = "BLEND"
        trail_obj.data.materials.append(trail_mat)

        return emission

    # Initialize curve and material
    trail_obj_a, curve_data_a = setup_curve_object()
    trail_obj_b, curve_data_b = setup_curve_object()
    emission_node_a = setup_material(trail_obj_a)
    emission_node_b = setup_material(trail_obj_b)
    emission_node_b.inputs["Color"].default_value = (
        *hex_to_blender_rgb(base_color),
        1.0,
    )

    # Get data from the dataframe
    x_values = df["X"].values
    y_values = df["Y"].values
    throttle_values = df["Throttle"].values
    brake_values = df["Brake"].values
    total_frames = len(df)

    z_value_a = 0.1
    z_value_b = -0.5

    # Define colors
    red_rgb, yellow_rgb, green_rgb = define_color_constants()

    # Create spline and initialize
    spline_a = curve_data_a.splines.new("NURBS")
    spline_b = curve_data_b.splines.new("NURBS")
    effective_length = max(trail_length // stride, 2)  # Ensure at least 2 points
    spline_a.points.add(effective_length - 1)  # -1 because NURBS starts with 1 point
    spline_b.points.add(effective_length - 1)
    for i in range(effective_length):
        spline_a.points[i].co = (x_values[0], y_values[0], z_value_a, 1)
        spline_b.points[i].co = (x_values[0], y_values[0], z_value_b, 1)

    # Process growing trail phase
    for frame in range(1, min(effective_length * stride, total_frames), stride):
        bpy.context.scene.frame_set(frame)

        # Update each point's position
        for i in range(effective_length):
            history_frame = frame - i * stride + stride
            if history_frame >= 0 and history_frame < total_frames:
                x = x_values[history_frame]
                y = y_values[history_frame]
            else:
                # Interpolate backwards from first frame
                x_diff = x_values[0] - x_values[1]
                x = x_values[0] + x_diff * abs(history_frame)

                y_diff = y_values[0] - y_values[1]
                y = y_values[0] + y_diff * abs(history_frame)

            spline_a.points[i].co = (x, y, z_value_a, 1)
            spline_a.points[i].keyframe_insert(data_path="co", frame=frame)

            spline_b.points[i].co = (x, y, z_value_b, 1)
            spline_b.points[i].keyframe_insert(data_path="co", frame=frame)

            # Get and apply color
            color = get_color_for_frame(
                max(0, history_frame),  # Ensure valid frame index for color
                throttle_values,
                brake_values,
                red_rgb,
                yellow_rgb,
                green_rgb,
            )
            apply_color_keyframe(emission_node_a, color, frame)

    # Process full-length trail phase
    for frame in range(effective_length * stride, total_frames + 1, stride):
        bpy.context.scene.frame_set(frame)

        # Update all points in the trail
        for i in range(effective_length):
            history_frame = frame - i * stride + stride

            if history_frame >= 0 and history_frame < total_frames:
                x = x_values[history_frame]
                y = y_values[history_frame]

            spline_a.points[i].co = (x, y, z_value_a, 1)
            spline_a.points[i].keyframe_insert(data_path="co", frame=frame)

            spline_b.points[i].co = (x, y, z_value_b, 1)
            spline_b.points[i].keyframe_insert(data_path="co", frame=frame)

        # Get color for current frame
        current_frame = frame - 1  # Adjust to 0-indexed
        color = get_color_for_frame(
            current_frame,
            throttle_values,
            brake_values,
            red_rgb,
            yellow_rgb,
            green_rgb,
        )
        apply_color_keyframe(emission_node_a, color, frame)

    # Reset to frame 1
    bpy.context.scene.frame_set(1)

    return trail_obj_a, trail_obj_b


def add_particle_trail(driver_obj, color):
    # Create a particle emitter object
    bpy.ops.mesh.primitive_plane_add(size=0.1)
    emitter = bpy.context.object
    emitter.name = f"{driver_obj.name}Emitter"
    emitter.parent = driver_obj
    emitter.location = (0, 0.1, 0.5)  # Behind the car

    # Set up particle system
    particle_system = emitter.modifiers.new("ParticleSystem", "PARTICLE_SYSTEM")
    particle_settings = particle_system.particle_system.settings
    particle_settings.type = "EMITTER"
    particle_settings.lifetime = 60
    particle_settings.emit_from = "VERT"
    particle_settings.count = 10000
    # Set frame range for particles
    particle_settings.frame_start = 1
    particle_settings.frame_end = 10000

    # Apply material
    mat = bpy.data.materials.new(name=f"{driver_obj.name}_Trail")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear existing nodes
    nodes.clear()

    # Create emission shader setup
    output = nodes.new(type="ShaderNodeOutputMaterial")
    emission = nodes.new(type="ShaderNodeEmission")

    # Set color and strength
    rgb_color = hex_to_blender_rgb(color)
    emission.inputs["Color"].default_value = (*rgb_color, 1.0)
    emission.inputs["Strength"].default_value = 5.0  # Increase this for more visibility

    # Connect nodes
    links.new(emission.outputs[0], output.inputs[0])

    emitter.data.materials.append(mat)

    return emitter


def replace_color_in_image(blender_obj, hex_color, driver):
    """Replace color in image texture node of a material.

    This is done by creating a new image file and by replacing the pixels.
    Using numpy here for faster processing of the pixels.
    """
    material = blender_obj.material_slots[0].material
    if not material.node_tree.nodes:
        raise ValueError(f"Material {material.name} has no nodes.")

    image_node = None
    for node in material.node_tree.nodes:
        if node.type == "TEX_IMAGE":
            image_node = node
            break

    if not image_node:
        raise ValueError(f"Material {material.name} has no image node.")

    image_path = bpy.path.abspath(image_node.image.filepath)
    new_image_path = str(
        file_utils.project_paths.get_new_texture_image_path(blender_obj.name, hex_color)
    )

    # first check if the image already exists
    if os.path.exists(new_image_path):
        new_image = bpy.data.images.load(new_image_path)
        image_node.image = new_image
        return

    # Read image and convert to numpy array
    with Image.open(image_path) as img:
        # Convert image to numpy array for faster processing
        img_array = np.array(img)

        # Define the colors
        old_color = np.array(hex_to_normal_rgb("#FF472C"))
        new_color = np.array(hex_to_normal_rgb(hex_color))

        # Create a mask where pixels match the old color
        # The == comparison will create a boolean array for each color channel
        # All channels must match for a pixel to be replaced
        mask = np.all(img_array == old_color, axis=2)

        # Use the mask to replace the colors
        # This is much faster than pixel-by-pixel operations
        img_array[mask] = new_color

        # Create a new image from the array
        new_img = Image.fromarray(img_array)
        new_img.save(new_image_path)

    # Load the new image into Blender and assign it to the material
    new_image = bpy.data.images.load(new_image_path)
    image_node.image = new_image


def set_color(driver_obj: bpy.types.Object, color: str, driver_abbrev: str):
    """Set color for different parts of the driver's car."""
    for child_obj in driver_obj.children:
        if "chassis" in child_obj.name.lower():
            start_time = time.time()
            replace_color_in_image(child_obj, color, driver_abbrev)
            log_info(
                f"  Time to replace color in chassis: {time.time() - start_time:.2f} seconds"
            )
        if "wings" in child_obj.name.lower():
            # Reset material nodes as it was originally an image and set color
            rgb_color = hex_to_blender_rgb(color)
            if child_obj.material_slots and child_obj.material_slots[0].material:
                material = child_obj.material_slots[0].material

                # Find the principled BSDF node
                bsdf_node = None
                for node in material.node_tree.nodes:  # pyright: ignore
                    if node.type == "BSDF_PRINCIPLED":
                        bsdf_node = node
                        break

                # Find any image texture connected to base color and disconnect it
                for link in material.node_tree.links:  # pyright: ignore
                    if (
                        link.to_node == bsdf_node
                        and link.to_socket.name == "Base Color"  # pyright: ignore
                    ):
                        material.node_tree.links.remove(link)  # pyright: ignore

                # Set the RGB color directly
                bsdf_node.inputs["Base Color"].default_value = (*rgb_color, 1.0)  # pyright: ignore

        if "steering" in child_obj.name.lower():
            child_obj.hide_viewport = True
            child_obj.hide_render = True


def add_color_marker_for_same_team(car_obj, color: str):
    """Add a 3D triangle marker to distinguish cars of the same team."""
    # Create triangle vertices (two triangles offset in Z)
    verts = [
        (0, 0.2, 1),  # Top front
        (-0.2, -0.2, 1),  # Bottom left front
        (0.2, -0.2, 1),  # Bottom right front
        (0, 0.2, 0.9),  # Top back
        (-0.2, -0.2, 0.9),  # Bottom left back
        (0.2, -0.2, 0.9),  # Bottom right back
    ]

    # Create faces - front triangle, back triangle, and connecting faces
    faces = [
        (0, 1, 2),  # Front triangle
        (3, 4, 5),  # Back triangle
        (0, 1, 4, 3),  # Left side
        (1, 2, 5, 4),  # Bottom
        (2, 0, 3, 5),  # Right side
    ]

    # Create mesh and object
    mesh = bpy.data.meshes.new("TeamMarker")
    obj = bpy.data.objects.new("TeamMarker", mesh)

    # Create the mesh from vertices and faces
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    # Create material with team color
    mat = bpy.data.materials.new(name="MarkerMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    rgb_color = hex_to_blender_rgb(color)
    bsdf.inputs["Base Color"].default_value = (*rgb_color, 1)
    bsdf.inputs["Emission Color"].default_value = (*rgb_color, 1)
    bsdf.inputs["Emission Strength"].default_value = 1.0

    obj.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = car_obj

    obj.scale = (2.0, 2.0, 2.0)
    obj.location = (0, -5, 2)
    obj.rotation_euler = (math.radians(-90), 0, 0)

    return obj


def main(
    driver_dfs: dict[Driver, pd.DataFrame],
    drivers: list[Driver],
    driver_colors: list[str],
    quick_textures_mode: bool,
    rest_of_field_focused_driver: Optional[Driver],
) -> dict[Driver, bpy.types.Object]:
    """Process all drivers and return a dictionary mapping driver abbreviations to their objects."""
    quick_textures_mode_max = 2

    # base_empty_objs_by_team: dict[str, bpy.types.Object] = {}
    count_by_team: dict[str, int] = {}

    # Create a collection for all driver objects
    drivers_collection = bpy.data.collections.new("DriversCollection")
    bpy.context.scene.collection.children.link(drivers_collection)

    driver_objs: dict[Driver, bpy.types.Object] = {}
    for i, (driver, color) in enumerate(zip(drivers, driver_colors)):
        if quick_textures_mode and i >= quick_textures_mode_max:
            continue

        log_info(f"Adding {i + 1}/{len(drivers)} driver: {driver} in color: {color}")
        start_time = time.time()

        # if rest_of_field_focused_driver and driver != rest_of_field_focused_driver:
        #     if "null" not in base_empty_objs_by_team:
        #         base_empty_objs_by_team["null"] = create_null_base()
        #     base_empty_obj = base_empty_objs_by_team["null"]
        #     driver_obj = create_car_obj(driver.team, driver.last_name)
        # elif driver.team in base_empty_objs_by_team:
        #     base_empty_obj = base_empty_objs_by_team[driver.team]
        #     driver_obj = create_car_obj(driver.team, driver.last_name)
        # else:
        #     base_empty_obj = create_team_base(driver.team)
        #     base_empty_objs_by_team[driver.team] = base_empty_obj
        #     driver_obj = create_car_obj(driver.team, driver.last_name)

        driver_obj = create_car_obj(driver.team, driver.last_name)

        # Move driver object from scene collection to drivers collection
        if driver_obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(driver_obj)
        drivers_collection.objects.link(driver_obj)

        # Also add all children to the collection
        for child in driver_obj.children_recursive:
            if child.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(child)
            drivers_collection.objects.link(child)

        if not quick_textures_mode:
            set_color(driver_obj, color, driver.abbrev)
        add_driver_keyframes(driver_obj, driver_dfs[driver])
        # add_particle_trail(driver_obj, color)
        # add_driver_trail_test(driver_obj, driver_dfs[driver], driver, color)
        add_driver_trail_test(driver_obj, driver_dfs[driver], driver, color)

        driver_objs[driver] = driver_obj
        count_by_team[driver.team] = count_by_team.get(driver.team, 0) + 1

        elapsed_time = time.time() - start_time
        log_info(f"Driver {driver} added in {elapsed_time:.2f} seconds")

    # now, if there is any team where count is >=2, we need to add the color marker
    # to distinguish between drivers of the same team
    for team, count in count_by_team.items():
        if count >= 2:
            for idx, (driver, driver_color) in enumerate(zip(drivers, driver_colors)):
                if driver.team == team:
                    marker = add_color_marker_for_same_team(
                        driver_objs[driver], driver_color
                    )
                    # Add the marker to the drivers collection
                    if marker.name in bpy.context.scene.collection.objects:
                        bpy.context.scene.collection.objects.unlink(marker)
                    drivers_collection.objects.link(marker)

    return driver_objs
