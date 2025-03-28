"""Add a timer to the bottom right, showing the time elapsed since the start."""

import bpy
from mathutils import Vector

from src.models.config import Config
from src.utils import file_utils
from src.utils.logger import log_info


class RaceTimer:
    """Add a timer to the bottom right, showing the time elapsed since the start."""

    def __init__(self, config: Config, camera_obj: bpy.types.Object, num_frames: int):
        """Add a timer to the bottom right, showing the time elapsed since the start."""
        log_info("Initializing RaceTimer...")
        self.config = config
        self.camera_obj = camera_obj
        self.start_frame = config["render"]["start_buffer_frames"]
        self.num_frames = num_frames

        self._create_parent_empty()

        # Create a collection to store all timer text objects
        self.timer_collection = bpy.data.collections.new("Timer_Frames")
        bpy.context.scene.collection.children.link(self.timer_collection)  # pyright: ignore

        self._create_all_frame_timers(self.parent_empty)
        self._parent_to_camera(self.camera_obj, self.parent_empty)

    def _create_parent_empty(self):
        # Create empty parent object for camera-relative positioning
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))  # pyright: ignore
        active_obj = bpy.context.active_object
        if not active_obj:
            raise TypeError(
                "Failed to create parent empty: Active object is not a valid Blender Object"
            )

        self.parent_empty = active_obj

        # ensure the parent empty is not rendered and invisible in viewport
        self.parent_empty.hide_render = True
        self.parent_empty.hide_viewport = True
        self.parent_empty.name = "TimerParent"

    def _create_timer(self, frame_num: int, text: str):
        """Create a text object to display the race timer."""
        # Create text object
        timer_curve = bpy.data.curves.new(name=f"Timer_{frame_num}", type="FONT")
        timer_obj = bpy.data.objects.new(
            name=f"Timer_{frame_num}", object_data=timer_curve
        )
        self.timer_collection.objects.link(timer_obj)  # pyright: ignore
        text_curve = timer_obj.data
        if not isinstance(text_curve, bpy.types.TextCurve):
            raise TypeError("Expected TextCurve, got {}".format(type(text_curve)))

        text_curve.body = text
        text_curve.align_x = "LEFT"
        text_curve.align_y = "CENTER"
        text_curve.font = bpy.data.fonts.load(str(file_utils.project_paths.IMPACT_FONT))
        text_curve.size = 0.04

        # Create bright white material
        mat = bpy.data.materials.new(name=f"TimerMaterial_{frame_num}")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes  # pyright: ignore
        # Set to pure white with emission for extra brightness
        nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 1, 1, 1)  # pyright: ignore
        # 26 and 27 are emission
        nodes["Principled BSDF"].inputs[26].default_value = (1, 1, 1, 1)  # pyright: ignore
        nodes["Principled BSDF"].inputs[27].default_value = 0.5  # pyright: ignore

        # Assign material to text
        text_curve.materials.append(mat)  # pyright: ignore

        return timer_obj

    def _create_all_frame_timers(self, parent_empty: bpy.types.Object):
        """Create a text object for each frame with visibility animation."""
        for frame in range(0, self.num_frames + 1):
            # Calculate time text for current frame
            if frame <= self.start_frame:
                text = "0:00.000"
            else:
                elapsed_frames = frame - self.start_frame
                elapsed_time = elapsed_frames / self.config["render"]["fps"]

                minutes = int(elapsed_time // 60)
                seconds = int(elapsed_time % 60)
                milliseconds = int((elapsed_time % 1) * 1000)

                text = f"{minutes}:{seconds:02d}.{milliseconds:03d}"

            # Create timer object for this frame
            timer_obj = self._create_timer(frame, text)
            timer_obj.parent = parent_empty

            # Set visibility keyframes
            timer_obj.hide_viewport = True
            timer_obj.hide_render = True
            timer_obj.keyframe_insert(data_path="hide_viewport", frame=0)  # pyright: ignore
            timer_obj.keyframe_insert(data_path="hide_render", frame=0)  # pyright: ignore

            timer_obj.hide_viewport = False
            timer_obj.hide_render = False
            timer_obj.keyframe_insert(data_path="hide_viewport", frame=frame)  # pyright: ignore
            timer_obj.keyframe_insert(data_path="hide_render", frame=frame)  # pyright: ignore

            timer_obj.hide_viewport = True
            timer_obj.hide_render = True
            timer_obj.keyframe_insert(data_path="hide_viewport", frame=frame + 1)  # pyright: ignore
            timer_obj.keyframe_insert(data_path="hide_render", frame=frame + 1)  # pyright: ignore

    def _parent_to_camera(
        self, camera_obj: bpy.types.Object, timer_obj: bpy.types.Object
    ) -> None:
        """Parent the leaderboard to the camera."""
        timer_obj.parent = camera_obj

        if self.config["render"]["is_shorts_output"]:
            position = (-0.04, -0.15, -1)
        else:
            position = (0.25, -0.18, -1)

        timer_obj.location = Vector(position)
        timer_obj.rotation_euler = camera_obj.rotation_euler
