import bpy

from src.models.app_state import AppState
from src.models.config import Config
from src.modules.video_edit.thumbnails.car_side_process import CarSideProcess
from src.modules.video_edit.thumbnails.two_car_process import TwoCarProcess


def process_thumbnails(config: Config, app_state: AppState):
    """Process all thumbnail types in sequence."""
    TwoCarProcess(config, app_state)

    # Clear all sequences before processing the next thumbnail
    for sequence in bpy.context.scene.sequence_editor.sequences_all:
        bpy.context.scene.sequence_editor.sequences.remove(sequence)

    CarSideProcess(config, app_state)
