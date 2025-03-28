"""Track data processing utilities.

This module provides functions for loading, processing, and manipulating track data.
It includes capabilities for loading raw track data from files,
smoothing track boundaries, calculating inner/outer track edges, and generating curb points.
The processed data can be used to create an accurate track representation.
"""

import math
import os
import sys

import numpy as np
import pandas as pd
from pandas import DataFrame
from scipy.interpolate import splev, splprep

from src.models.config import Config
from src.models.track_data import LineData, TrackData
from src.utils import file_utils
from src.utils.logger import log_err, log_info


def load_raw_data(year: int, track: str, use_latest_year: bool = True) -> DataFrame:
    """Load raw track data from CSV files.

    Searches for track data files matching the specified track name and loads
    the appropriate file based on the year parameter. If use_latest_year is True,
    the most recent track data file will be used regardless of the year parameter.

    Args:
        year: The year of the track data to load
        track: The name of the track to load
        use_latest_year: If True, use the most recent track data available. This is included so that we can get the
        track data based on 2024 for example and use it in 2025, 2026, etc. if the track hasn't changed.

    Returns:
        DataFrame containing the raw track data

    """
    project_paths = file_utils.project_paths
    track_data_dir = project_paths.TRACK_DATA_DIR
    # iterate through contents of track_data, finding all files containing track
    # then, we find the file with the latest year
    # if use_latest_year is false, we use the year given
    try:
        track_data_files = os.listdir(track_data_dir)
        track_data_files = [file for file in track_data_files if track in file]
    except OSError as e:
        log_err(f"Error accessing track data directory: {e}")
        sys.exit(1)

    if not track_data_files:
        raise FileNotFoundError(f"Track data not found for {track}")

    if use_latest_year:
        latest_year = 0
        latest_file = ""
        for file in track_data_files:
            year = project_paths.get_year_of_track_file(file)
            if int(year) > latest_year:
                latest_year = int(year)
                latest_file = file
        track_data_file = latest_file
    else:
        track_data_file = project_paths.get_track_file(str(year), track)

        if track_data_file not in track_data_files:
            raise FileNotFoundError(
                f"Track data not found for {track} in {year}, use_latest_year is set to False"
            )

    track_data_path = os.path.join(track_data_dir, track_data_file)
    track_data: DataFrame = pd.read_csv(track_data_path)  # pyright: ignore

    return track_data


def linearly_interpolate_z_vals(z_vals, num_new_points):
    """Linearly interpolate elevation (z) values to a new array size.

    This function stretches or compresses an array of z-values to a new length
    by first placing original values at their proportional positions in the new array,
    then filling gaps between known values with linear interpolation. The function
    handles wrapping around from the end to beginning of the array to ensure a
    continuous profile for closed paths.

    Args:
        z_vals (numpy.ndarray): Original array of elevation values
        num_new_points (int): Number of points in the output array

    Returns:
        numpy.ndarray: New array of linearly interpolated z-values with length num_new_points

    Example:
        If z_vals = [0, 10, 20] and num_new_points = 5, the result will be approximately
        [0, 5, 10, 15, 20], maintaining the same profile but with more points.

    """
    # we want to interpolate the z values, not smooth them
    # for now, the z value's will be the same for the inner and outer points
    # we stretch z values to fit num_new_points
    # if we have 1000 points and 2000 new points, we need to stretch the z values by 2
    stretch_val = num_new_points / len(z_vals)
    new_z_vals = np.zeros(num_new_points)

    for i, z_val in enumerate(z_vals):
        new_z_vals[int(i * stretch_val)] = z_val

    # if we have two values which are not 0 and say they are 20 apart, then we fill the vals between them linearly
    # if a is 10 and b is 20 and there are 3 spots between, we add 10.25, 10.5, 10.75

    # hold a pointer to the cur non-zero value in i, j is the next non zero value, then we step between them
    i = 0
    while new_z_vals[i] == 0:
        i += 1

    j = i + 1
    while j < len(new_z_vals):
        if new_z_vals[j] == 0:
            j += 1
            continue  # this should ensure that the loop doesnt break

        # now that we have i pointing to a and j to b, find the spaces between them
        num_spaces = (
            j - i - 1
        )  # if j = 3 and i = 0, then i 0 0 3, 2 spaces between = 3 - 0 - 1
        dif = new_z_vals[j] - new_z_vals[i]
        # if dif is 10 and num_spaces is 3, we add 10/4 to each space
        step = dif / (num_spaces + 1)

        for k in range(i + 1, j):
            new_z_vals[k] = new_z_vals[k - 1] + step

        # now we need to replace i with j and find the next non zero value
        i = j
        j += 1

    # now we need to interpolate between the last non zero value and the first non zero value
    # as it is, i is pointing to the last non zero value
    j = 0
    while new_z_vals[j] == 0:
        j += 1

    # now we have i pointing to the last non zero value and j to the first non zero value
    # now j is the smaller value, j might be 10 and i is 200, if there are 210 elems, then there are 9 + 11 = 20 spaces
    num_spaces = len(new_z_vals) - i - 1 + j
    dif = new_z_vals[j] - new_z_vals[i]
    step = dif / (num_spaces + 1)

    n = 1
    while n <= num_spaces:
        idx = (i + n) % len(new_z_vals)
        below_idx = (i + n - 1) % len(new_z_vals)
        new_z_vals[idx] = new_z_vals[below_idx] + step

        n += 1

    return new_z_vals


def smooth_points(track_points: DataFrame) -> DataFrame:
    """Smooths track boundary points and ensures consistent track width.

    This function processes raw track boundary points to create a smoother representation
    of the track while ensuring consistent track width. It smooths the left boundary points
    using a periodic spline and then generates corresponding right boundary points at a
    fixed distance perpendicular to the smoothed left boundary.

    Args:
        track_points: DataFrame containing the raw track boundary points with columns
                     'lefts_X', 'lefts_Y', 'rights_X', and 'rights_Y'

    Returns:
        pd.DataFrame: A new DataFrame containing smooth track boundaries with consistent width,
                     with columns 'lefts_X', 'lefts_Y', 'lefts_Z', 'rights_X', 'rights_Y',
                     and 'rights_Z'

    """

    def smooth_closed_loop(
        x: list[float], y: list[float], num_points: int = 10000, smoothing: float = 100
    ) -> tuple[list[float], list[float]]:
        tck, _ = splprep([x, y], s=smoothing, per=True)
        u_new = np.linspace(0, 1, num_points)
        smooth_x, smooth_y = splev(u_new, tck)
        return smooth_x, smooth_y  # pyright: ignore

    lefts_x: list[float] = track_points["lefts_X"].tolist()
    lefts_y: list[float] = track_points["lefts_Y"].tolist()

    rights_x: list[float] = track_points["rights_X"].tolist()
    rights_y: list[float] = track_points["rights_Y"].tolist()

    # Perform circular shift equivalent to np.roll
    shift_amount = len(lefts_x) // 3
    lefts_x = lefts_x[shift_amount:] + lefts_x[:shift_amount]
    lefts_y = lefts_y[shift_amount:] + lefts_y[:shift_amount]
    rights_x = rights_x[shift_amount:] + rights_x[:shift_amount]
    rights_y = rights_y[shift_amount:] + rights_y[:shift_amount]

    lefts_x, lefts_y = smooth_closed_loop(lefts_x, lefts_y)

    prev_point = None
    for i, (left_x, left_y) in enumerate(zip(lefts_x, lefts_y)):
        cur_point = (left_x, left_y)
        if prev_point:
            distance = math.sqrt(
                (prev_point[0] - cur_point[0]) ** 2
                + (prev_point[1] - cur_point[1]) ** 2
            )
            assert distance < 1.0, (
                f"Distance between left points {i} and {i + 1} out of {len(lefts_x)} is {distance}"
            )
        prev_point = cur_point

    # instead of generating a spline for both lefts and rights, we generate a spline for just the lefts
    # this is because around corners, the lines end up overlapping due to the fact that the
    # distances are shorter around the two curves, this way we can ensure that they do not
    # overlap and also make the width more constant around the track.
    rights_x: list[float] = []
    rights_y: list[float] = []
    track_width = 12  # this is hardcoded from how we generate the track
    for i in range(len(lefts_x)):
        next_idx = i + 1 if i + 1 < len(lefts_x) else i - 1
        cur_point_x, cur_point_y = lefts_x[i], lefts_y[i]
        next_point_x, next_point_y = lefts_x[next_idx], lefts_y[next_idx]

        vec_x = next_point_x - cur_point_x
        vec_y = next_point_y - cur_point_y
        mag = (vec_x**2 + vec_y**2) ** 0.5
        unit_vec_x = vec_x / mag
        unit_vec_y = vec_y / mag

        perp_vec_x, perp_vec_y = unit_vec_y, -unit_vec_x
        # we go track width in each direction
        a_x = cur_point_x - perp_vec_x * track_width
        a_y = cur_point_y - perp_vec_y * track_width

        b_x = cur_point_x + perp_vec_x * track_width
        b_y = cur_point_y + perp_vec_y * track_width

        # if this is the first, we need to choose the point closest to lefts[0]
        if i == 0:
            left_x, left_y = lefts_x[0], lefts_y[0]

            a_distance = math.sqrt((left_x - a_x) ** 2 + (left_y - a_y) ** 2)
            b_distance = math.sqrt((left_x - b_x) ** 2 + (left_y - b_y) ** 2)
            if a_distance < b_distance:
                rights_x.append(a_x)
                rights_y.append(a_y)
            else:
                rights_x.append(b_x)
                rights_y.append(b_y)
        elif i == len(lefts_x) - 1:
            rights_x.append(rights_x[0])
            rights_y.append(rights_y[0])
        else:
            # find the closest point to the last right point
            last_x, last_y = rights_x[-1], rights_y[-1]

            a_distance = math.sqrt((last_x - a_x) ** 2 + (last_y - a_y) ** 2)
            b_distance = math.sqrt((last_x - b_x) ** 2 + (last_y - b_y) ** 2)
            if a_distance < b_distance:
                rights_x.append(a_x)
                rights_y.append(a_y)
            else:
                rights_x.append(b_x)
                rights_y.append(b_y)

    prev_point = None
    for i, (right_x, right_y) in enumerate(zip(rights_x, rights_y)):
        cur_point = (right_x, right_y)
        if prev_point:
            distance = math.sqrt(
                (prev_point[0] - cur_point[0]) ** 2
                + (prev_point[1] - cur_point[1]) ** 2
            )
            assert distance < 1.5, (
                f"Distance between right points {i} and {i + 1} out of {len(rights_x)} is {distance}"
            )
        prev_point = cur_point

    new_track_points = pd.DataFrame(
        {
            "lefts_X": lefts_x,
            "lefts_Y": lefts_y,
            "lefts_Z": np.zeros(len(lefts_x)),
            "rights_X": rights_x,
            "rights_Y": rights_y,
            "rights_Z": np.zeros(len(rights_x)),
        }
    )

    return new_track_points


def assign_inner_outer(
    track_points: DataFrame,
) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]]]:
    """Determine inner and outer track boundaries from left and right points.

    The track data API provides left and right points, but doesn't specify which is inner vs outer.
    Since the car could go clockwise or counter-clockwise around the track, this function
    calculates which points represent the inner and outer edges based on path length.
    The shorter path is assumed to be the inner boundary of the track.

    Args:
        track_points: DataFrame containing track boundary points with lefts_X, lefts_Y, lefts_Z,
                     rights_X, rights_Y, and rights_Z columns

    Returns:
        tuple: (inner_points, outer_points) where each is a list of (x,y,z) coordinate tuples

    """
    # Extract coordinates directly from DataFrame to avoid type issues with iterrows
    lefts_x: list[float] = track_points["lefts_X"].tolist()
    lefts_y: list[float] = track_points["lefts_Y"].tolist()
    lefts_z: list[float] = track_points["lefts_Z"].tolist()

    rights_x: list[float] = track_points["rights_X"].tolist()
    rights_y: list[float] = track_points["rights_Y"].tolist()
    rights_z: list[float] = track_points["rights_Z"].tolist()

    # Create coordinate tuples
    lefts: list[tuple[float, float, float]] = [
        (x, y, z) for x, y, z in zip(lefts_x, lefts_y, lefts_z)
    ]
    rights: list[tuple[float, float, float]] = [
        (x, y, z) for x, y, z in zip(rights_x, rights_y, rights_z)
    ]

    # we want to assume the inner points as the shorter distnace, the outer points as the longer distance
    left_dist = 0
    right_dist = 0
    for i in range(len(lefts) - 1):
        left_dist += (
            (lefts[i][0] - lefts[i + 1][0]) ** 2 + (lefts[i][1] - lefts[i + 1][1]) ** 2
        ) ** 0.5
        right_dist += (
            (rights[i][0] - rights[i + 1][0]) ** 2
            + (rights[i][1] - rights[i + 1][1]) ** 2
        ) ** 0.5

    if left_dist <= right_dist:
        outer_points = rights
        inner_points = lefts
    else:
        inner_points = lefts
        outer_points = rights

    return inner_points, outer_points


def curb(
    cur: list[tuple[float, float, float]],
    other: list[tuple[float, float, float]],
    curb_width: float,
) -> list[tuple[float, float, float]]:
    """Calculate curb points perpendicular to the track boundary.

    Takes the line which is perpendicular to the current point and the next point,
    then extends curb_width distance along that line, away from the opposite track boundary.

    Args:
        cur: Current track boundary points
        other: Opposite track boundary points
        curb_width: Width of the curb to generate

    Returns:
        List of curb points

    """
    curb: list[tuple[float, float, float]] = []
    for i in range(len(cur)):
        next_idx = i + 1
        if next_idx == len(cur):
            # this ensures that they won't overlap, because they will be parallel at the end
            next_idx = i - 1

        cur_vec = (cur[next_idx][0] - cur[i][0], cur[next_idx][1] - cur[i][1])
        perp_vec = (-cur_vec[1], cur_vec[0])
        mag = math.sqrt(perp_vec[0] ** 2 + perp_vec[1] ** 2)

        unit_perp_vec = (perp_vec[0] / mag, perp_vec[1] / mag)

        curb_vec = (unit_perp_vec[0] * curb_width, unit_perp_vec[1] * curb_width)
        # in order to get the correct curb point, we both subtract and add the curb_vec
        # then, we find the one which is further from the other point

        curb_point_a = (cur[i][0] - curb_vec[0], cur[i][1] - curb_vec[1])
        curb_point_b = (cur[i][0] + curb_vec[0], cur[i][1] + curb_vec[1])

        other_point = other[i]

        dist_a = (other_point[0] - curb_point_a[0]) ** 2 + (
            other_point[1] - curb_point_a[1]
        ) ** 2
        dist_b = (other_point[0] - curb_point_b[0]) ** 2 + (
            other_point[1] - curb_point_b[1]
        ) ** 2

        if dist_a > dist_b:
            # we also need to add the z value of cur to the curb point
            curb_point_a = (curb_point_a[0], curb_point_a[1], cur[i][2])
            curb.append(curb_point_a)
        else:
            curb_point_b = (curb_point_b[0], curb_point_b[1], cur[i][2])
            curb.append(curb_point_b)

    assert len(curb) == len(cur)
    return curb


def create_white_lines(
    inner_points: list[tuple[float, float, float]],
    outer_points: list[tuple[float, float, float]],
) -> tuple[LineData, LineData]:
    # we want to create a line which is parallel to the inner points but slightly closer to the outer
    a_trace: list[tuple[float, float, float]] = []
    a_fill: list[tuple[float, float, float]] = []

    b_trace: list[tuple[float, float, float]] = []
    b_fill: list[tuple[float, float, float]] = []

    def get_trace_line(
        point1: tuple[float, float, float], point2: tuple[float, float, float]
    ) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        vec = (point2[0] - point1[0], point2[1] - point1[1], point2[2] - point1[2])
        vec_length = math.sqrt(vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2)
        normalized_vec = (vec[0] / vec_length, vec[1] / vec_length, vec[2] / vec_length)

        trace_point_dist = 0.2
        fill_point_dist = 0.4

        trace_point = (
            point1[0] + normalized_vec[0] * trace_point_dist,
            point1[1] + normalized_vec[1] * trace_point_dist,
            point1[2] + normalized_vec[2] * trace_point_dist + 0.02,
        )
        fill_point = (
            point1[0] + normalized_vec[0] * fill_point_dist,
            point1[1] + normalized_vec[1] * fill_point_dist,
            point1[2] + normalized_vec[2] * fill_point_dist + 0.02,
        )

        return trace_point, fill_point

    for inner_point, outer_point in zip(inner_points, outer_points):
        a_trace_point, a_fill_point = get_trace_line(inner_point, outer_point)
        a_trace.append(a_trace_point)
        a_fill.append(a_fill_point)

        b_trace_point, b_fill_point = get_trace_line(outer_point, inner_point)
        b_trace.append(b_trace_point)
        b_fill.append(b_fill_point)

    line_a = LineData(a_trace, a_fill)
    line_b = LineData(b_trace, b_fill)
    return line_a, line_b


def main(config: Config):
    """Load track data from the csv_repo and return TrackData."""
    log_info("Processing track data")
    use_latest_year = True  # this may cause problems if the track changes year to year
    track_edges = load_raw_data(config["year"], config["track"], use_latest_year)
    track_edges = smooth_points(track_edges)

    inner_points, outer_points = assign_inner_outer(track_edges)
    curb_width = 2
    inner_curb_points = curb(inner_points, outer_points, curb_width)
    outer_curb_points = curb(outer_points, inner_points, curb_width)

    inner_line, outer_line = create_white_lines(inner_points, outer_points)

    log_info("Done processing track data")
    return TrackData(
        inner_points,
        inner_line,
        outer_points,
        outer_line,
        inner_curb_points,
        outer_curb_points,
    )
