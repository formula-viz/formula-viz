import os
import subprocess


def open_in_gimp(file_path, driver_image_path, run_script=True):
    try:
        # Base command for Flatpak GIMP
        gimp_cmd = ["flatpak", "run", "org.gimp.GIMP", "--no-splash"]

        if run_script and driver_image_path:
            # Add Python-Fu script execution parameters and open the file
            gimp_cmd.extend(
                [
                    file_path,
                    "--batch-interpreter",
                    "python-fu-eval",
                    "-b",
                    f"import sys; sys.path.append('{os.path.abspath(os.path.dirname(os.path.dirname(file_path)))}'); from dev.gimp_processor import main; main('{os.path.abspath(driver_image_path)}')",
                ]
            )
        else:
            # Just open the file(s) without running script
            gimp_cmd.append(file_path)

        # Launch GIMP through Flatpak
        subprocess.Popen(gimp_cmd)

        if run_script and driver_image_path:
            print(
                f"Opening {file_path} in GIMP and importing {driver_image_path} with script"
            )
        else:
            print(
                f"Opening {file_path} in GIMP"
                + (f" with {driver_image_path}" if driver_image_path else "")
            )

        return True

    except Exception as e:
        print(f"Error launching GIMP: {e}")
        return False


if __name__ == "__main__":
    driver_image_path = "assets/images/driver-headshots/HAM-Ferrari-2025.png"
    file_path = "dev/DriverWidget.xcf"

    open_in_gimp(file_path, driver_image_path, run_script=True)
