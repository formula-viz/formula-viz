"""Convert hex color to Blender RGB tuple."""

from typing import cast

import numpy as np
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000
from colormath.color_objects import LabColor, sRGBColor

from src.models.driver import Driver

GOLD_RGB = (255, 215, 0)
# MAIN_TRACK_COLOR = "#444545"
MAIN_TRACK_COLOR = "#0D0D0D"
# CURB_COLOR = "#0f0f0f"
CURB_COLOR = "#1F1F1F"
SCENE_BG_COLOR = "#171717"
ALTERNATE_CURB_COLOR = "#202020"

SECTOR_1_COLOR = "#F13B23"
SECTOR_2_COLOR = "#1783DE"
SECTOR_3_COLOR = "#FAD300"


def hex_to_blender_rgb(hex_color: str) -> tuple[float, float, float]:
    # Convert a hex color to a Blender RGB tuple.
    # In blender, the RGB values are between 0 and 1.
    hex_color = hex_color.lstrip("#")

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return r / 255.0, g / 255.0, b / 255.0


def hex_to_normal_rgb(hex_color: str) -> tuple[float, float, float]:
    # Convert a hex color to a normal RGB tuple.
    hex_color = hex_color.lstrip("#")

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return r, g, b


def rgb_to_hex(rgb_color: tuple[float, float, float]) -> str:
    # Convert an RGB tuple to a hex color.
    return f"#{''.join(f'{int(x):02x}' for x in rgb_color)}"


# 19 gray scale colors and one gold color, the gold must be at index 0
def get_rest_of_field_colors(driver: Driver):
    gray_scale = [(x, x, x) for x in np.linspace(70, 255, 19, dtype=float)]
    gray_scale.insert(
        0,
        hex_to_normal_rgb(driver.default_driver_color),
    )

    return [rgb_to_hex(x) for x in gray_scale]


def get_head_to_head_colors(drivers: list[Driver]):
    def rgb_to_lab(rgb: tuple[float, float, float]) -> LabColor:
        srgb = sRGBColor(*rgb, is_upscaled=True)
        return cast(LabColor, convert_color(srgb, LabColor))

    def color_difference(hex1: str, hex2: str) -> float:
        rgb1 = hex_to_normal_rgb(hex1)
        rgb2 = hex_to_normal_rgb(hex2)

        lab1 = rgb_to_lab(rgb1)
        lab2 = rgb_to_lab(rgb2)

        # this code fixed asscalar deprecation used by colormath
        def patch_asscalar(a):
            return a.item()

        np.asscalar = patch_asscalar  # pyright: ignore
        delta_e = delta_e_cie2000(lab1, lab2)

        return cast(float, delta_e)

    base_colors = ["#FFFFFF", "#808080", "#404040"]  # white, gray, dark gray
    base_color_idx = 0

    colors = [driver.default_driver_color for driver in drivers]

    return colors


def blender_rgb_to_linear(
    tup: tuple[float, float, float],
) -> tuple[float, float, float]:
    def srgb_to_linearrgb(c: float):
        if c < 0:
            return 0
        elif c < 0.04045:
            return c / 12.92
        else:
            return ((c + 0.055) / 1.055) ** 2.4

    r = srgb_to_linearrgb(tup[0])
    g = srgb_to_linearrgb(tup[1])
    b = srgb_to_linearrgb(tup[2])

    return (r, g, b)


class CurbColor:
    @staticmethod
    def get_scene_rgb() -> tuple[float, float, float]:
        return blender_rgb_to_linear(hex_to_blender_rgb(CURB_COLOR))


class AlternateCurbColor:
    @staticmethod
    def get_scene_rgb() -> tuple[float, float, float]:
        return blender_rgb_to_linear(hex_to_blender_rgb(ALTERNATE_CURB_COLOR))


class MainTrackColor:
    @staticmethod
    def get_scene_rgb() -> tuple[float, float, float]:
        return blender_rgb_to_linear(hex_to_blender_rgb(MAIN_TRACK_COLOR))


class BackgroundColor:
    @staticmethod
    def get_scene_rgb() -> tuple[float, float, float]:
        return blender_rgb_to_linear(hex_to_blender_rgb(SCENE_BG_COLOR))

    @staticmethod
    def get_sequence_editor_rgb() -> tuple[float, float, float]:
        return hex_to_blender_rgb(SCENE_BG_COLOR)
