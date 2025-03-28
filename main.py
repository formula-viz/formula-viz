"""Start Formula Viz rendering and publishing process."""

import os
import sys
from pathlib import Path

from src.pipeline import run_pipeline


def main():
    """Start Formula Viz rendering and publishing process."""
    project_root = Path(__file__).parent.absolute()

    os.environ["PYTHONPATH"] = (
        f"{project_root}:{project_root}/py:{os.environ.get('PYTHONPATH', '')}"
    )

    is_batch_mode = len(sys.argv) > 1 and sys.argv[1] == "batch"
    return run_pipeline(project_root, is_batch_mode)


if __name__ == "__main__":
    sys.exit(main())
