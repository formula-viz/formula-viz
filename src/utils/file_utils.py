"""Central class for all project paths and path-related utilities."""

from pathlib import Path

from src.models.config import Config
from src.models.driver import Driver


class FileUtils:
    """Central class for all project paths and path-related utilities."""

    def __init__(self):
        """Initialize project paths structure.

        Args:
            project_root: Optional override for project root directory

        """
        self.PROJECT_ROOT = Path(__file__).parent.parent.parent

        self.ASSETS_DIR = self.PROJECT_ROOT / "assets"
        self.OUTPUT_DIR = self.PROJECT_ROOT / "output"

        # assets children
        self.AUDIO_DIR = self.ASSETS_DIR / "audio"
        self.BLENDER_DIR = self.ASSETS_DIR / "blender"
        self.FONTS_DIR = self.ASSETS_DIR / "fonts"
        self.IMAGES_DIR = self.ASSETS_DIR / "images"
        self.TRACK_DATA_DIR = self.ASSETS_DIR / "track_data"

        self._init_resource_paths()

    def _init_resource_paths(self):
        """Initialize frequently accessed resource paths."""
        self.F1_GENERIC_CAR_BLEND_PATH = self.BLENDER_DIR / "f1-2024-generic.blend"
        self.CAR_PAINTS_DIR = (
            self.IMAGES_DIR / "generic_car-textures" / "alternate_textures"
        )
        self.FORMULA_VIZ_CAR_PATH = self.BLENDER_DIR / "formula-viz-car.blend"

        self.BACKGROUND_MUSIC_PATH = self.AUDIO_DIR / "lofi-hiphop-background.m4a"

        self.FORMULA_VIZ_ICON_PATH = (
            self.IMAGES_DIR / "formula-viz-icon" / "formula-viz-icon.png"
        )
        self.FORMULA_VIZ_ICON_TRANSPARENT_PATH = (
            self.IMAGES_DIR / "formula-viz-icon" / "formula-viz-icon-transparent.png"
        )
        self.FORMULA_VIZ_CIRCLE_ICON_PATH = (
            self.IMAGES_DIR / "formula-viz-icon" / "formula-viz-icon-circled.png"
        )

        self.MAIN_FONT = self.FONTS_DIR / "Formula1-Regular.ttf"
        self.BOLD_FONT = self.FONTS_DIR / "Formula1-Bold.ttf"
        self.IMPACT_FONT = self.FONTS_DIR / "Impact.ttf"

        # Social icons
        self.YOUTUBE_ICON_PATH = self.IMAGES_DIR / "social-icons" / "youtube.png"
        self.DISCORD_ICON_PATH = self.IMAGES_DIR / "social-icons" / "discord.webp"
        self.INSTAGRAM_ICON_PATH = self.IMAGES_DIR / "social-icons" / "instagram.png"
        self.TIKTOK_ICON_PATH = self.IMAGES_DIR / "social-icons" / "tiktok.webp"

    def get_render_output(self, config: Config) -> Path:
        """Get the path for the render output file.

        Args:
            config: Application configuration

        Returns:
            Path to the render output file

        """
        return self.OUTPUT_DIR / config["render"]["output"]

    def get_post_process_output(self, config: Config) -> Path:
        """Get the path for the post-processed output file.

        Args:
            config: Application configuration

        Returns:
            Path to the post-processed output file

        """
        return self.OUTPUT_DIR / config["post_process"]["output"]

    def get_driver_image_path(self, driver: Driver) -> Path:
        """Get the path to a driver's image.

        Args:
            driver: Driver object

        Returns:
            Path to the driver's image file

        """
        return (
            self.IMAGES_DIR
            / "driver-headshots"
            / f"{driver.abbrev}-{driver.team}-{driver.year}.png"
        )

    def get_track_file(self, year: str, track: str) -> str:
        """Get the filename for track data.

        Args:
            year: Year of the data
            track: Track name

        Returns:
            Filename for the track data CSV

        """
        return f"{year}_{track}.csv"

    @staticmethod
    def get_year_of_track_file(track_file: str) -> int:
        """Extract the year from a track filename.

        Args:
            track_file: Track filename

        Returns:
            Year as an integer

        """
        return int(track_file.split("_")[1].split(".")[0])

    def get_new_texture_image_path(self, blender_obj_name: str, hex_color: str) -> Path:
        """Get the path for a new texture image.

        Args:
            blender_obj_name: Name of the Blender object
            hex_color: Hexadecimal color code

        Returns:
            Path to the texture image

        """
        return (
            self.ASSETS_DIR
            / "blender"
            / "alternate_textures"
            / f"{blender_obj_name.split('-')[-1]}_{hex_color}.png"
        )


# Create a singleton instance for global access
project_paths = FileUtils()
