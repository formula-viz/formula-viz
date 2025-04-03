import bpy


def add_sky_texture():
    """Add a sky texture to the world."""
    world = bpy.data.worlds["World"]
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    for node in nodes:
        nodes.remove(node)

    def configure_sky_texture():
        sky_texture = nodes.new(type="ShaderNodeTexSky")
        sky_texture.sky_type = "NISHITA"
        sky_texture.sun_disc = False
        sky_texture.sun_elevation = 1.0
        sky_texture.sun_rotation = 0.0
        sky_texture.altitude = 1000.0
        sky_texture.air_density = 0.430
        sky_texture.dust_density = 0.352
        sky_texture.ozone_density = 10.0

        # Position the sky texture node
        sky_texture.location = (-600, 300)
        return sky_texture

    def create_nodes():
        sky_texture = configure_sky_texture()

        # Create and position the background nodes
        background_sky = nodes.new(type="ShaderNodeBackground")
        background_sky.location = (-400, 300)
        background_sky.inputs[1].default_value = 0.1

        solid_blue_bg = nodes.new(type="ShaderNodeBackground")
        solid_blue_bg.location = (-400, 150)
        solid_blue_bg.inputs[0].default_value = (0.354671, 0.603643, 0.979584, 1)
        solid_blue_bg.inputs[1].default_value = 0.2

        # Create and position mix shader
        mix_shader = nodes.new(type="ShaderNodeMixShader")
        mix_shader.location = (-200, 250)
        mix_shader.inputs[0].default_value = 0.8

        # Create and position Musgrave texture nodes
        musgrave = nodes.new(type="ShaderNodeTexMusgrave")
        musgrave.location = (-600, -50)
        musgrave.inputs["Scale"].default_value = 3.3
        musgrave.inputs["Detail"].default_value = 10.0
        musgrave.inputs["Dimension"].default_value = 0.47
        musgrave.inputs["Lacunarity"].default_value = 2.0

        # Create and position color ramp
        color_ramp = nodes.new(type="ShaderNodeValToRGB")
        color_ramp.location = (-400, -50)

        # Create and position background for Musgrave
        background_musgrave = nodes.new(type="ShaderNodeBackground")
        background_musgrave.location = (-200, -50)

        # Create and position add shader
        add_shader = nodes.new(type="ShaderNodeAddShader")
        add_shader.location = (0, 200)

        # Create and position output node
        output = nodes.new(type="ShaderNodeOutputWorld")
        output.location = (200, 200)

        return {
            "sky_texture": sky_texture,
            "background_sky": background_sky,
            "solid_blue_bg": solid_blue_bg,
            "mix_shader": mix_shader,
            "musgrave": musgrave,
            "color_ramp": color_ramp,
            "background_musgrave": background_musgrave,
            "add_shader": add_shader,
            "output": output,
        }

    def connect_nodes(node_dict):
        # Sky texture to mix shader
        links.new(
            node_dict["sky_texture"].outputs[0], node_dict["background_sky"].inputs[0]
        )
        links.new(
            node_dict["background_sky"].outputs[0], node_dict["mix_shader"].inputs[1]
        )
        links.new(
            node_dict["solid_blue_bg"].outputs[0], node_dict["mix_shader"].inputs[2]
        )

        # Musgrave setup
        links.new(node_dict["musgrave"].outputs[0], node_dict["color_ramp"].inputs[0])
        links.new(
            node_dict["color_ramp"].outputs[0],
            node_dict["background_musgrave"].inputs[0],
        )

        # Connect mix shader where sky texture was previously connected
        links.new(node_dict["mix_shader"].outputs[0], node_dict["add_shader"].inputs[0])
        links.new(
            node_dict["background_musgrave"].outputs[0],
            node_dict["add_shader"].inputs[1],
        )

        # Final output
        links.new(node_dict["add_shader"].outputs[0], node_dict["output"].inputs[0])

    nodes_dict = create_nodes()
    connect_nodes(nodes_dict)
