"""A class for creating and managing a status track visualization in Blender.

The status track is a miniature representation of the track that displays
the current position of a driver as a dot. It is positioned relative to the camera
and scales appropriately based on the output mode (shorts or landscape).
"""

import math
from typing import Tuple

import bmesh
import bpy
from fastf1.mvapi.data import CircuitInfo
from mathutils import Vector
from pandas import DataFrame

from src.models.app_state import AppState
from src.models.config import Config
from src.models.driver import Driver
from src.models.track_data import TrackData
from src.modules.render.add_funcs.add_track import create_planes
from src.modules.render.add_funcs.add_track_idx_line import add_track_idx_line
from src.utils import file_utils
from src.utils.colors import (
    SECTOR_1_COLOR,
    SECTOR_2_COLOR,
    SECTOR_3_COLOR,
    hex_to_blender_rgb,
)
from src.utils.logger import log_info
from src.utils.materials import create_material

# In the shorts mode, if we have a dot object, 1 meter away from the camera,
# an x value of 0.2 will be the edge and a y value of 0.36 will be the top edge
# This can be used to dynamically position the status track regardless of the
# particular dimensions of that particular track
SHORTS_MODE_RIGHT_EDGE = 0.2
SHORTS_MODE_TOP_EDGE = 0.36

# I guess they are symmetrical because of the aspect ratios, but this is not by design
LANDSCAPE_MODE_RIGHT_EDGE = 0.36
LANDSCAPE_MODE_TOP_EDGE = 0.2

LANDSCAPE_EDGE_BUFFER = 0.01
SHORTS_MODE_EDGE_BUFFER = 0.05


class StatusTrack:
    """A class for creating and managing a status track visualization in Blender.

    The status track is a miniature representation of the track that displays
    the current position of a driver as a dot. It is positioned relative to the camera
    and scales appropriately based on the output mode (shorts or landscape).
    """

    def __init__(
        self,
        state: AppState,
        config: Config,
    ):
        """Initialize the StatusTrack with track data and positioning parameters.

        Args:
            state: The application state
            config: Global configuration settings

        """
        self.state = state
        self.config = config

        self._create_parent_empty()
        log_info("Initializing StatusTrack...")

        scaled_track_width, scaled_track_height = self._setup()
        self._parent_to_camera(
            self.state.camera_obj, scaled_track_width, scaled_track_height
        )

    def _create_parent_empty(self):
        empty_obj = bpy.data.objects.new("StatusTrackEmptyParent", None)
        empty_obj.empty_display_type = "PLAIN_AXES"
        bpy.context.collection.objects.link(empty_obj)
        empty_obj.hide_viewport = True
        empty_obj.hide_render = True
        self.parent_empty = empty_obj

    def _widen_track(
        self, new_track_data: TrackData, total_widen: int
    ) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]]]:
        """Widen track by moving inner and outer points 5 meters each outward.

        Args:
            new_track_data: Track data containing points to widen
            total_widen: Total amount to widen the track by

        Returns:
            TrackData with widened track points

        """
        new_inner_points: list[tuple[float, float, float]] = []
        new_outer_points: list[tuple[float, float, float]] = []

        for inner_point, outer_point in zip(
            new_track_data.inner_points, new_track_data.outer_points
        ):
            # Calculate vector from inner to outer point
            vector_x = outer_point[0] - inner_point[0]
            vector_y = outer_point[1] - inner_point[1]
            vector_z = outer_point[2] - inner_point[2]

            # Calculate vector length
            length = (vector_x**2 + vector_y**2 + vector_z**2) ** 0.5

            norm_x = vector_x / length
            norm_y = vector_y / length
            norm_z = vector_z / length

            # Widen by 5 meters in each direction
            widen_distance = total_widen / 2

            # Move inner point further inward
            new_inner_x = inner_point[0] - widen_distance * norm_x
            new_inner_y = inner_point[1] - widen_distance * norm_y
            new_inner_z = inner_point[2] - widen_distance * norm_z
            new_inner_points.append((new_inner_x, new_inner_y, new_inner_z))

            # Move outer point further outward
            new_outer_x = outer_point[0] + widen_distance * norm_x
            new_outer_y = outer_point[1] + widen_distance * norm_y
            new_outer_z = outer_point[2] + widen_distance * norm_z
            new_outer_points.append((new_outer_x, new_outer_y, new_outer_z))

        return new_inner_points, new_outer_points

    def _add_background(self, new_inner_points, new_outer_points):
        def calculate_background_points(
            base_points, reference_points, expansion=45, stride=5
        ):
            """Calculate background points from base and reference points.

            Args:
                base_points: Points to expand from (e.g., outer_curb_points)
                reference_points: Points used for direction calculation (e.g., outer_points)
                expansion: Distance to expand in units
                stride: Take every nth point

            Returns:
                List of calculated background points and total distance

            """
            result_points = []
            total_distance = 0

            for i in range(0, len(base_points), stride):
                base_point = base_points[i]
                ref_point = reference_points[i]

                vec = (
                    base_point[0] - ref_point[0],
                    base_point[1] - ref_point[1],
                    base_point[2] - ref_point[2],
                )
                length = (vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2) ** 0.5
                total_distance += length

                if length > 0:
                    normalized = (vec[0] / length, vec[1] / length, vec[2] / length)
                else:
                    normalized = (0, 0, 0)

                new_point = (
                    base_point[0] - expansion * normalized[0],
                    base_point[1] - expansion * normalized[1],
                    base_point[2],  # Keep Z the same
                )
                result_points.append(new_point)

            return result_points, total_distance

        # the assignment of outer and inner points may be incorrect so I'm
        # calculating for both and then validating that we actually choose the correct outer
        outer_bg_points, outer_total_distance = calculate_background_points(
            new_outer_points, new_inner_points, stride=5
        )
        inner_bg_points, inner_total_distance = calculate_background_points(
            new_inner_points, new_outer_points, stride=5
        )
        if outer_total_distance >= inner_total_distance:
            status_track_background_points = outer_bg_points
        else:
            status_track_background_points = inner_bg_points

        bg_mesh = bpy.data.meshes.new("StatusTrackBackgroundMesh")
        bg_obj = bpy.data.objects.new("StatusTrackBackground", bg_mesh)
        bpy.context.scene.collection.objects.link(bg_obj)  # pyright: ignore
        vertices = [(p[0], p[1], p[2]) for p in status_track_background_points]
        faces = [list(range(len(vertices)))]
        bg_mesh.from_pydata(vertices, [], faces)
        bg_mesh.update()
        bg_mat = create_material(
            (0.027375, 0.027375, 0.027375),
            "StatusTrackBackgroundMaterial",
            0.0,
            1.0,
            1.0,
        )
        bg_obj.data.materials.append(bg_mat)  # pyright: ignore
        # Position the background slightly behind the track to avoid z-fighting
        bg_obj.location.z = -0.001
        return bg_obj

    def _get_spread(self, points: list[tuple[float, float, float]], spread_val: float):
        # we want to create an inner and outer spread, essentially
        spread_a = []
        spread_b = []
        for i in range(len(points) - 1):
            # find vec between cur and prev
            next = points[i + 1] if i < len(points) - 1 else points[0]
            cur = points[i]
            vec = (next[0] - cur[0], next[1] - cur[1], next[2] - cur[2])

            # find the perpendicular
            perp = (-vec[1], vec[0], 0)
            length = math.sqrt(perp[0] ** 2 + perp[1] ** 2 + perp[2] ** 2)
            print(i, cur, next)
            perp_norm = (perp[0] / length, perp[1] / length, perp[2] / length)

            spread_a.append(
                (
                    cur[0] + perp_norm[0] * spread_val,
                    cur[1] + perp_norm[1] * spread_val,
                    cur[2] + perp_norm[2] * spread_val,
                )
            )
            spread_b.append(
                (
                    cur[0] - perp_norm[0] * spread_val,
                    cur[1] - perp_norm[1] * spread_val,
                    cur[2] - perp_norm[2] * spread_val,
                )
            )
        return spread_a, spread_b

    def _add_start_finish_line(self, a_points, b_points) -> bpy.types.Object:
        assert self.state.load_data is not None
        for i in range(len(a_points)):
            a_points[i] = (a_points[i][0], a_points[i][1], 1)
            b_points[i] = (b_points[i][0], b_points[i][1], 1)

        status_start_finish_line = add_track_idx_line(
            a_points,
            b_points,
            self.state.load_data.start_finish_line_idx,
            "StatusStartFinishLine",
            line_width=40,
        )
        # Create start/finish line material with texture
        start_finish_mat = bpy.data.materials.new(name="StartFinishLineMaterial")
        start_finish_mat.use_nodes = True
        if not start_finish_mat.node_tree:
            raise ValueError("Material node tree is not initialized")

        nodes = start_finish_mat.node_tree.nodes
        links = start_finish_mat.node_tree.links
        # Clear default nodes
        nodes.clear()
        # Add texture image node
        texture_node = nodes.new(type="ShaderNodeTexImage")
        texture_path = bpy.path.abspath(
            f"{file_utils.project_paths.IMAGES_DIR}/start-finish-line-texture.png"
        )
        texture_image = bpy.data.images.load(texture_path)
        texture_node.image = texture_image  # pyright: ignore
        # Add UV mapping nodes for proper texture projection
        mapping_node = nodes.new(type="ShaderNodeMapping")
        texcoord_node = nodes.new(type="ShaderNodeTexCoord")

        # Add principled BSDF node
        bsdf_node = nodes.new(type="ShaderNodeBsdfPrincipled")
        output_node = nodes.new(type="ShaderNodeOutputMaterial")

        # Connect nodes for proper UV mapping
        links.new(texcoord_node.outputs["UV"], mapping_node.inputs["Vector"])
        links.new(mapping_node.outputs["Vector"], texture_node.inputs["Vector"])
        links.new(texture_node.outputs["Color"], bsdf_node.inputs["Base Color"])
        links.new(bsdf_node.outputs["BSDF"], output_node.inputs["Surface"])
        # Apply material to start/finish line
        status_start_finish_line.data.materials[0] = start_finish_mat  # pyright: ignore
        # Ensure proper UV mapping
        # Select the object and enter edit mode
        bpy.context.view_layer.objects.active = status_start_finish_line  # pyright: ignore
        bpy.ops.object.mode_set(mode="EDIT")
        # Select all faces and perform unwrap
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.001)
        # Return to object mode
        bpy.ops.object.mode_set(mode="OBJECT")
        return status_start_finish_line

    def _create_sector_indicators(self, inner_points_copy, outer_points_copy):
        assert self.state.load_data is not None

        sector_1_inners: list[tuple[float, float, float]] = []
        sector_1_outers: list[tuple[float, float, float]] = []

        sector_2_inners: list[tuple[float, float, float]] = []
        sector_2_outers: list[tuple[float, float, float]] = []

        sector_3_inners: list[tuple[float, float, float]] = []
        sector_3_outers: list[tuple[float, float, float]] = []

        assert self.state.load_data.sectors_info is not None, (
            "Sectors info must be assigned before creating status track."
        )

        cur_track_idx = self.state.load_data.start_finish_line_idx
        cur_sec = "section-1"
        for i in range(cur_track_idx, cur_track_idx + len(inner_points_copy)):
            cur_track_idx = i % len(inner_points_copy)
            inner_point = inner_points_copy[cur_track_idx]
            outer_point = outer_points_copy[cur_track_idx]

            if cur_track_idx == self.state.load_data.sectors_info.sector_1_idx:
                sector_1_inners.append(inner_point)
                sector_1_outers.append(outer_point)
                cur_sec = "section-2"
            elif cur_track_idx == self.state.load_data.sectors_info.sector_2_idx:
                sector_2_inners.append(inner_point)
                sector_2_outers.append(outer_point)
                cur_sec = "section-3"

            if cur_sec == "section-1":
                sector_1_inners.append(inner_point)
                sector_1_outers.append(outer_point)
            elif cur_sec == "section-2":
                sector_2_inners.append(inner_point)
                sector_2_outers.append(outer_point)
            else:
                sector_3_inners.append(inner_point)
                sector_3_outers.append(outer_point)
        # append to sector 3 to close the loop so theres no gap
        sector_3_inners.append(
            inner_points_copy[self.state.load_data.start_finish_line_idx]
        )
        sector_3_outers.append(
            outer_points_copy[self.state.load_data.start_finish_line_idx]
        )

        # Create a parent empty for sector indicators
        sectors_parent = bpy.data.objects.new("SectorIndicatorsParent", None)
        bpy.context.scene.collection.objects.link(sectors_parent)  # pyright: ignore
        sectors_parent.hide_viewport = True
        sectors_parent.hide_render = True

        # Create sector planes and parent them
        sector1_obj = create_planes(
            sector_1_inners,
            sector_1_outers,
            "Sector1",
            create_material(
                hex_to_blender_rgb(SECTOR_1_COLOR), "Sector1StatusMat", 0.0, 1.0, 1.0
            ),
        )
        sector2_obj = create_planes(
            sector_2_inners,
            sector_2_outers,
            "Sector2",
            create_material(
                hex_to_blender_rgb(SECTOR_2_COLOR), "Sector2StatusMat", 0.0, 1.0, 1.0
            ),
        )
        sector3_obj = create_planes(
            sector_3_inners,
            sector_3_outers,
            "Sector3",
            create_material(
                hex_to_blender_rgb(SECTOR_3_COLOR), "Sector3StatusMat", 0.0, 1.0, 1.0
            ),
        )

        sector1_obj.parent = sectors_parent
        sector2_obj.parent = sectors_parent
        sector3_obj.parent = sectors_parent

        return sectors_parent

    def _wipe_z_vals(self, points: list[tuple[float, float, float]]):
        return [(x, y, 0.0) for x, y, _ in points]

    def _setup(self):
        load_data = self.state.load_data
        assert load_data is not None
        focused_driver = load_data.run_drivers.focused_driver

        driver_dfs_copy: dict[Driver, DataFrame] = {}
        if self.config["type"] == "rest-of-field":
            driver_dfs_copy[focused_driver] = load_data.run_drivers.driver_run_data[
                focused_driver
            ].sped_point_df.copy()
        else:
            for (
                driver,
                run_driver_data,
            ) in load_data.run_drivers.driver_run_data.items():
                driver_dfs_copy[driver] = run_driver_data.sped_point_df.copy()

        track_data_copy, driver_dfs_copy = self._orient(
            load_data.track_data,
            load_data.circuit_info,
            driver_dfs_copy,
        )

        track_data_copy, driver_dfs_copy = self._center(
            track_data_copy, driver_dfs_copy
        )

        inner_points_copy, outer_points_copy = self._widen_track(track_data_copy, 14)
        # inner_points_copy = self._wipe_z_vals(inner_points_copy)
        # outer_points_copy = self._wipe_z_vals(outer_points_copy)
        track_width, track_height = self._get_track_dimensions(
            inner_points_copy, outer_points_copy
        )
        optimal_scale = self._calculate_optimal_scale(
            track_width,
            track_height,
            self.state.camera_obj,
            self.config["render"]["is_shorts_output"],
        )
        scaled_track_width, scaled_track_height = (
            track_width * optimal_scale,
            track_height * optimal_scale,
        )

        spread_val = 6
        inner_spread_a, inner_spread_b = self._get_spread(inner_points_copy, spread_val)
        outer_spread_a, outer_spread_b = self._get_spread(outer_points_copy, spread_val)

        track_mat = create_material(
            hex_to_blender_rgb("#000000"), "Status", 0.0, 1.0, 1.0
        )
        inner_spread_obj = create_planes(
            inner_spread_a,
            inner_spread_b,
            "InnerStatusSpread",
            track_mat,
        )

        outer_spread_obj = create_planes(
            outer_spread_a,
            outer_spread_b,
            "OuterStatusSpread",
            track_mat,
        )

        sectors_indicator_obj = self._create_sector_indicators(
            inner_points_copy, outer_points_copy
        )
        sectors_indicator_obj.location = (0, 0, -0.0001)

        # given outer_spread_a, outer_spread_b, and inner, we want to find the sets which are furthest
        # so either, outer_spread_a and inner a or b
        # or outer_spread_b and inner a or b
        def dist(a, b):
            return math.sqrt(
                (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2
            )

        max_dist = 0
        cur_as = []
        cur_bs = []
        if dist(outer_spread_a[0], inner_spread_a[0]) > max_dist:
            max_dist = dist(outer_spread_a[0], outer_spread_b[0])
            cur_as = outer_spread_a
            cur_bs = outer_spread_b
        if dist(outer_spread_a[0], inner_spread_b[0]) > max_dist:
            max_dist = dist(outer_spread_a[0], inner_spread_b[0])
            cur_as = outer_spread_a
            cur_bs = inner_spread_b
        if dist(outer_spread_b[0], inner_spread_a[0]) > max_dist:
            max_dist = dist(outer_spread_b[0], inner_spread_a[0])
            cur_as = outer_spread_b
            cur_bs = inner_spread_a
        if dist(outer_spread_b[0], inner_spread_b[0]) > max_dist:
            max_dist = dist(outer_spread_b[0], inner_spread_b[0])
            cur_as = outer_spread_b
            cur_bs = inner_spread_b

        # status_start_finish_line = self._add_start_finish_line(cur_as, cur_bs)
        # background_obj = self._add_background(inner_points_copy, outer_points_copy)

        self._scale(optimal_scale, inner_spread_obj)
        self._scale(optimal_scale, outer_spread_obj)
        # self._scale(optimal_scale, status_start_finish_line)
        # self._scale(optimal_scale, background_obj)
        self._scale(optimal_scale, sectors_indicator_obj)

        if self.config["type"] == "rest-of-field":
            indicator_dot = self._add_indicator_dot(
                focused_driver.last_name,
                load_data.run_drivers.driver_applied_colors[focused_driver],
                driver_dfs_copy[focused_driver],
                0,
            )
            indicator_dot.parent = inner_spread_obj
        else:
            # Get all drivers and move the focused driver to the end of the list
            drivers = list(load_data.run_drivers.driver_run_data.keys())
            focused_driver = load_data.run_drivers.focused_driver
            drivers.remove(focused_driver)
            drivers.append(focused_driver)

            for idx, driver in enumerate(drivers):
                indicator_dot = self._add_indicator_dot(
                    driver.last_name,
                    load_data.run_drivers.driver_applied_colors[driver],
                    driver_dfs_copy[driver],
                    idx,
                )
                indicator_dot.parent = inner_spread_obj

        # status_start_finish_line.parent = self.parent_empty
        inner_spread_obj.parent = self.parent_empty
        outer_spread_obj.parent = self.parent_empty
        # background_obj.parent = self.parent_empty
        sectors_indicator_obj.parent = self.parent_empty

        return scaled_track_width, scaled_track_height

    # TODO: this will need to be updated for different resolutions,
    # for now it just assumes it is in the phone mode
    def _parent_to_camera(
        self,
        camera_obj: bpy.types.Object,
        scaled_track_width: float,
        scaled_track_height: float,
    ) -> None:
        """Parent the leaderboard to the camera."""
        if not self.parent_empty:
            raise ValueError("Parent empty has not been initialized")

        self.parent_empty.parent = camera_obj

        # the track will already be centered so its highest point will be scaled_track_height / 2
        up_y, right_x = scaled_track_height / 2, scaled_track_width / 2

        if self.config["render"]["is_shorts_output"]:
            position = (
                SHORTS_MODE_RIGHT_EDGE - right_x - SHORTS_MODE_EDGE_BUFFER,
                SHORTS_MODE_TOP_EDGE - up_y - SHORTS_MODE_EDGE_BUFFER,
                -1,
            )
        else:
            position = (
                LANDSCAPE_MODE_RIGHT_EDGE - right_x - LANDSCAPE_EDGE_BUFFER,
                LANDSCAPE_MODE_TOP_EDGE - up_y - LANDSCAPE_EDGE_BUFFER,
                -1,
            )

        self.parent_empty.location = Vector(position)
        self.parent_empty.rotation_euler = camera_obj.rotation_euler

    def _get_track_dimensions(
        self, new_inner_points, new_outer_points
    ) -> Tuple[float, float]:
        """Calculate the width and height of the track."""
        # Get track dimensions for inner points
        inner_x_points = [point[0] for point in new_inner_points]
        inner_y_points = [point[1] for point in new_inner_points]
        inner_track_width = max(inner_x_points) - min(inner_x_points)
        inner_track_height = max(inner_y_points) - min(inner_y_points)

        # Get track dimensions for outer points
        outer_x_points = [point[0] for point in new_outer_points]
        outer_y_points = [point[1] for point in new_outer_points]
        outer_track_width = max(outer_x_points) - min(outer_x_points)
        outer_track_height = max(outer_y_points) - min(outer_y_points)

        # Use the maximum of inner and outer dimensions
        track_width = max(inner_track_width, outer_track_width)
        track_height = max(inner_track_height, outer_track_height)

        return track_width, track_height

    # TODO: this may need to be reworked later
    def _calculate_optimal_scale(
        self,
        track_width: float,
        track_height: float,
        camera_obj: bpy.types.Object,
        is_shorts_output: bool,
    ) -> float:
        # At 1 meter distance with 50mm lens
        total_width_covered = 0.72  # meters
        total_height_covered = 0.48  # meters

        # Calculate usable space based on resolution aspect ratio
        if is_shorts_output:
            resolution_aspect = 1080 / 1920  # 0.5625 (9:16)
            usable_width = total_height_covered * resolution_aspect
            usable_height = total_height_covered
        else:
            resolution_aspect = 1920 / 1080  # 1.7778 (16:9)
            usable_height = total_width_covered / resolution_aspect
            usable_width = total_width_covered

        # Calculate desired size as fraction of usable space
        if is_shorts_output:
            desired_width = 0.50
            desired_height = 0.30
        else:
            desired_width = 0.20
            desired_height = 0.25

        desired_width_meters = usable_width * desired_width
        desired_height_meters = usable_height * desired_height

        scale_x = desired_width_meters / track_width
        scale_y = desired_height_meters / track_height

        return min(scale_x, scale_y)

    def _scale(self, optimal_scale: float, status_track_obj: bpy.types.Object) -> None:
        status_track_obj.scale.x = optimal_scale
        status_track_obj.scale.y = optimal_scale
        status_track_obj.scale.z = optimal_scale

    def _orient(
        self,
        track_data: TrackData,
        circuit_info: CircuitInfo,
        driver_dfs: dict[Driver, DataFrame],
    ) -> tuple[TrackData, dict[Driver, DataFrame]]:
        """Rotate the track and driver data by the needed rotation angle."""
        rotation_angle = math.radians(circuit_info.rotation)

        def _rotate_point(point, angle):
            """Rotate a point around the origin by the given angle."""
            x, y, z = point
            cos_angle = math.cos(angle)
            sin_angle = math.sin(angle)
            new_x = x * cos_angle - y * sin_angle
            new_y = x * sin_angle + y * cos_angle
            return (new_x, new_y, z)

        # Apply rotation to all track points
        rotated_inner_points = [
            _rotate_point(p, rotation_angle) for p in track_data.inner_points
        ]
        rotated_outer_points = [
            _rotate_point(p, rotation_angle) for p in track_data.outer_points
        ]

        # Apply rotation to driver positions
        for driver, df in driver_dfs.items():
            # Create temporary numpy arrays for faster processing
            x_values = df["X"].to_numpy(dtype=float)
            y_values = df["Y"].to_numpy(dtype=float)

            # Precompute trig values
            cos_angle = math.cos(rotation_angle)
            sin_angle = math.sin(rotation_angle)

            # Vectorized rotation calculation
            new_x_values = x_values * cos_angle - y_values * sin_angle
            new_y_values = x_values * sin_angle + y_values * cos_angle

            # Assign back to dataframe
            df_copy = df.copy()
            df_copy["X"] = new_x_values
            df_copy["Y"] = new_y_values

            # Update the driver dataframe
            driver_dfs[driver] = df_copy

        rotated_track_data = TrackData(
            rotated_inner_points,
            None,
            rotated_outer_points,
            None,
            None,
            None,
        )

        return rotated_track_data, driver_dfs

    def _center(
        self, track_data: TrackData, driver_dfs: dict[Driver, DataFrame]
    ) -> tuple[TrackData, dict[Driver, DataFrame]]:
        """Center the track and driver data around the origin."""

        def _calculate_offset(points):
            """Calculate the center offset for a set of points."""
            min_x = min([point[0] for point in points])
            max_x = max([point[0] for point in points])
            offset_x = -(max_x + min_x) / 2

            min_y = min([point[1] for point in points])
            max_y = max([point[1] for point in points])
            offset_y = -(max_y + min_y) / 2

            min_z = min([point[2] for point in points])
            max_z = max([point[2] for point in points])
            offset_z = -(max_z + min_z) / 2

            return (offset_x, offset_y, offset_z)

        def _apply_offset(points, offset):
            """Apply offset to a list of points."""
            return [(x + offset[0], y + offset[1], z + offset[2]) for x, y, z in points]

        # Calculate offset based on outer points
        offset = _calculate_offset(track_data.outer_points)

        # Apply offset to all point sets
        new_inner_points = _apply_offset(track_data.inner_points, offset)
        new_outer_points = _apply_offset(track_data.outer_points, offset)

        # Apply the same offset to all driver DataFrames
        centered_driver_dfs = {}
        for driver, df in driver_dfs.items():
            centered_df = df.copy()
            # Apply offset to each coordinate column
            centered_df["X"] = centered_df["X"] + offset[0]
            centered_df["Y"] = centered_df["Y"] + offset[1]
            centered_df["Z"] = centered_df["Z"] + offset[2]
            centered_driver_dfs[driver] = centered_df

        centered_track_data = TrackData(
            new_inner_points,
            None,
            new_outer_points,
            None,
            None,
            None,
        )

        return centered_track_data, centered_driver_dfs

    def _add_indicator_dot(
        self, driver_name: str, driver_color: str, new_driver_df: DataFrame, idx: int
    ) -> bpy.types.Object:
        # indicator = add_flag(self.config, None, 150.0)
        is_flag = True
        indicator = None
        if indicator is None:
            indicator = self._create_indicator_dot(driver_name, driver_color, idx)
            is_flag = False

        x_vals = new_driver_df["X"].astype(float)
        y_vals = new_driver_df["Y"].astype(float)
        z_vals = new_driver_df["Z"].astype(float)

        for i in range(len(x_vals)):
            frame = i + 1
            if is_flag:
                indicator.location = (
                    x_vals.iloc[i],
                    y_vals.iloc[i],
                    z_vals.iloc[i] + 10,
                )
            else:
                indicator.location = (x_vals.iloc[i], y_vals.iloc[i], z_vals.iloc[i])
            indicator.keyframe_insert(data_path="location", frame=frame)  # pyright: ignore

        return indicator

    def _create_indicator_dot(
        self, driver_name: str, hex_color: str, idx: int
    ) -> bpy.types.Object:
        # Create a circle (disk) instead of a sphere using circle primitive
        # Create circle mesh and object directly without operators
        circle_mesh = bpy.data.meshes.new(f"IndicatorDot{driver_name}Mesh")
        dot = bpy.data.objects.new(f"IndicatorDot{driver_name}", circle_mesh)
        bpy.context.collection.objects.link(dot)

        # Create circle vertices for the dot
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=True, segments=32, radius=27.5)
        bm.to_mesh(circle_mesh)
        bm.free()
        dot.name = f"IndicatorDot{driver_name}"
        dot_mat = create_material(
            hex_to_blender_rgb(hex_color),
            f"IndicatorDotMat{driver_name}",
            0.0,
            1.0,
            1.0,
        )
        dot.data.materials.append(dot_mat)  # pyright: ignore

        # Create border using the same approach as the dot
        border_mesh = bpy.data.meshes.new(f"IndicatorBorder{driver_name}Mesh")
        border = bpy.data.objects.new(f"IndicatorBorder{driver_name}", border_mesh)
        bpy.context.collection.objects.link(border)

        # Create circle vertices for the border
        bm_border = bmesh.new()
        bmesh.ops.create_circle(bm_border, cap_ends=True, segments=32, radius=35)
        bm_border.to_mesh(border_mesh)
        bm_border.free()

        border_mat = create_material(
            (1, 1, 1), f"IndicatorBorderMat{driver_name}", 0.0, 1.0, 1.0
        )
        border.data.materials.append(border_mat)  # pyright: ignore

        # Create a parent empty to help with positioning
        parent_empty = bpy.data.objects.new(f"{driver_name}DotParent", None)
        bpy.context.scene.collection.objects.link(parent_empty)  # pyright: ignore
        parent_empty.empty_display_type = "PLAIN_AXES"
        parent_empty.hide_viewport = True
        parent_empty.hide_render = True

        # Set dot initial position with slight z elevation based on index
        dot.location = (0, 0, 3 * idx + 2.5)
        border.location = (0, 0, 3 * idx + 0.5)

        border.parent = parent_empty
        dot.parent = parent_empty
        return parent_empty
