"""Calculate car ranking.

For each frame in the video, return a list of tuples containing the driver and their distance to the reference line.
"""

import numpy as np
import pandas as pd

from src.models.config import Config
from src.models.driver import Driver
from src.models.track_data import TrackData


def point_to_line_distance(
    point: tuple[float, float, float],
    line_start: tuple[float, float, float],
    line_end: tuple[float, float, float],
) -> float:
    """Calculate the distance from a point to a line segment."""
    # Convert tuples to numpy arrays for vector operations
    point_arr = np.array(point, dtype=float)
    line_start_arr = np.array(line_start, dtype=float)
    line_end_arr = np.array(line_end, dtype=float)

    # Calculate vector along the line segment
    line_vec_arr = line_end_arr - line_start_arr
    line_length = float(np.linalg.norm(line_vec_arr))

    line_unit_vec = line_vec_arr / line_length
    point_vec_arr = point_arr - line_start_arr
    projection_length = float(np.dot(point_vec_arr, line_unit_vec))

    # If projection falls before beginning of line segment
    if projection_length < 0:
        return float(np.linalg.norm(point_arr - line_start_arr))
    # If projection falls after end of line segment
    if projection_length > line_length:
        return float(np.linalg.norm(point_arr - line_end_arr))

    # Calculate the projection point
    projection_arr = line_start_arr + line_unit_vec * projection_length
    return float(np.linalg.norm(point_arr - projection_arr))


def find_closest_track_idx(
    inner_points: list[tuple[float, float, float]],
    outer_points: list[tuple[float, float, float]],
    previous_reference_idx: int,
    car_point: tuple[float, float, float],
) -> int:
    """Find the closest track segment to a car point.

    This function searches for the track segment closest to the car point,
    starting from the previous reference index. It searches in both positive
    and negative directions along the track.

    Args:
        inner_points: List of inner track boundary points
        outer_points: List of outer track boundary points
        previous_reference_idx: The index of the line from which the previous
            frame's ranking was calculated
        car_point: The position of the car

    Returns:
        The index of the closest track segment to the car point

    """
    assert len(inner_points) == len(outer_points), (
        "Inner and outer points must have the same length"
    )

    # using normalize for indexes because we want the "absolute" index in order to rank them properly
    # for example if we have 5000 and len is 5001, then we need to be able to show that 0 is above 5000 by
    # recording that as 5001.
    def normalize(idx: int):
        return idx % len(inner_points)

    pos = previous_reference_idx
    neg = previous_reference_idx - 1

    pos_distance = point_to_line_distance(
        car_point, inner_points[pos], outer_points[pos]
    )
    neg_distance = point_to_line_distance(
        car_point, inner_points[normalize(neg)], outer_points[normalize(neg)]
    )

    while (
        point_to_line_distance(
            car_point,
            inner_points[normalize(pos + 1)],
            outer_points[normalize(pos + 1)],
        )
        < pos_distance
    ):
        pos += 1
        pos_distance = point_to_line_distance(
            car_point, inner_points[normalize(pos)], outer_points[normalize(pos)]
        )

    # only do one less for neg
    if (
        point_to_line_distance(
            car_point,
            inner_points[normalize(neg - 1)],
            outer_points[normalize(neg - 1)],
        )
        < neg_distance
    ):
        neg -= 1
        neg_distance = point_to_line_distance(
            car_point, inner_points[normalize(neg)], outer_points[normalize(neg)]
        )

    return pos if pos_distance < neg_distance else neg


def find_most_distant_closest_point(
    inner_points: list[tuple[float, float, float]],
    outer_points: list[tuple[float, float, float]],
    previous_reference_idx: int,
    car_points: list[tuple[float, float, float]],
):
    """Find the point which is furthest from the previous line which was used to calculate the ranking.

    This will allow us to find the next reference line.
    """
    closest_idxs = [
        find_closest_track_idx(
            inner_points, outer_points, previous_reference_idx, car_point
        )
        for car_point in car_points
    ]

    cur_farthest_point_idx = 0
    for idx in closest_idxs:
        cur_farthest_point_idx = max(cur_farthest_point_idx, idx)

    # now, we have the farthest point idx, we want to check if the car is actually
    # the car might not actually be infront of this point, we should be able to just add 1 to the idx
    # track points are close enough together that this should not cause bugs
    return (cur_farthest_point_idx + 1) % len(inner_points)


# the frame here is implicit. All of the car points will be different cars at the same frame
def ranking_at_frame(
    inner_points: list[tuple[float, float, float]],
    outer_points: list[tuple[float, float, float]],
    previous_reference_idx: int,
    car_points: list[tuple[float, float, float]],
) -> tuple[list[tuple[int, float]], int]:
    """Calculate car ranking at one frame."""
    new_reference_idx = find_most_distant_closest_point(
        inner_points, outer_points, previous_reference_idx, car_points
    )
    # for each driver, we calculate their distance to the new reference line

    drivers: list[tuple[int, float]] = []
    for driver_idx in range(len(car_points)):
        distance = float(
            point_to_line_distance(
                car_points[driver_idx],
                inner_points[new_reference_idx],
                outer_points[new_reference_idx],
            )
        )
        drivers.append((driver_idx, distance))

    return (sorted(drivers, key=lambda x: x[1]), new_reference_idx)


def main(
    track_data: TrackData,
    start_finish_line_idx: int,
    driver_dfs: dict[Driver, pd.DataFrame],
    config: Config,
    focused_driver: Driver,
) -> list[list[tuple[Driver, float]]]:
    """Caclulate car ranking.

    For each frame in the video, return a list of tuples containing the driver and their distance to the reference line.
    """
    start_buffer_frames = config["render"]["start_buffer_frames"]
    end_buffer_frames = config["render"]["end_buffer_frames"]

    indices: dict[int, Driver] = {}
    driver_data: list[list[tuple[float, float, float]]] = []
    for i, (driver, df) in enumerate(driver_dfs.items()):
        car_points: list[tuple[float, float, float]] = [
            (df.iloc[i]["X"], df.iloc[i]["Y"], df.iloc[i]["Z"]) for i in range(len(df))
        ]
        driver_data.append(car_points)
        indices[i] = driver

    final_rank: list[list[tuple[Driver, float]]] = []
    reference_idx = start_finish_line_idx
    for i in range(
        start_buffer_frames, len(driver_dfs[focused_driver]) - end_buffer_frames
    ):
        current_frame_positions = [driver_points[i] for driver_points in driver_data]

        rankings, reference_idx = ranking_at_frame(
            track_data.inner_points,
            track_data.outer_points,
            reference_idx,
            current_frame_positions,
        )

        final_rank.append([(indices[rank[0]], rank[1]) for rank in rankings])

    return final_rank
