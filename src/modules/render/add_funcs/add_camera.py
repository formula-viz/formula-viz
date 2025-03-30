"""Create a camera that tracks the driver.

Follows a path which is a scaled version of the driver's path, accounted for correct distance.
"""

import bpy
import mathutils
import pandas as pd
from pandas import DataFrame, Series

from src.models.config import Config

MIN_CAM_DISTANCE = 70
MAX_CAM_DISTANCE = 70


def scale_frames(df_for_cam: DataFrame):
    """Scales the camera positions based on the input DataFrame.

    Args:
        df_for_cam (DataFrame): DataFrame containing position data (X, Y, Z)

    Returns:
        DataFrame: A new DataFrame with scaled X and Y coordinates and fixed Z height

    """
    scale_factor = 0.8
    z_up = 50

    df_for_cam_x = df_for_cam["X"].astype(float)
    df_for_cam_y = df_for_cam["Y"].astype(float)
    df_for_cam_z = df_for_cam["Z"].astype(float)

    cam_x: Series[float] = df_for_cam_x * scale_factor
    cam_y: Series[float] = df_for_cam_y * scale_factor
    cam_z: Series[float] = df_for_cam_z * scale_factor

    cam_x = cam_x + df_for_cam_x.mean() - cam_x.mean()  # pyright: ignore
    cam_y = cam_y + df_for_cam_y.mean() - cam_y.mean()  # pyright: ignore
    cam_z = cam_z + df_for_cam_z.mean() - cam_z.mean() + z_up  # pyright: ignore

    return pd.DataFrame({"X": cam_x, "Y": cam_y, "Z": cam_z})


def move_with_min_max_distance(cam_df: DataFrame, car_df: DataFrame) -> DataFrame:
    """Adjust camera position to maintain a distance from the car between min_distance and max_distance.

    Args:
        cam_df (DataFrame): DataFrame containing camera position data (X, Y, Z)
        car_df (DataFrame): DataFrame containing car position data (X, Y, Z)

    Returns:
        DataFrame: A new camera DataFrame with adjusted positions

    """
    assert len(cam_df) == len(car_df)

    # Extract values from DataFrames
    cam_xs = cam_df["X"].astype(float)
    cam_ys = cam_df["Y"].astype(float)
    cam_zs = cam_df["Z"].astype(float)

    car_xs = car_df["X"].astype(float)
    car_ys = car_df["Y"].astype(float)
    car_zs = car_df["Z"].astype(float)

    # Create new arrays to store adjusted positions
    new_cam_xs = []
    new_cam_ys = []
    new_cam_zs = []

    for i in range(len(cam_df)):
        cam_x = cam_xs.iloc[i]
        cam_y = cam_ys.iloc[i]
        cam_z = cam_zs.iloc[i]

        car_x = car_xs.iloc[i]
        car_y = car_ys.iloc[i]
        car_z = car_zs.iloc[i]

        cam_point = (cam_x, cam_y, cam_z)
        car_point = (car_x, car_y, car_z)

        vector = mathutils.Vector(cam_point) - mathutils.Vector(car_point)

        # Determine adjusted camera position
        if vector.length > MAX_CAM_DISTANCE:
            new_x = float(car_x + vector.normalized().x * MAX_CAM_DISTANCE)
            new_y = float(car_y + vector.normalized().y * MAX_CAM_DISTANCE)
            new_z = float(car_z + vector.normalized().z * MAX_CAM_DISTANCE)
        elif vector.length < MIN_CAM_DISTANCE:
            new_x = float(car_x + vector.normalized().x * MIN_CAM_DISTANCE)
            new_y = float(car_y + vector.normalized().y * MIN_CAM_DISTANCE)
            new_z = float(car_z + vector.normalized().z * MIN_CAM_DISTANCE)
        else:
            # Keep original position if distance is within range
            new_x = cam_x
            new_y = cam_y
            new_z = cam_z

        # Append adjusted values to new arrays
        new_cam_xs.append(new_x)
        new_cam_ys.append(new_y)
        new_cam_zs.append(new_z)

    # Create a completely new DataFrame with the same length
    new_cam_df = pd.DataFrame({"X": new_cam_xs, "Y": new_cam_ys, "Z": new_cam_zs})
    # Verify the new DataFrame has the expected length
    assert len(new_cam_df) == len(car_df)

    return new_cam_df


def add_keyframes(
    config: Config,
    camera_obj: bpy.types.Object,
    cam_df: DataFrame,
    driver_df: DataFrame,
    start_buffer_frames: int,
    end_buffer_frames: int,
):
    """Add keyframes to animate a camera following a driver object.

    Before the car is actually on the run, after hitting the start/finish and before hitting it again,
    the camera will point at the line, providing a visual indication for the viewer that the run hasn't started.

    Args:
        camera_obj (Object): The Blender camera object to animate
        cam_df (DataFrame): DataFrame containing camera position data (X, Y, Z)
        driver_df (DataFrame): DataFrame containing driver position data (X, Y, Z)
        start_buffer_frames (int): Number of frames at the start before the main animation begins
        end_buffer_frames (int): Number of frames at the end after the main animation ends

    """
    assert len(cam_df) == len(driver_df)

    cam_xs = cam_df["X"].astype(float)
    cam_ys = cam_df["Y"].astype(float)
    cam_zs = cam_df["Z"].astype(float)

    driver_xs = driver_df["X"].astype(float)
    driver_ys = driver_df["Y"].astype(float)
    driver_zs = driver_df["Z"].astype(float)

    # iterate through rows of df
    for i in range(len(cam_df)):
        frame = i + 1

        # Use proper type casting to fix diagnostic errors
        cam_x = cam_xs.iloc[i]
        cam_y = cam_ys.iloc[i]
        cam_z = cam_zs.iloc[i]
        camera_point = (cam_x, cam_y, cam_z)

        if frame <= len(cam_df) - end_buffer_frames:
            # for shorts mode, we don't want to point at the start line at the beginning,
            # shorts viewers may want to see the cars from the start to have a good indication of the
            # content of the video
            look_at_point = mathutils.Vector(
                (driver_xs.iloc[i], driver_ys.iloc[i], driver_zs.iloc[i])
            )
        elif frame < start_buffer_frames:
            idx = start_buffer_frames - 1
            look_at_point = mathutils.Vector(
                (driver_xs.iloc[idx], driver_ys.iloc[idx], driver_zs.iloc[idx])
            )
        else:  # frame > end_buffer_frames
            idx = len(cam_df) - end_buffer_frames - 1
            camera_point = (cam_xs.iloc[idx], cam_ys.iloc[idx], cam_zs.iloc[idx])
            look_at_point = mathutils.Vector(
                (driver_xs.iloc[idx], driver_ys.iloc[idx], driver_zs.iloc[idx])
            )

        camera_obj.location = mathutils.Vector(camera_point)
        camera_obj.keyframe_insert(data_path="location", frame=frame)  # pyright: ignore

        direction = look_at_point - camera_obj.location
        rot_quat = direction.to_track_quat("-Z", "Y")

        camera_obj.rotation_mode = "QUATERNION"
        camera_obj.rotation_quaternion = rot_quat
        camera_obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)  # pyright: ignore


def main(
    config: Config,
    df_for_cam: DataFrame,
    start_buffer_frames: int,
    end_buffer_frames: int,
):
    """Create a camera that tracks the driver.

    Args:
        df_for_cam (DataFrame): DataFrame containing position data used for camera path
        driver_obj (Object): The Blender object that the camera will follow/look at
        start_buffer_frames (int): Number of frames at the start before the main animation begins
        end_buffer_frames (int): Number of frames at the end after the main animation ends

    Returns:
        Object: The created camera object

    """
    camera_collection = bpy.data.collections.new(name="CameraCollection")

    bpy.context.scene.collection.children.link(camera_collection)  # pyright: ignore
    bpy.context.view_layer.active_layer_collection = (  # pyright: ignore
        bpy.context.view_layer.layer_collection.children[-1]  # pyright: ignore
    )

    camera_data = bpy.data.cameras.new(name="VideoCamera")
    camera_obj = bpy.data.objects.new(name="VideoCamera", object_data=camera_data)
    bpy.context.collection.objects.link(camera_obj)  # pyright: ignore

    cam_df = scale_frames(df_for_cam)
    cam_df = move_with_min_max_distance(cam_df, df_for_cam)

    add_keyframes(
        config, camera_obj, cam_df, df_for_cam, start_buffer_frames, end_buffer_frames
    )

    bpy.context.scene.camera = camera_obj  # pyright: ignore
    return camera_obj
