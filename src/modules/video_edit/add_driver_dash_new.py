import os

import bpy
import numpy as np
from pandas import Timedelta
from PIL import Image

from src.models.app_state import AppState
from src.models.config import Config
from src.models.driver import Driver, RunDrivers
from src.utils import file_utils


class DriverDash:
    def __init__(
        self,
        state: AppState,
        config: Config,
        run_drivers: RunDrivers,
        cur_channel: int,
    ):
        self.state = state
        self.config = config
        self.run_drivers = run_drivers
        self.cur_channel = cur_channel

        self.start_frame = 1
        self.end_frame = bpy.context.scene.frame_end
        if self.config["dev_settings"]["limited_frames_mode"]:
            # we want to be able to add the graphics even if the video is shorter for testing purpose
            self.end_frame = 3000

        self._add_driver_comps()

    def _add_sectors_and_bar_img(self, driver: Driver, color: str, position: str):
        scene = bpy.context.scene
        if not scene.sequence_editor:
            scene.sequence_editor_create()

        alternative_sector_lines_and_bar_path = (
            file_utils.project_paths.IMAGES_DIR
            / "sectors_and_bar_alternates"
            / f"{color}.png"
        )

        if not os.path.exists(alternative_sector_lines_and_bar_path):
            default_sector_lines_and_bar_path = (
                file_utils.project_paths.IMAGES_DIR / "testing.png"
            )

            # Define function to convert hex to RGB
            def hex_to_normal_rgb(hex_color):
                hex_color = hex_color.lstrip("#")
                return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

            # Open the default image
            img = Image.open(default_sector_lines_and_bar_path)
            img_data = np.array(img)

            # Get RGB values from hex color
            rgb_color = hex_to_normal_rgb(color)

            # The issue is with RGB vs BGR order - PIL loads as RGB but we're checking with BGR order
            # Use a color tolerance approach instead of exact matching
            target_green_rgb = (74, 255, 29)
            alt_target_green_rgb = (
                74,
                252,
                29,
            )

            # Create a mask for pixels close to our target colors
            green_mask = np.zeros(img_data.shape[:2], dtype=bool)

            # Add pixels that match the first green target with some tolerance
            color_diff1 = (
                np.abs(img_data[:, :, 0] - target_green_rgb[0])
                + np.abs(img_data[:, :, 1] - target_green_rgb[1])
                + np.abs(img_data[:, :, 2] - target_green_rgb[2])
            )
            green_mask |= color_diff1 < 15  # Allow some tolerance for color variations

            # Add pixels that match the second green target with some tolerance
            color_diff2 = (
                np.abs(img_data[:, :, 0] - alt_target_green_rgb[0])
                + np.abs(img_data[:, :, 1] - alt_target_green_rgb[1])
                + np.abs(img_data[:, :, 2] - alt_target_green_rgb[2])
            )
            green_mask |= color_diff2 < 15

            # Get coordinates of pixels to change
            green_pixels = np.where(green_mask)

            # Print diagnostic info
            if len(green_pixels[0]) == 0:
                print(
                    f"Warning: No green pixels found in image {default_sector_lines_and_bar_path}"
                )
                # Check some sample pixel values to understand what's in the image
                if img_data.size > 0:
                    sample_pixels = img_data[
                        img_data.shape[0] // 2, img_data.shape[1] // 2
                    ]
                    print(f"Sample pixel RGB value: {sample_pixels}")

            # Update the pixels with the new color
            for i in range(len(green_pixels[0])):
                y, x = green_pixels[0][i], green_pixels[1][i]
                img_data[y, x, 0] = rgb_color[0]  # R
                img_data[y, x, 1] = rgb_color[1]  # G
                img_data[y, x, 2] = rgb_color[2]  # B

            # Create the output directory if it doesn't exist
            os.makedirs(
                os.path.dirname(alternative_sector_lines_and_bar_path), exist_ok=True
            )

            # Save the modified image
            modified_img = Image.fromarray(img_data)
            modified_img.save(alternative_sector_lines_and_bar_path)

        sector_lines_and_bar_path = alternative_sector_lines_and_bar_path

        # Import sector lines and bar image
        sectors_bar_strip = scene.sequence_editor.sequences.new_image(
            name=f"SectorsAndBar{driver.abbrev}",
            filepath=str(sector_lines_and_bar_path),
            channel=self.cur_channel,
            frame_start=self.start_frame,
        )

        if not self.config["render"]["is_shorts_output"]:
            # Set position and duration
            if position == "left-of-two":
                sectors_bar_strip.transform.offset_x = -1540
            elif position == "right-of-two":
                sectors_bar_strip.transform.offset_x = 1565
            elif position == "center-of-one":
                sectors_bar_strip.transform.offset_x = 0
            else:
                raise ValueError(f"Invalid position: {position}")

            sectors_bar_strip.transform.scale_x = 0.35
            sectors_bar_strip.transform.scale_y = 0.35
            sectors_bar_strip.transform.offset_y = -930
        else:
            # Set position and duration
            if position == "left-of-two":
                sectors_bar_strip.transform.offset_x = -287
            elif position == "right-of-two":
                sectors_bar_strip.transform.offset_x = 304
            elif position == "center-of-one":
                sectors_bar_strip.transform.offset_x = 0
            else:
                raise ValueError(f"Invalid position: {position}")

            sectors_bar_strip.transform.scale_x = 0.25
            sectors_bar_strip.transform.scale_y = 0.25
            sectors_bar_strip.transform.offset_y = -753
        sectors_bar_strip.frame_final_end = self.end_frame
        self.cur_channel += 1

    def _add_driver_component_package(
        self,
        driver: Driver,
        sector_package: tuple[list[Timedelta], list[int], list[Timedelta]],
        color: str,
        position: str,
    ):
        """Add a complete driver component package including, Driver image, Color bar, Sector times.

        Args:
            driver: Driver object
            sector_package: first is list of times for sectors, second is frame of video where car passes sector, third is the time slower than fastest sector of all drivers in this run
            color: Hex color for the driver
            is_left: Whether this is the left (first) or right (second) driver

        """
        scene = bpy.context.scene
        if not scene.sequence_editor:
            scene.sequence_editor_create()

        # Adjust positions based on shorts output
        if self.config["render"]["is_shorts_output"]:
            base_y = -450

            if position == "left-of-two":
                base_x = -300
            elif position == "right-of-two":
                base_x = 300
            elif position == "center-of-one":
                base_x = 0
            else:
                raise ValueError("Invalid position")

            image_scale = 0.5

            sectors_y_offset = -300
            sectors_x_offset = -150
        else:
            base_y = -500
            if position == "left-of-two":
                base_x = -1550
            elif position == "right-of-two":
                base_x = 1550
            elif position == "center-of-one":
                base_x = 0
            else:
                raise ValueError("Invalid position")

            image_scale = 0.7

            sectors_y_offset = -425
            sectors_x_offset = -150

        # Driver Image
        driver_image_strip = self._add_driver_image_to_vse(
            driver,
            channel=self.cur_channel,
            position_x=base_x,
            position_y=base_y,
            scale=image_scale,
        )
        self.cur_channel += 1

        self._add_sectors_and_bar_img(driver, color, position)

        # Add sector times
        self._add_driver_sector_times(
            driver=driver,
            sector_package=sector_package,
            base_x=base_x + sectors_x_offset,
            base_y=base_y + sectors_y_offset,
        )

    def _add_driver_sector_times(
        self,
        driver: Driver,
        sector_package,
        base_x: float,
        base_y: float,
    ):
        """Add sector times for a specific driver with customizable positioning.

        Args:
            driver: Driver object
            sector_package:
            base_x: Base X position for sector times
            base_y: Base Y position for sector times
            is_left: Whether this is the left (first) or right (second) driver

        """
        scene = bpy.context.scene

        base_x = base_x if self.config["render"]["is_shorts_output"] else base_x - 50
        x_hop = 150 if self.config["render"]["is_shorts_output"] else 200
        sector_time_x_positions = [base_x + i * x_hop for i in range(3)]
        text_size = 30 if self.config["render"]["is_shorts_output"] else 40

        y_up = 40 if self.config["render"]["is_shorts_output"] else 50
        self._add_sector_times(
            driver, sector_package, text_size, sector_time_x_positions, base_y + y_up
        )

    def _process_sector_times(self):
        run_data = self.run_drivers

        fastest_sector_1 = None
        fastest_sector_2 = None
        fastest_sector_3 = None

        sector_times_dict: dict[Driver, list[Timedelta]] = {}
        end_frames_dict: dict[Driver, list[int]] = {}

        for driver, driver_run in run_data.driver_run_data.items():
            driver_sector_times = run_data.driver_sector_times[driver]

            absolute_to_sped_conversion = driver_run.absolute_frame_to_sped_frame
            sector_times = [
                driver_sector_times.sector1,
                driver_sector_times.sector2,
                driver_sector_times.sector3,
            ]

            end_frames_absolute: list[int] = [
                absolute_to_sped_conversion[driver_run.sector_1_end_absolute_frame],
                absolute_to_sped_conversion[driver_run.sector_2_end_absolute_frame],
                absolute_to_sped_conversion[driver_run.sector_3_end_absolute_frame]
                if driver_run.sector_3_end_absolute_frame in absolute_to_sped_conversion
                else 10000,
            ]

            if fastest_sector_1 is None or sector_times[0] < fastest_sector_1:
                fastest_sector_1 = sector_times[0]
            if fastest_sector_2 is None or sector_times[1] < fastest_sector_2:
                fastest_sector_2 = sector_times[1]
            if fastest_sector_3 is None or sector_times[2] < fastest_sector_3:
                fastest_sector_3 = sector_times[2]

            end_frames_dict[driver] = end_frames_absolute
            sector_times_dict[driver] = sector_times

        assert (
            fastest_sector_1 is not None
            and fastest_sector_2 is not None
            and fastest_sector_3 is not None
        )

        sector_packages: dict[
            Driver, tuple[list[Timedelta], list[int], list[Timedelta]]
        ] = {}
        for driver, sector_times in sector_times_dict.items():
            end_frames = end_frames_dict[driver]

            time_slower_than_fastest_in_sector = [
                sector_times[0] - fastest_sector_1,
                sector_times[1] - fastest_sector_2,
                sector_times[2] - fastest_sector_3,
            ]

            sector_packages[driver] = (
                sector_times,
                end_frames,
                time_slower_than_fastest_in_sector,
            )

        return sector_packages

    def _add_driver_comps(self):
        load_data = self.state.load_data
        assert load_data is not None

        sector_packages = self._process_sector_times()

        if (
            self.config["type"] == "rest-of-field"
            or len(load_data.run_drivers.drivers) >= 3
        ):
            driver = load_data.run_drivers.focused_driver
            driver_color = load_data.run_drivers.driver_applied_colors[driver]

            if self.config["render"]["is_shorts_output"]:
                self._add_driver_component_package(
                    driver,
                    sector_packages[driver],
                    driver_color,
                    position="center-of-one",
                )
            else:
                # NOTE, for theres only one driver so of two doesnt make sense but this does position it in the
                # right corner which is a good spot for landscape rest of field mode
                self._add_driver_component_package(
                    driver,
                    sector_packages[driver],
                    driver_color,
                    position="right-of-two",
                )

        elif len(load_data.run_drivers.drivers) == 2:
            driver_a = load_data.run_drivers.drivers[0]
            driver_b = load_data.run_drivers.drivers[1]

            driver_a_color = load_data.run_drivers.driver_applied_colors[driver_a]
            driver_b_color = load_data.run_drivers.driver_applied_colors[driver_b]

            self._add_driver_component_package(
                driver_a,
                sector_packages[driver_a],
                driver_a_color,
                position="left-of-two",
            )
            self._add_driver_component_package(
                driver_b,
                sector_packages[driver_b],
                driver_b_color,
                position="right-of-two",
            )

    def _add_driver_image_to_vse(
        self,
        driver: Driver,
        channel: int,
        position_x: float,
        position_y: float,
        scale: float,
    ):
        # Get the current scene
        scene = bpy.context.scene

        # Ensure we have a sequence editor
        if not scene.sequence_editor:
            scene.sequence_editor_create()

        # Add the image as a strip to the VSE
        driver_image_path = str(file_utils.project_paths.get_driver_image_path(driver))
        image_strip = scene.sequence_editor.sequences.new_image(
            name=f"{driver}Image",
            filepath=driver_image_path,
            channel=channel,
            frame_start=self.start_frame,
        )

        # Set strip properties
        image_strip.transform.offset_x = position_x
        image_strip.transform.offset_y = position_y
        image_strip.transform.scale_x = scale
        image_strip.transform.scale_y = scale

        image_strip.frame_final_end = self.end_frame

        return image_strip

    def _add_color_strip_to_vse(
        self,
        name: str,
        channel: int,
        position_x: float,
        position_y: float,
        scale_x: float,
        scale_y: float,
        color: tuple[float, float, float],
    ):
        # Get the current scene
        scene = bpy.context.scene

        # Ensure we have a sequence editor
        if not scene.sequence_editor:
            scene.sequence_editor_create()

        # Add a color strip
        color_strip = scene.sequence_editor.sequences.new_effect(
            name=name,
            type="COLOR",
            channel=channel,
            frame_start=self.start_frame,
            frame_end=self.end_frame,
        )

        # Set color
        color_strip.color = color

        # Set position and size
        color_strip.transform.offset_x = position_x
        color_strip.transform.offset_y = position_y
        color_strip.transform.scale_x = scale_x
        color_strip.transform.scale_y = scale_y

        return color_strip

    def _add_sector_times(
        self,
        driver: Driver,
        sector_package: tuple[list[Timedelta], list[int], list[Timedelta]],
        text_size: float,
        sector_time_x_positions: list[float],
        y_position: float,
    ):
        """Add sector times for a specific driver with customizable positioning.

        Args:
        driver: Driver object
        sector_time_x_positions: List of X positions for sector times
        y_position: Y position for sector times

        """
        scene = bpy.context.scene

        def add_sector_time(
            sector_complete_frame: int,
            sector_time: Timedelta,
            offset_from_quickest: Timedelta,
            idx: int,
        ):
            text_strip = scene.sequence_editor.sequences.new_effect(
                name="SectorCounter",
                type="TEXT",
                channel=self.cur_channel,
                frame_start=sector_complete_frame,
                frame_end=self.end_frame,
            )
            self.cur_channel += 1

            # Configure text display
            text_strip.font_size = text_size
            # text_strip.font = bpy.data.fonts.load(
            #     str(file_utils.project_paths.MAIN_FONT)
            # )
            text_strip.font = bpy.data.fonts.load(
                str(
                    file_utils.project_paths.FONTS_DIR
                    / "Azeret_Mono/static/AzeretMono-Bold.ttf"
                )
            )
            text_strip.use_shadow = True
            text_strip.shadow_color = (0, 0, 0, 1)  # Black shadow
            text_strip.location = (0.5, 0.5)
            text_strip.transform.offset_x = sector_time_x_positions[idx]
            text_strip.transform.offset_y = y_position

            if offset_from_quickest.total_seconds() > 0:
                text_strip.color = (1.0, 0.0, 0.0, 1.0)
                seconds = offset_from_quickest.total_seconds() % 60
                text_strip.text = f"+{seconds:0.3f}"
            else:
                text_strip.color = (0.0, 0.9, 0.0, 1.0)
                seconds = sector_time.total_seconds() % 60
                text_strip.text = f"{seconds:0.3f}"

        def add_final_time(lap_complete_time: int, race_time: Timedelta):
            # Create the text strip for total time
            text_strip = scene.sequence_editor.sequences.new_effect(
                name="TotalTimeCounter",
                type="TEXT",
                channel=self.cur_channel,
                frame_start=lap_complete_time,
                frame_end=self.end_frame,
            )
            self.cur_channel += 1

            # Configure text display
            text_strip.font_size = 60
            # text_strip.font = bpy.data.fonts.load(
            #     str(file_utils.project_paths.BOLD_FONT)
            # )
            text_strip.font = bpy.data.fonts.load(
                str(
                    file_utils.project_paths.FONTS_DIR
                    / "Azeret_Mono/static/AzeretMono-Bold.ttf"
                )
            )

            text_strip.color = (1, 1, 1, 1)

            text_strip.use_shadow = True
            text_strip.shadow_color = (0, 0, 0, 1)
            text_strip.transform.offset_x = sector_time_x_positions[1]
            text_strip.transform.offset_y = y_position - 125

            minutes = int(race_time.total_seconds() // 60)
            seconds = race_time.total_seconds() % 60
            text_strip.text = f"{minutes:01d}:{seconds:06.3f}"

        for idx, (
            sector_time,
            sped_frame_sector_end,
            offset_from_quickest,
        ) in enumerate(zip(sector_package[0], sector_package[1], sector_package[2])):
            add_sector_time(
                sped_frame_sector_end, sector_time, offset_from_quickest, idx
            )

        add_final_time(
            sector_package[1][2],
            sector_package[0][0] + sector_package[0][1] + sector_package[0][2],
        )
