import os
import subprocess
from pathlib import Path

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent

    os.environ["PYTHONPATH"] = (
        f"{project_root}:{project_root}/py:{os.environ.get('PYTHONPATH', '')}"
    )

    cmd = ["blender"]

    cmd.extend(
        [
            "--python",
            f"{project_root}/src/modules/video_edit/video_edit_blender_entry.py",
            "--",
            str(project_root / "assets" / "dev" / "config.json"),
            str(project_root / "assets" / "dev" / "app_state.pkl"),
        ]
    )

    subprocess.run(cmd, check=True)
