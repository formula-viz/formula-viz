import json
import os
from dataclasses import dataclass

import gi

gi.require_version("Gimp", "3.0")
from gi.repository import Gegl, Gimp, Gio


@dataclass
class DriverDashData:
    img_file_path: str
    output_dir_path: str

    color: str
    position: int
    num_frames: int
    throttle: list[int]  # each from 0 to 100
    is_brake: list[bool]
    is_drs: list[int]
    sector_times: list[str]
    sector_end_frames: list[int]
    sector_delta_times: list[str]


def main(driver_dash_data_file):
    with open(driver_dash_data_file, "rb") as f:
        ddj = json.load(f)

    driver_data = DriverDashData(
        ddj["img_file_path"],
        ddj["output_dir_path"],
        ddj["color"],
        ddj["position"],
        ddj["num_frames"],
        ddj["throttle"],
        ddj["is_brake"],
        ddj["is_drs"],
        ddj["sector_times"],
        ddj["sector_end_frames"],
        ddj["sector_delta_times"],
    )

    # Create the driver widget once
    create_driver_widget(
        driver_data.img_file_path, driver_data.color, driver_data.position
    )

    # Get the current image with the widget
    current_image = Gimp.get_images()[0]

    # Create output directory
    output_dir = driver_data.output_dir_path
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Iterate through frames
    for frame_num in range(driver_data.num_frames):
        # Create a duplicate of the current image to save
        temp_image = Gimp.Image.duplicate(current_image)

        # Get frame-specific data
        throttle_value = (
            driver_data.throttle[frame_num]
            if frame_num < len(driver_data.throttle)
            else 0
        )
        drs = (
            driver_data.is_drs[frame_num] if frame_num < len(driver_data.is_drs) else 0
        )
        is_brake = (
            driver_data.is_brake[frame_num]
            if frame_num < len(driver_data.is_brake)
            else False
        )

        if not is_brake:
            add_throttle_indicator(
                temp_image, throttle_value, Gegl.Color.new("rgb(0.0, 0.4, 0.0)")
            )
        else:
            add_throttle_indicator(temp_image, 1, Gegl.Color.new("rgb(0.4, 0.0, 0.0)"))

        if drs in [10, 12, 14]:
            add_drs_indicator(temp_image)

        sector_x_offset = 235

        red_color = "rgb(0.4, 0.0, 0.0)"
        green_color = "rgb(0.0, 0.4, 0.0)"
        gray_color = "#292929"

        # Sector 1
        if frame_num >= driver_data.sector_end_frames[0]:
            sector_delta = driver_data.sector_delta_times[0]
            if sector_delta != "0:00.000":
                add_sector_background(temp_image, 183, 786, red_color, "S1")
                add_sector_text(
                    temp_image, 182, 922, "#ffffff", f"+{sector_delta[3:]}", 40
                )
            else:
                add_sector_background(temp_image, 183, 786, green_color, "S1")
                add_sector_text(
                    temp_image, 182, 922, "#ffffff", driver_data.sector_times[0][2:], 40
                )
        else:
            add_sector_background(temp_image, 183, 786, gray_color, "S1")
        add_sector_text(temp_image, 224, 809, "#ffffff", "S1", 50)

        # Sector 2
        if frame_num >= driver_data.sector_end_frames[1]:
            sector_delta = driver_data.sector_delta_times[1]
            if sector_delta != "0:00.000":
                add_sector_background(
                    temp_image, 183 + sector_x_offset, 786, red_color, "S2"
                )
                add_sector_text(
                    temp_image,
                    182 + sector_x_offset,
                    922,
                    "#ffffff",
                    f"+{sector_delta[3:]}",
                    40,
                )
            else:
                add_sector_background(
                    temp_image, 183 + sector_x_offset, 786, green_color, "S2"
                )
                add_sector_text(
                    temp_image,
                    182 + sector_x_offset,
                    922,
                    "#ffffff",
                    driver_data.sector_times[1][2:],
                    40,
                )
        else:
            add_sector_background(
                temp_image, 183 + sector_x_offset, 786, gray_color, "S2"
            )
        add_sector_text(temp_image, 224 + sector_x_offset, 809, "#ffffff", "S2", 50)

        # Sector 3
        if frame_num >= driver_data.sector_end_frames[2]:
            sector_delta = driver_data.sector_delta_times[2]
            if sector_delta != "0:00.000":
                add_sector_background(
                    temp_image, 183 + 2 * sector_x_offset, 786, red_color, "S3"
                )
                add_sector_text(
                    temp_image,
                    182 + 2 * sector_x_offset,
                    922,
                    "#ffffff",
                    f"+{sector_delta[3:]}",
                    40,
                )
            else:
                add_sector_background(
                    temp_image, 183 + 2 * sector_x_offset, 786, green_color, "S3"
                )
                add_sector_text(
                    temp_image,
                    182 + 2 * sector_x_offset,
                    922,
                    "#ffffff",
                    driver_data.sector_times[2][2:],
                    40,
                )
        else:
            add_sector_background(
                temp_image, 183 + 2 * sector_x_offset, 786, gray_color, "S3"
            )
        add_sector_text(temp_image, 224 + 2 * sector_x_offset, 809, "#ffffff", "S3", 50)

        # Only display final time once sector 3 is complete
        if frame_num >= driver_data.sector_end_frames[2]:
            add_sector_text(
                temp_image, 300, 1024, "#ffffff", driver_data.sector_times[3], 80
            )
        # Merge all layers
        temp_image.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)

        # Create output filename
        output_filename = os.path.join(output_dir, f"frame_{frame_num:04d}.png")

        # Export as PNG
        Gimp.file_save(
            Gimp.RunMode.NONINTERACTIVE,
            temp_image,
            Gio.File.new_for_path(output_filename),
        )

        Gimp.Image.delete(temp_image)

        print(
            f"Saved frame {frame_num + 1}/{driver_data.num_frames}: {output_filename}"
        )

    print(f"All frames saved to {output_dir}")


def create_background_circle(current_gimp_image, center_x, center_y, radius, color_hex):
    # Create gray background circle layer (transparent)
    bg_circle_layer = Gimp.Layer.new(
        current_gimp_image,
        "Background Circle",
        current_gimp_image.get_width(),
        current_gimp_image.get_height(),
        Gimp.ImageType.RGBA_IMAGE,
        100,  # Opacity
        Gimp.LayerMode.NORMAL,
    )
    # Clear the layer to make it transparent
    bg_circle_layer.fill(Gimp.FillType.TRANSPARENT)
    # Add the background circle layer to the image
    current_gimp_image.insert_layer(bg_circle_layer, None, 0)
    # Set gray color for the background
    old_fg = Gimp.context_get_foreground()
    # color = Gegl.Color.new("#959595")
    color = Gegl.Color.new(color_hex)
    Gimp.context_set_foreground(color)
    # Create the selection for the background circle
    current_gimp_image.select_ellipse(
        Gimp.ChannelOps.REPLACE,
        center_x - radius,
        center_y - radius,
        radius * 2,
        radius * 2,
    )
    # Fill only the selection with gray
    bg_circle_layer.edit_fill(Gimp.FillType.FOREGROUND)
    # Restore the original foreground color
    Gimp.context_set_foreground(old_fg)
    return bg_circle_layer


def add_driver_image(
    current_gimp_image,
    driver_file,
    offset_x,
    offset_y,
    width,
    height,
    radius,
    center_x,
    center_y,
):
    # Convert string path to Gio.File object
    file = Gio.File.new_for_path(driver_file)
    # Open the driver image as a layer and add it to the current image
    driver_layer = Gimp.file_load_layer(
        Gimp.RunMode.NONINTERACTIVE, current_gimp_image, file
    )
    # Add the driver layer above the background circle
    current_gimp_image.insert_layer(driver_layer, None, 0)
    # Resize the driver image
    driver_layer.scale(width, height, False)
    driver_layer.set_offsets(offset_x, offset_y)
    # Create a circular selection for the mask
    current_gimp_image.select_ellipse(
        Gimp.ChannelOps.REPLACE,
        center_x - radius,
        center_y - radius,
        radius * 2,
        radius * 2,
    )
    # Create and apply layer mask to driver layer
    layer_mask = driver_layer.create_mask(Gimp.AddMaskType.SELECTION)
    driver_layer.add_mask(layer_mask)
    return driver_layer


def create_white_border(current_gimp_image, center_x, center_y, radius, border_width):
    # Create white border circle layer (transparent)
    border_layer = Gimp.Layer.new(
        current_gimp_image,
        "White Border",
        current_gimp_image.get_width(),
        current_gimp_image.get_height(),
        Gimp.ImageType.RGBA_IMAGE,
        100,  # Opacity
        Gimp.LayerMode.NORMAL,
    )
    # Clear the layer to make it transparent
    border_layer.fill(Gimp.FillType.TRANSPARENT)
    # Add the border layer on top
    current_gimp_image.insert_layer(border_layer, None, 0)
    # Create border by making two selections
    current_gimp_image.select_ellipse(
        Gimp.ChannelOps.REPLACE,
        center_x - (radius + border_width),
        center_y - (radius + border_width),
        (radius + border_width) * 2,
        (radius + border_width) * 2,
    )
    # Then subtract the inner circle
    current_gimp_image.select_ellipse(
        Gimp.ChannelOps.SUBTRACT,
        center_x - radius,
        center_y - radius,
        radius * 2,
        radius * 2,
    )
    # Set white color for the border
    old_fg = Gimp.context_get_foreground()
    white_color = Gegl.Color.new("rgb(1.0, 1.0, 1.0)")
    Gimp.context_set_foreground(white_color)
    # Fill only the selection with white
    border_layer.edit_fill(Gimp.FillType.FOREGROUND)
    # Restore the original foreground color
    Gimp.context_set_foreground(old_fg)
    return border_layer


def add_drs_indicator(current_gimp_image):
    # Create new DRS text layer
    text_layer = Gimp.TextLayer.new(
        current_gimp_image,
        "DRS",
        Gimp.Font.get_by_name("Sans-serif Bold Italic"),
        75,  # Font size
        Gimp.Unit.pixel(),
    )

    current_gimp_image.insert_layer(text_layer, None, 3)
    text_layer.set_color(Gegl.Color.new("rgb(0.0, 0.4, 0.0)"))
    text_layer.set_offsets(735, 637)

    return text_layer


def add_position_text(current_gimp_image, position, center_x, center_y, radius):
    position_text = f"P{position}"
    size = 110

    # Create text layer
    text_layer = Gimp.TextLayer.new(
        current_gimp_image,
        f"P{position}",
        Gimp.Font.get_by_name(
            "Sans-serif Bold Italic"
        ),  # Using Gimp.Font instead of string
        size,  # Font size
        Gimp.Unit.pixel(),
    )

    # First add the layer to the image at position 1 (just above the background circle)
    current_gimp_image.insert_layer(text_layer, None, 1)

    # AFTER attaching the layer to the image, set its properties
    text_layer.set_color(Gegl.Color.new("rgb(1.0, 1.0, 1.0)"))  # White text

    # Set justification to centered
    text_layer.set_justification(Gimp.TextJustification.CENTER)

    # We can't get the exact dimensions, so we'll estimate based on font size and text length
    # For positioning, we need to estimate the text dimensions
    # This is an approximation since we don't have get_extents()
    estimated_text_width = len(position_text) * 30  # Rough estimate for width
    estimated_text_height = 60  # Rough estimate for height with 50pt font

    # Position the text layer at the center
    text_x = center_x - (estimated_text_width // 2)
    text_y = center_y - (estimated_text_height // 2)

    # Position the text layer
    text_layer.set_offsets(text_x, text_y)

    return text_layer


THROTTLE_BAR_WIDTH = 150  # Width of the throttle bar in pixels
THROTTLE_BAR_MAX_HEIGHT = 650  # Maximum height of the throttle bar
THROTTLE_CORNER_RADIUS = 10  # Radius for rounded corners

THROTTLE_CENTER_X = 100
THROTTLE_CENTER_Y = 100
THROTTLE_RADIUS = 100


def add_throttle_indicator(current_gimp_image, throttle_value, color):
    # Create throttle indicator layer (transparent)
    throttle_layer = Gimp.Layer.new(
        current_gimp_image,
        "Throttle Indicator",
        current_gimp_image.get_width(),
        current_gimp_image.get_height(),
        Gimp.ImageType.RGBA_IMAGE,
        100,  # Opacity
        Gimp.LayerMode.NORMAL,
    )
    # Clear the layer to make it transparent
    throttle_layer.fill(Gimp.FillType.TRANSPARENT)
    # Add the throttle layer to the image
    current_gimp_image.insert_layer(throttle_layer, None, 5)
    # Calculate throttle bar dimensions - with clamped throttle value
    throttle_value = max(0, min(1, throttle_value))
    bar_height = int((throttle_value / 1.0) * THROTTLE_BAR_MAX_HEIGHT)
    # Position the bar to the left of the circle
    bar_x = THROTTLE_CENTER_X
    bar_y = THROTTLE_CENTER_Y + (THROTTLE_BAR_MAX_HEIGHT - bar_height)
    # Set throttle color
    old_fg = Gimp.context_get_foreground()
    throttle_color = color
    Gimp.context_set_foreground(throttle_color)
    # Create the selection for the throttle bar
    current_gimp_image.select_round_rectangle(
        Gimp.ChannelOps.REPLACE,
        bar_x,
        bar_y,
        THROTTLE_BAR_WIDTH,
        bar_height,
        THROTTLE_CORNER_RADIUS,
        THROTTLE_CORNER_RADIUS,
    )
    # Fill the selection
    throttle_layer.edit_fill(Gimp.FillType.FOREGROUND)
    # Restore the original foreground color
    Gimp.context_set_foreground(old_fg)
    return throttle_layer


def add_throttle_background(current_gimp_image):
    # Border thickness
    border_thickness = 2

    # Calculate background dimensions
    bg_width = THROTTLE_BAR_WIDTH + 6  # 3px border on each side
    bg_height = THROTTLE_BAR_MAX_HEIGHT + 6  # 3px border on top and bottom
    bg_x = THROTTLE_CENTER_X - 3  # Offset to center the background around the throttle
    bg_y = THROTTLE_CENTER_Y - 3  # Offset for top border

    # Calculate the outer white border dimensions
    border_x = bg_x - border_thickness
    border_y = bg_y - border_thickness
    border_width = bg_width + (border_thickness * 2)
    border_height = bg_height + (border_thickness * 2)

    # 1. First create the white border layer (bottom layer)
    border_layer = Gimp.Layer.new(
        current_gimp_image,
        "Throttle Border",
        current_gimp_image.get_width(),
        current_gimp_image.get_height(),
        Gimp.ImageType.RGBA_IMAGE,
        100,  # Opacity
        Gimp.LayerMode.NORMAL,
    )

    # Clear the layer to make it transparent
    border_layer.fill(Gimp.FillType.TRANSPARENT)

    # Add the border layer to the image
    current_gimp_image.insert_layer(border_layer, None, 2)

    # Save original foreground color
    old_fg = Gimp.context_get_foreground()

    # Set white color for the border
    white_color = Gegl.Color.new("rgb(1.0, 1.0, 1.0)")
    Gimp.context_set_foreground(white_color)

    # Create and fill the white border
    current_gimp_image.select_round_rectangle(
        Gimp.ChannelOps.REPLACE,
        border_x,
        border_y,
        border_width,
        border_height,
        THROTTLE_CORNER_RADIUS + 5,  # Slightly larger corner radius for border
        THROTTLE_CORNER_RADIUS + 5,
    )

    # Fill the white border
    border_layer.edit_fill(Gimp.FillType.FOREGROUND)

    # 2. Now create the gray background layer (on top of the border)
    bg_layer = Gimp.Layer.new(
        current_gimp_image,
        "Throttle Background",
        current_gimp_image.get_width(),
        current_gimp_image.get_height(),
        Gimp.ImageType.RGBA_IMAGE,
        100,  # Opacity
        Gimp.LayerMode.NORMAL,
    )

    # Clear the layer to make it transparent
    bg_layer.fill(Gimp.FillType.TRANSPARENT)

    # Add the background layer above the border layer
    current_gimp_image.insert_layer(bg_layer, None, 1)

    # Set gray color for the background
    bg_color = Gegl.Color.new("rgb(0.3, 0.3, 0.3)")  # Dark gray background
    Gimp.context_set_foreground(bg_color)

    # Create and fill the gray background
    current_gimp_image.select_round_rectangle(
        Gimp.ChannelOps.REPLACE,
        bg_x,
        bg_y,
        bg_width,
        bg_height,
        THROTTLE_CORNER_RADIUS + 3,  # Slightly larger corner radius
        THROTTLE_CORNER_RADIUS + 3,
    )

    # Fill the gray background
    bg_layer.edit_fill(Gimp.FillType.FOREGROUND)

    # Restore the original foreground color
    Gimp.context_set_foreground(old_fg)

    return bg_layer, border_layer


def add_sector_text(image, x, y, color, text, font_size):
    # Create text layer
    text_layer = Gimp.TextLayer.new(
        image,
        text,
        Gimp.Font.get_by_name("Sans-serif Bold"),  # Using Gimp.Font instead of string
        font_size,  # Font size
        Gimp.Unit.pixel(),
    )

    image.insert_layer(text_layer, None, 0)
    text_layer.set_color(Gegl.Color.new(color))  # White text
    text_layer.set_justification(Gimp.TextJustification.CENTER)
    text_layer.set_offsets(x, y)

    return text_layer


def add_sector_background(image, x, y, color, text):
    layer = Gimp.Layer.new(
        image,
        f"{text} Background Layer",
        image.get_width(),
        image.get_height(),
        Gimp.ImageType.RGBA_IMAGE,
        100,  # Opacity
        Gimp.LayerMode.NORMAL,
    )

    layer.fill(Gimp.FillType.TRANSPARENT)
    image.insert_layer(layer, None, 0)

    bg_color = Gegl.Color.new(color)  # Dark gray background
    Gimp.context_set_foreground(bg_color)

    image.select_round_rectangle(Gimp.ChannelOps.REPLACE, x, y, 155, 104, 10, 10)

    layer.edit_fill(Gimp.FillType.FOREGROUND)
    return layer


def create_driver_widget(driver_file, color_hex, position=None):
    # Get the first open image
    current_gimp_image = Gimp.get_images()[0]

    # Set up dimensions
    width, height = 650, 650
    offset_x = 176
    offset_y = 95
    center_x = offset_x + (width // 2)
    center_y = offset_y + (height // 2)
    radius = min(width, height) // 2
    border_width = 5  # Width of the border in pixels

    # throttle_background = add_throttle_background(current_gimp_image)

    # # Create the background circle
    bg_circle_layer = create_background_circle(
        current_gimp_image, center_x, center_y, radius, color_hex
    )

    # Add position text behind the background if position is provided
    if position is not None:
        text_layer = add_position_text(current_gimp_image, position, 715, 100, radius)

    # Add the driver image
    driver_layer = add_driver_image(
        current_gimp_image,
        driver_file,
        offset_x,
        offset_y,
        width,
        height,
        radius,
        center_x,
        center_y,
    )

    # Create white border
    border_layer = create_white_border(
        current_gimp_image, center_x, center_y, radius, border_width
    )

    # Refresh the display
    Gimp.displays_flush()

    return driver_layer
