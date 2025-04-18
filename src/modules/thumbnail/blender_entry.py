import os
import pickle
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(project_root)

from src.modules.thumbnail.abstract import ThumbnailInput
from src.modules.thumbnail.implementations.finish_line import FinishLine


def main():
    pickle_path = sys.argv[-1]
    with open(pickle_path, "rb") as f:
        thumbnail_input: ThumbnailInput = pickle.load(f)

    temp = FinishLine(thumbnail_input)

    if thumbnail_input.should_render:
        temp.setup_scene()
        temp.render()

    if thumbnail_input.should_post_process:
        temp.setup_post_process()
        if not thumbnail_input.ui_mode:
            temp.post_process_run()


if __name__ == "__main__":
    main()
