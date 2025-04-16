from pandas import Timedelta
from src.models.driver import Driver, RunDrivers


def process_sector_times(run_data: RunDrivers):
    fastest_sector_1 = None
    fastest_sector_2 = None
    fastest_sector_3 = None

    sector_times_dict: dict[Driver, list[Timedelta]] = {}
    end_frames_dict: dict[Driver, list[int]] = {}

    for driver, driver_run in run_data.driver_run_data.items():
        driver_sector_times = run_data.driver_sector_times[driver]

        absolute_to_sped_conversion = driver_run.absolute_frame_to_sped_frame
        sector_times = [
            driver_sector_times.sector1,
            driver_sector_times.sector2,
            driver_sector_times.sector3,
        ]

        end_frames_absolute: list[int] = [
            absolute_to_sped_conversion[driver_run.sector_1_end_absolute_frame],
            absolute_to_sped_conversion[driver_run.sector_2_end_absolute_frame],
            absolute_to_sped_conversion[driver_run.sector_3_end_absolute_frame]
            if driver_run.sector_3_end_absolute_frame in absolute_to_sped_conversion
            else 10000,
        ]

        if fastest_sector_1 is None or sector_times[0] < fastest_sector_1:
            fastest_sector_1 = sector_times[0]
        if fastest_sector_2 is None or sector_times[1] < fastest_sector_2:
            fastest_sector_2 = sector_times[1]
        if fastest_sector_3 is None or sector_times[2] < fastest_sector_3:
            fastest_sector_3 = sector_times[2]

        end_frames_dict[driver] = end_frames_absolute
        sector_times_dict[driver] = sector_times

    assert (
        fastest_sector_1 is not None
        and fastest_sector_2 is not None
        and fastest_sector_3 is not None
    )

    sector_packages: dict[
        Driver, tuple[list[Timedelta], list[int], list[Timedelta]]
    ] = {}
    for driver, sector_times in sector_times_dict.items():
        end_frames = end_frames_dict[driver]

        time_slower_than_fastest_in_sector = [
            sector_times[0] - fastest_sector_1,
            sector_times[1] - fastest_sector_2,
            sector_times[2] - fastest_sector_3,
        ]

        sector_packages[driver] = (
            sector_times,
            end_frames,
            time_slower_than_fastest_in_sector,
        )

    return sector_packages
