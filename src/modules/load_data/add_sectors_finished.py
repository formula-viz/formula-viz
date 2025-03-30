from pandas import DataFrame

from src.models.config import Config
from src.models.driver import Driver
from src.models.sectors import SectorTimes


def add_sectors_finished(
    config: Config,
    driver_dfs: dict[Driver, DataFrame],
    driver_sector_times: dict[Driver, SectorTimes],
) -> tuple[dict[Driver, int], dict[Driver, int], dict[Driver, int]]:
    driver_sector_1_end_frames_absolute = {}
    driver_sector_2_end_frames_absolute = {}
    driver_sector_3_end_frames_absolute = {}

    for driver, sector_times in driver_sector_times.items():
        sector_1_end_absolute_frame = config["render"]["start_buffer_frames"] + int(
            sector_times.sector1.total_seconds() * config["render"]["fps"]
        )
        sector_2_end_absolute_frame = sector_1_end_absolute_frame + int(
            sector_times.sector2.total_seconds() * config["render"]["fps"]
        )
        sector_3_end_absolute_frame = sector_2_end_absolute_frame + int(
            sector_times.sector3.total_seconds() * config["render"]["fps"]
        )

        driver_sector_1_end_frames_absolute[driver] = sector_1_end_absolute_frame
        driver_sector_2_end_frames_absolute[driver] = sector_2_end_absolute_frame
        driver_sector_3_end_frames_absolute[driver] = sector_3_end_absolute_frame

    return (
        driver_sector_1_end_frames_absolute,
        driver_sector_2_end_frames_absolute,
        driver_sector_3_end_frames_absolute,
    )
