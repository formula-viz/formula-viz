from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from src.models.driver import Driver
from src.utils import file_utils
from src.utils.logger import log_info


class ThumbnailType(Enum):
    """Enum for different types of thumbnails"""

    FINISH_LINE = auto()
    CAR_SIDE = auto()
    SIMULATED_SCREENSHOT = auto()


class ImageMode(Enum):
    """Enum for different image modes (subtypes) in thumbnails.

    Refers to the number of driver images placed in the overlay.
    This determines the positioning of the cars and the scene.
    """

    NO_IMAGE = auto()
    ONE_IMAGE = auto()
    TWO_IMAGES = auto()


@dataclass
class ThumbnailInput:
    ui_mode: bool
    should_render: bool
    should_post_process: bool
    image_mode: ImageMode

    drivers: list[Driver]
    driver_for_img_one: Driver
    driver_for_img_two: Driver


class ThumbnailAbstract(ABC):
    """Abstract base class for thumbnail generators.

    Each thumbnail type supports different image modes as subtypes.
    Subclasses must implement setup_scene method.
    """

    def __init__(self, thumbnail_input: ThumbnailInput, thumbnail_type: ThumbnailType):
        """Initialize the thumbnail generator."""
        self.render_output_path: str = str(
            file_utils.project_paths.OUTPUT_DIR
            / f"render-{thumbnail_type.name}-{thumbnail_input.image_mode.name}.png"
        )
        self.final_output_path: str = str(
            file_utils.project_paths.OUTPUT_DIR / "thumbnail.png"
        )
        self.thumbnail_type = thumbnail_type
        self.image_mode = thumbnail_input.image_mode
        self.thumbnail_input = thumbnail_input

    @abstractmethod
    def setup_scene(self):
        """Set up the scene, does not trigger the actual render. This is used for previewing in UI Mode.

        Each thumbnail class will have a blender file which is used as the template for the
        thumbnail, and will include the track, lighting, etc.
        """
        pass

    @abstractmethod
    def render(self):
        """Render the thumbnail image."""
        pass

    def post_process_run(self):
        import bpy

        scene = bpy.context.scene
        scene.render.filepath = self.final_output_path
        scene.render.image_settings.file_format = "PNG"
        scene.render.resolution_percentage = 80

        bpy.ops.render.render(animation=False, write_still=True)
        log_info(f"Thumbnail post-processed and saved to {self.final_output_path}")

    def setup_post_process(self):
        """Post-process the rendered image."""
        import bpy

        # Clear any existing VSE sequences
        bpy.context.scene.sequence_editor_clear()

        # Create a new sequence editor if it doesn't exist
        if not bpy.context.scene.sequence_editor:
            bpy.context.scene.sequence_editor_create()

        # Add the rendered image to the sequence editor
        sequences = bpy.context.scene.sequence_editor.sequences
        sequences.new_image(
            name="ThumbnailImage",
            filepath=self.render_output_path,
            channel=1,
            frame_start=1,
        )

        formula_viz_car_path = file_utils.project_paths.FORMULA_VIZ_ICON_CIRCLED_BASE
        formula_viz_car_strip = sequences.new_image(
            name="FormulaVizCar",
            filepath=str(formula_viz_car_path),
            channel=2,
            frame_start=1,
        )
        formula_viz_car_strip.transform.scale_x = 0.2
        formula_viz_car_strip.transform.scale_y = 0.2
        formula_viz_car_strip.transform.offset_x = -733
        formula_viz_car_strip.transform.offset_y = 306

        # Set the sequence length to match the image
        scene = bpy.context.scene
        scene.frame_start = 1
        scene.frame_end = 1

        if self.image_mode == ImageMode.ONE_IMAGE:
            driver_one_img_path = file_utils.project_paths.get_driver_image_path(
                self.thumbnail_input.driver_for_img_one
            )
            driver_one_img_strip = sequences.new_image(
                name="DriverOneImage",
                filepath=str(driver_one_img_path),
                channel=3,
                frame_start=1,
            )
            driver_one_img_strip.transform.scale_x = 1.3
            driver_one_img_strip.transform.scale_y = 1.3
            driver_one_img_strip.transform.offset_x = 420
            driver_one_img_strip.transform.offset_y = 0

        if self.image_mode == ImageMode.TWO_IMAGES:
            driver_one_img_path = file_utils.project_paths.get_driver_image_path(
                self.thumbnail_input.driver_for_img_one
            )
            driver_one_img_strip = sequences.new_image(
                name="driveroneimage",
                filepath=str(driver_one_img_path),
                channel=3,
                frame_start=1,
            )
            driver_one_img_strip.transform.scale_x = 1.1
            driver_one_img_strip.transform.scale_y = 1.1
            driver_one_img_strip.transform.offset_x = 504
            driver_one_img_strip.transform.offset_y = -81

            driver_two_img_path = file_utils.project_paths.get_driver_image_path(
                self.thumbnail_input.driver_for_img_two
            )
            driver_two_img_strip = sequences.new_image(
                name="drivertwoimage",
                filepath=str(driver_two_img_path),
                channel=4,
                frame_start=1,
            )
            driver_two_img_strip.transform.scale_x = 0.8
            driver_two_img_strip.transform.scale_y = 0.8
            driver_two_img_strip.transform.offset_x = -630
            driver_two_img_strip.transform.offset_y = -214

        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "None"
        scene.view_settings.gamma = 1.0

    def _eevee_render(self):
        """Incorporate all possible settings for Eevee rendering."""
        import bpy

        scene = bpy.data.scenes["Scene"]
        scene.render.engine = "BLENDER_EEVEE"  # type: ignore
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = self.render_output_path

        eevee = scene.eevee
        if not eevee:
            raise ValueError("Eevee settings not found")

        eevee.taa_render_samples = 64
        eevee.use_bloom = True  # type: ignore
        eevee.use_ssr = True  # type: ignore
        eevee.use_motion_blur = True  # type: ignore
        eevee.motion_blur_shutter = 0.5  # type: ignore
        eevee.shadow_cube_size = "4096"  # type: ignore
        eevee.shadow_cascade_size = "4096"  # type: ignore
        eevee.use_shadow_high_bitdepth = True  # type: ignore
        eevee.use_soft_shadows = True  # type: ignore
        scene.render.filter_size = 2.5
        scene.display_settings.display_device = "sRGB"  # type: ignore
        scene.view_settings.view_transform = "AgX"  # type: ignore
        scene.view_settings.look = "AgX - Base Contrast"  # type: ignore
        scene.view_settings.gamma = 0.95  # pyright: ignore

        bpy.ops.render.render(write_still=True)  # pyright: ignore
        log_info(f"Thumbnail rendered and saved to {self.render_output_path}")

    def _cycles_render(self):
        """Render the thumbnail image.

        Returns:
            The output path where the rendered image is saved.

        """
        log_info(f"Rendering thumbnail and saving to {self.render_output_path}")
        import bpy

        scene = bpy.context.scene
        if not scene:
            raise ValueError("No active scene found")

        scene.render.engine = "CYCLES"
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = self.render_output_path

        scene.display_settings.display_device = "sRGB"
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
        scene.view_settings.gamma = 0.95

        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.resolution_percentage = 100

        # GPU rendering
        scene.cycles.device = "GPU"
        bpy.context.preferences.addons[
            "cycles"
        ].preferences.compute_device_type = "CUDA"

        bpy.ops.render.render(write_still=True)
        log_info(f"Thumbnail rendered and saved to {self.render_output_path}")
