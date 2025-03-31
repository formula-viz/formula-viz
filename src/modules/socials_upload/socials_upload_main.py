from src.models.config import Config
from src.modules.socials_upload import youtube_upload
from src.utils import file_utils


def socials_upload_main(config: Config):
    final_vid_path = (
        file_utils.project_paths.OUTPUT_DIR / config["post_process"]["output"]
    )
    youtube_upload.main(config, str(final_vid_path))
