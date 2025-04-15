import gi

gi.require_version("Gimp", "3.0")
from gi.repository import Gimp, Gio


def main(driver_file):
    print("in gimp")

    import_driver_image(driver_file)


def import_driver_image(driver_file):
    # Get the first open image
    current_gimp_image = Gimp.get_images()[0]

    # Convert string path to Gio.File object
    file = Gio.File.new_for_path(driver_file)

    # Open the driver image as a layer and add it to the current image
    driver_layer = Gimp.file_load_layer(
        Gimp.RunMode.NONINTERACTIVE, current_gimp_image, file
    )

    # Add the layer to the current image
    current_gimp_image.insert_layer(driver_layer, None, 0)

    # Resize if needed (adjust values as needed)
    width, height = 300, 300
    driver_layer.scale(width, height, False)

    # Center the driver image in the current image
    image_width = current_gimp_image.get_width()
    image_height = current_gimp_image.get_height()
    offset_x = (image_width - width) // 2
    offset_y = (image_height - height) // 2
    driver_layer.set_offsets(offset_x, offset_y)

    # Refresh the display
    Gimp.displays_flush()

    return driver_layer
