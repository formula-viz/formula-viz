import math

from pandas.core.frame import DataFrame

from src.models.config import Config
from src.models.driver import Driver
from src.utils.logger import log_info


def set_fast_forward_frames(
    focused_driver: Driver,
    driver_dfs: dict[Driver, DataFrame],
    config: Config,
    fast_forward_mult: float = 3.0,
    straight_line_threshold: float = 0.1,  # Threshold in radians (about 3 degrees)
    lookahead: int = 25,  # Points to look ahead/behind
):
    """Identify frames where the focused driver is on a straight line and mark them for fast forwarding.

    Uses a simple method: checks if the angle between (i-lookahead) -> i -> (i+lookahead)
    is below the threshold.

    Args:
        focused_driver: The driver to focus on for determining straight lines
        driver_dfs: Dictionary mapping drivers to their DataFrames
        config: Configuration dictionary with render settings
        fast_forward_mult: Speed multiplier for fast forward segments
        straight_line_threshold: Angle threshold in radians (lower = straighter)
        lookahead: Number of points to look ahead/behind to determine straightness

    Returns:
        Updated driver_dfs with 'FastForward' column added to each DataFrame

    """
    # Get the focused driver's DataFrame
    df = driver_dfs[focused_driver]

    # Calculate start and end frames based on buffer settings
    start_buffer = config["render"]["start_buffer_frames"] * 2
    end_buffer = config["render"]["end_buffer_frames"]

    # Initialize FastForward column as False for all drivers
    for driver, driver_df in driver_dfs.items():
        driver_df["FastForward"] = False

    # Get positions
    x_values = df["X"].values
    y_values = df["Y"].values
    total_frames = len(df)

    # Skip if we don't have enough frames
    if total_frames <= start_buffer + end_buffer + 2 * lookahead:
        return driver_dfs

    is_on_straight: list[tuple[int, bool]] = []
    # Process each frame within valid range
    for i in range(start_buffer + lookahead, total_frames - end_buffer - lookahead):
        # Get points before and after current point
        p_before = (x_values[i - lookahead], y_values[i - lookahead])
        p_current = (x_values[i], y_values[i])
        p_after = (x_values[i + lookahead], y_values[i + lookahead])

        # Calculate vectors
        vec1 = (p_current[0] - p_before[0], p_current[1] - p_before[1])
        vec2 = (p_after[0] - p_current[0], p_after[1] - p_current[1])

        # Normalize vectors
        len1 = math.sqrt(vec1[0] ** 2 + vec1[1] ** 2)
        len2 = math.sqrt(vec2[0] ** 2 + vec2[1] ** 2)

        if len1 > 0 and len2 > 0:
            vec1_norm = (vec1[0] / len1, vec1[1] / len1)
            vec2_norm = (vec2[0] / len2, vec2[1] / len2)

            # Calculate dot product
            dot_product = vec1_norm[0] * vec2_norm[0] + vec1_norm[1] * vec2_norm[1]

            # Clamp to valid range
            dot_product = max(-1.0, min(1.0, dot_product))

            # Calculate angle
            angle = math.acos(dot_product)

            # If angle is small enough, mark as straight
            should_skip = angle < straight_line_threshold
            is_on_straight.append((i, should_skip))

    new_is_on_straight = []
    was_previous_straight = False
    for idx, is_straight in is_on_straight:
        if is_straight and not was_previous_straight:
            num_in_group = 1
            for j in range(idx + 1, len(is_on_straight)):
                if is_on_straight[j][1]:
                    num_in_group += 1
                else:
                    break

            if num_in_group >= 15:
                new_is_on_straight.append((idx, True))
                was_previous_straight = True
            else:
                new_is_on_straight.append((idx, False))
        elif is_straight and was_previous_straight:
            new_is_on_straight.append((idx, True))
        else:
            new_is_on_straight.append((idx, False))
            was_previous_straight = False

    ff_frames = sum([is_straight[1] for is_straight in is_on_straight])
    is_on_straight = new_is_on_straight
    new_is_on_straight = {}

    skipped_in_a_row = 0
    for idx, is_straight in is_on_straight:
        if is_straight and skipped_in_a_row < 2:
            new_is_on_straight[idx] = True
            skipped_in_a_row += 1
        else:
            new_is_on_straight[idx] = False
            skipped_in_a_row = 0

    for driver, driver_df in driver_dfs.items():
        for i, row in driver_df.iterrows():
            if i not in new_is_on_straight:
                driver_df.at[i, "FastForward"] = False
            else:
                driver_df.at[i, "FastForward"] = new_is_on_straight[i]

    # Count and report fast forwarded frames
    total_valid_frames = total_frames - start_buffer - end_buffer - 2 * lookahead
    ff_percent = (ff_frames / total_valid_frames) * 100 if total_valid_frames > 0 else 0

    log_info(
        f"Fast forward frames: {ff_frames}/{total_valid_frames} ({ff_percent:.1f}%)"
    )
    return driver_dfs
