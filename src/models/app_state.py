from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from fastf1.mvapi.data import CircuitInfo

from src.models.driver import Driver
from src.models.sectors import SectorsInfo, SectorTimes
from src.models.track_data import TrackData


@dataclass
class LoadData:
    """Data from the load_data module."""

    track_data: TrackData
    driver_dfs: dict[Driver, Any]
    driver_sector_times: dict[Driver, SectorTimes]
    sectors_info: SectorsInfo
    start_finish_line_idx: int
    circuit_info: CircuitInfo
    focused_driver: Driver
    drivers_in_color_order: list[Driver]
    driver_colors: list[str]


@dataclass
class AppState:
    """Holds all state variables used during rendering to make data flow explicit."""

    project_root: Path
    render_output_path: Path

    load_data: Optional[LoadData] = None

    driver_objs: dict[Driver, Any] = field(default_factory=dict)
    num_frames: int = 0
    camera_obj: Any = None
    car_rankings: list[list[tuple[Driver, float]]] = field(default_factory=list)
