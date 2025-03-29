"""Handles the invocation of the various render functions based on the simulation and render types."""

from abc import ABC, abstractmethod

import bpy
from bpy.types import Driver
from pandas.core.frame import DataFrame

from src.models.app_state import AppState
from src.models.config import Config
from src.modules.render import render_animation
from src.modules.render.add_funcs import (
    add_camera,
    add_car_rankings,
    add_driver_objects,
    add_formula_viz_car,
    add_status_track,
    add_sun,
    add_track,
    add_track_idx_line,
)

# from src.modules.render.thumbnail.create_thumbnail import ThumbnailGenerator
from src.modules.render.add_funcs.add_camera_plane import add_camera_plane
from src.utils.colors import (
    SECTOR_2_COLOR,
    SECTOR_3_COLOR,
)
from src.utils.logger import log_info


class AbstractRenderer(ABC):
    """Abstract base class for all renderers.

    Defines the common interface and provides shared functionality for different types
    of F1 race visualization renderers.
    """

    def __init__(self, config: Config, app_state: AppState):
        """Initialize renderer with configuration.

        Args:
            config: Config object containing render configuration parameters

        """
        self.config: Config = config
        self.state = app_state

    @abstractmethod
    def add_drivers(self):
        """Load driver data and set up driver objects.

        This method must be implemented by subclasses to load and initialize
        driver-specific data for the renderer.
        """
        pass

    @abstractmethod
    def add_camera(self):
        """Set up and configure the camera for the rendering.

        This method must be implemented by subclasses to create and configure
        the camera that will be used for the visualization.
        """
        pass

    @abstractmethod
    def configure_widgets(self):
        """Set up UI widgets and overlays for the rendering.

        This method must be implemented by subclasses to create and configure
        the various UI elements that will appear in the visualization.
        """
        pass

    def setup_world(self):
        """Initialize the 3D world with track and lighting.

        Sets up the basic environment by removing all collections
        and adding lighting.
        """
        # Clear all collections
        for collection in bpy.data.collections:
            bpy.data.collections.remove(collection, do_unlink=True)  # type: ignore

        # Clear all objects
        for obj in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)  # type: ignore

        # Clear all materials
        for material in bpy.data.materials:
            bpy.data.materials.remove(material, do_unlink=True)  # type: ignore

        add_sun.main()
        bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[  # pyright: ignore
            0
        ].default_value = (0.045, 0.046, 0.051, 1)  # pyright: ignore

    def trigger_render(self):
        """Start the rendering process.

        Initiates the rendering animation process with the configured settings.
        """
        log_info("Starting Rendering...")
        render_animation.main(self.config, self.state.num_frames)

    def add_indicators(self):
        """Add track indicators and markers.

        Adds visual elements like the start/finish line to the track.
        This is separate from track creation as it requires driver data to be loaded first.
        """
        assert self.state.load_data is not None, (
            "Must load track data before adding indicators"
        )
        add_track_idx_line.main(
            self.state.load_data.track_data.inner_curb_points,
            self.state.load_data.track_data.outer_curb_points,
            self.state.load_data.start_finish_line_idx,
            "StartFinishLine",
        )

        assert self.state.load_data.sectors_info is not None, (
            "Must load sectors info before adding indicators"
        )
        add_track_idx_line.add_track_idx_line(
            self.state.load_data.track_data.inner_points,
            self.state.load_data.track_data.outer_points,
            self.state.load_data.sectors_info.sector_1_idx,
            "Sector1LineEnd",
            1,
            SECTOR_2_COLOR,
        )
        add_track_idx_line.add_track_idx_line(
            self.state.load_data.track_data.inner_points,
            self.state.load_data.track_data.outer_points,
            self.state.load_data.sectors_info.sector_2_idx,
            "Sector2LineEnd",
            1,
            SECTOR_3_COLOR,
        )

    def render(self):
        """Execute the rendering process.

        Main process that coordinates the setup and rendering steps in the proper sequence.
        The order of the setup functions is significant because some create dependencies.
        """
        # thumbnail generator needs these
        self.setup_world()
        # log_info("Before thumbnail generation.")
        # ThumbnailGenerator(
        #     config=self.config,
        #     drivers_in_color_order=self.state.drivers_in_color_order,
        #     colors=self.state.driver_colors,
        # )
        if not self.config["dev_settings"]["thumbnail_mode"]:
            # run setup_world again to reset the world
            self.setup_world()
            # add_background_grid.main()
            add_track.main(self.state)
            self.add_drivers()
            self.add_indicators()
            self.add_camera()
            self.configure_widgets()
            add_formula_viz_car.main(
                self.state.camera_obj, self.config["render"]["is_shorts_output"]
            )
            # add_driver_dash.DriverDash(self.state, self.config)
            add_camera_plane(self.config, self.state.camera_obj)
            # add_outro.Outro(self.config, self.state.camera_obj, self.state.num_frames)
            self.trigger_render()


class HeadToHeadRenderer(AbstractRenderer):
    """Head to Head render will have a finite number of drivers, designed for 2-4."""

    def add_drivers(self):
        """Load and set up driver data for head-to-head comparison.

        Creates driver objects with appropriate colors for direct comparison
        between a small number of drivers.
        """
        assert self.state.load_data is not None

        new_driver_dfs: dict[Driver, DataFrame] = {}
        for driver, df in self.state.load_data.driver_dfs.items():
            new_driver_dfs[driver] = df[~df["FastForward"]]
        self.state.load_data.driver_dfs = new_driver_dfs

        self.state.driver_objs = add_driver_objects.main(
            self.state.load_data.driver_dfs,
            self.state.load_data.drivers_in_color_order,
            self.state.load_data.driver_colors,
            self.config["dev_settings"]["quick_textures_mode"],
            None,
        )

        assert self.state.load_data.track_data is not None, (
            "Must load track data before adding car rankings"
        )

        if self.state.load_data.focused_driver is None:
            raise ValueError("Focused driver is not set.")

        self.state.car_rankings = add_car_rankings.main(
            self.state.load_data.track_data,
            self.state.load_data.start_finish_line_idx,
            self.state.load_data.driver_dfs,
            self.config,
            self.state.load_data.focused_driver,
        )

        # for head to head render, the fastest might not be first in the config, iterate and find the largest df
        self.state.num_frames = max(
            len(df) for df in self.state.load_data.driver_dfs.values()
        )

    def add_camera(self):
        """Configure camera to focus on the first driver in the config.

        Sets up camera positioning and movement to follow the focused driver.
        """
        assert self.state.load_data is not None

        if self.state.load_data.focused_driver is None:
            raise ValueError("Focused driver is not set.")

        self.state.camera_obj = add_camera.main(
            self.config,
            self.state.load_data.driver_dfs[self.state.load_data.focused_driver],
            self.state.driver_objs[self.state.load_data.focused_driver],
            self.config["render"]["start_buffer_frames"],
            self.config["render"]["end_buffer_frames"],
        )

    def configure_widgets(self):
        """Set up UI elements specific to head-to-head visualization.

        Creates and configures widgets like the status track, leaderboard,
        race timer, and outro sequence.
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
    """Rest of Field Render is when all the drivers are included in the sim.

    The highlighted driver, first in the config list of drivers will be highlighted. The rest of the will be shades of gray / white / black.
    """

    def add_drivers(self):
        """Load and set up driver data for the entire field.

        Creates driver objects with the focused driver (first in config) highlighted
        and all other drivers in grayscale.
        """
        assert self.state.load_data is not None

        if not self.state.load_data.focused_driver:
            raise ValueError(
                "No focused driver found,this indicates that the focused driver was not the first in the array of drivers in config."
            )

        new_driver_dfs: dict[Driver, DataFrame] = {}
        for driver, df in self.state.load_data.driver_dfs.items():
            new_driver_dfs[driver] = df[~df["FastForward"]]
        self.state.load_data.driver_dfs = new_driver_dfs

        self.state.driver_objs = add_driver_objects.main(
            self.state.load_data.driver_dfs,
            self.state.load_data.drivers_in_color_order,
            self.state.load_data.driver_colors,
            self.config["dev_settings"]["quick_textures_mode"],
            self.state.load_data.focused_driver,
        )

        self.state.car_rankings = add_car_rankings.main(
            self.state.load_data.track_data,
            self.state.load_data.start_finish_line_idx,
            self.state.load_data.driver_dfs,
            self.config,
            self.state.load_data.focused_driver,
        )

        # for rest of field render, some cars might be very far behind, just take len of fastest
        self.state.num_frames = len(
            self.state.load_data.driver_dfs[self.state.load_data.focused_driver]
        )

    def add_camera(self):
        """Configure camera to focus on the highlighted driver.

        Sets up camera positioning and movement to follow the focused driver
        (first driver in the config).
        """
        assert self.state.load_data is not None

        if self.state.load_data.focused_driver is None:
            raise ValueError("Focused driver is not set.")

        self.state.camera_obj = add_camera.main(
            self.config,
            self.state.load_data.driver_dfs[self.state.load_data.focused_driver],
            self.state.driver_objs[self.state.load_data.focused_driver],
            self.config["render"]["start_buffer_frames"],
            self.config["render"]["end_buffer_frames"],
        )

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
