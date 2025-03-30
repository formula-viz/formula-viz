from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from src.models.driver import Driver
from src.models.load_data import LoadData


@dataclass
class AppState:
    """Holds all state variables used during rendering to make data flow explicit."""

    project_root: Path

    load_data: Optional[LoadData] = None

    driver_objs: dict[Driver, Any] = field(default_factory=dict)
    num_frames: int = 0
    camera_obj: Any = None
    car_rankings: list[list[tuple[Driver, float]]] = field(default_factory=list)
