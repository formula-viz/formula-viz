import bpy

from src.models.app_state import AppState
from src.models.config import Config
from src.modules.video_edit.thumbnails import car_side_process, two_car_process


def process_thumbnails(config: Config, app_state: AppState):
    car_side_process.CarSideProcess(config, app_state)
    for sequence in bpy.context.scene.sequence_editor.sequences_all:
        bpy.context.scene.sequence_editor.sequences.remove(sequence)
    two_car_process.TwoCarProcess(config, app_state)
