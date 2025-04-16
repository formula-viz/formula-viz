import json
import os
import random
import subprocess

from dataclasses import dataclass


def open_in_gimp(file_path, pickle_path, run_script=True):
    try:
        # Base command for Flatpak GIMP
        gimp_cmd = ["flatpak", "run", "org.gimp.GIMP", "--no-splash"]

        if run_script and pickle_path:
            # Add Python-Fu script execution parameters and open the file
            gimp_cmd.extend(
                [
                    file_path,
                    "--batch-interpreter",
                    "python-fu-eval",
                    "-b",
                    f"import sys; sys.path.append('{os.path.abspath(os.path.dirname(os.path.dirname(file_path)))}'); from dev.gimp_processor import main; main('{os.path.abspath(pickle_path)}')",
                ]
            )
        else:
            # Just open the file(s) without running script
            gimp_cmd.append(file_path)

        # Launch GIMP through Flatpak
        subprocess.Popen(gimp_cmd)
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
    is_drs: list[bool]

def add_sample_driver_dash_data():
    driver_image_path = "assets/images/driver-headshots/LEC-Ferrari-2025.png"
    # Generate 100 random throttle values between 0 and 100
    throttle_data = [random.randint(0, 100) for _ in range(100)]
    # Generate 100 random DRS states (True or False)
    drs_data = [random.choice([True, False]) for _ in range(100)]
    brake_data = [random.choice([True, False]) for _ in range(100)]

    driver_dash_data = DriverDashData(
        img_file_path=driver_image_path,
        output_dir_path="output/driver_dash_sample",
        color="#DC3D22",
        position=3,
        num_frames=100,
        throttle=throttle_data,
        is_brake=brake_data,
        is_drs=drs_data,
    )

    # Convert the DriverDashData object to a dictionary
    driver_data_dict = {
        "img_file_path": driver_dash_data.img_file_path,
        "output_dir_path": driver_dash_data.output_dir_path,
        "color": driver_dash_data.color,
        "position": driver_dash_data.position,
        "num_frames": driver_dash_data.num_frames,
        "throttle": driver_dash_data.throttle,
        "is_brake": driver_dash_data.is_brake,
        "is_drs": driver_dash_data.is_drs,
    }

    # Define the file path for JSON
    json_file_path = "dev/sample_driver_data.json"

    # Save to JSON file
    with open(json_file_path, "w") as f:
        json.dump(driver_data_dict, f, indent=4)

    print(f"Saved driver data to {json_file_path}")
    return json_file_path


if __name__ == "__main__":
    file_path = "dev/DriverWidget.xcf"

    pickle_path = add_sample_driver_dash_data()

    open_in_gimp(file_path, pickle_path, run_script=True)
