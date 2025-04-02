import bpy


def add_sky_texture():
    """Add a sky texture to the world."""
    world = bpy.data.worlds["World"]
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    for node in nodes:
        nodes.remove(node)

    # Create sky texture node
    sky_texture = nodes.new(type="ShaderNodeTexSky")

    # Configure the sky texture with Nishita model
    sky_texture.sky_type = "NISHITA"
    # Disable sun disk
    sky_texture.sun_disc = False

    # Configure other Nishita parameters
    sky_texture.sun_elevation = (
        1.0  # Sun angle above horizon in radians (about 57 degrees)
    )
    sky_texture.sun_rotation = 0.0  # Sun angle around the horizon in radians
    sky_texture.altitude = 1000.0  # Viewer altitude in km
    sky_texture.air_density = 0.430
    sky_texture.dust_density = 0.352
    sky_texture.ozone_density = 10.0

    # Create background node for sky
    background_sky = nodes.new(type="ShaderNodeBackground")
    background_sky.inputs[1].default_value = 0.2

    # Create Musgrave texture node
    musgrave = nodes.new(type="ShaderNodeTexMusgrave")
    musgrave.inputs["Scale"].default_value = 3.3
    musgrave.inputs["Detail"].default_value = 10.0
    musgrave.inputs["Dimension"].default_value = 0.47
    musgrave.inputs["Lacunarity"].default_value = 2.0

    # Create color ramp node
    color_ramp = nodes.new(type="ShaderNodeValToRGB")

    # Create second background node for Musgrave
    background_musgrave = nodes.new(type="ShaderNodeBackground")

    # Create Add Shader node
    add_shader = nodes.new(type="ShaderNodeAddShader")

    # Create output node
    output = nodes.new(type="ShaderNodeOutputWorld")

    # Connect nodes
    # Musgrave → Color Ramp → Background
    links.new(musgrave.outputs[0], color_ramp.inputs[0])
    links.new(color_ramp.outputs[0], background_musgrave.inputs[0])

    # Sky Texture → Background
    links.new(sky_texture.outputs[0], background_sky.inputs[0])

    # Both backgrounds → Add Shader
    links.new(background_sky.outputs[0], add_shader.inputs[0])
    links.new(background_musgrave.outputs[0], add_shader.inputs[1])

    # Add Shader → Output
    links.new(add_shader.outputs[0], output.inputs[0])
