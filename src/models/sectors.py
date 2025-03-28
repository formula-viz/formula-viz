from dataclasses import dataclass

from pandas import Timedelta


@dataclass
class SectorTimes:
    """Sector times for a driver."""

    sector1: Timedelta
    sector2: Timedelta
    sector3: Timedelta


@dataclass
class SectorsInfo:
    """Sector information for a driver."""

    sector1_loc: tuple[float, float, float]
    sector2_loc: tuple[float, float, float]
    sector3_loc: tuple[float, float, float]

    sector_1_idx: int
    sector_2_idx: int
    sector_3_idx: int
