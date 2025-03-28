from typing import Optional

import bpy
from pandas import Timedelta

from src.models.app_state import AppState
from src.models.config import Config
from src.models.driver import Driver
from src.models.sectors import SectorTimes
from src.utils import file_utils
from src.utils.colors import hex_to_blender_rgb


class DriverDash:
    def __init__(self, state: AppState, config: Config, cur_channel: int):
        self.state = state
        self.config = config
        self.cur_channel = cur_channel

        self.start_frame = 1
        self.end_frame = 1 + self.state.num_frames

        self._add_driver_images()

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
        driver_sectors_times_left: SectorTimes,
        driver_sectors_times_right: SectorTimes,
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

        assert self.state.load_data is not None
        scene = bpy.context.scene

        add_sector_underlines(-423)
        add_sector_underlines(122)

        sectors: list[tuple[Timedelta, Timedelta]] = [
            (driver_sectors_times_left.sector1, driver_sectors_times_right.sector1),
            (driver_sectors_times_left.sector2, driver_sectors_times_right.sector2),
            (driver_sectors_times_left.sector3, driver_sectors_times_right.sector3),
        ]

        left_sector_next_start = self.config["render"]["start_buffer_frames"]
        right_sector_next_start = self.config["render"]["start_buffer_frames"]

        cur_left_loc: tuple[float, float] = (0.055, 0.10)
        cur_right_loc: tuple[float, float] = (0.555, 0.10)

        for left_sector, right_sector in sectors:
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

            left_sector_next_start += int(
                left_sector.total_seconds() * self.config["render"]["fps"]
            )
            right_sector_next_start += int(
                right_sector.total_seconds() * self.config["render"]["fps"]
            )

            add_sector_time(
                left_sector_next_start,
                left_sector,
                cur_left_loc,
                left_color,
                left_behind_time,
            )
            cur_left_loc = (cur_left_loc[0] + 0.14, cur_left_loc[1])
            add_sector_time(
                right_sector_next_start,
                right_sector,
                cur_right_loc,
                right_color,
                right_behind_time,
            )
            cur_right_loc = (cur_right_loc[0] + 0.14, cur_right_loc[1])

        total_race_time_left = (
            driver_sectors_times_left.sector1.total_seconds()
            + driver_sectors_times_left.sector2.total_seconds()
            + driver_sectors_times_left.sector3.total_seconds()
        )
        add_final_time(
            self.config["render"]["start_buffer_frames"]
            + int(total_race_time_left * self.config["render"]["fps"]),
            total_race_time_left,
            (0.16, 0.04),
            (1, 1, 1, 1),
        )

        total_race_time_right = (
            driver_sectors_times_right.sector1.total_seconds()
            + driver_sectors_times_right.sector2.total_seconds()
            + driver_sectors_times_right.sector3.total_seconds()
        )
        add_final_time(
            self.config["render"]["start_buffer_frames"]
            + int(total_race_time_right * self.config["render"]["fps"]),
            total_race_time_right,
            (0.67, 0.04),
            (1, 1, 1, 1),
        )

    def _add_driver_images(self):
        assert self.state.load_data is not None

        if self.config["render"]["is_shorts_output"]:
            # Get current scene
            scene = bpy.context.scene

            # Ensure we have a sequence editor
            if not scene.sequence_editor:
                scene.sequence_editor_create()

            # Set up VSE if we have 2 drivers
            if len(self.state.load_data.drivers_in_color_order) == 2:
                driver_a = self.state.load_data.drivers_in_color_order[0]
                driver_b = self.state.load_data.drivers_in_color_order[1]

                # Add driver A image
                driver_image_a = self._add_driver_image_to_vse(
                    self.state.load_data.drivers_in_color_order[0],
                    channel=self.cur_channel,
                    position_x=-275,
                    position_y=-500,
                    scale=0.5,
                )
                self.cur_channel += 1

                # Add driver A color bar
                driver_stopper_a = self._add_color_strip_to_vse(
                    name="DriverAColor",
                    channel=self.cur_channel,
                    position_x=-270,
                    position_y=-700,
                    scale_x=0.43,
                    scale_y=0.02,
                    color=hex_to_blender_rgb(self.state.load_data.driver_colors[0]),
                )
                self.cur_channel += 1

                # Add driver B image
                driver_image_b = self._add_driver_image_to_vse(
                    self.state.load_data.drivers_in_color_order[1],
                    channel=self.cur_channel,
                    position_x=275,
                    position_y=-500,
                    scale=0.5,
                )
                self.cur_channel += 1

                # Add driver B color bar
                driver_stopper_b = self._add_color_strip_to_vse(
                    name="DriverBColor",
                    channel=self.cur_channel,
                    position_x=270,
                    position_y=-700,
                    scale_x=0.43,
                    scale_y=0.02,
                    color=hex_to_blender_rgb(self.state.load_data.driver_colors[1]),
                )
                self.cur_channel += 1

                driver_sectors_times_left = self.state.load_data.driver_sector_times[
                    driver_a
                ]
                driver_sectors_times_right = self.state.load_data.driver_sector_times[
                    driver_b
                ]

                # Add driver A sector time
                driver_sector_time_a = self._add_sector_times(
                    name="DriverASectorTime",
                    driver_sectors_times_left=driver_sectors_times_left,
                    driver_sectors_times_right=driver_sectors_times_right,
                )
                self.cur_channel += 1
