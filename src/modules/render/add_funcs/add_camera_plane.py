"""Add a gradient plane to the scene."""

import math

import bpy

from src.models.config import Config


def add_camera_plane(config: Config, camera_obj: bpy.types.Object):
    """Add a gradient plane to the scene."""
    # Create a new mesh for the plane
    mesh = bpy.data.meshes.new("GradientPlaneMesh")
    plane_obj = bpy.data.objects.new("GradientPlane", mesh)

    # Create vertices for the plane (simple rectangle)
    width = 2.0  # Width of the plane
    height = 0.5  # Height of the plane
    vertices = [
        (-width / 2, -height / 2, 0),
        (width / 2, -height / 2, 0),
        (width / 2, height / 2, 0),
        (-width / 2, height / 2, 0),
    ]

    # Create faces (just one face with 4 vertices)
    faces = [(0, 1, 2, 3)]

    # Create the mesh from vertices and faces
    mesh.from_pydata(vertices, [], faces)
    mesh.update()

    # Add the plane to the scene
    bpy.context.collection.objects.link(plane_obj)  # pyright: ignore

    # Make the plane a child of the camera
    plane_obj.parent = camera_obj
    plane_obj.location = (0, 0, -1)  # Position at (0, 0, -1) relative to camera

    # Create gradient material
    mat = bpy.data.materials.new(name="GradientMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes  # pyright: ignore
    links = mat.node_tree.links  # pyright: ignore

    # Clear default nodes
    for node in nodes:
        nodes.remove(node)

    # Create new nodes for the gradient
    output_node = nodes.new("ShaderNodeOutputMaterial")
    mix_shader = nodes.new("ShaderNodeMixShader")
    transparent_shader = nodes.new("ShaderNodeBsdfTransparent")
    diffuse_shader = nodes.new("ShaderNodeBsdfDiffuse")
    gradient_node = nodes.new("ShaderNodeTexGradient")

    # Position nodes for better readability
    output_node.location = (300, 0)
    mix_shader.location = (100, 0)
    transparent_shader.location = (-100, -100)
    diffuse_shader.location = (-100, 100)
    gradient_node.location = (-300, 0)

    # Set the diffuse shader to black
    diffuse_shader.inputs[0].default_value = (0, 0, 0, 1)  # pyright: ignore

    # Create node connections
    links.new(gradient_node.outputs[0], mix_shader.inputs[0])
    links.new(diffuse_shader.outputs[0], mix_shader.inputs[1])
    links.new(transparent_shader.outputs[0], mix_shader.inputs[2])
    links.new(mix_shader.outputs[0], output_node.inputs[0])

    # Set material settings
    mat.blend_method = "BLEND"
    mat.shadow_method = "NONE"  # pyright: ignore

    plane_obj.data.materials.append(mat)  # pyright: ignore

    if config["render"]["is_shorts_output"]:
        plane_obj.location = (0, 0.21, -1.1)
        plane_obj.rotation_euler = (0, 0, math.radians(270))
        plane_obj.scale = (0.19, 0.9, 1)

        plane_obj_2 = plane_obj.copy()
        plane_obj_2.data = plane_obj.data.copy()
        plane_obj_2.parent = camera_obj
        plane_obj_2.location = (0, -0.21, -1.1)
        plane_obj_2.rotation_euler = (0, 0, math.radians(90))
        bpy.context.collection.objects.link(plane_obj_2)
    else:
        plane_obj.location = (0, 0.16, -1.1)
        plane_obj.rotation_euler = (0, 0, math.radians(270))
        plane_obj.scale = (0.07, 1.6, 1)
