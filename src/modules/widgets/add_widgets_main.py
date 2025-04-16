import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from src.models.app_state import AppState
from src.models.config import Config
from src.models.driver import Driver, DriverRunData
from src.modules.widgets import process_sector_times
from src.utils import file_utils
from src.utils.logger import log_info


def open_in_gimp(gimp_path, json_path, run_script=True, headless=False):
    """Opens GIMP with the specified file and optionally runs a script.

    Args:
        gimp_path: Path to the GIMP file to open
        json_path: Path to the JSON file containing data for processing
        run_script: Whether to run the Python-Fu script
        headless: Whether to run GIMP in headless mode

    Returns:
        bool: True if GIMP was launched successfully, False otherwise

    """
    try:
        # Base command for Flatpak GIMP
        gimp_cmd = ["flatpak", "run", "org.gimp.GIMP"]

        # Add headless mode if requested
        if headless:
            gimp_cmd.append("--no-interface")
        else:
            gimp_cmd.append("--no-splash")

        from pathlib import Path

        current_dir = Path(__file__).absolute().parent
        project_root = current_dir.parents[2]
        log_info(f"{project_root}")

        if run_script and json_path:
            # Add Python-Fu script execution parameters and open the file
            gimp_cmd.extend(
                [
                    gimp_path,
                    "--batch-interpreter",
                    "python-fu-eval",
                    "-b",
                    f"import sys; sys.path.append('{project_root}'); from src.modules.widgets.gimp_processor import main; main('{os.path.abspath(json_path)}')",
                ]
            )
        else:
            # Just open the file(s) without running script
            gimp_cmd.append(gimp_path)

        # Launch GIMP through Flatpak synchronously
        # (wait for the subprocess to complete before returning)
        subprocess.run(gimp_cmd, check=True)
        # subprocess.Popen(gimp_cmd)
        return True

    except Exception as e:
        print(f"Error launching GIMP: {e}")
        return False


@dataclass
class DriverDashData:
    img_file_path: str
    output_dir_path: str

    color: str
    position: int
    num_frames: int
    throttle: list[int]  # each from 0 to 100
    is_brake: list[bool]
    is_drs: list[int]
    sector_times: list[str]
    sector_end_frames: list[int]
    sector_delta_times: list[str]


def add_driver_dash_data(
    driver: Driver,
    driver_run_data: DriverRunData,
    driver_applied_color: str,
    json_friendly_sector_packages: tuple[list[str], list[int], list[str]],
):
    driver_image_path = file_utils.project_paths.get_driver_image_path(driver)

    sped_point_df = driver_run_data.sped_point_df

    # Extract throttle, DRS, and brake data from the DataFrame
    throttle_data = sped_point_df["Throttle"].tolist()
    drs_data = sped_point_df["DRS"].astype(int).tolist()
    brake_data = sped_point_df["Brake"].astype(bool).tolist()

    # Unpack the sector data from json_friendly_sector_packages
    sector_times, sector_end_frames, sector_delta_times = json_friendly_sector_packages

    driver_data_dict = {
        "img_file_path": str(driver_image_path),
        "output_dir_path": f"output/driver_widgets/{driver.last_name}",
        "color": driver_applied_color,
        "position": driver.position,
        "num_frames": len(sped_point_df),
        "throttle": throttle_data,
        "is_brake": brake_data,
        "is_drs": drs_data,
        "sector_times": sector_times,
        "sector_end_frames": sector_end_frames,
        "sector_delta_times": sector_delta_times,
    }

    json_file_path = f"output/driver_widgets/{driver.last_name}.json"
    with open(json_file_path, "w") as f:
        json.dump(driver_data_dict, f, indent=4)

    print(f"Saved driver data to {json_file_path}")
    return json_file_path


def process_driver(
    driver,
    gimp_path,
    driver_run_data,
    driver_applied_color,
    json_friendly_sector_packages,
    headless,
):
    """Process a single driver - to be run in parallel"""
    json_path = add_driver_dash_data(
        driver,
        driver_run_data,
        driver_applied_color,
        json_friendly_sector_packages[driver],
    )
    return open_in_gimp(gimp_path, json_path, headless=headless)


def add_widgets_main(config: Config, app_state: AppState):
    gimp_path = "dev/DriverWidget.xcf"

    load_data = app_state.load_data
    assert load_data is not None

    run_drivers = load_data.run_drivers
    sector_packages = process_sector_times.process_sector_times(run_drivers)
    json_friendly_sector_packages: dict[
        Driver, tuple[list[str], list[int], list[str]]
    ] = {}
    for driver, (
        sector_times,
        end_frames,
        time_slower_than_fastest_in_sector,
    ) in sector_packages.items():
        new_sector_times: list[str] = [
            f"{int(sector_time.total_seconds() // 60)}:{sector_time.total_seconds() % 60:05.3f}"
            for sector_time in sector_times
        ]
        new_time_slower_than_fastest_in_sector: list[str] = [
            f"{int(time.total_seconds() // 60)}:{time.total_seconds() % 60:05.3f}"
            for time in time_slower_than_fastest_in_sector
        ]

        json_friendly_sector_packages[driver] = (
            new_sector_times,
            end_frames,
            new_time_slower_than_fastest_in_sector,
        )

    # Delete output/driver_widgets directory and recreate it
    output_dir = "output/driver_widgets"
    if os.path.exists(output_dir):
        import shutil

        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    drivers = run_drivers.drivers
    driver_applied_colors = run_drivers.driver_applied_colors
    # Determine optimal number of processes (can be adjusted based on your system)
    max_workers = min(len(drivers), os.cpu_count() or 4)
    print(f"Starting parallel processing with {max_workers} workers")

    is_headless = not config["dev_settings"]["ui_mode"]

    # Use ThreadPoolExecutor to process drivers in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks to the executor
        future_to_driver = {
            executor.submit(
                process_driver,
                driver,
                gimp_path,
                run_drivers.driver_run_data[driver],
                driver_applied_colors[driver],
                json_friendly_sector_packages,
                is_headless,
            ): driver
            for driver in drivers
        }

        # Wait for all tasks to complete and collect results
        for future in as_completed(future_to_driver):
            driver = future_to_driver[future]
            try:
                result = future.result()
                print(
                    f"Completed processing driver: {driver.last_name}, result: {result}"
                )
            except Exception as exc:
                print(
                    f"Processing for driver {driver.last_name} generated an exception: {exc}"
                )

    print("All drivers have been processed")
