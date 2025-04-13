"""Add start/finish line."""

import bmesh
import bpy
from bpy.types import Object

from src.utils.colors import hex_to_blender_rgb
from src.utils.materials import create_asphalt_material


def add_track_idx_line(
    inner_points: list[tuple[float, float, float]],
    outer_points: list[tuple[float, float, float]],
    start_finish_line_idx: int,
    name: str,
    line_width: int = 3,
    color: str = "#000000",
) -> Object:
    """Create a start/finish line between inner and outer track points.

    Uses the index of inner_points and outer_points that defines the start/finish line
    to build a plane with multiple vertices. The line width determines how many vertices
    are added to the line (typically 3 works well for normal tracks, higher values like 10
    may be used for status tracks). The line is slightly raised above the track surface
    to prevent z-fighting.

    Args:
        inner_points: List of inner track boundary points
        outer_points: List of outer track boundary points
        start_finish_line_idx: Index of the point defining the start/finish line
        name: Name of the start/finish line object
        line_width: Number of vertices to use for line width

    Returns:
        The created start/finish line object

    """
    z_offset = 0.02
    points: list[tuple[float, float, float]] = []

    points.append(inner_points[start_finish_line_idx % len(inner_points)])
    points.append(
        inner_points[(start_finish_line_idx + line_width) % len(inner_points)]
    )
    points.append(
        outer_points[(start_finish_line_idx + line_width) % len(outer_points)]
    )
    points.append(outer_points[start_finish_line_idx % len(outer_points)])

    # Apply Z offset to all points
    for i in range(len(points)):
        points[i] = (points[i][0], points[i][1], points[i][2] + z_offset)

    prefix = name
    mesh = bpy.data.meshes.new(f"{prefix}Mesh")
    obj = bpy.data.objects.new(prefix, mesh)
    bpy.context.collection.objects.link(obj)  # pyright: ignore

    bm = bmesh.new()
    for point in points:
        bm.verts.new(point)

    bm.verts.ensure_lookup_table()  # pyright: ignore
    bm.faces.new(bm.verts)  # pyright: ignore
    bm.to_mesh(mesh)  # pyright: ignore
    bm.free()  # pyright: ignore
    mesh.update()  # pyright: ignore

    # mat = create_material(hex_to_blender_rgb(color), "StartFinishLineMaterial")
    mat = create_asphalt_material(hex_to_blender_rgb(color), name)

    obj.data.materials.append(mat)  # pyright: ignore
    return obj


# where at_start is the index of the point where the car is at the start/finish line
def main(
    inner_curb_points: list[tuple[float, float, float]],
    outer_curb_points: list[tuple[float, float, float]],
    track_idx_line: int,
    name: str,
):
    """Add start/finish line."""
    indicators_collection = bpy.data.collections.new(name="IndicatorsCollection")
    bpy.context.scene.collection.children.link(indicators_collection)  # pyright: ignore
    bpy.context.view_layer.active_layer_collection = (  # pyright: ignore
        bpy.context.view_layer.layer_collection.children[-1]  # pyright: ignore
    )

    return add_track_idx_line(
        inner_curb_points, outer_curb_points, track_idx_line, name
    )
