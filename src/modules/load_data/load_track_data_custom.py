import pickle
import subprocess
import sys
from pathlib import Path

from src.models.config import Config
from src.models.track_data import TrackData
from src.utils import file_utils
from src.utils.logger import log_err, log_info


def find_track_path(track: str, year: int):
    project_paths = file_utils.project_paths
    track_files_dir = Path(project_paths.BLENDER_DIR / "tracks")
    # iterate through contents of track_data, finding all files containing track
    # then, we find the file with the latest year
    # if use_latest_year is false, we use the year given
    try:
        track_blend_file = [
            file for file in track_files_dir.iterdir() if track in file.name
        ]
    except OSError as e:
        log_err(f"Error accessing track data directory: {e}")
        sys.exit(1)

    if not track_blend_file:
        raise FileNotFoundError(f"Track data not found for {track}")

    latest_year = 0
    latest_file = ""
    for file in track_blend_file:
        # Extract just the filename from the path before splitting on hyphens
        filename = str(file).split("/")[-1]  # Get the last part after the final slash
        year = int(filename.split("-")[1].split(".")[0])
        if int(year) > latest_year:
            latest_year = int(year)
            latest_file = file.name
    track_data_file = latest_file

    return track_files_dir / track_data_file


def get_track_data(track_blend_file: Path, track: str, year: int):
    """Extract track data from a Blender file and load it from a pickle file.

    Args:
        track_blend_file: Path to the Blender file containing the track
        track: Name of the track
        year: Year of the track data

    Returns:
        A tuple containing the inner and outer track points

    """
    # Get the directory where the current script is located
    script_dir = Path(__file__).parent.absolute()
    helper_script = script_dir / "load_track_data_custom_helper.py"

    track_data_save_path = (
        file_utils.project_paths.BLENDER_DIR / "tracks" / f"{track}-{year}.pickle"
    )

    if not track_data_save_path.exists():
        # Run Blender with the helper script and pass the track file as an argument
        cmd = [
            "blender",
            "--background",
            str(track_blend_file),
            "--python",
            str(helper_script),
            "--",
            str(track_data_save_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)

    # Load the TrackData object from the pickle file
    if track_data_save_path.exists():
        with open(track_data_save_path, "rb") as f:
            track_data = pickle.load(f)
        return track_data
    else:
        log_err(f"Pickle file not created at {track_data_save_path}")
        raise FileNotFoundError(
            f"Track data pickle file not found at {track_data_save_path}"
        )


def main(config: Config):
    """Load track data from the csv_repo and return TrackData."""
    log_info("Processing track data from custom blend file")
    track = config["track"].lower()
    year = config["year"]

    track_path = find_track_path(track, year)
    track_data: TrackData = get_track_data(track_path, track, year)

    return track_data
