"""Car Data Processing Module.

This module processes telemetry data from Formula 1 qualifying sessions to extract car movement,
position, and speed data for visualization and analysis purposes. It handles downloading driver
images, processing telemetry data, generating smooth interpolated paths, adding buffer frames
before and after laps, calculating car rotations, and validating track limits.

Main functionality includes:
- Loading F1 telemetry data via FastF1 API
- Standardizing start/finish lines across drivers
- Generating smooth car paths using spline interpolation
- Adding realistic car rotations and wheel rotations
- Ensuring cars stay within track limits
- Saving processed data for later visualization

The processed data can be used to create 3D visualizations of qualifying laps.
"""

import os
from datetime import timedelta
from typing import Optional

import fastf1 as ff1
import mathutils
import numpy as np
import pandas as pd
import requests
from fastf1.core import Laps, Session, Telemetry
from fastf1.mvapi.data import CircuitInfo
from fastf1.plotting import get_driver_style
from pandas import Series
from pandas.core.frame import DataFrame
from scipy.interpolate import UnivariateSpline, interp1d

from src.models.config import Config
from src.models.driver import Driver
from src.models.sectors import SectorsInfo, SectorTimes
from src.models.track_data import TrackData
from src.utils import file_utils
from src.utils.logger import log_info, log_warn

# Uses the new API which has access to the 2025 data
ff1.ergast.interface.BASE_URL = "https://api.jolpi.ca/ergast/f1"  # pyright: ignore


def load_driver_headshots(drivers: list[Driver]) -> None:
    """Download driver headshot images if they aren't already cached.

    Args:
        drivers: List of Driver objects
        headshot_urls: List of URLs for driver headshots

    """
    project_paths = file_utils.project_paths
    # taking before .transform gives the original image
    headshot_urls = [driver.headshot_url.split(".transform")[0] for driver in drivers]

    downloaded_count = 0
    for driver, url in zip(drivers, headshot_urls):
        image_path = project_paths.get_driver_image_path(driver)

        if not os.path.exists(image_path):
            try:
                response = requests.get(url)
                response.raise_for_status()

                with open(image_path, "wb") as image_file:
                    image_file.write(response.content)
                    downloaded_count += 1
            except requests.exceptions.RequestException as e:
                log_warn(f"Failed to download image for driver {driver}: {e}")

    if downloaded_count > 0:
        log_info(f"Downloaded {downloaded_count} driver headshots")


def process_tel(q: Laps, driver: Driver) -> tuple[Telemetry, SectorTimes]:
    """Process telemetry data for a given driver.

    Args:
        q: Laps object containing the driver's laps
        driver: Driver object for which to process telemetry

    Returns:
        Telemetry object containing processed data, or None if processing failed

    """
    try:
        fastest = q.pick_not_deleted().pick_fastest()
        if fastest is None:
            raise ValueError(f"Couldn't find fastest lap for {driver}")

        sector_times = SectorTimes(
            fastest["Sector1Time"], fastest["Sector2Time"], fastest["Sector3Time"]
        )

        tel: Telemetry = fastest.get_telemetry(frequency="original")
    except Exception as e:
        raise ValueError(f"Couldn't get proper telemetry for {driver}: {e}")

    tel = tel[tel["Source"].isin(["pos", "interpolation"])]  # pyright: ignore
    tel.reset_index(drop=True)

    tel = tel.astype({"X": float, "Y": float, "Z": float})

    tel.loc[:, "X"] = tel["X"] / 10
    tel.loc[:, "Y"] = tel["Y"] / 10
    tel.loc[:, "Z"] = tel["Z"] / 10

    total_time = str(tel["Time"].iloc[-1])
    # this is a time_delta, we want format: 1:23.342
    # it will be in the format of: 00:01:23.342343
    total_time = total_time.split(" ")[-1][3:12]

    # if exactly 01:21, then the decimals aren't added automatically. This is not
    # aesthetically pleasing, so add them manually
    if "." not in total_time:
        total_time += ".000"

    return tel, sector_times


def get_driver_classes(ff1_session: Session, year: int, session: str) -> list[Driver]:
    """Get a list of Driver objects for the given session.

    Args:
        ff1_session: Session object containing the driver data
        year: Year of the session
        session: Session type ("Q", "SQ") for qualifying or sprint qualifying

    Returns:
        List of Driver objects for the given session

    """
    drivers = ff1_session.drivers
    drivers = [ff1_session.get_driver(d) for d in drivers]

    driver_classes: list[Driver] = []
    for d in drivers:
        abbrev = str(d["Abbreviation"])
        last_name = str(d["LastName"])
        headshot_url = str(d["HeadshotUrl"])
        team = str(d["TeamName"]).replace(" ", "")

        driver_color = get_driver_style(abbrev, "color", ff1_session)["color"]
        driver_classes.append(
            Driver(last_name, abbrev, headshot_url, year, session, team, driver_color)
        )

    return driver_classes


def process_driver_session_results(
    driver_tels: dict[Driver, Telemetry],
    driver_sector_times: dict[Driver, SectorTimes],
    drivers: list[Driver],
    ff1_session: Session,
):
    """Populate the driver_tels dictionary with telemetry data for the given drivers and session."""
    for driver in drivers:
        laps = ff1_session.laps.pick_drivers(driver.abbrev)
        if laps is None or len(laps) == 0:
            log_warn(f"No lap data found for driver {driver}")
            continue

        q1, q2, q3 = laps.split_qualifying_sessions()
        # we want to get the fastest lap for the highest qualifying session which the driver reached
        if q3 is not None:
            tel, sector_times = process_tel(q3, driver)
            if tel is not None:
                driver_tels[driver] = tel
                driver_sector_times[driver] = sector_times

        elif q2 is not None:
            tel, sector_times = process_tel(q2, driver)
            if tel is not None:
                driver_tels[driver] = tel
                driver_sector_times[driver] = sector_times

        elif q1 is not None:
            tel, sector_times = process_tel(q1, driver)
            if tel is not None:
                driver_tels[driver] = tel
                driver_sector_times[driver] = sector_times


def get_driver_tels(
    config: Config,
) -> tuple[dict[Driver, Telemetry], dict[Driver, SectorTimes], CircuitInfo]:
    """Return a dictionary of Driver objects and their telemetry data for the given session.

    Args:
        config: Configuration object containing the session data

    Returns:
        Dictionary of Driver objects and their telemetry data for the given session

    """
    driver_tels: dict[Driver, Telemetry] = {}
    driver_sector_times: dict[Driver, SectorTimes] = {}
    circuit_info = None

    if config["mixed_mode"]["enabled"]:
        touched_ff1_sessions: set[tuple[int, str]] = set()
        for driver_last_name, sub_dict in config["mixed_mode"]["drivers"].items():
            year = int(sub_dict["year"])
            session = str(sub_dict["session"])
            if (year, session) not in touched_ff1_sessions:
                ff1_session = ff1.get_session(year, config["track"], session)
                ff1_session.load()

                if circuit_info is None:
                    circuit_info = ff1_session.get_circuit_info()

                drivers = get_driver_classes(ff1_session, year, session)
                # load the driver images if they are not present already
                load_driver_headshots(drivers)
                process_driver_session_results(
                    driver_tels, driver_sector_times, drivers, ff1_session
                )

                touched_ff1_sessions.add((year, session))
    else:
        ff1_session = ff1.get_session(
            config["year"], config["track"], config["session"]
        )
        ff1_session.load()
        circuit_info = ff1_session.get_circuit_info()

        drivers = get_driver_classes(ff1_session, config["year"], config["session"])
        # load the driver images if they are not present already
        load_driver_headshots(drivers)
        process_driver_session_results(
            driver_tels, driver_sector_times, drivers, ff1_session
        )

    assert circuit_info is not None
    return driver_tels, driver_sector_times, circuit_info


def process_grouped_driver_tels(
    driver_tels: dict[Driver, Telemetry],
    inner_points: list[tuple[float, float, float]],
    outer_points: list[tuple[float, float, float]],
):
    """Process telemetry data to standardize start/finish lines.

    The data for the start and end of runs from fastf1 is unreliable. We can get close to the actual
    start/finish line by getting the average of all the start and end points, as it is the same line for
    start and finish. Then, use track data to define a line based on these points. The starting and end
    point of each car will be the part on the line which is closest to the actual data we have for that
    car's start or end point.

    Args:
        driver_tels: Dictionary mapping Driver objects to their telemetry data
        inner_points: List of inner track boundary points
        outer_points: List of outer track boundary points

    Returns:
        Index of the point in track data that represents the start/finish line

    """

    def get_average_start_end() -> tuple[float, float, float]:
        start_points = np.array(
            [
                [
                    driver_tels[k]["X"].iloc[0],
                    driver_tels[k]["Y"].iloc[0],
                    driver_tels[k]["Z"].iloc[0],
                ]
                for k in driver_tels.keys()
            ]
        )
        end_points = np.array(
            [
                [
                    driver_tels[k]["X"].iloc[-1],
                    driver_tels[k]["Y"].iloc[-1],
                    driver_tels[k]["Z"].iloc[-1],
                ]
                for k in driver_tels.keys()
            ]
        )
        all_points = np.vstack((start_points, end_points))
        mean_of_all = np.mean(all_points, axis=0)

        return mean_of_all[0], mean_of_all[1], mean_of_all[2]

    # using inner_points, outer_points find the idx which is closest to our start/finish line
    # we know that len(inner_points) == len(outer_points)
    def get_line(
        inner_points: list[tuple[float, float, float]],
        outer_points: list[tuple[float, float, float]],
        start_end_point: tuple[float, float, float],
    ):
        closest_idx = 0
        closest_dist = float("inf")
        for i, (inner_point, outer_point) in enumerate(zip(inner_points, outer_points)):
            dist_to_inner = (
                (start_end_point[0] - inner_point[0]) ** 2
                + (start_end_point[1] - inner_point[1]) ** 2
                + (start_end_point[2] - inner_point[2]) ** 2
            ) ** 0.5
            dist_to_outer = (
                (start_end_point[0] - outer_point[0]) ** 2
                + (start_end_point[1] - outer_point[1]) ** 2
                + (start_end_point[2] - outer_point[2]) ** 2
            ) ** 0.5

            if dist_to_inner + dist_to_outer < closest_dist:
                closest_dist = dist_to_inner + dist_to_outer
                closest_idx = i

        # now, we have two points, the inner and outer points, and we want to represent
        # the line between these two points

        return closest_idx, (inner_points[closest_idx], outer_points[closest_idx])

    start_end_point = get_average_start_end()
    line_idx, (point_a, point_b) = get_line(inner_points, outer_points, start_end_point)

    for key in driver_tels:
        # Use .loc for proper DataFrame row/column access
        first_idx = driver_tels[key].index[0]
        last_idx = driver_tels[key].index[-1]

        driver_tels[key].loc[first_idx, "X"] = start_end_point[0]
        driver_tels[key].loc[first_idx, "Y"] = start_end_point[1]
        driver_tels[key].loc[first_idx, "Z"] = 0
        driver_tels[key].loc[last_idx, "X"] = start_end_point[0]
        driver_tels[key].loc[last_idx, "Y"] = start_end_point[1]
        driver_tels[key].loc[last_idx, "Z"] = 0

    return line_idx


def get_driver_df(
    tel: Telemetry, s_divisor: int, frames_per_second: int, track_data: TrackData
):
    """Generate a driver's position and speed DataFrame from telemetry.

    Processes raw telemetry data to create a DataFrame with X, Y, Z coordinates
    and Speed values at a consistent frame rate. Uses spline interpolation for
    smooth path generation.

    Args:
        tel: Raw telemetry data
        s_divisor: Smoothness divisor for the spline (higher = less smooth)
        frames_per_second: Target frame rate for the output data

    Returns:
        DataFrame with X, Y, Z, and Speed columns at specified frame rate

    """
    total_distance = 0
    distances = [0.0]

    prev_x: Optional[float] = None
    prev_y: Optional[float] = None
    prev_z: Optional[float] = None

    x_vals: Series[float] = tel["X"]
    y_vals: Series[float] = tel["Y"]
    z_vals = []

    # Variables to track the last closest segment
    last_closest_idx = 0
    search_radius = (
        len(track_data.inner_points) // 10
    )  # Number of points to check before and after last closest index
    track_length = len(track_data.inner_points)

    # For each point in telemetry data
    for i, (x, y) in enumerate(zip(x_vals, y_vals)):
        min_dist = float("inf")
        interpolated_z = 0
        closest_t = 0
        closest_inner = None
        closest_outer = None
        closest_idx = last_closest_idx

        if i == 0:
            start_idx = 0
            end_idx = len(track_data.inner_points) - 1
        else:
            # Subsequent points: check only nearby segments
            start_idx = (last_closest_idx - search_radius) % track_length
            end_idx = (last_closest_idx + search_radius) % track_length

        idx = start_idx
        while idx != end_idx:
            inner_point = track_data.inner_points[idx]
            outer_point = track_data.outer_points[idx]

            # Create vectors for the line segment
            line_start = mathutils.Vector((inner_point[0], inner_point[1]))
            line_end = mathutils.Vector((outer_point[0], outer_point[1]))
            point = mathutils.Vector((x, y))

            line_vec = line_end - line_start
            line_length_squared = line_vec.length_squared
            if line_length_squared == 0:
                continue

            t = max(0, min(1, (point - line_start).dot(line_vec) / line_length_squared))
            closest_point = line_start + t * line_vec
            dist = (point - closest_point).length

            # Update if this is the closest line segment
            if dist < min_dist:
                min_dist = dist
                closest_t = t
                closest_inner = inner_point
                closest_outer = outer_point
                closest_idx = idx
            idx = (idx + 1) % track_length

        if closest_inner is not None and closest_outer is not None:
            # Interpolate Z value based on position along closest line segment
            interpolated_z = (
                closest_inner[2]  # Z value at inner point
                + closest_t
                * (closest_outer[2] - closest_inner[2])  # Interpolated difference
            )
        else:
            # Fallback if no valid line segment found
            interpolated_z = (
                0 if not z_vals else z_vals[-1]
            )  # Use previous Z value if available

        z_vals.append(interpolated_z)
        last_closest_idx = closest_idx  # Update last closest index for next iteration

    for cur_x, cur_y, cur_z in zip(x_vals, y_vals, z_vals):
        if prev_x is not None and prev_y is not None and prev_z is not None:
            distance = (
                (prev_x - cur_x) ** 2 + (prev_y - cur_y) ** 2 + (prev_z - cur_z) ** 2
            ) ** 0.5
            total_distance += distance
            distances.append(total_distance)
        prev_x = cur_x
        prev_y = cur_y
        prev_z = cur_z

    displacements = [a / total_distance for a in distances]
    # we want to set weights such that the spline is forced to go through the start and end points
    weights = np.ones(len(displacements))
    weights[0] = 1000
    weights[-1] = 1000

    spl_x = UnivariateSpline(
        displacements, x_vals, w=weights, s=len(displacements) // s_divisor
    )
    spl_y = UnivariateSpline(
        displacements, y_vals, w=weights, s=len(displacements) // s_divisor
    )
    z_interp = interp1d(
        displacements,  # x values (original positions)
        z_vals,  # z values to interpolate between
        kind="linear",  # use linear interpolation
        bounds_error=False,  # don't raise error for out of bounds
        # fill_value=z_vals[0],  # use first/last values for out of bounds
    )

    # Extract time and speed data together, ensuring they're properly aligned
    mask = tel["Time"].notna()
    time_deltas: Series[timedelta] = tel["Time"][mask]
    speeds: Series[float] = tel["Speed"][mask]

    # Convert time deltas to seconds
    time_floats: Series[float] = time_deltas.apply(lambda t: t.total_seconds())
    std_time_floats: Series[float] = time_floats / time_floats.max()

    speed_spline = UnivariateSpline(std_time_floats, speeds, s=len(time_floats))

    frame_count = int(time_floats.max() * frames_per_second)

    # now, we want to sample the spline at 60hz
    sampled_speeds = speed_spline(np.linspace(0, 1, frame_count))

    # now that we have speeds, we can use this to get what % of the track is covered at each frame
    d_covered = [0.0]

    sampled_speeds_m_per_s = np.array(sampled_speeds) / 1000 * frames_per_second

    # first lets find the total d which will be covered based on the speed
    total_d: float = 0.0
    for i in sampled_speeds_m_per_s:
        total_d += i  # because each is over 1/frames_per_second of a second
        d_covered.append(total_d)

    adj_d_covered = [a / total_d for a in d_covered]

    final_x = spl_x(adj_d_covered)
    final_y = spl_y(adj_d_covered)
    final_z = z_interp(adj_d_covered)

    # add the first value to the beginning of sampled_speeds_m_per_s so they match length
    sampled_speeds_m_per_s = np.insert(
        sampled_speeds_m_per_s, 0, sampled_speeds_m_per_s[0]
    )

    times = [x / frames_per_second for x in range(len(final_x))]

    throttle = tel["Throttle"]
    brake = tel["Brake"]
    rpm = tel["RPM"]
    gear = tel["nGear"]
    drs = tel["DRS"]
    # Create interpolation for continuous telemetry channels
    throttle_interp = UnivariateSpline(
        std_time_floats,
        throttle[throttle.notna()],
        s=len(std_time_floats) // s_divisor,
    )
    rpm_interp = UnivariateSpline(
        std_time_floats,
        rpm[rpm.notna()],
        s=len(std_time_floats) // s_divisor,
    )

    # Brake (boolean values)
    brake_values = brake[brake.notna()].values
    brake_interp = interp1d(
        std_time_floats,
        brake_values,
        kind="nearest",
        bounds_error=False,
        fill_value=(brake_values[0], brake_values[-1]),
    )

    # Gear (integer values)
    gear_values = gear[gear.notna()].values
    gear_interp = interp1d(
        std_time_floats,
        gear_values,
        kind="nearest",
        bounds_error=False,
        fill_value=(gear_values[0], gear_values[-1]),
    )

    # DRS (boolean values)
    drs_values = drs[drs.notna()].values
    drs_interp = interp1d(
        std_time_floats,
        drs_values,
        kind="nearest",
        bounds_error=False,
        fill_value=(drs_values[0], drs_values[-1]),
    )

    # Sample at the times corresponding to final_x
    time_normalized = np.linspace(0, 1, len(final_x))
    interpolated_throttle = throttle_interp(time_normalized)
    interpolated_brake = brake_interp(time_normalized)
    interpolated_rpm = rpm_interp(time_normalized)
    interpolated_gear = gear_interp(time_normalized)
    interpolated_drs = drs_interp(time_normalized)

    for i, throttle in enumerate(interpolated_throttle):
        if throttle > 1.0:
            interpolated_throttle[i] = 1.0
        elif throttle < 0.0:
            interpolated_throttle[i] = 0.0

    return pd.DataFrame(
        {
            "X": final_x,
            "Y": final_y,
            "Z": final_z,
            "Time": times,
            "Speed": sampled_speeds_m_per_s,
            "Throttle": interpolated_throttle,
            "Brake": interpolated_brake,
            "RPM": interpolated_rpm,
            "Gear": interpolated_gear,
            "DRS": interpolated_drs,
        }
    )


def _generate_buffer(driver_df, num_frames, is_start=True):
    """Generate buffer points for start and end_buffers.

    This is based on essentially what the car would have been doing before or after the official lap started.
    It is unnecessary to try to get the actual movement because it is irrelevant, essentially they will just go in
    a straight line at the speed they were traveling after / before.

    Args:
        driver_df: DataFrame with position and speed data, columns: X, Y, Z, Speed
        num_frames: Number of buffer frames to add
        is_start: If True, generate start buffer; if False, generate end buffer

    Returns:
        DataFrame with buffer points

    """
    # first or last 25 points, previously only the first 2 or last 2 points were used,
    # this gave inconsistent results.
    num_points = min(25, len(driver_df) - 1)
    ref_points = (
        driver_df.iloc[:num_points] if is_start else driver_df.iloc[-num_points:]
    )

    # Calculate average differences between consecutive points
    x_diffs = ref_points["X"].diff().mean()
    y_diffs = ref_points["Y"].diff().mean()
    z_diffs = ref_points["Z"].diff().mean()

    # Starting position and speed
    if is_start:
        start_pos = (
            driver_df["X"].iloc[0],
            driver_df["Y"].iloc[0],
            driver_df["Z"].iloc[0],
        )
        start_speed = driver_df["Speed"].iloc[0]
        # For start buffer, we go in the opposite direction
        x_diffs, y_diffs, z_diffs = -x_diffs, -y_diffs, -z_diffs
    else:
        start_pos = (
            driver_df["X"].iloc[-1],
            driver_df["Y"].iloc[-1],
            driver_df["Z"].iloc[-1],
        )
        start_speed = driver_df["Speed"].iloc[-1]

    # Generate new points
    new_x, new_y, new_z = [], [], []
    prev = start_pos
    for _ in range(num_frames):
        cur_x, cur_y, cur_z = prev[0] + x_diffs, prev[1] + y_diffs, prev[2] + z_diffs
        new_x.append(cur_x)
        new_y.append(cur_y)
        new_z.append(cur_z)
        prev = (cur_x, cur_y, cur_z)

    # Reverse lists for start buffer
    if is_start:
        new_x = new_x[::-1]
        new_y = new_y[::-1]
        new_z = new_z[::-1]

    # Use first index for start buffer, last index for end buffer
    idx = 0 if is_start else -1
    throttle_vals = [driver_df["Throttle"].iloc[idx]] * num_frames
    brake_vals = [driver_df["Brake"].iloc[idx]] * num_frames
    rpm_vals = [driver_df["RPM"].iloc[idx]] * num_frames
    gear_vals = [driver_df["Gear"].iloc[idx]] * num_frames
    drs_vals = [driver_df["DRS"].iloc[idx]] * num_frames

    # Create DataFrame with buffer points
    new_speeds = [start_speed] * num_frames
    buffer_df = pd.DataFrame(
        {
            "X": new_x,
            "Y": new_y,
            "Z": new_z,
            "Speed": new_speeds,
            "Throttle": throttle_vals,
            "Brake": brake_vals,
            "RPM": rpm_vals,
            "Gear": gear_vals,
            "DRS": drs_vals,
        }
    )

    return buffer_df


def add_start_buffer(driver_df, start_buffer_frames):
    """Add buffer frames before the start line.

    Args:
        driver_df: DataFrame with position and speed data
        start_buffer_frames: Number of buffer frames to add

    Returns:
        DataFrame with added start buffer

    """
    if start_buffer_frames <= 0:
        log_warn(
            f"Start buffer frames is {start_buffer_frames}, this may be a mistake."
        )
        return driver_df

    before_startline_df = _generate_buffer(
        driver_df, start_buffer_frames, is_start=True
    )
    driver_df = pd.concat([before_startline_df, driver_df], ignore_index=True)

    return driver_df.reset_index(drop=True)


def add_end_buffer(driver_df, end_buffer_frames):
    """Add buffer frames after the finish line.

    Args:
        driver_df: DataFrame with position and speed data
        end_buffer_frames: Number of buffer frames to add

    Returns:
        DataFrame with added end buffer

    """
    if end_buffer_frames <= 0:
        log_warn(f"End buffer frames is {end_buffer_frames}, this may be a mistake.")
        return driver_df

    after_endline_df = _generate_buffer(driver_df, end_buffer_frames, is_start=False)
    driver_df = pd.concat([driver_df, after_endline_df], ignore_index=True)
    return driver_df.reset_index(drop=True)


def add_car_rots(df):
    """Add car rotation quaternions to the DataFrame.

    Calculates two sets of quaternion rotations for the car:
    1. Standard rotations with more smoothing for natural-looking movement
    2. "Harsher" rotations with less smoothing for more responsive cornering visualization

    The rotations are calculated by looking ahead at future positions and creating
    a direction vector, then converting this to a quaternion rotation. Spherical
    linear interpolation (SLERP) is used to smooth transitions between rotations.

    Args:
        df: DataFrame with X, Y, Z position data

    Returns:
        DataFrame with added rotation quaternion columns (RotW, RotX, RotY, RotZ)
        and harsher rotation quaternions (HarsherRotW, HarsherRotX, HarsherRotY, HarsherRotZ)

    """
    points = [(df["X"][i], df["Y"][i], df["Z"][i]) for i in range(len(df))]

    def get_rots(points, lookahead_points=20, slerp_val=0.1):
        # Previous rotation quaternion for SLERP
        prev_rot = None
        rot_w = []
        rot_x = []
        rot_y = []
        rot_z = []

        for i, point in enumerate(points):
            # Define how far ahead we look based on available points
            lookahead = min(lookahead_points, len(points) - i - 1)

            combined_pos = mathutils.Vector(point)
            for j in range(1, lookahead + 1):
                combined_pos += mathutils.Vector(points[i + j])

            combined_pos /= lookahead + 1
            direction = combined_pos - mathutils.Vector(point)

            # Calculate rotation to track direction
            rot_quat = direction.to_track_quat("-Y", "Z")

            if prev_rot and rot_quat:
                # Interpolate between previous and current quaternion
                rot_quat = prev_rot.slerp(rot_quat, slerp_val)

            rot_w.append(rot_quat.w)
            rot_x.append(rot_quat.x)
            rot_y.append(rot_quat.y)
            rot_z.append(rot_quat.z)

            # Update previous rotation
            prev_rot = rot_quat

        return rot_w, rot_x, rot_y, rot_z

    rot_w, rot_x, rot_y, rot_z = get_rots(points)
    df["RotW"] = rot_w
    df["RotX"] = rot_x
    df["RotY"] = rot_y
    df["RotZ"] = rot_z

    (
        less_lookahead_rot_w,
        less_lookahead_rot_x,
        less_lookahead_rot_y,
        less_lookahead_rot_z,
    ) = get_rots(points, lookahead_points=5, slerp_val=0.1)

    df["LessLookaheadRotW"] = less_lookahead_rot_w
    df["LessLookaheadRotX"] = less_lookahead_rot_x
    df["LessLookaheadRotY"] = less_lookahead_rot_y
    df["LessLookaheadRotZ"] = less_lookahead_rot_z
    # df["RotZ"] = less_lookahead_rot_z

    harsher_rot_w, harsher_rot_x, harsher_rot_y, harsher_rot_z = get_rots(
        points, lookahead_points=40, slerp_val=0.1
    )
    df["HarsherRotW"] = [h - r for h, r in zip(harsher_rot_w, rot_w)]
    df["HarsherRotX"] = [h - r for h, r in zip(harsher_rot_x, rot_x)]
    df["HarsherRotY"] = [h - r for h, r in zip(harsher_rot_y, rot_y)]
    df["HarsherRotZ"] = [h - r for h, r in zip(harsher_rot_z, rot_z)]

    return df


# angular velocity is calculated as v/r where v is linear velocity or 10 m/s for example and r is 0.33 meters
def add_wheel_rots(df):
    prev_rot = 0  # this is arbitrary but shouldnt matter because it is a wheel
    tire_rots = []
    for i in range(len(df)):
        rad_per_s = df["Speed"][i] / 0.33
        new_rot = -(
            prev_rot + rad_per_s / 60
        )  # should rotate in negative x, this is arbitrary, relative to the model
        tire_rots.append(new_rot)
        prev_rot = new_rot

    df["TireRot"] = tire_rots
    return df


# if all 4 wheels go off the track, then they are out of track limits
# we already checked that none of these runs were disqualified so we can assume
# that in real life non went off limits, therefore the smoothing shouldnt cause them to here
def in_track_limits(driver_df: pd.DataFrame, track_edges: pd.DataFrame):
    # find the closest point on the track to the driver's position, it must be within 1 meter
    for i in range(len(driver_df)):
        cur_point = (driver_df["X"][i], driver_df["Y"][i])
        for j in range(len(track_edges)):
            track_point_inner = (track_edges["inner_X"][j], track_edges["inner_Y"][j])
            track_point_outer = (track_edges["outer_X"][j], track_edges["outer_Y"][j])

            dist_inner = (
                (cur_point[0] - track_point_inner[0]) ** 2
                + (cur_point[1] - track_point_inner[1]) ** 2
            ) ** 0.5
            dist_outer = (
                (cur_point[0] - track_point_outer[0]) ** 2
                + (cur_point[1] - track_point_outer[1]) ** 2
            ) ** 0.5

            if dist_inner > 1 or dist_outer > 1:
                return False

    return True


def optimize_smoothness(
    track_edges: pd.DataFrame, fps: int, driver_tels: dict[str, Telemetry]
):
    dfs: dict[str, pd.DataFrame] = {}

    s_divisor = 3  # increasing this s_divisor will make the spline more rigid
    max_s_divisor = 10

    found_max_smoothness = False
    while not found_max_smoothness:
        if s_divisor > max_s_divisor:
            log_info("Using max smoothness, this means something is probably wrong...")
            for driver, tel in driver_tels.items():
                dfs[driver] = get_driver_df(tel, s_divisor, fps)

        for driver, tel in driver_tels.items():
            dfs[driver] = get_driver_df(tel, s_divisor, fps)

            if not in_track_limits(dfs[driver], track_edges):
                s_divisor += 1
                break

        found_max_smoothness = True

    return dfs


def _get_sectors_info(
    driver_dfs: dict[Driver, DataFrame],
    driver_sector_times: dict[Driver, SectorTimes],
    track_data: TrackData,
) -> SectorsInfo:
    # Initialize lists to collect sector location data
    sector_positions = [[] for _ in range(3)]  # For sectors 1, 2, 3

    # Process each driver's data to find sector locations
    for driver, driver_df in driver_dfs.items():
        sector_times = driver_sector_times[driver]

        # Calculate cumulative sector times
        sector_end_times = [
            sector_times.sector1.total_seconds(),
            sector_times.sector1.total_seconds() + sector_times.sector2.total_seconds(),
            sector_times.sector1.total_seconds()
            + sector_times.sector2.total_seconds()
            + sector_times.sector3.total_seconds(),
        ]

        # Filter out null Time values
        df_with_time = driver_df[driver_df["Time"].notna()]

        if not df_with_time.empty:
            # Find positions for each sector
            for i, time in enumerate(sector_end_times):
                idx = (df_with_time["Time"] - time).abs().idxmin()
                sector_positions[i].append(
                    (
                        driver_df.loc[idx, "X"],
                        driver_df.loc[idx, "Y"],
                        driver_df.loc[idx, "Z"],
                    )
                )

    # Calculate average positions for each sector
    sector_locs = []
    for positions in sector_positions:
        if positions:
            sector_locs.append(
                tuple(sum(coord) / len(positions) for coord in zip(*positions))
            )
        else:
            sector_locs.append((0, 0, 0))

    sector_1_loc, sector_2_loc, sector_3_loc = sector_locs

    # Find the indices of track points closest to each sector location
    # Initialize closest indices and distances for all three sectors
    closest_indices = [0, 0, 0]
    min_dists = [float("inf"), float("inf"), float("inf")]

    # Iterate through all track points once
    for i, (inner_point, outer_point) in enumerate(
        zip(track_data.inner_points, track_data.outer_points)
    ):
        # Calculate vector from inner to outer point (track width direction)
        line_vec = (
            outer_point[0] - inner_point[0],
            outer_point[1] - inner_point[1],
            outer_point[2] - inner_point[2],
        )

        # Calculate line length squared (for normalization)
        line_length_sq = line_vec[0] ** 2 + line_vec[1] ** 2 + line_vec[2] ** 2

        if line_length_sq == 0:
            # Skip if inner and outer points are the same
            continue

        # Process all three sector locations in one loop iteration
        for s_idx, sector_loc in enumerate([sector_1_loc, sector_2_loc, sector_3_loc]):
            # Calculate vector from inner point to sector location
            point_vec = (
                sector_loc[0] - inner_point[0],
                sector_loc[1] - inner_point[1],
                sector_loc[2] - inner_point[2],
            )

            # Calculate dot product to find projection
            dot_product = (
                point_vec[0] * line_vec[0]
                + point_vec[1] * line_vec[1]
                + point_vec[2] * line_vec[2]
            ) / line_length_sq

            # Clamp to line segment
            dot_product = max(0, min(1, dot_product))

            # Calculate closest point on the line
            closest_point = (
                inner_point[0] + dot_product * line_vec[0],
                inner_point[1] + dot_product * line_vec[1],
                inner_point[2] + dot_product * line_vec[2],
            )

            # Calculate distance from sector location to closest point
            dist = (
                (sector_loc[0] - closest_point[0]) ** 2
                + (sector_loc[1] - closest_point[1]) ** 2
                + (sector_loc[2] - closest_point[2]) ** 2
            ) ** 0.5

            if dist < min_dists[s_idx]:
                min_dists[s_idx] = dist
                closest_indices[s_idx] = i

    # Create and return SectorsInfo object with all the required fields
    return SectorsInfo(
        sector1_loc=sector_1_loc,
        sector2_loc=sector_2_loc,
        sector3_loc=sector_3_loc,
        sector_1_idx=closest_indices[0],
        sector_2_idx=closest_indices[1],
        sector_3_idx=closest_indices[2],
    )


def get_drivers_included_in_run(
    drivers_from_tels: list[str], config: Config
) -> set[str]:
    if config["type"] == "rest-of-field":
        return set(drivers_from_tels)
    elif not config["mixed_mode"]["enabled"]:
        return set(config["drivers"])
    else:
        return set(config["mixed_mode"]["drivers"].keys())


# in order to run this function, we need to already have the track data for this track and year
# because this will be necessary to ensure that we have the correct smoothness so the movement
# looks natural but also so that we are within track limits
def main(
    track_data: TrackData, config: Config
) -> tuple[
    dict[Driver, pd.DataFrame], dict[Driver, SectorTimes], SectorsInfo, int, CircuitInfo
]:
    """Load driver data, returning all dataframes, needed ones are filtered later."""
    log_info("Fetching and processing car data")

    driver_tels, driver_sector_times, circuit_info = get_driver_tels(config)
    circuit_info = circuit_info
    start_finish_line_idx = process_grouped_driver_tels(
        driver_tels,
        track_data.inner_points,
        track_data.outer_points,
    )

    drivers_included_in_run = get_drivers_included_in_run(
        list([driver.last_name for driver in driver_tels.keys()]), config
    )

    driver_dfs: dict[Driver, pd.DataFrame] = {}
    for driver, tel in driver_tels.items():
        if driver.last_name in drivers_included_in_run:
            driver_df = get_driver_df(tel, 3, config["render"]["fps"], track_data)
            driver_df = add_start_buffer(
                driver_df, config["render"]["start_buffer_frames"]
            )
            driver_df = add_end_buffer(driver_df, config["render"]["end_buffer_frames"])

            driver_dfs[driver] = driver_df

    for driver, driver_df in driver_dfs.items():
        driver_df = add_car_rots(driver_df)
        driver_df = add_wheel_rots(driver_df)
        driver_dfs[driver] = driver_df

    sectors_info = _get_sectors_info(driver_dfs, driver_sector_times, track_data)

    log_info("Done processing car data")
    return (
        driver_dfs,
        driver_sector_times,
        sectors_info,
        start_finish_line_idx,
        circuit_info,
    )
