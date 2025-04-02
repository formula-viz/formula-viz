"""Generate track surfaces and curbs with appropriate materials."""

import math
from typing import Optional

import bmesh
import bpy

from src.models.sectors import SectorsInfo
from src.models.track_data import TrackData
from src.utils.materials import (
    create_asphalt_material,
)


def create_boxes(
    inner_points: list[tuple[float, float, float]],
    outer_points: list[tuple[float, float, float]],
    sectors_info: SectorsInfo,
    name: str,
    height: float = 0.1,
    material: Optional[bpy.types.Material] = None,
    alternate_material: Optional[bpy.types.Material] = None,
    is_pattern: bool = False,
):
    """Create a mesh of 3D boxes between two sets of points.

    Args:
        inner_points: List of 3D coordinates representing the inner edge
        outer_points: List of 3D coordinates representing the outer edge
        name: Base name for the created object
        height: Height of the boxes
        material: Blender material to apply to the mesh (optional)
        alternate_material: Second material for alternating pattern (optional)
        is_pattern: Whether to apply an alternating material pattern

    Returns:
        The created Blender object

    """
    mesh = bpy.data.meshes.new(name + "BoxMesh")
    obj = bpy.data.objects.new(name + "Box", mesh)
    bpy.context.collection.objects.link(obj)  # pyright: ignore

    bm = bmesh.new()

    # Create vertices for the bottom face
    bottom_inner_verts = [bm.verts.new(coord) for coord in inner_points]
    bottom_outer_verts = [bm.verts.new(coord) for coord in outer_points]

    # Create vertices for the top face (add height to z-coordinate)
    top_inner_verts = [bm.verts.new((p[0], p[1], p[2] + height)) for p in inner_points]
    top_outer_verts = [bm.verts.new((p[0], p[1], p[2] + height)) for p in outer_points]

    bm.verts.ensure_lookup_table()  # pyright: ignore

    # List to store all created faces
    all_faces = []

    # Create faces for each segment
    for i in range(len(inner_points) - 1):
        # Bottom face
        bottom_face = bm.faces.new(
            [
                bottom_inner_verts[i],
                bottom_inner_verts[i + 1],
                bottom_outer_verts[i + 1],
                bottom_outer_verts[i],
            ]
        )
        all_faces.append(bottom_face)

        # Top face
        top_face = bm.faces.new(
            [
                top_inner_verts[i],
                top_inner_verts[i + 1],
                top_outer_verts[i + 1],
                top_outer_verts[i],
            ]
        )
        all_faces.append(top_face)

        # Inner side face
        inner_side_face = bm.faces.new(
            [
                bottom_inner_verts[i],
                bottom_inner_verts[i + 1],
                top_inner_verts[i + 1],
                top_inner_verts[i],
            ]
        )
        all_faces.append(inner_side_face)

        # Outer side face
        outer_side_face = bm.faces.new(
            [
                bottom_outer_verts[i],
                bottom_outer_verts[i + 1],
                top_outer_verts[i + 1],
                top_outer_verts[i],
            ]
        )
        all_faces.append(outer_side_face)

        # Start cap face (only for the first segment)
        if i == 0:
            start_cap_face = bm.faces.new(
                [
                    bottom_inner_verts[0],
                    bottom_outer_verts[0],
                    top_outer_verts[0],
                    top_inner_verts[0],
                ]
            )
            all_faces.append(start_cap_face)

        # End cap face (for each segment end)
        end_cap_face = bm.faces.new(
            [
                bottom_inner_verts[i + 1],
                bottom_outer_verts[i + 1],
                top_outer_verts[i + 1],
                top_inner_verts[i + 1],
            ]
        )
        all_faces.append(end_cap_face)

    bm.to_mesh(mesh)  # pyright: ignore
    bm.free()  # pyright: ignore

    # Add materials
    if material:
        obj.data.materials.append(material)  # pyright: ignore

        # Create alternating pattern
        pattern_size = 6  # Number of faces per segment (6 faces per box)
        if is_pattern and alternate_material:
            obj.data.materials.append(alternate_material)  # pyright: ignore

            # Assign material indices to faces
            for i, poly in enumerate(obj.data.polygons):  # pyright: ignore
                # Integer division to determine which material to use
                # Each box has 6 faces, so divide by 6 to get box index
                segment_index = i // pattern_size
                material_index = segment_index % 2  # Alternate between 0 and 1
                poly.material_index = material_index

    return obj


def create_planes_new(
    inner_points: list[tuple[float, float, float]],
    outer_points: list[tuple[float, float, float]],
    name: str,
    material: Optional[bpy.types.Material] = None,
    alternate_material: Optional[bpy.types.Material] = None,
    is_curb: bool = True,
):
    """Create a mesh plane between two sets of points with a single material.

    Args:
        inner_points: List of 3D coordinates representing the inner edge
        outer_points: List of 3D coordinates representing the outer edge
        name: Base name for the created object
        material: Blender material to apply to the mesh (optional)
        alternate_material: Second material (not used, kept for compatibility)
        is_curb: Whether this is a curb section

    Returns:
        The created Blender object

    """
    mesh = bpy.data.meshes.new(name + "TrackMesh")
    obj = bpy.data.objects.new(name + "Track", mesh)
    bpy.context.collection.objects.link(obj)  # pyright: ignore

    bm = bmesh.new()

    inner_verts = [bm.verts.new(coord) for coord in inner_points]
    outer_verts = [bm.verts.new(coord) for coord in outer_points]

    bm.verts.ensure_lookup_table()  # pyright: ignore

    # Create faces
    faces = []
    for i in range(len(inner_points) - 1):
        face = bm.faces.new(
            [inner_verts[i], inner_verts[i + 1], outer_verts[i + 1], outer_verts[i]]
        )
        faces.append(face)

    bm.to_mesh(mesh)  # pyright: ignore
    bm.free()  # pyright: ignore

    # Add the material
    if material:
        obj.data.materials.append(material)  # pyright: ignore

    # Add UV mapping for better texture control
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")

    return obj


def create_planes_curb(
    inner_points: list[tuple[float, float, float]],
    outer_points: list[tuple[float, float, float]],
    name: str,
    default_material: bpy.types.Material,
    curbstone_a_mat: bpy.types.Material,
    curbstone_b_mat: bpy.types.Material,
    curve_threshold: float = 0.07,
):
    """Create a mesh plane with curb patterns only on curved sections.

    Args:
        inner_points: List of 3D coordinates representing the inner edge
        outer_points: List of 3D coordinates representing the outer edge
        name: Base name for the created object
        default_material: Blender material for the main curb surface
        curbstone_a_mat: Blender material for type A curbs (usually white)
        curbstone_b_mat: Blender material for type B curbs (usually red)
        curve_threshold: Minimum angle (in radians) to consider a section as curved

    Returns:
        The created Blender object

    """
    mesh = bpy.data.meshes.new(name + "CurbMesh")
    obj = bpy.data.objects.new(name + "Curb", mesh)
    bpy.context.collection.objects.link(obj)  # pyright: ignore

    bm = bmesh.new()

    # Create all vertices for inner and outer edges
    inner_verts = [bm.verts.new(coord) for coord in inner_points]
    outer_verts = [bm.verts.new(coord) for coord in outer_points]

    bm.verts.ensure_lookup_table()  # pyright: ignore

    # List to track which segments are curved
    is_curved_segment = []

    # Create faces and determine if each segment is curved
    faces = []
    for i in range(len(inner_points) - 1):
        # Create the face
        face = bm.faces.new(
            [inner_verts[i], inner_verts[i + 1], outer_verts[i + 1], outer_verts[i]]
        )
        faces.append(face)

        # Determine if this segment is part of a curve
        # Calculate angle between consecutive segments
        is_curved = False

        if i > 0 and i < len(inner_points) - 3:
            # Use wider spacing for better curve detection
            skip_distance = 20
            prev_idx = max(0, i - skip_distance)
            next_idx = min(len(inner_points) - 1, i + skip_distance)

            prev_point = inner_points[prev_idx]
            cur_point = inner_points[i]
            next_point = inner_points[next_idx]

            # Get vectors between these more distant points
            prev_vec = (
                cur_point[0] - prev_point[0],
                cur_point[1] - prev_point[1],
            )
            curr_vec = (
                next_point[0] - cur_point[0],
                next_point[1] - cur_point[1],
            )

            # Calculate angle using dot product
            dot_product = prev_vec[0] * curr_vec[0] + prev_vec[1] * curr_vec[1]
            prev_len = (prev_vec[0] ** 2 + prev_vec[1] ** 2) ** 0.5
            curr_len = (curr_vec[0] ** 2 + curr_vec[1] ** 2) ** 0.5

            if prev_len > 0 and curr_len > 0:
                cos_angle = dot_product / (prev_len * curr_len)
                # Clamp to avoid numerical errors
                cos_angle = max(min(cos_angle, 1.0), -1.0)
                angle = abs(math.acos(cos_angle))

                # If angle is greater than threshold, it's a curve
                is_curved = angle > curve_threshold
        is_curved_segment.append(is_curved)

    # Apply the mesh to the object
    bm.to_mesh(mesh)  # pyright: ignore
    bm.free()  # pyright: ignore

    # First, unwrap the UVs - this is essential for material continuity
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Add materials
    obj.data.materials.append(default_material)  # pyright: ignore
    obj.data.materials.append(curbstone_a_mat)  # pyright: ignore
    obj.data.materials.append(curbstone_b_mat)  # pyright: ignore

    # Create material slots for each section
    material_sections = []  # Will track continuous sections of the same material

    # Variables to track the state of curb pattern
    in_curve = False
    current_material = 1  # Start with curbstone_a_mat (index 1)
    accumulated_area = 0.0
    target_area_a = 5.0
    target_area_b = 3.5

    # First pass - identify continuous sections with the same material
    current_section = {"material": 0, "start": 0, "end": 0}

    # Assign material indices to faces
    for i, poly in enumerate(obj.data.polygons):  # pyright: ignore
        # Calculate face area (approximate)
        face_area = poly.area

        # If we're entering a curve
        if is_curved_segment[i] and not in_curve:
            in_curve = True
            accumulated_area = 0.0
            current_material = 1  # Start with curbstone_a_mat

            # Close previous section and start a new one if material changed
            if current_section["material"] != current_material:
                current_section["end"] = i - 1
                material_sections.append(current_section.copy())
                current_section = {"material": current_material, "start": i, "end": i}

        # If we're in a curve or completing a pattern segment
        if in_curve:
            # Assign current material
            poly.material_index = current_material

            # Add face area to accumulated area
            accumulated_area += face_area

            # Check if we've completed a pattern segment - use different target areas for each material
            current_target = target_area_a if current_material == 1 else target_area_b
            if accumulated_area >= current_target:
                # Switch materials
                previous_material = current_material
                current_material = 3 - current_material  # Toggle between 1 and 2
                accumulated_area = 0.0  # Reset accumulated area

                # Close current section and start a new one
                current_section["end"] = i
                material_sections.append(current_section.copy())
                current_section = {
                    "material": current_material,
                    "start": i + 1,
                    "end": i + 1,
                }

                # If we've left the curve, check if any of the next 10 elements are curved
                if not is_curved_segment[i]:
                    # Look ahead to see if we should stay in curve mode
                    stay_in_curve = False
                    for j in range(1, 21):  # Check next 20 segments
                        look_ahead_idx = (i + j) % len(is_curved_segment)
                        if is_curved_segment[look_ahead_idx]:
                            stay_in_curve = True
                            break
                    in_curve = stay_in_curve

                    # If we're leaving curve mode, close the section
                    if not stay_in_curve:
                        current_section["end"] = i
                        material_sections.append(current_section.copy())
                        current_section = {"material": 0, "start": i + 1, "end": i + 1}
        else:
            # Not in curve, use default material
            poly.material_index = 0

            # If we're just starting with default material
            if i == 0:
                current_section = {"material": 0, "start": 0, "end": 0}
            elif current_section["material"] != 0:
                # Close previous section and start default material section
                current_section["end"] = i - 1
                material_sections.append(current_section.copy())
                current_section = {"material": 0, "start": i, "end": i}
            else:
                # Continue default material section
                current_section["end"] = i

    # Add the last section if necessary
    if current_section["start"] <= current_section["end"]:
        material_sections.append(current_section)

    # Enter edit mode to work with UV mapping
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")

    # Get bmesh for UV editing
    bm = bmesh.from_edit_mesh(obj.data)

    # Ensure UV layer exists
    if not bm.loops.layers.uv:
        bm.loops.layers.uv.new()
    uv_layer = bm.loops.layers.uv.verify()

    # Process each material section for continuous UV mapping
    for section in material_sections:
        material_idx = section["material"]
        start_idx = section["start"]
        end_idx = section["end"]

        # Skip very small sections
        if end_idx - start_idx < 1:
            continue

        # Select faces in this section
        bpy.ops.mesh.select_all(action="DESELECT")
        bm.faces.ensure_lookup_table()

        # Select all faces in this section
        for i in range(start_idx, end_idx + 1):
            if i < len(bm.faces):
                bm.faces[i].select = True

        # Update the mesh to reflect selection
        bmesh.update_edit_mesh(obj.data)

        # Now unwrap just these faces together for continuous mapping
        bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.02)

        # For curb materials, adjust UVs to be along the curb direction
        if material_idx in (1, 2):  # Curb materials
            for i in range(start_idx, end_idx + 1):
                if i < len(bm.faces):
                    face = bm.faces[i]
                    # For each loop in the face (loop = edge+vertex)
                    for loop in face.loops:
                        # Get current UV
                        uv = loop[uv_layer].uv
                        # Stretch UVs along curb direction
                        uv.y *= 0.25  # Scale down in V direction
                        uv.x *= 2.0  # Scale up in U direction
                        # Store back
                        loop[uv_layer].uv = uv

    # Return to object mode
    bpy.ops.object.mode_set(mode="OBJECT")

    return obj


def create_planes(
    inner_points: list[tuple[float, float, float]],
    outer_points: list[tuple[float, float, float]],
    name: str,
    material: Optional[bpy.types.Material] = None,
    alternate_material: Optional[bpy.types.Material] = None,
    is_curb: bool = True,
):
    """Create a mesh plane between two sets of points.

    Args:
        inner_points: List of 4D coordinates representing the inner edge
        outer_points: List of 4D coordinates representing the outer edge
        name: Base name for the created object
        material: Blender material to apply to the mesh (optional)

    Returns:
        The created Blender object

    """
    mesh = bpy.data.meshes.new(name + "TrackMesh")
    obj = bpy.data.objects.new(name + "Track", mesh)
    bpy.context.collection.objects.link(obj)  # pyright: ignore

    bm = bmesh.new()

    inner_verts = [bm.verts.new(coord) for coord in inner_points]
    outer_verts = [bm.verts.new(coord) for coord in outer_points]

    bm.verts.ensure_lookup_table()  # pyright: ignore

    for i in range(len(inner_points) - 1):
        bm.faces.new(
            [inner_verts[i], inner_verts[i + 1], outer_verts[i + 1], outer_verts[i]]
        )

    bm.to_mesh(mesh)  # pyright: ignore
    bm.free()  # pyright: ignore

    pattern_size = 5
    if material:
        obj.data.materials.append(material)  # pyright: ignore

        # Create alternating pattern for curbs
        if is_curb and alternate_material:
            obj.data.materials.append(alternate_material)  # pyright: ignore

            # Assign material indices to faces
            for i, poly in enumerate(obj.data.polygons):  # pyright: ignore
                # Integer division to determine which material to use
                # e.g., with pattern_size=4: 0,1,2 get mat1, 3,4,5 get mat2, etc.
                material_index = (i // pattern_size) % 3
                poly.material_index = material_index

    return obj


def main(track_data: TrackData, sectors_info: Optional[SectorsInfo]) -> None:
    """Create the complete track with main surfaces and curbs.

    Args:
        track_data: The track data containing track information.
        sectors_info: Optional information about sectors.

    """
    track_collection = bpy.data.collections.new(name="TrackCollection")
    bpy.context.scene.collection.children.link(track_collection)  # pyright: ignore
    bpy.context.view_layer.active_layer_collection = (  # pyright: ignore
        bpy.context.view_layer.layer_collection.children[-1]  # pyright: ignore
    )

    curb_mat = create_asphalt_material((0.01, 0.01, 0.01), "CurbAsphalt")
    red_color = (0.128, 0, 0)
    white_color = (0.76, 0.76, 0.76)

    # curbstone_a_mat = create_racing_curb_material_evens(
    #     white_color, red_color, "CurbstoneA"
    # )
    # curbstone_b_mat = create_test_material("CurbstoneB")
    # curbstone_b_mat = create_racing_curb_material_odds(red_color, "CurbstoneB")
    # curbstone_a_mat = create_material((1, 1, 1), "CurbstoneA")
    # curbstone_b_mat = create_material((0.128, 0, 0), "CurbstoneB")

    curbstone_a_mat = create_asphalt_material(white_color, "CurbstoneA")
    curbstone_b_mat = create_asphalt_material(red_color, "CurbstoneB")
    line_mat = create_asphalt_material((0.5, 0.5, 0.5), "Line")

    # # Load the asphalt material from external blend file
    # file_path = f"{RESOURCES_DIR}/asphalt_track_4k.blend/asphalt_track_4k.blend"
    # with bpy.data.libraries.load(file_path) as (data_from, data_to):
    #     if "asphalt_track" in data_from.materials:
    #         data_to.materials = ["asphalt_track"]

    # # Use the loaded material for the track if it was successfully loaded
    # if "asphalt_track" in bpy.data.materials:
    #     track_mat = bpy.data.materials["asphalt_track"]

    track_mat = create_asphalt_material()
    create_planes_new(
        track_data.inner_points,
        track_data.outer_points,
        "Main",
        track_mat,
    )

    create_planes_curb(
        track_data.outer_points,
        track_data.outer_curb_points,
        "CurbOuter",
        curb_mat,
        curbstone_a_mat,
        curbstone_b_mat,
    )
    create_planes_curb(
        track_data.inner_points,
        track_data.inner_curb_points,
        "CurbInner",
        curb_mat,
        curbstone_a_mat,
        curbstone_b_mat,
    )

    if track_data.inner_trace_line and track_data.outer_trace_line and sectors_info:
        create_boxes(
            track_data.inner_trace_line.a_points,
            track_data.inner_trace_line.b_points,
            sectors_info,
            "InnerLine",
            0.005,
            line_mat,
        )
        create_boxes(
            track_data.outer_trace_line.a_points,
            track_data.outer_trace_line.b_points,
            sectors_info,
            "OuterLine",
            0.005,
            line_mat,
        )
