from src.models.app_state import AppState, LoadData
from src.models.config import Config
from src.modules.load_data import load_driver_data, load_track_data
from src.modules.load_data.setup_drivers import setup_drivers_h2h, setup_drivers_rof


def load_data_main(config: Config, app_state: AppState):
    track_data = load_track_data.main(config)

    (
        driver_dfs,
        driver_sector_times,
        sectors_info,
        start_finish_line_idx,
        circuit_info,
    ) = load_driver_data.main(track_data, config)

    if config["type"] == "rest-of-field":
        focused_driver, drivers_in_color_order, driver_colors = setup_drivers_rof(
            config, driver_dfs
        )
    else:
        focused_driver, drivers_in_color_order, driver_colors = setup_drivers_h2h(
            config, driver_dfs
        )

    return LoadData(
        track_data=track_data,
        driver_dfs=driver_dfs,
        driver_sector_times=driver_sector_times,
        sectors_info=sectors_info,
        start_finish_line_idx=start_finish_line_idx,
        circuit_info=circuit_info,
        focused_driver=focused_driver,
        drivers_in_color_order=drivers_in_color_order,
        driver_colors=driver_colors,
    )
