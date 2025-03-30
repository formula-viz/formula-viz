"""Maintains the data for each driver for the current run."""

from dataclasses import dataclass

from pandas import DataFrame

from src.models.sectors import SectorTimes


@dataclass
class DriverRunData:
    # the original dataframe of keyframes, rotations, speeds, rpm for this driver with start and end buffers
    point_df: DataFrame
    # the dataframe after applying fast forwarding to the video along the straight lines
    sped_point_df: DataFrame

    sector_1_end_absolute_frame: int
    sector_2_end_absolute_frame: int
    sector_3_end_absolute_frame: int

    absolute_frame_to_sped_frame: dict[int, int]
    sped_frame_to_absolute_frame: dict[int, int]


@dataclass(frozen=True)
class Driver:
    """Represent a Formula 1 driver with identifying information."""

    last_name: str
    abbrev: str
    headshot_url: str
    year: int
    session: str
    team: str
    default_driver_color: str

    def __str__(self) -> str:
        """Return a string representation of the Driver."""
        return f"{self.last_name} ({self.abbrev}, {self.year}, {self.session}, {self.team}, {self.default_driver_color})"

    def __hash__(self) -> int:
        """Return a hash value for the Driver."""
        return hash(
            (
                self.last_name,
                self.abbrev,
                self.headshot_url,
                self.year,
                self.session,
                self.team,
                self.default_driver_color,
            )
        )


@dataclass
class RunDrivers:
    """Maintains the data for each driver for the current run."""

    drivers: list[Driver]
    focused_driver: Driver
    driver_run_data: dict[Driver, DriverRunData]

    driver_sector_times: dict[Driver, SectorTimes]
    driver_applied_colors: dict[Driver, str]
