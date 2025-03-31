"""Create all drivers and return a dictionary mapping driver abbreviations to their objects given the driver data."""

import math
import os
import time

import bpy
import mathutils
import numpy as np
from PIL import Image

from src.models.config import Config
from src.models.driver import Driver, DriverRunData, RunDrivers
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
    # center_y = (min_y + max_y) / 2
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

            # Set Metallic to 0.5 for all materials
            if obj.material_slots:
                for slot in obj.material_slots:
                    if slot.material and slot.material.use_nodes:
                        for node in slot.material.node_tree.nodes:
                            if node.type == "BSDF_PRINCIPLED":
                                node.inputs["Metallic"].default_value = 0.5

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

        new_obj.name = f"{driver_abbrev.title()}Car{src_obj.name}"
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
    scale_and_position_car(new_empty)
    new_empty.scale = (1.3, 1.3, 1.3)

    for obj in base_empty_obj.children:
        copy_object_and_children(obj, new_empty)

    return new_empty


# Time,X,Y,Z,RotW,RotX,RotY,RotZ
def add_driver_keyframes(driver_obj, df):
    """Add keyframes to driver object based on dataframe values."""
    # Pre-fetch all the data we'll need to avoid repeated lookups
    x_values = df["X"]
    y_values = df["Y"]
    z_values = df["Z"]

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
        cur_frame = i + 1
        point = mathutils.Vector((x_values.iloc[i], y_values.iloc[i], z_values.iloc[i]))

        rot_quat = mathutils.Quaternion(
            (rot_w.iloc[i], rot_x.iloc[i], rot_y.iloc[i], rot_z.iloc[i])
        )
        rot_eul = rot_quat.to_euler()

        driver_loc_keyframes.append((point, cur_frame))
        driver_rot_keyframes.append((rot_eul, cur_frame))

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
                    child.rotation_euler.x = tire_rot.iloc[i]
                    # child.rotation_euler.z = harsher_rot_z[i]
                    child.keyframe_insert(data_path="rotation_euler", frame=frame)
            animate_pyrotate_objects(child)

    animate_pyrotate_objects(driver_obj)


def add_driver_trail(
    driver: Driver,
    driver_obj: bpy.types.Object,
    run_data: DriverRunData,
    base_color: str,
    trail_length=600,
    stride=5,
):
    """Create a trailing effect behind a driver object using an animated curve."""

    # Setup helpers
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
        nodes.clear()
        output = nodes.new(type="ShaderNodeOutputMaterial")
        emission = nodes.new(type="ShaderNodeEmission")
        links.new(emission.outputs[0], output.inputs[0])
        emission.inputs["Strength"].default_value = 5.0
        trail_mat.blend_method = "BLEND"
        trail_obj.data.materials.append(trail_mat)
        return emission

    def update_full_trail(
        sped_frame,
        spline_a,
        spline_b,
        x_values,
        y_values,
        z_value_a,
        z_value_b,
        sped_to_absolute,
        effective_length,
        stride,
    ):
        """Update trail when at full length."""
        # Get absolute frame for current sped frame
        current_absolute_frame = sped_frame

        cur_vec = (
            x_values[current_absolute_frame + 1] - x_values[current_absolute_frame],
            y_values[current_absolute_frame + 1] - y_values[current_absolute_frame],
            0,
        )
        vec_length = (cur_vec[0] ** 2 + cur_vec[1] ** 2) ** 0.5
        cur_vec_normalized = (cur_vec[0] / vec_length, cur_vec[1] / vec_length, 0)

        # Update all trail points
        for i in range(effective_length):
            vals_idx = current_absolute_frame - i * stride
            if i == 0:
                x = x_values[vals_idx] + cur_vec_normalized[0] * 2
                y = y_values[vals_idx] + cur_vec_normalized[1] * 2
            else:
                x = x_values[vals_idx]
                y = y_values[vals_idx]

            # Update spline points
            spline_a.points[i].co = (x, y, z_value_a, 1)
            spline_a.points[i].keyframe_insert(data_path="co", frame=sped_frame + 1)

            spline_b.points[i].co = (x, y, z_value_b, 1)
            spline_b.points[i].keyframe_insert(data_path="co", frame=sped_frame + 1)

    # Main function logic starts here
    sped_point_df = run_data.sped_point_df
    sped_to_absolute = run_data.sped_frame_to_absolute_frame

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
    x_values = sped_point_df["X"].values
    y_values = sped_point_df["Y"].values
    throttle_values = (
        sped_point_df["Throttle"].values
        if "Throttle" in sped_point_df.columns
        else np.zeros(len(sped_point_df))
    )
    brake_values = (
        sped_point_df["Brake"].values
        if "Brake" in sped_point_df.columns
        else np.zeros(len(sped_point_df))
    )
    total_frames = len(sped_point_df)

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

    # Initialize all spline points to first position
    for i in range(effective_length):
        spline_a.points[i].co = (x_values[0], y_values[0], z_value_a, 1)
        spline_b.points[i].co = (x_values[0], y_values[0], z_value_b, 1)

    # Animation phase 1: Growing trail
    growing_phase_end = min(effective_length * stride, total_frames)

    # Animation phase 2: Full-length trail
    for sped_frame in range(growing_phase_end + stride, total_frames, stride):
        bpy.context.scene.frame_set(sped_frame + 1)

        update_full_trail(
            sped_frame,
            spline_a,
            spline_b,
            x_values,
            y_values,
            z_value_a,
            z_value_b,
            sped_to_absolute,
            effective_length,
            stride,
        )

        # Set color for the trail
        current_absolute_frame = sped_to_absolute.get(sped_frame, 0)
        color = get_color_for_frame(
            min(current_absolute_frame, len(throttle_values) - 1),
            throttle_values,
            brake_values,
            red_rgb,
            yellow_rgb,
            green_rgb,
        )
        apply_color_keyframe(emission_node_a, color, sped_frame)

    bpy.context.scene.frame_set(10)
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


def add_driver_particle_trail(
    driver: Driver,
    driver_obj: bpy.types.Object,
    base_color: str,
    lifetime=300,
    emission_rate=1000,
):
    """Create a trailing effect behind a driver object using particles."""
    # Create a small emitter plane
    bpy.ops.mesh.primitive_plane_add(size=0.1)
    emitter = bpy.context.object
    emitter.name = f"{driver.abbrev}_ParticleTrail"

    # Parent to the car and position it at the rear
    emitter.parent = driver_obj
    emitter.location = (0, -1.5, 0.1)  # Behind and slightly above the car

    # Make emitter invisible in rendering
    emitter.hide_render = True

    # Create a dedicated material for the particles
    particle_mat = bpy.data.materials.new(name=f"{driver.abbrev}_ParticleMaterial")
    particle_mat.use_nodes = True
    nodes = particle_mat.node_tree.nodes
    links = particle_mat.node_tree.links
    nodes.clear()

    # Create emission shader
    output = nodes.new(type="ShaderNodeOutputMaterial")
    emission = nodes.new(type="ShaderNodeEmission")

    # Set color and strength
    rgb_color = hex_to_blender_rgb(base_color)
    emission.inputs["Color"].default_value = (*rgb_color, 1.0)
    emission.inputs["Strength"].default_value = 5.0

    # Connect nodes
    links.new(emission.outputs[0], output.inputs[0])

    # Set transparency mode
    particle_mat.blend_method = "BLEND"

    # Add material to emitter object first
    emitter.data.materials.append(particle_mat)

    # Add particle system
    particle_system = emitter.modifiers.new("ParticleSystem", "PARTICLE_SYSTEM")
    settings = particle_system.particle_system.settings
    settings.type = "EMITTER"
    settings.count = lifetime * emission_rate
    settings.frame_start = 1
    settings.frame_end = 10000
    settings.lifetime = lifetime

    # Emission settings
    settings.emit_from = "VERT"
    settings.use_emit_random = False
    settings.normal_factor = 0.02

    # Physics settings
    settings.physics_type = "BOIDS"
    settings.boids.health = 1.0
    settings.boids.accuracy = 1.0
    settings.boids.aggression = 0.0
    settings.boids.air_speed_min = 0.1
    settings.boids.air_speed_max = 0.5

    # IMPORTANT: Set the material slot index
    # settings.material = "1"  # Use the material we added (1-based indexing)

    # Path visualization settings
    settings.render_type = "PATH"
    settings.path_start = 0.0  # Start of path (0 = birth)
    settings.path_end = 1.0  # End of path (1 = death)
    # settings.line_length = 1.0  # Full path length
    settings.use_parent_particles = True

    # These settings affect the appearance of the path
    settings.display_step = 1  # Show every frame
    settings.render_step = 1
    settings.display_method = "RENDER"  # Always show as it will render

    # Critical - set the trail color directly
    rgb_color = hex_to_blender_rgb(base_color)

    # Size of particles
    settings.particle_size = 0.05
    settings.use_size_deflect = True
    # settings.use_path_follow = True

    return emitter


def main(config: Config, run_drivers: RunDrivers):
    applied_colors = run_drivers.driver_applied_colors
    focused_driver = run_drivers.focused_driver

    drivers_collection = bpy.data.collections.new("DriversCollection")
    bpy.context.scene.collection.children.link(drivers_collection)

    count_by_team: dict[str, int] = {}
    driver_objs: dict[Driver, bpy.types.Object] = {}

    base_empty_obj = create_null_base()

    for i, (driver, run_data) in enumerate(run_drivers.driver_run_data.items()):
        log_info(
            f"Adding {i + 1}/{len(run_drivers.drivers)} driver: {driver} in color: {applied_colors[driver]}"
        )
        start_time = time.time()

        if config["type"] == "rest-of-field" and driver != focused_driver:
            driver_obj = create_driver_from_base(driver.abbrev, base_empty_obj)
            set_color(driver_obj, applied_colors[driver], driver.abbrev)
        else:
            driver_obj = create_car_obj(driver.team, driver.last_name)
        driver_objs[driver] = driver_obj

        # Move driver object from scene collection to drivers collection
        if driver_obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(driver_obj)
        drivers_collection.objects.link(driver_obj)

        # Also add all children to the collection
        for child in driver_obj.children_recursive:
            if child.name in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.unlink(child)
            drivers_collection.objects.link(child)

        add_driver_keyframes(driver_obj, run_data.sped_point_df)
        # add_driver_trail(
        #     driver, driver_obj, run_data, run_drivers.driver_applied_colors[driver]
        # )
        # add_driver_particle_trail(
        #     driver, driver_obj, run_drivers.driver_applied_colors[driver]
        # )

        elapsed_time = time.time() - start_time
        count_by_team[driver.team] = count_by_team.get(driver.team, 0) + 1
        log_info(f"Driver {driver} added in {elapsed_time:.2f} seconds")

    # now, if there is any team where count is >=2, we need to add the color marker
    # to distinguish between drivers of the same team, the colors were already set previously
    # for this purpose
    if not config["type"] == "rest-of-field":
        for team, count in count_by_team.items():
            if count >= 2:
                for i, (driver, run_data) in enumerate(
                    run_drivers.driver_run_data.items()
                ):
                    if driver.team == team:
                        marker = add_color_marker_for_same_team(
                            driver_objs[driver],
                            run_drivers.driver_applied_colors[driver],
                        )
                        # Add the marker to the drivers collection
                        if marker.name in bpy.context.scene.collection.objects:
                            bpy.context.scene.collection.objects.unlink(marker)
                        drivers_collection.objects.link(marker)


# def main(
#     driver_dfs: dict[Driver, pd.DataFrame],
#     drivers: list[Driver],
#     driver_colors: list[str],
#     quick_textures_mode: bool,
#     rest_of_field_focused_driver: Optional[Driver],
# ) -> dict[Driver, bpy.types.Object]:
#     """Process all drivers and return a dictionary mapping driver abbreviations to their objects."""
#     quick_textures_mode_max = 2

#     # base_empty_objs_by_team: dict[str, bpy.types.Object] = {}
#     count_by_team: dict[str, int] = {}

#     # Create a collection for all driver objects
#     drivers_collection = bpy.data.collections.new("DriversCollection")
#     bpy.context.scene.collection.children.link(drivers_collection)

#     driver_objs: dict[Driver, bpy.types.Object] = {}
#     for i, (driver, color) in enumerate(zip(drivers, driver_colors)):
#         if quick_textures_mode and i >= quick_textures_mode_max:
#             continue

#         log_info(f"Adding {i + 1}/{len(drivers)} driver: {driver} in color: {color}")
#         start_time = time.time()

#         # if rest_of_field_focused_driver and driver != rest_of_field_focused_driver:
#         #     if "null" not in base_empty_objs_by_team:
#         #         base_empty_objs_by_team["null"] = create_null_base()
#         #     base_empty_obj = base_empty_objs_by_team["null"]
#         #     driver_obj = create_car_obj(driver.team, driver.last_name)
#         # elif driver.team in base_empty_objs_by_team:
#         #     base_empty_obj = base_empty_objs_by_team[driver.team]
#         #     driver_obj = create_car_obj(driver.team, driver.last_name)
#         # else:
#         #     base_empty_obj = create_team_base(driver.team)
#         #     base_empty_objs_by_team[driver.team] = base_empty_obj
#         #     driver_obj = create_car_obj(driver.team, driver.last_name)

#         driver_obj = create_car_obj(driver.team, driver.last_name)

#         # Move driver object from scene collection to drivers collection
#         if driver_obj.name in bpy.context.scene.collection.objects:
#             bpy.context.scene.collection.objects.unlink(driver_obj)
#         drivers_collection.objects.link(driver_obj)

#         # Also add all children to the collection
#         for child in driver_obj.children_recursive:
#             if child.name in bpy.context.scene.collection.objects:
#                 bpy.context.scene.collection.objects.unlink(child)
#             drivers_collection.objects.link(child)

#         if not quick_textures_mode:
#             set_color(driver_obj, color, driver.abbrev)
#         add_driver_keyframes(driver_obj, driver_dfs[driver])
#         # add_particle_trail(driver_obj, color)
#         # add_driver_trail_test(driver_obj, driver_dfs[driver], driver, color)
#         # add_driver_trail(driver, driver_obj, dr, color)
#         add_driver_trail_sped(
#             driver,
#             driver_obj,
#         )

#         driver_objs[driver] = driver_obj
#         count_by_team[driver.team] = count_by_team.get(driver.team, 0) + 1

#         elapsed_time = time.time() - start_time
#         log_info(f"Driver {driver} added in {elapsed_time:.2f} seconds")

#     return driver_objs
