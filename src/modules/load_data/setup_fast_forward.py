import math

from pandas.core.frame import DataFrame

from src.models.config import Config
from src.models.driver import Driver
from src.utils.logger import log_info


def _find_initial_straights(
    config: Config, focused_driver_df: DataFrame
) -> list[tuple[int, bool]]:
    straight_line_threshold: float = 0.1
    lookahead: int = 25

    start_buffer = config["render"]["start_buffer_frames"] * 2
    end_buffer = config["render"]["end_buffer_frames"]

    x_values = focused_driver_df["X"].to_numpy()
    y_values = focused_driver_df["Y"].to_numpy()

    is_on_straight: list[tuple[int, bool]] = []
    # Process each frame within valid range
    for i in range(
        start_buffer + lookahead, len(focused_driver_df) - end_buffer - lookahead
    ):
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

    return is_on_straight


def _filter_out_isolated_sections(is_on_straight: list[tuple[int, bool]]):
    is_skip_zone = []
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
                is_skip_zone.append((idx, True))
                was_previous_straight = True
            else:
                is_skip_zone.append((idx, False))
        elif is_straight and was_previous_straight:
            is_skip_zone.append((idx, True))
        else:
            is_skip_zone.append((idx, False))
            was_previous_straight = False

    return is_skip_zone


def _apply_basis_points(is_skip_zone: list[tuple[int, bool]]) -> dict[int, bool]:
    """Given the list of indices and their skip status, we want to go through and sprinkle in non skipped points so that the car actually fast forwards instead of jumps."""
    should_skip_point: dict[int, bool] = {}
    skipped_in_a_row = 0
    for idx, is_straight in is_skip_zone:
        if is_straight and skipped_in_a_row < 4:
            should_skip_point[idx] = True
            skipped_in_a_row += 1
        else:
            should_skip_point[idx] = False
            skipped_in_a_row = 0

    return should_skip_point


def set_fast_forward_frames(
    config: Config,
    focused_driver: Driver,
    driver_dfs: dict[Driver, DataFrame],
):
    """Identify frames where the focused driver is on a straight line and mark them for fast forwarding.

    Uses a simple method: checks if the angle between (i-lookahead) -> i -> (i+lookahead)
    is below the threshold.

    Args:
        focused_driver: The driver to focus on for determining straight lines
        driver_dfs: Dictionary mapping drivers to their DataFrames
        config: Configuration dictionary with render settings

    Returns:
        Updated driver_dfs with 'FastForward' column added to each DataFrame

    """
    is_on_straights = _find_initial_straights(config, driver_dfs[focused_driver])
    is_skip_zone = _filter_out_isolated_sections(is_on_straights)
    ff_frames = sum([is_straight[1] for is_straight in is_skip_zone])
    should_skip_point = _apply_basis_points(is_skip_zone)

    for driver, driver_df in driver_dfs.items():
        for i, row in enumerate(driver_df.iterrows()):
            if i not in should_skip_point:
                driver_df.at[i, "FastForward"] = False
            else:
                driver_df.at[i, "FastForward"] = should_skip_point[i]

    ff_percent = (ff_frames / len(driver_dfs[focused_driver])) * 100
    log_info(
        f"Fast forward frames: {ff_frames}/{len(driver_dfs[focused_driver])} ({ff_percent:.1f}%)"
    )
    return driver_dfs, should_skip_point
