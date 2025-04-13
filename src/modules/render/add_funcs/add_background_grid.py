"""Add background grids.

Mimic the default viewport blender background grid but improved and visible during the render.
"""

import bpy

from src.utils.logger import log_info


def create_grid_curves(
    index: int = 0,
    size: int = 1000,
    spacing: float = 1.0,
    offset: tuple[float, float, float] = (0, 0, 0),
    collection=None,
):
    """Create grid using curves instead of mesh."""
    curve_data = bpy.data.curves.new("GridCurve", type="CURVE")
    curve_data.dimensions = "3D"

    curve_data.resolution_u = 1
    curve_data.bevel_depth = 0.02  # Line thickness

    # Create grid lines
    for i in range(-size // 2, size // 2 + 1):
        # X direction
        spline = curve_data.splines.new("POLY")
        spline.points.add(1)
        pos = i * spacing
        spline.points[0].co = (
            -size * spacing / 2 + offset[0],
            pos + offset[1],
            -10 + offset[2],
            1,
        )
        spline.points[1].co = (
            size * spacing / 2 + offset[0],
            pos + offset[1],
            -10 + offset[2],
            1,
        )

        # Y direction
        spline = curve_data.splines.new("POLY")
        spline.points.add(1)
        spline.points[0].co = (
            pos + offset[0],
            -size * spacing / 2 + offset[1],
            -10 + offset[2],
            1,
        )
        spline.points[1].co = (
            pos + offset[0],
            size * spacing / 2 + offset[1],
            -10 + offset[2],
            1,
        )

    # Create object
    grid_obj = bpy.data.objects.new("BackgroundGrid" + str(index), curve_data)

    # Add to collection if specified, otherwise to scene collection
    if collection:
        collection.objects.link(grid_obj)
    else:
        bpy.context.scene.collection.objects.link(grid_obj)

    return grid_obj


def create_grid_material(rgb: tuple[float, float, float, float] = (0.1, 0.2, 0.2, 1)):
    """Create an emission material for the grid."""
    material = bpy.data.materials.new(name="GridMaterial")
    material.use_nodes = True
    nodes = material.node_tree.nodes  # pyright: ignore
    links = material.node_tree.links  # pyright: ignore

    nodes.clear()  # pyright: ignore

    emission = nodes.new(type="ShaderNodeEmission")
    output = nodes.new(type="ShaderNodeOutputMaterial")

    emission.inputs["Color"].default_value = rgb  # pyright: ignore
    emission.inputs["Strength"].default_value = 0.5  # pyright: ignore

    links.new(emission.outputs[0], output.inputs[0])

    return material


def main():
    """Create a background grid."""
    log_info("Creating background grid")

    grid_collection = bpy.data.collections.new("BackgroundGrids")
    bpy.context.scene.collection.children.link(grid_collection)  # pyright: ignore

    grid_obj1 = create_grid_curves(
        index=1, size=1000, spacing=3.0, offset=(0, 0, 0), collection=grid_collection
    )
    grid_obj2 = create_grid_curves(
        index=2,
        size=1000,
        spacing=3.0,
        offset=(1.0, 0.5, 0),
        collection=grid_collection,
    )

    grid_material1 = create_grid_material((0.1, 0.2, 0.2, 1))  # cyan
    grid_obj1.data.materials.append(grid_material1)  # pyright: ignore

    grid_material2 = create_grid_material((0.4, 0.4, 0.4, 1))  # gray
    grid_obj2.data.materials.append(grid_material2)  # pyright: ignore
