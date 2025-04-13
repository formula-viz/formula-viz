from src.modules.video_edit.thumbnails.base_thumbnail_process import ThumbnailProcess
from src.utils import file_utils


class TwoCarProcess(ThumbnailProcess):
    """Processes a two-car view thumbnail"""

    def __init__(self, config, app_state):
        raw_path = "output/two-car-thumbnail-raw.png"
        output_path = "output/two-car-thumbnail.png"
        super().__init__(config, app_state, raw_path, output_path)

    def _add_specific_elements(self):
        """Add elements specific to the two car thumbnail"""
        self._add_driver_image()

    def _add_driver_image(self):
        """Add the main driver image"""
        load_data = self.app_state.load_data
        assert load_data is not None
        focused_driver = load_data.run_drivers.focused_driver

        driver_img_path = file_utils.project_paths.get_driver_image_path(focused_driver)

        driver_image_strip = self.seq_editor.sequences.new_image(
            name="DriverImage",
            filepath=str(driver_img_path),
            channel=self.cur_channel,
            frame_start=1,
        )
        self.cur_channel += 1

        driver_image_strip.transform.offset_x = 370
        driver_image_strip.transform.offset_y = 0
        driver_image_strip.transform.scale_x = 1.3
        driver_image_strip.transform.scale_y = 1.3
