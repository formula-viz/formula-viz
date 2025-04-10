from dataclasses import dataclass
from typing import Optional


@dataclass
class LineData:
    """Line data containing points for line A and line B."""

    a_points: list[tuple[float, float, float]]
    b_points: list[tuple[float, float, float]]


@dataclass
class TrackData:
    """Track data containing inner, outer, and curb points."""

    inner_points: list[tuple[float, float, float]]
    inner_trace_line: Optional[LineData]

    outer_points: list[tuple[float, float, float]]
    outer_trace_line: Optional[LineData]

    inner_curb_points: Optional[list[tuple[float, float, float]]]
    outer_curb_points: Optional[list[tuple[float, float, float]]]
