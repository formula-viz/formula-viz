"""Handles the invocation of the various render functions based on the simulation and render types."""

from abc import ABC, abstractmethod

import bpy

from src.models.app_state import AppState
from src.models.config import Config
from src.modules.render import render_animation
from src.modules.render.add_funcs import (
    add_camera,
    add_camera_plane,
    add_driver_objects,
    add_formula_viz_car,
    add_light,
    add_status_track,
    add_track,
    add_track_idx_line,
)

# from src.modules.render.thumbnail.create_thumbnail import ThumbnailGenerator
from src.utils.colors import (
    SECTOR_2_COLOR,
    SECTOR_3_COLOR,
)
from src.utils.logger import log_info


class AbstractRenderer(ABC):
    """Abstract base class for all renderers."""

    def __init__(self, config: Config, app_state: AppState):
        """Initialize renderer."""
        self.config: Config = config
        self.state = app_state

    @abstractmethod
    def add_drivers(self):
        """Load driver data and set up driver objects."""
        pass

    def add_camera(self):
        """Configure camera to focus on the highlighted driver.

        Sets up camera positioning and movement to follow the focused driver
        (first driver in the config).
        """
        load_data = self.state.load_data
        assert load_data is not None

        focused_driver_run_data = load_data.run_drivers.driver_run_data[
            load_data.run_drivers.focused_driver
        ]
        sped_point_df = focused_driver_run_data.sped_point_df

        self.state.camera_obj = add_camera.main(
            self.config,
            sped_point_df,
            self.config["render"]["start_buffer_frames"],
            self.config["render"]["end_buffer_frames"],
        )

    @abstractmethod
    def configure_widgets(self):
        """Set up UI widgets and overlays for the rendering."""
        pass

    def setup_world(self):
        """Initialize the 3D world with track and lighting."""
        # Clear all collections
        for collection in bpy.data.collections:
            bpy.data.collections.remove(collection, do_unlink=True)  # type: ignore

        # Clear all objects
        for obj in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)  # type: ignore

        # Clear all materials
        for material in bpy.data.materials:
            bpy.data.materials.remove(material, do_unlink=True)  # type: ignore

        add_light.main()
        bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[  # pyright: ignore
            0
        ].default_value = (0.045, 0.046, 0.051, 1)  # pyright: ignore

    def trigger_render(self):
        """Start the rendering process.

        Initiates the rendering animation process with the configured settings.
        """
        assert self.state.load_data is not None
        log_info("Starting Rendering...")
        render_animation.main(
            self.config,
            len(
                self.state.load_data.run_drivers.driver_run_data[
                    self.state.load_data.run_drivers.focused_driver
                ].sped_point_df
            ),
        )

    def add_track(self):
        load_data = self.state.load_data
        assert load_data is not None

        add_track.main(self.state)

        add_track_idx_line.main(
            load_data.track_data.inner_curb_points,
            load_data.track_data.outer_curb_points,
            load_data.start_finish_line_idx,
            "StartFinishLine",
        )
        add_track_idx_line.add_track_idx_line(
            load_data.track_data.inner_points,
            load_data.track_data.outer_points,
            load_data.sectors_info.sector_1_idx,
            "Sector1LineEnd",
            1,
            SECTOR_2_COLOR,
        )
        add_track_idx_line.add_track_idx_line(
            load_data.track_data.inner_points,
            load_data.track_data.outer_points,
            load_data.sectors_info.sector_2_idx,
            "Sector2LineEnd",
            1,
            SECTOR_3_COLOR,
        )

    def render(self):
        """Execute the rendering process.

        Main process that coordinates the setup and rendering steps in the proper sequence.
        The order of the setup functions is significant because some create dependencies.
        """
        self.setup_world()
        # add_background_grid.main()
        self.add_drivers()
        self.add_track()
        self.add_camera()

        add_status_track.StatusTrack(
            self.state,
            self.config,
        )
        add_formula_viz_car.main(
            self.state.camera_obj, self.config["render"]["is_shorts_output"]
        )
        add_camera_plane.add_camera_plane(self.config, self.state.camera_obj)
        self.trigger_render()


class HeadToHeadRenderer(AbstractRenderer):
    """Head to Head render will have a finite number of drivers, designed for 2-4."""

    def add_drivers(self):
        """Load and set up driver data for head-to-head comparison."""
        assert self.state.load_data is not None
        add_driver_objects.main(self.config, self.state.load_data.run_drivers)

        # self.state.car_rankings = add_car_rankings.main(
        #     self.state.load_data.track_data,
        #     self.state.load_data.start_finish_line_idx,
        #     self.state.load_data.driver_dfs,
        #     self.config,
        #     self.state.load_data.focused_driver,
        # )

        # for head to head render, the fastest might not be first in the config, iterate and find the largest df
        # self.state.num_frames = max(
        #     len(df) for df in self.state.load_data.driver_dfs.values()
        # )

    def configure_widgets(self):
        """Set up UI elements specific to head-to-head visualization."""
        assert self.state.load_data is not None

        if self.state.load_data.focused_driver is None:
            raise ValueError("Focused driver is not set.")

        if not self.state.load_data.track_data:
            raise ValueError("Track data is not set.")

        add_status_track.StatusTrack(
            self.state,
            self.config,
        )
        # add_live_leaderboard_new.LiveLeaderboard(
        #     self.config,
        #     list(zip(self.state.drivers_in_order, self.state.driver_colors)),
        #     self.state.car_rankings,
        #     True,
        #     self.state.camera_obj,
        # )
        # add_race_timer.RaceTimer(
        #     self.config,
        #     self.state.camera_obj,
        #     self.state.num_frames,
        # )
        # add_outro.Outro(self.config, self.state.camera_obj, self.state.num_frames)


class RestOfFieldRenderer(AbstractRenderer):
    """Rest of Field Render is when all the drivers are included in the sim."""

    def add_drivers(self):
        """Load and set up driver data for the entire field.

        Creates driver objects with the focused driver (first in config) highlighted
        and all other drivers in grayscale.
        """
        assert self.state.load_data is not None
        add_driver_objects.main(self.config, self.state.load_data.run_drivers)

    def configure_widgets(self):
        """Set up UI elements specific to rest-of-field visualization.

        Creates and configures widgets like the status track, leaderboard,
        race timer, driver indicator circle, and outro sequence.
        """
        assert self.state.load_data is not None

        if self.state.load_data.focused_driver is None:
            raise ValueError("Focused driver is not set.")

        if not self.state.load_data.track_data:
            raise ValueError("Track data is not set.")

        add_status_track.StatusTrack(
            self.state,
            self.config,
        )
        # add_race_timer.RaceTimer(
        #     self.config,
        #     self.state.camera_obj,
        #     self.state.num_frames,
        # )
        # add_live_leaderboard_new.LiveLeaderboard(
        #     self.config,
        #     list(
        #         zip(
        #             self.state.drivers_in_color_order,
        #             self.state.driver_colors[0 : len(self.state.load_data.driver_dfs)],
        #         )
        #     ),
        #     self.state.car_rankings,
        #     False,
        #     self.state.camera_obj,
        # )
        # add_driver_circle.DriverCircle(
        #     self.state.focused_driver,
        #     self.state.driver_colors[0],
        #     self.state.driver_objs[self.state.focused_driver],
        #     self.state.camera_obj,
        # )
        # add_outro.Outro(self.config, self.state.camera_obj, self.state.num_frames)
