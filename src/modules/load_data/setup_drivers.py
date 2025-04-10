from typing import Optional

from pandas import DataFrame

from src.models.config import Config
from src.models.driver import Driver
from src.utils.colors import get_head_to_head_colors, get_rest_of_field_colors


def setup_drivers_rof(
    config: Config, driver_dfs: dict[Driver, DataFrame]
) -> tuple[Driver, dict[Driver, str]]:
    focused_driver: Optional[Driver] = None

    for driver in driver_dfs.keys():
        if driver.last_name == config["drivers"][0]:
            focused_driver = driver

    assert focused_driver is not None, "Focused driver not found"
    driver_colors_list = get_rest_of_field_colors(focused_driver)

    driver_colors = {}
    driver_colors[focused_driver] = driver_colors_list.pop(0)
    for driver in driver_dfs.keys():
        if driver != focused_driver:
            driver_colors[driver] = driver_colors_list.pop(0)

    return focused_driver, driver_colors


def setup_drivers_h2h(
    config: Config, driver_dfs: dict[Driver, DataFrame]
) -> tuple[Driver, dict[Driver, str]]:
    drivers_in_color_order = []
    new_driver_dfs: dict[Driver, DataFrame] = {}
    if config["mixed_mode"]["enabled"]:
        for driver_dict in config["mixed_mode"]["drivers"]:
            for driver_class in driver_dfs.keys():
                if (
                    driver_dict["name"] == driver_class.last_name
                    and driver_dict["year"] == driver_class.year
                    and driver_dict["session"] == driver_class.session
                ):
                    new_driver_dfs[driver_class] = driver_dfs[driver_class]
                    drivers_in_color_order.append(driver_class)
                    break
    else:
        for driver_last_name in config["drivers"]:
            for driver_class in driver_dfs.keys():
                if driver_last_name == driver_class.last_name:
                    new_driver_dfs[driver_class] = driver_dfs[driver_class]
                    drivers_in_color_order.append(driver_class)
                    break
    driver_dfs = new_driver_dfs

    focused_driver = drivers_in_color_order[0]
    driver_colors_list = get_head_to_head_colors(drivers_in_color_order)

    driver_colors_dict: dict[Driver, str] = {}
    for driver, color in zip(drivers_in_color_order, driver_colors_list):
        driver_colors_dict[driver] = color

    count_by_team: dict[str, int] = {}
    for driver in driver_dfs.keys():
        count_by_team[driver.team] = count_by_team.get(driver.team, 0) + 1

    # now, if there is any team where count is >=2, we need to add the color marker
    # to distinguish between drivers of the same team
    for team, count in count_by_team.items():
        if count >= 2:
            is_first_done = False
            for idx, (driver, driver_color) in enumerate(
                zip(drivers_in_color_order, driver_colors_list)
            ):
                if driver.team == team:
                    if not is_first_done:
                        is_first_done = True
                    else:
                        driver_colors_dict[driver] = "#ffffff"

    return focused_driver, driver_colors_dict
