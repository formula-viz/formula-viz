from typing import Optional

import bpy
import pandas as pd
from pandas import Timedelta

from src.models.app_state import AppState
from src.models.config import Config
from src.models.driver import Driver, RunDrivers
from src.utils import file_utils
from src.utils.colors import hex_to_blender_rgb


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

        self._add_driver_comps()

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
        name: str,
        num_drivers: int,
    ):
        def add_sector_underlines(x_offset: int):
            color = scene.sequence_editor.sequences.new_effect(
                name="SectorUnderline",
                type="COLOR",
                channel=self.cur_channel,
                frame_start=self.start_frame,
                frame_end=self.end_frame,
            )
            y = -810
            color.transform.offset_x = x_offset
            color.transform.offset_y = y
            color.transform.scale_x = 0.12
            color.transform.scale_y = 0.005
            color.color = (1, 1, 1)
            self.cur_channel += 1

            x_offset += 150
            color = scene.sequence_editor.sequences.new_effect(
                name="SectorUnderline",
                type="COLOR",
                channel=self.cur_channel,
                frame_start=self.start_frame,
                frame_end=self.end_frame,
            )
            color.transform.offset_x = x_offset
            color.transform.offset_y = y
            color.transform.scale_x = 0.12
            color.transform.scale_y = 0.005
            color.color = (1, 1, 1)
            self.cur_channel += 1

            x_offset += 150
            color = scene.sequence_editor.sequences.new_effect(
                name="SectorUnderline",
                type="COLOR",
                channel=self.cur_channel,
                frame_start=self.start_frame,
                frame_end=self.end_frame,
            )
            color.transform.offset_x = x_offset
            color.transform.offset_y = y
            color.transform.scale_x = 0.12
            color.transform.scale_y = 0.005
            color.color = (1, 1, 1)
            self.cur_channel += 1

        def add_sector_time(
            sector_complete_frame: int,
            sector_time: Timedelta,
            location: tuple[float, float],
            color: tuple[float, float, float, float],
            behind_time: Optional[Timedelta],
        ):
            # Create the text strip
            text_strip = scene.sequence_editor.sequences.new_effect(
                name="SectorCounter",
                type="TEXT",
                channel=self.cur_channel,
                frame_start=sector_complete_frame,
                frame_end=self.end_frame,
            )
            self.cur_channel += 1

            # Configure text display
            text_strip.font_size = 30
            text_strip.font = bpy.data.fonts.load(
                str(file_utils.project_paths.MAIN_FONT)
            )
            # text_strip.font = bpy.data.fonts.load(str(file_utils.project_paths.IMPACT_FONT))
            text_strip.color = color
            text_strip.use_shadow = False
            text_strip.shadow_color = (0, 0, 0, 1)  # Black shadow
            text_strip.location = location
            text_strip.align_x = "LEFT"

            if behind_time is not None:
                seconds = behind_time.total_seconds() % 60
                text_strip.text = f"+{seconds:0.3f}"
            else:
                seconds = sector_time.total_seconds() % 60
                text_strip.text = f"{seconds:0.3f}"

        def add_final_time(
            race_complete_time: int,
            race_time: float,
            location: tuple[float, float],
            color: tuple[float, float, float, float],
        ):
            # Create the text strip
            text_strip = scene.sequence_editor.sequences.new_effect(
                name="SectorCounter",
                type="TEXT",
                channel=self.cur_channel,
                frame_start=race_complete_time,
                frame_end=self.end_frame,
            )
            self.cur_channel += 1

            # Configure text display
            text_strip.font_size = 45
            text_strip.font = bpy.data.fonts.load(
                str(file_utils.project_paths.BOLD_FONT)
            )
            # text_strip.font = bpy.data.fonts.load(str(file_utils.project_paths.IMPACT_FONT))
            text_strip.color = color
            text_strip.use_shadow = False
            text_strip.shadow_color = (0, 0, 0, 1)  # Black shadow
            text_strip.location = location
            text_strip.align_x = "LEFT"

            minutes = int(race_time // 60)
            seconds = race_time % 60
            text_strip.text = f"{minutes:01d}:{seconds:06.3f}"

        scene = bpy.context.scene
        run_data = self.run_drivers

        driver_a = run_data.drivers[0]
        driver_b = run_data.drivers[1]

        driver_a_run = run_data.driver_run_data[driver_a]
        driver_b_run = run_data.driver_run_data[driver_b]

        absolute_to_sped_conversion = driver_a_run.absolute_frame_to_sped_frame

        driver_a_sector_times = run_data.driver_sector_times[driver_a]
        driver_b_sector_times = run_data.driver_sector_times[driver_b]

        sector_times: list[tuple[Timedelta, Timedelta]] = [
            (driver_a_sector_times.sector1, driver_b_sector_times.sector1),
            (driver_a_sector_times.sector2, driver_b_sector_times.sector2),
            (driver_a_sector_times.sector3, driver_b_sector_times.sector3),
        ]

        end_frames_absolute: list[tuple[int, int]] = [
            (
                driver_a_run.sector_1_end_absolute_frame,
                driver_b_run.sector_1_end_absolute_frame,
            ),
            (
                driver_a_run.sector_2_end_absolute_frame,
                driver_b_run.sector_2_end_absolute_frame,
            ),
            (
                driver_a_run.sector_3_end_absolute_frame,
                driver_b_run.sector_3_end_absolute_frame,
            ),
        ]

        end_frames_sped = []
        for a, b in end_frames_absolute:
            end_frames_sped.append(
                (absolute_to_sped_conversion[a], absolute_to_sped_conversion[b])
            )

        add_sector_underlines(-423)
        add_sector_underlines(122)

        fps = self.config["render"]["fps"]

        cur_left_loc: tuple[float, float] = (0.055, 0.10)
        cur_right_loc: tuple[float, float] = (0.555, 0.10)

        for (left_sector, right_sector), (
            left_end_sector,
            right_end_sector,
        ) in zip(sector_times, end_frames_sped):
            left_behind_time = None
            right_behind_time = None

            if left_sector < right_sector:
                left_color = (0.0, 1.0, 0.0, 1.0)  # Green for faster
                right_color = (1.0, 0.0, 0.0, 1.0)  # Red for slower
                right_behind_time = right_sector - left_sector
            elif left_sector > right_sector:
                left_color = (1.0, 0.0, 0.0, 1.0)  # Red for slower
                right_color = (0.0, 1.0, 0.0, 1.0)  # Green for faster
                left_behind_time = left_sector - right_sector
            else:
                left_color = (1.0, 1.0, 0.0, 1.0)  # Yellow for even
                right_color = (1.0, 1.0, 0.0, 1.0)  # Yellow for even

            add_sector_time(
                left_end_sector,
                left_sector,
                cur_left_loc,
                left_color,
                left_behind_time,
            )
            cur_left_loc = (cur_left_loc[0] + 0.14, cur_left_loc[1])
            add_sector_time(
                right_end_sector,
                right_sector,
                cur_right_loc,
                right_color,
                right_behind_time,
            )
            cur_right_loc = (cur_right_loc[0] + 0.14, cur_right_loc[1])

        driver_sector_times = run_data.driver_sector_times

        driver_a_sector_times = driver_sector_times[driver_a]
        driver_a_total_time = (
            driver_a_sector_times.sector1
            + driver_a_sector_times.sector2
            + driver_a_sector_times.sector3
        )
        driver_a_end_frame = 0
        is_before = True
        for i, row in enumerate(driver_a_run.sped_point_df.iterrows()):
            if pd.notna(row[1].get("Time")):
                if not is_before:
                    # If we were previously in a null section and now have Time data again
                    driver_a_end_frame = i + 1
            else:
                is_before = False

        driver_b_sector_times = driver_sector_times[driver_b]
        driver_b_total_time = (
            driver_b_sector_times.sector1
            + driver_b_sector_times.sector2
            + driver_b_sector_times.sector3
        )
        driver_b_end_frame = 0
        is_before = True
        for i, row in enumerate(driver_b_run.sped_point_df.iterrows()):
            if pd.notna(row[1].get("Time")):
                if not is_before:
                    # If we were previously in a null section and now have Time data again
                    driver_b_end_frame = i + 1
            else:
                is_before = False

        add_final_time(
            driver_a_end_frame,
            driver_a_total_time.total_seconds(),
            (0.16, 0.04),
            (1, 1, 1, 1),
        )

        add_final_time(
            driver_b_end_frame,
            driver_b_total_time.total_seconds(),
            (0.67, 0.04),
            (1, 1, 1, 1),
        )

    def _add_driver_comps(self):
        load_data = self.state.load_data
        assert load_data is not None

        # Get current scene
        scene = bpy.context.scene

        # Ensure we have a sequence editor
        if not scene.sequence_editor:
            scene.sequence_editor_create()

        if len(load_data.run_drivers.drivers) == 2:
            driver_a = load_data.run_drivers.drivers[0]
            driver_b = load_data.run_drivers.drivers[1]

            driver_a_color = load_data.run_drivers.driver_applied_colors[driver_a]
            driver_b_color = load_data.run_drivers.driver_applied_colors[driver_b]

            # Position and scale adjustments based on shorts output
            if self.config["render"]["is_shorts_output"]:
                image_x_a, image_y_a, image_scale_a = -275, -500, 0.5
                image_x_b, image_y_b, image_scale_b = 275, -500, 0.5
                color_x_a, color_y_a, color_scale_x_a, color_scale_y_a = (
                    -270,
                    -700,
                    0.43,
                    0.02,
                )
                color_x_b, color_y_b, color_scale_x_b, color_scale_y_b = (
                    270,
                    -700,
                    0.43,
                    0.02,
                )
            else:
                image_x_a, image_y_a, image_scale_a = 0, 0, 0.7
                image_x_b, image_y_b, image_scale_b = 0, 0, 0.7
                color_x_a, color_y_a, color_scale_x_a, color_scale_y_a = 0, 0, 0.7, 0.05
                color_x_b, color_y_b, color_scale_x_b, color_scale_y_b = 0, 0, 0.7, 0.05

            # Add driver A image
            self._add_driver_image_to_vse(
                driver_a,
                channel=self.cur_channel,
                position_x=image_x_a,
                position_y=image_y_a,
                scale=image_scale_a,
            )
            self.cur_channel += 1

            # Add driver A color bar
            self._add_color_strip_to_vse(
                name="DriverAColor",
                channel=self.cur_channel,
                position_x=color_x_a,
                position_y=color_y_a,
                scale_x=color_scale_x_a,
                scale_y=color_scale_y_a,
                color=hex_to_blender_rgb(driver_a_color),
            )
            self.cur_channel += 1

            # Add driver B image
            self._add_driver_image_to_vse(
                driver_b,
                channel=self.cur_channel,
                position_x=image_x_b,
                position_y=image_y_b,
                scale=image_scale_b,
            )
            self.cur_channel += 1

            # Add driver B color bar
            self._add_color_strip_to_vse(
                name="DriverBColor",
                channel=self.cur_channel,
                position_x=color_x_b,
                position_y=color_y_b,
                scale_x=color_scale_x_b,
                scale_y=color_scale_y_b,
                color=hex_to_blender_rgb(driver_b_color),
            )
            self.cur_channel += 1

            # Add driver A sector time
            self._add_sector_times(name="DriverASectorTime", num_drivers=2)
            self.cur_channel += 1
