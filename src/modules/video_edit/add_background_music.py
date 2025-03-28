from pathlib import Path

import bpy


def add_background_music(
    audio_path: str | Path,
    channel: int,
    scene_end_frame: int,
    start_frame: int = 1,
    volume: float = 1.0,
    fade_out_seconds: float = 5.0,
):
    """Add background music to the sequence editor with fade out at scene end.

    Args:
        audio_path: Path to the audio file
        channel: The VSE channel to place the audio strip in
        scene_end_frame: Frame where the scene ends
        start_frame: Frame to start the audio (default: 1)
        volume: Volume multiplier (default: 1.0)
        fade_out_seconds: Duration of fade out in seconds (default: 5.0)

    Returns:
        The created sound sequence strip

    """
    # Convert string path to Path object if needed
    audio_path = Path(audio_path) if isinstance(audio_path, str) else audio_path

    # Validate inputs
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if channel < 1:
        raise ValueError("Channel must be 1 or greater")

    # Ensure we have a sequence editor
    scene = bpy.context.scene
    if not scene.sequence_editor:
        scene.sequence_editor_create()

    # Add the sound strip
    sound_strip = scene.sequence_editor.sequences.new_sound(
        name="Background Music",
        filepath=str(audio_path),
        channel=channel,
        frame_start=start_frame,
    )

    # Set initial volume
    sound_strip.volume = volume

    # Cut the strip to scene length
    sound_strip.frame_final_end = scene_end_frame

    # Calculate fade out frames
    fps = scene.render.fps
    fade_out_frames = int(fade_out_seconds * fps)
    fade_start_frame = scene_end_frame - fade_out_frames

    # Set keyframes for fade out
    sound_strip.volume = volume
    sound_strip.keyframe_insert(data_path="volume", frame=fade_start_frame)
    sound_strip.volume = 0
    sound_strip.keyframe_insert(data_path="volume", frame=scene_end_frame)

    # Set F-Curve interpolation to smooth the fade
    fcurves = scene.animation_data.action.fcurves
    for fc in fcurves:
        if fc.data_path == 'sequence_editor.sequences_all["Background Music"].volume':
            for kf in fc.keyframe_points:
                kf.interpolation = "BEZIER"
                kf.easing = "AUTO"
