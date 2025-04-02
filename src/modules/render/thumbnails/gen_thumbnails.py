from src.models.app_state import AppState
from src.models.config import Config
from src.modules.render.thumbnails.car_side import CarSideThumbnail


def gen_thumbnails(config: Config, state: AppState):
    car_side_thumbnail = CarSideThumbnail(config, state)
