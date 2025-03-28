import bpy


def create_material(
    color: tuple[float, float, float],
    name: str,
    emission_value: float = 0.0,
    metallic_value: float = 0.0,
    roughness_value: float = 0.0,
):
    """Create a Blender material with the specified color.

    Args:
        color: RGB color values as a tuple (r, g, b)
        name: Base name for the material

    Returns:
        The created Blender material

    """
    mat = bpy.data.materials.new(name=name + "TrackMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]  # pyright: ignore
    bsdf.inputs["Base Color"].default_value = (*color, 1)  # pyright: ignore

    bsdf.inputs["Emission Color"].default_value = (*color, 1)  # pyright: ignore
    bsdf.inputs["Emission Strength"].default_value = emission_value  # pyright: ignore

    bsdf.inputs["Metallic"].default_value = metallic_value  # pyright: ignore
    bsdf.inputs["Roughness"].default_value = roughness_value  # pyright: ignore

    return mat


def create_magic_material(
    color: tuple[float, float, float],
    name: str,
    emission_value: float = 0.0,
):
    mat = bpy.data.materials.new(name=name + "TrackMaterial")
    mat.use_nodes = True

    # Get the node tree and clear default nodes
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Keep output node and remove others for a clean slate
    output_node = nodes.get("Material Output")
    if not output_node:
        output_node = nodes.new(type="ShaderNodeOutputMaterial")

    # Create principled BSDF node
    bsdf = nodes.get("Principled BSDF")
    if not bsdf:
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")

    # Link BSDF to output
    links.new(bsdf.outputs[0], output_node.inputs[0])

    # Set base color and emission
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = emission_value

    # Create Magic texture
    magic_tex = nodes.new(type="ShaderNodeTexMagic")

    # Configure magic texture
    magic_tex.turbulence_depth = 2  # Number of iterations (1-10)
    magic_tex.inputs["Scale"].default_value = 5.0  # Scale of the pattern
    magic_tex.inputs["Distortion"].default_value = 2.0  # Amount of distortion

    # Color correction for magic texture
    hue_sat = nodes.new(type="ShaderNodeHueSaturation")
    hue_sat.inputs["Saturation"].default_value = 0.8
    hue_sat.inputs["Value"].default_value = 0.7

    # Calculate brightness from original color for hue shift
    brightness = (color[0] + color[1] + color[2]) / 3
    hue_shift = 0.5 if brightness > 0.5 else 0.0
    hue_sat.inputs["Hue"].default_value = hue_shift

    # Mix with base color
    mix_rgb = nodes.new(type="ShaderNodeMixRGB")
    mix_rgb.blend_type = "MULTIPLY"
    mix_rgb.inputs[0].default_value = 0.7  # Blending factor
    mix_rgb.inputs[1].default_value = (*color, 1.0)  # Base color

    # Connect nodes
    links.new(magic_tex.outputs["Color"], hue_sat.inputs["Color"])
    links.new(hue_sat.outputs["Color"], mix_rgb.inputs[2])
    links.new(mix_rgb.outputs[0], bsdf.inputs["Base Color"])

    # Add texture coordinates for proper mapping
    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    mapping = nodes.new(type="ShaderNodeMapping")

    # Connect texture coordinates
    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], magic_tex.inputs["Vector"])

    # Add roughness variation
    rough_mix = nodes.new(type="ShaderNodeMixRGB")
    rough_mix.blend_type = "MULTIPLY"
    rough_mix.inputs[0].default_value = 0.5
    rough_mix.inputs[1].default_value = (0.7, 0.7, 0.7, 1.0)  # Base roughness

    # Get brightness from magic texture for roughness
    bright = nodes.new(type="ShaderNodeRGBToBW")
    links.new(magic_tex.outputs["Color"], bright.inputs["Color"])
    links.new(bright.outputs[0], rough_mix.inputs[2])
    links.new(rough_mix.outputs[0], bsdf.inputs["Roughness"])

    return mat


def create_asphalt_material(color=(0.05, 0.05, 0.05), name: str = "Asphalt"):
    """Create a realistic asphalt material with improved darkness and seamless blending."""
    # Darker base color - real asphalt is nearly black
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True  # Clear existing nodes
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()  # Create nodes
    output = nodes.new(type="ShaderNodeOutputMaterial")
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    output.location = (600, 0)
    bsdf.location = (400, 0)

    # Set base properties - darker and less reflective
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9  # More rough
    # bsdf.inputs["Specular"].default_value = 0.05  # Less specular reflection

    # Add texture coordinates for consistent mapping
    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    tex_coord.location = (-800, 0)

    # Add mapping node to control texture scale and ensure seamless blending
    mapping = nodes.new(type="ShaderNodeMapping")
    mapping.location = (-600, 0)

    # Use UV coordinates for better control over seams
    links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])

    # Scale textures to be very small (high number = small details)
    mapping.inputs["Scale"].default_value = (30.0, 30.0, 30.0)

    # Add noise texture for asphalt graininess
    noise = nodes.new(type="ShaderNodeTexNoise")
    noise.location = (-400, 200)
    noise.inputs["Scale"].default_value = 5.0  # Will be multiplied by the mapping scale
    noise.inputs["Detail"].default_value = 8.0  # More detail
    noise.inputs["Roughness"].default_value = 0.6
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])

    # Add color ramp to control noise effect - less contrast
    ramp = nodes.new(type="ShaderNodeValToRGB")
    ramp.location = (-200, 200)
    ramp.color_ramp.elements[0].position = 0.4

    # Darker minimum (less contrast)
    color_dark = (color[0] * 0.9, color[1] * 0.9, color[2] * 0.9, 1.0)
    ramp.color_ramp.elements[0].color = color_dark

    ramp.color_ramp.elements[1].position = 0.6

    # Less contrast for the light areas
    color_light = (
        min(color[0] * 1.05, 1.0),  # Only 5% brighter instead of 10%
        min(color[1] * 1.05, 1.0),
        min(color[2] * 1.05, 1.0),
        1.0,
    )
    ramp.color_ramp.elements[1].color = color_light

    links.new(noise.outputs["Fac"], ramp.inputs[0])

    # Add a subtle voronoi texture for larger asphalt details
    voronoi = nodes.new(type="ShaderNodeTexVoronoi")
    voronoi.location = (-400, 0)
    voronoi.inputs["Scale"].default_value = 3.0  # Will be multiplied by mapping scale
    voronoi.voronoi_dimensions = "3D"  # Better for seamless blending
    links.new(mapping.outputs["Vector"], voronoi.inputs["Vector"])

    # Create a separate color ramp for the voronoi to control its contrast
    voronoi_ramp = nodes.new(type="ShaderNodeValToRGB")
    voronoi_ramp.location = (-200, 0)
    voronoi_ramp.color_ramp.elements[0].position = 0.3
    voronoi_ramp.color_ramp.elements[0].color = (0.03, 0.03, 0.03, 1.0)  # Very dark
    voronoi_ramp.color_ramp.elements[1].position = 0.7
    voronoi_ramp.color_ramp.elements[1].color = (0.08, 0.08, 0.08, 1.0)  # Dark
    links.new(voronoi.outputs[0], voronoi_ramp.inputs[0])

    # Mix with the noise - more subtle effect
    mix = nodes.new(type="ShaderNodeMixRGB")
    mix.location = (0, 100)
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 0.3  # More subtle voronoi effect (was 0.7)

    links.new(voronoi_ramp.outputs[0], mix.inputs[2])
    links.new(ramp.outputs[0], mix.inputs[1])

    # Add bump mapping for texture - more subtle
    bump = nodes.new(type="ShaderNodeBump")
    bump.location = (200, -100)
    bump.inputs["Strength"].default_value = 0.1  # More subtle bump (was 0.2)

    # Mix noise and voronoi for the bump input
    bump_mix = nodes.new(type="ShaderNodeMixRGB")
    bump_mix.location = (0, -100)
    bump_mix.blend_type = "ADD"
    bump_mix.inputs[0].default_value = 0.5

    links.new(noise.outputs["Fac"], bump_mix.inputs[1])
    links.new(voronoi.outputs[0], bump_mix.inputs[2])
    links.new(bump_mix.outputs[0], bump.inputs["Height"])

    # Add ambient occlusion for more depth in crevices
    ao = nodes.new(type="ShaderNodeAmbientOcclusion")
    ao.location = (200, 100)
    ao.inputs["Distance"].default_value = 0.1  # Small-scale AO
    links.new(mix.outputs[0], ao.inputs["Color"])

    # Final connections
    links.new(ao.outputs[0], bsdf.inputs["Base Color"])
    links.new(bump.outputs[0], bsdf.inputs["Normal"])
    links.new(bsdf.outputs[0], output.inputs[0])

    return mat


def create_racing_curb_material_evens(
    main_color: tuple[float, float, float],
    splotch_color: tuple[float, float, float],
    name: str,
):
    """Create a rough outdoor paint material with spotty texture and random color splotches.

    Args:
        main_color: Base RGB color values
        splotch_color: Secondary RGB color for random splotches
        name: Base name for the material

    Returns:
        The created Blender material

    """
    mat = bpy.data.materials.new(name=name + "EvensCurb")
    mat.use_nodes = True

    # Get the node tree and clear it
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Create basic nodes
    output = nodes.new(type="ShaderNodeOutputMaterial")
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    output.location = (600, 0)
    bsdf.location = (400, 0)

    # Connect shader to output
    links.new(bsdf.outputs[0], output.inputs[0])

    # Setup rough outdoor paint properties
    bsdf.inputs["Base Color"].default_value = (*main_color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7  # Quite rough for outdoor paint

    # Add texture coordinates for proper UV mapping
    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    mapping = nodes.new(type="ShaderNodeMapping")
    tex_coord.location = (-800, 0)
    mapping.location = (-600, 0)

    # Use UV coordinates for consistent mapping between sections
    links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])

    # Add noise for spotty base texture (similar to asphalt)
    noise_base = nodes.new(type="ShaderNodeTexNoise")
    noise_base.location = (-400, 100)
    # Settings for spotty appearance rather than lines
    noise_base.inputs["Scale"].default_value = 20.0  # Higher scale for smaller spots
    noise_base.inputs["Detail"].default_value = 6.0  # More detail for spotty look
    noise_base.inputs["Roughness"].default_value = 0.6
    noise_base.inputs[
        "Distortion"
    ].default_value = 0.4  # Add some distortion for less linear pattern
    links.new(mapping.outputs["Vector"], noise_base.inputs["Vector"])

    # Add Voronoi texture for spotty pattern (similar to asphalt)
    voronoi = nodes.new(type="ShaderNodeTexVoronoi")
    voronoi.location = (-400, -100)
    voronoi.voronoi_dimensions = "3D"  # Better for spotty look
    voronoi.feature = "F1"  # Cell distance
    voronoi.inputs["Scale"].default_value = 15.0
    links.new(mapping.outputs["Vector"], voronoi.inputs["Vector"])

    # Mix noise and voronoi for base texture variation
    mix_texture = nodes.new(type="ShaderNodeMixRGB")
    mix_texture.location = (-200, 0)
    mix_texture.blend_type = "MULTIPLY"
    mix_texture.inputs[0].default_value = 0.7
    links.new(noise_base.outputs["Fac"], mix_texture.inputs[1])
    links.new(voronoi.outputs["Distance"], mix_texture.inputs[2])

    # Color ramp for texture variation
    ramp_base = nodes.new(type="ShaderNodeValToRGB")
    ramp_base.location = (0, 100)

    # More contrast for rough outdoor paint
    ramp_base.color_ramp.elements[0].position = 0.4
    ramp_base.color_ramp.elements[1].position = 0.6

    # More visible variation for weathered outdoor paint
    color_dark = (
        max(main_color[0] * 0.85, 0.0),  # 15% darker
        max(main_color[1] * 0.85, 0.0),
        max(main_color[2] * 0.85, 0.0),
        1.0,
    )
    ramp_base.color_ramp.elements[0].color = color_dark

    color_light = (
        min(main_color[0] * 1.1, 1.0),  # 10% lighter
        min(main_color[1] * 1.1, 1.0),
        min(main_color[2] * 1.1, 1.0),
        1.0,
    )
    ramp_base.color_ramp.elements[1].color = color_light

    # Connect mixed texture to color ramp
    links.new(mix_texture.outputs[0], ramp_base.inputs[0])

    # Create second noise for random splotches of secondary color
    noise_splotch = nodes.new(type="ShaderNodeTexNoise")
    noise_splotch.location = (-400, -250)
    noise_splotch.inputs[
        "Scale"
    ].default_value = 5.0  # Larger scale for bigger splotches
    noise_splotch.inputs[
        "Detail"
    ].default_value = 2.0  # Less detail for clear splotches
    noise_splotch.inputs["Roughness"].default_value = 0.5
    links.new(mapping.outputs["Vector"], noise_splotch.inputs["Vector"])

    # Color ramp to create distinct splotches
    ramp_splotch = nodes.new(type="ShaderNodeValToRGB")
    ramp_splotch.location = (-200, -250)

    # Set positions for clear splotches
    ramp_splotch.color_ramp.elements[
        0
    ].position = 0.6  # Only high values become splotches
    ramp_splotch.color_ramp.elements[0].color = (*main_color, 1.0)  # Main color
    ramp_splotch.color_ramp.elements[1].position = 0.7  # Sharp transition
    ramp_splotch.color_ramp.elements[1].color = (*splotch_color, 1.0)  # Splotch color

    links.new(noise_splotch.outputs["Fac"], ramp_splotch.inputs[0])

    # Mix base texture with splotches
    mix_splotch = nodes.new(type="ShaderNodeMixRGB")
    mix_splotch.location = (200, 0)
    mix_splotch.blend_type = "MIX"
    mix_splotch.inputs[0].default_value = 0.9  # Strength of splotch effect
    links.new(
        ramp_splotch.outputs["Color"], mix_splotch.inputs[0]
    )  # Use splotch as factor
    links.new(ramp_base.outputs["Color"], mix_splotch.inputs[1])
    links.new(ramp_splotch.outputs["Color"], mix_splotch.inputs[2])

    # Create bump mapping for rough paint texture
    bump = nodes.new(type="ShaderNodeBump")
    bump.location = (200, -100)
    bump.inputs["Strength"].default_value = 0.2  # More pronounced for rough paint

    # Mix noises for bump input
    mix_bump = nodes.new(type="ShaderNodeMixRGB")
    mix_bump.location = (0, -100)
    mix_bump.blend_type = "ADD"
    mix_bump.inputs[0].default_value = 0.5
    links.new(noise_base.outputs["Fac"], mix_bump.inputs[1])
    links.new(voronoi.outputs["Distance"], mix_bump.inputs[2])

    links.new(mix_bump.outputs[0], bump.inputs["Height"])

    # Final connections
    links.new(mix_splotch.outputs[0], bsdf.inputs["Base Color"])
    links.new(bump.outputs[0], bsdf.inputs["Normal"])

    return mat


def create_racing_curb_material_odds(color: tuple[float, float, float], name: str):
    """Create a rough outdoor paint material for odd-numbered racing curb segments.

    This creates a solid color with rough texture for segments that will
    alternate with white segments. The material matches the properties and
    texture of the main racing curb material for seamless transitions.

    Args:
        color: Base RGB color values (typically red)
        name: Base name for the material

    Returns:
        The created Blender material

    """
    mat = bpy.data.materials.new(name=name + "OddsCurb")
    mat.use_nodes = True

    # Get the node tree and clear it
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Create basic nodes
    output = nodes.new(type="ShaderNodeOutputMaterial")
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    output.location = (400, 0)
    bsdf.location = (200, 0)

    # Connect shader to output
    links.new(bsdf.outputs[0], output.inputs[0])

    # Setup rough outdoor paint properties - matching the other material
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7  # Quite rough for outdoor paint

    # Texture coordinates for proper UV mapping
    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    mapping = nodes.new(type="ShaderNodeMapping")
    tex_coord.location = (-600, 0)
    mapping.location = (-400, 0)
    # Use UV coordinates for consistent mapping between sections
    links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])

    # Add simple noise for rough paint texture - matching the other material
    noise = nodes.new(type="ShaderNodeTexNoise")
    noise.location = (-200, 100)
    noise.inputs["Scale"].default_value = 15.0
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.7  # Rough texture
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])

    # Color ramp for texture variation
    ramp = nodes.new(type="ShaderNodeValToRGB")
    ramp.location = (0, 100)

    # More contrast for rough outdoor paint
    ramp.color_ramp.elements[0].position = 0.4
    ramp.color_ramp.elements[1].position = 0.6

    # More visible variation for weathered outdoor paint
    color_dark = (
        max(color[0] * 0.85, 0.0),  # 15% darker
        max(color[1] * 0.85, 0.0),
        max(color[2] * 0.85, 0.0),
        1.0,
    )
    ramp.color_ramp.elements[0].color = color_dark

    color_light = (
        min(color[0] * 1.1, 1.0),  # 10% lighter
        min(color[1] * 1.1, 1.0),
        min(color[2] * 1.1, 1.0),
        1.0,
    )
    ramp.color_ramp.elements[1].color = color_light

    # Connect noise to color ramp
    links.new(noise.outputs["Fac"], ramp.inputs[0])

    # Create bump mapping for rough paint texture
    bump = nodes.new(type="ShaderNodeBump")
    bump.location = (0, -100)
    bump.inputs["Strength"].default_value = 0.2  # More pronounced for rough paint
    links.new(noise.outputs["Fac"], bump.inputs["Height"])

    # Final connections
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bump.outputs[0], bsdf.inputs["Normal"])

    return mat


def create_test_material(name: str):
    # Create a new material
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    # Clear all nodes
    nodes = mat.node_tree.nodes
    for node in nodes:
        nodes.remove(node)

    # Create links
    links = mat.node_tree.links

    # Create texture coordinate node
    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    tex_coord.location = (-700, 600)

    # Create mapping node
    mapping = nodes.new(type="ShaderNodeMapping")
    mapping.location = (-500, 450)
    mapping.inputs["Location"].default_value[0] = 0
    mapping.inputs["Location"].default_value[1] = 0
    mapping.inputs["Location"].default_value[2] = 0
    mapping.inputs["Rotation"].default_value[0] = 0
    mapping.inputs["Rotation"].default_value[1] = 0
    mapping.inputs["Rotation"].default_value[2] = 0
    mapping.inputs["Scale"].default_value[0] = 1.0
    mapping.inputs["Scale"].default_value[1] = 1.0
    mapping.inputs["Scale"].default_value[2] = 1.0

    # Create noise texture node
    noise_tex = nodes.new(type="ShaderNodeTexNoise")
    noise_tex.location = (-300, 300)
    noise_tex.inputs["Scale"].default_value = 31.0
    noise_tex.inputs["Detail"].default_value = 7.2
    noise_tex.inputs["Roughness"].default_value = 1.0
    noise_tex.inputs["Lacunarity"].default_value = 4.6
    noise_tex.inputs["Distortion"].default_value = 0.0
    noise_tex.noise_dimensions = "3D"

    # Create first color ramp node (for noise)
    color_ramp1 = nodes.new(type="ShaderNodeValToRGB")
    color_ramp1.location = (0, 300)
    color_ramp1.color_ramp.elements[0].position = 0
    color_ramp1.color_ramp.elements[0].color = (1, 0, 0, 1)  # Red
    color_ramp1.color_ramp.elements[1].position = 0.094
    color_ramp1.color_ramp.elements[1].color = (1, 1, 1, 1)  # White

    # Create gradient texture node
    gradient_tex = nodes.new(type="ShaderNodeTexGradient")
    gradient_tex.location = (-300, 0)

    # Create second color ramp node (for gradient)
    color_ramp2 = nodes.new(type="ShaderNodeValToRGB")
    color_ramp2.location = (0, 0)

    color_ramp2.color_ramp.elements[0].position = 0
    color_ramp2.color_ramp.elements[0].color = (1, 0.2, 0.2, 1)

    # Add second element - red
    red_element1 = color_ramp2.color_ramp.elements.new(0.175)
    red_element1.color = (0.19613, 0, 0, 1)  # Red

    # Add third element - red
    red_element2 = color_ramp2.color_ramp.elements.new(0.5)
    red_element2.color = (0.19613, 0, 0, 1)  # Red

    # Add fourth element - red
    red_element3 = color_ramp2.color_ramp.elements.new(0.825)
    red_element3.color = (0.19613, 0, 0, 1)  # Red

    # Add fifth element - white
    white_element = color_ramp2.color_ramp.elements.new(1.0)
    white_element.color = (1, 0.2, 0.2, 1)

    color_ramp2.color_ramp.interpolation = "B_SPLINE"
    # Create mix node
    mix = nodes.new(type="ShaderNodeMixRGB")
    mix.location = (300, 150)
    mix.inputs["Fac"].default_value = 0.995

    # Create bump node
    bump = nodes.new(type="ShaderNodeBump")
    bump.location = (300, 400)
    bump.inputs["Strength"].default_value = 0.073
    bump.inputs["Distance"].default_value = 0.1

    # Create principled BSDF node
    principled = nodes.new(type="ShaderNodeBsdfPrincipled")
    principled.location = (600, 150)
    principled.inputs["Metallic"].default_value = 0.0
    principled.inputs["Roughness"].default_value = 0.5
    principled.inputs["IOR"].default_value = 1.45
    principled.inputs["Alpha"].default_value = 1.0

    # Create material output node
    material_output = nodes.new(type="ShaderNodeOutputMaterial")
    material_output.location = (800, 150)

    # Create links
    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], gradient_tex.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise_tex.inputs["Vector"])
    links.new(gradient_tex.outputs["Fac"], color_ramp2.inputs["Fac"])
    links.new(noise_tex.outputs["Fac"], bump.inputs["Height"])
    links.new(noise_tex.outputs["Fac"], color_ramp1.inputs["Fac"])
    links.new(color_ramp1.outputs["Color"], mix.inputs["Color1"])
    links.new(color_ramp2.outputs["Color"], mix.inputs["Color2"])
    links.new(mix.outputs["Color"], principled.inputs["Base Color"])
    links.new(bump.outputs["Normal"], principled.inputs["Normal"])
    links.new(principled.outputs["BSDF"], material_output.inputs["Surface"])

    return mat
