import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.models.config import Config
from src.modules.load_data import load_driver_data, load_track_data
from src.modules.render.add_funcs import (
    add_light,
    add_sky_texture,
    add_track,
    add_track_idx_line,
)
from src.utils.colors import SECTOR_1_COLOR, SECTOR_2_COLOR, SECTOR_3_COLOR


def build_just_track():
    config_file = project_root / "config" / "config.json"

    with open(config_file, "r") as f:
        data = json.load(f)
        config = Config(data)

    assert config is not None, "Config object is None"
    track_data = load_track_data.main(config)

    # we still need to load the driver data here because it is used to place the start finish
    # line and the sector line locations
    (
        _,
        _,
        sectors_info,
        start_finish_line_idx,
        _,
    ) = load_driver_data.main(track_data, config)

    add_track.main(track_data, sectors_info)

    add_track_idx_line.add_track_idx_line(
        track_data.inner_curb_points,
        track_data.outer_curb_points,
        start_finish_line_idx,
        "Sector3LineEnd",
        3,
        SECTOR_1_COLOR,
    )
    add_track_idx_line.add_track_idx_line(
        track_data.inner_points,
        track_data.outer_points,
        sectors_info.sector_1_idx,
        "Sector1LineEnd",
        1,
        SECTOR_2_COLOR,
    )
    add_track_idx_line.add_track_idx_line(
        track_data.inner_points,
        track_data.outer_points,
        sectors_info.sector_2_idx,
        "Sector2LineEnd",
        1,
        SECTOR_3_COLOR,
    )

    add_light.main()
    add_sky_texture.add_sky_texture()


# uses the main config file under the config directory to grab the year and circuit (ex, Japan)
# run using blender --python tools/build_just_track.py
if __name__ == "__main__":
    build_just_track()
