from src.models.config import Config


def get_base_config() -> Config:
    config = Config(
        track="SAUDI",
        year=2024,
        session="Q",
        type="head-to-head",
        sort_section="recap",
        drivers=["Verstappen", "Leclerc", "Perez", "Alonso"],
        mixed_mode={
            "enabled": False,
            "title": "How Verstappen beat Vettel's 2019 Suzuka Lap Record #f1",
            "drivers": [
                {"name": "Verstappen", "year": 2025, "session": "Q"},
                {"name": "Vettel", "year": 2019, "session": "Q"}
            ]
        },
        dev_settings={
            "ui_mode": False,
            "thumbnail_mode": False,
            "quick_textures_mode": False,
            "limited_frames_mode": False,
            "skip_render": False,
            "skip_gimp": False,
            "skip_load": False
        },
        render={
            "engine": "eevee",
            "fps": 30,
            "samples": 32,
            "is_both_mode": False,
            "is_shorts_output": False,
            "output": "render-output.mp4",
            "start_buffer_frames": 15,
            "end_buffer_frames": 55,
            "auto_track_mode": True
        },
        post_process={
            "output": "post-process-output.mp4",
            "music_fadeout_seconds": 5
        },
        socials={
            "title": "Saudi 2024 Quali Recap, Verstappen sets the Lap Record, beats Leclerc, Perez, & Alonso #f1",
            "tags": [],  # Empty list since not provided in the JSON
            "thumbnail_path": None,  # Not provided in the JSON
            "youtube": {
                "client_secret_path": "formula-viz-981f62016605.json",  # Note: Changed from service_account_path to match Config definition
                "visibility": "unlisted",
                "publish_at": None,
                "title": "Saudi 2024 Quali Recap, Verstappen sets the Lap Record, beats Leclerc, Perez, & Alonso #f1"
            }
        }
    )

    return config
