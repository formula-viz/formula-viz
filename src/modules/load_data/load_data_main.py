from src.models.app_state import AppState
from src.models.config import Config
from src.models.driver import Driver, DriverRunData, RunDrivers
from src.models.load_data import LoadData
from src.modules.load_data import (
    add_sectors_finished,
    load_driver_data,
    load_track_data_auto,
    load_track_data_custom,
)
from src.modules.load_data.setup_drivers import setup_drivers_h2h, setup_drivers_rof
from src.modules.load_data.setup_fast_forward import set_fast_forward_frames
from src.utils.logger import log_info


def load_data_main(config: Config, app_state: AppState):
    log_info(f"Loading data for {config['type']} race")

    # the track data for the thumbnail uses the same track everytime
    config_copy = config.copy()
    config_copy["track"] = "JAPAN"
    config_copy["year"] = 2024
    thumbnail_track_data = load_track_data_auto.main(config_copy)
    app_state.thumbnail_track_data = thumbnail_track_data

    # even when we are using a custom track file, we still need track data and inner / outer points
    # in order to properly adjust the Z values of the cars so they don't float or clip under the track
    if config["render"]["auto_track_mode"]:
        track_data = load_track_data_auto.main(config)
    else:
        track_data = load_track_data_custom.main(config)
    (
        driver_dfs,
        driver_sector_times,
        sectors_info,
        start_finish_line_idx,
        circuit_info,
    ) = load_driver_data.main(track_data, config)

    if config["type"] == "rest-of-field":
        focused_driver, driver_applied_colors = setup_drivers_rof(config, driver_dfs)
    else:
        focused_driver, driver_applied_colors = setup_drivers_h2h(config, driver_dfs)

    (
        driver_sector_1_end_frames_absolute,
        driver_sector_2_end_frames_absolute,
        driver_sector_3_end_frames_absolute,
    ) = add_sectors_finished.add_sectors_finished(
        config, driver_dfs, driver_sector_times
    )

    driver_point_dfs, should_skip_point = set_fast_forward_frames(
        config, focused_driver, driver_dfs
    )

    absolute_frame_to_sped_frame: dict[int, int] = {}
    sped_frame_to_absolute_frame: dict[int, int] = {}
    cur_sped_frame = -1
    for i in range(len(driver_point_dfs[focused_driver])):
        is_cur_frame_skipped = should_skip_point.get(i, False)
        # if the current frame is skipped, then that means that no sped frame has been touched
        # so the cur_sped_frame does not increment
        if not is_cur_frame_skipped:
            cur_sped_frame += 1

        absolute_frame_to_sped_frame[i] = cur_sped_frame
        sped_frame_to_absolute_frame[cur_sped_frame] = i

    driver_sped_point_dfs = {}
    for driver, driver_point_df in driver_point_dfs.items():
        # Create a list of indices to keep (frames that shouldn't be skipped)
        rows_to_keep = [
            i
            for i in range(len(driver_point_df))
            if not should_skip_point.get(i, False)
        ]

        driver_sped_point_dfs[driver] = driver_point_df.iloc[rows_to_keep].reset_index(
            drop=True
        )

    driver_run_data: dict[Driver, DriverRunData] = {}
    for driver, driver_point_df in driver_point_dfs.items():
        driver_sped_df = driver_sped_point_dfs[driver]

        sector_1_end_absolute_frame = driver_sector_1_end_frames_absolute[driver]
        sector_2_end_absolute_frame = driver_sector_2_end_frames_absolute[driver]
        sector_3_end_absolute_frame = driver_sector_3_end_frames_absolute[driver]

        driver_run_data[driver] = DriverRunData(
            driver_point_df,
            driver_sped_df,
            sector_1_end_absolute_frame,
            sector_2_end_absolute_frame,
            sector_3_end_absolute_frame,
            absolute_frame_to_sped_frame,
            sped_frame_to_absolute_frame,
        )

    run_drivers = RunDrivers(
        list(driver_dfs.keys()),
        focused_driver,
        driver_run_data,
        driver_sector_times,
        driver_applied_colors,
    )

    log_info("LoadData initialized successfully")
    return LoadData(
        track_data, run_drivers, start_finish_line_idx, sectors_info, circuit_info
    )
