import bpy

from src.utils import file_utils


def add_snow_background():
    """Add a snow background by appending material from external blend file and applying to a large plane."""
    snow_texture_blend_path = (
        file_utils.project_paths.BLENDER_DIR
        / "snow_field_aerial_4k.blend"
        / "snow_field_aerial_4k.blend"
    )

    bpy.ops.wm.append(
        filepath=str(snow_texture_blend_path),
        directory=str(snow_texture_blend_path) + "/Material/",
        filename="snow_field_aerial",
    )

    # Create a large plane
    bpy.ops.mesh.primitive_plane_add(size=100000)
    snow_plane = bpy.context.active_object
    snow_plane.name = "Snow_Background"

    # Assign the material to the plane
    snow_material = bpy.data.materials["snow_field_aerial"]
    if len(snow_plane.data.materials) == 0:
        snow_plane.data.materials.append(snow_material)
    else:
        snow_plane.data.materials[0] = snow_material

    # Scale the UVs
    for face in snow_plane.data.polygons:
        for loop_idx in face.loop_indices:
            uv = snow_plane.data.uv_layers.active.data[loop_idx].uv
            # Scale up
            uv.x *= 110
            uv.y *= 100
