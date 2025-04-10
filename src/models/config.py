"""Casts the raw json configuration of the application into specific types for language server support."""

from typing import List, Literal, Optional, TypedDict, Union


class DevelopmentConfig(TypedDict):
    """Handles the conditional invocations of the separate modules."""

    ui_mode: bool
    quick_textures_mode: bool
    limited_frames_mode: bool
    thumbnail_mode: bool


class RenderConfig(TypedDict):
    """Handles the configuration of the final render / output."""

    engine: str
    fps: int
    samples: int
    is_both_mode: bool
    is_shorts_output: bool
    output: str
    start_buffer_frames: int
    end_buffer_frames: int
    auto_track_mode: bool


class YouTubeConfig(TypedDict):
    """YouTube-specific configuration settings."""

    client_secret_path: str
    visibility: Literal["public", "private", "unlisted"]
    publish_at: Optional[str]
    title: Optional[str]


class SocialsConfig(TypedDict):
    """Handles social media configuration for publishing the output."""

    title: str
    tags: List[str]
    thumbnail_path: Optional[str]
    youtube: Optional[YouTubeConfig]


class MixedConfig(TypedDict):
    """Handles mixed config, like 2025 Pole vs 2024 Pole."""

    enabled: bool
    title: str  # since the mixed config may be complicated, custom title
    drivers: list[
        dict[str, Union[str, int]]
    ]  # dict from driver name to year of the data we want


class PostProcessConfig(TypedDict):
    """Handles post-processing configuration for the output."""

    output: str
    music_fadeout_seconds: int


class Config(TypedDict):
    """Handles general configuration and holds the specific configuration classes.

    Contains general fields (track, year, type, drivers),
    development configuration (),
    render settings (engine, fps, output format),
    and social media publication settings.
    """

    track: str
    year: int
    session: str  # Q or SQ, for Qualifying or Sprint Qualifying
    type: Literal["head-to-head", "rest-of-field"]
    mixed_mode: MixedConfig
    dev_settings: DevelopmentConfig
    render: RenderConfig
    socials: SocialsConfig
    post_process: PostProcessConfig
    drivers: List[str]
