"""Add a sun to the scene."""

import bpy


def create_sun(name, location, energy=1.5, color=(0.991268, 1.0, 0.863095)):
    """Create a sun light at the specified location.

    Args:
        name: Name of the sun
        location: (x, y, z) location
        energy: Light energy/intensity
        color: RGB color tuple

    Returns:
        The created sun object

    """
    light_data = bpy.data.lights.new(name=f"{name}-Data", type="SUN")
    light_data.energy = energy  # pyright: ignore
    light_object = bpy.data.objects.new(name=name, object_data=light_data)

    # Set sun color
    light_data.color = color  # RGB values for warm sunlight

    bpy.context.collection.objects.link(light_object)  # pyright: ignore
    light_object.location = location

    return light_object


def main():
    """Add suns to the scene."""
    # Create a collection for the suns
    sun_collection = bpy.data.collections.new(name="SunCollection")
    bpy.context.scene.collection.children.link(sun_collection)  # pyright: ignore
    bpy.context.view_layer.active_layer_collection = (  # pyright: ignore
        bpy.context.view_layer.layer_collection.children[-1]  # pyright: ignore
    )

    sun1 = create_sun("Sun1", (250, 250, 200))
    sun2 = create_sun("Sun2", (-250, -250, 200))
    sun3 = create_sun("Sun3", (0, 0, 150))
    sun4 = create_sun("Sun4", (250, -250, 200))
    sun5 = create_sun("Sun5", (-250, 250, 200))
