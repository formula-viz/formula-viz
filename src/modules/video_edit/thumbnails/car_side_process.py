from src.modules.video_edit.thumbnails.base_thumbnail_process import ThumbnailProcess
from src.utils import file_utils


class CarSideProcess(ThumbnailProcess):
    """Process a single car side view thumbnail of the focused driver."""

    def __init__(self, config, app_state):
        raw_path = "output/car-side-thumbnail-raw.png"
        output_path = "output/car-side-thumbnail.png"
        super().__init__(config, app_state, raw_path, output_path)

    def _add_specific_elements(self):
        """Add elements specific to the car side thumbnail"""
        self._add_driver_images()

    def _add_driver_images(self):
        """Add driver images based on configuration"""
        load_data = self.app_state.load_data
        assert load_data is not None

        if self.config["type"] == "head-to-head":
            drivers = load_data.run_drivers.drivers
            if len(drivers) == 2:
                # If there are 2 drivers in the head to head, then we want to have one image on the left, one on the right
                for i, driver in enumerate(drivers):
                    driver_image_path = file_utils.project_paths.get_driver_image_path(
                        driver
                    )

                    driver_image_strip = self.seq_editor.sequences.new_image(
                        name="DriverImage",
                        filepath=str(driver_image_path),
                        channel=self.cur_channel,
                        frame_start=1,
                    )
                    self.cur_channel += 1

                    driver_image_strip.transform.offset_x = -600 if i == 0 else 600
                    driver_image_strip.transform.offset_y = -180
                    driver_image_strip.transform.scale_x = 0.8
                    driver_image_strip.transform.scale_y = 0.8
