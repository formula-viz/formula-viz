from dataclasses import dataclass

from fastf1.mvapi.data import CircuitInfo

from src.models.driver import RunDrivers
from src.models.sectors import SectorsInfo
from src.models.track_data import TrackData


@dataclass
class LoadData:
    """Data from the load_data module."""

    track_data: TrackData
    run_drivers: RunDrivers

    start_finish_line_idx: int
    sectors_info: SectorsInfo
    circuit_info: CircuitInfo
