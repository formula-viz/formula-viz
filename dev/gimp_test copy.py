import os
import subprocess
import sys


def open_in_gimp(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        return False

    try:
        subprocess.Popen(["gimp", file_path])
        print(f"Opening {file_path} in GIMP")
        return True
    except Exception as e:
        print(f"Error launching GIMP: {e}")
        return False


# Example usage
if __name__ == "__main__":
    # If a file path is provided as a command line argument, use it
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Otherwise use a default path
        file_path = "dev/DriverWidget.xcf"

    open_in_gimp(file_path)
