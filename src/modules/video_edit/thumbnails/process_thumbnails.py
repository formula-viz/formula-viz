from src.models.app_state import AppState
from src.models.config import Config
from src.modules.video_edit.thumbnails import car_side_process


def process_thumbnails(config: Config, app_state: AppState):
    car_side_process.CarSideProcess(config, app_state)
