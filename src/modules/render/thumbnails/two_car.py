import math

import bpy

from src.modules.render.add_funcs.add_driver_objects import create_car_obj
from src.modules.render.thumbnails.base_thumbnail_renderer import BaseThumbnailRenderer


class TwoCarThumbnail(BaseThumbnailRenderer):
    def _add_objects(self):
        load_data = self.state.load_data
        assert load_data is not None
        run_drivers = load_data.run_drivers

        focused_driver = run_drivers.focused_driver
        secondary_driver = next(
            (driver for driver in run_drivers.drivers if driver != focused_driver), None
        )
        assert secondary_driver is not None

        focused_driver_obj, _ = create_car_obj(
            focused_driver.team, focused_driver.last_name
        )
        focused_driver_obj.location = (-126.8, 3.58, 91.85)
        focused_driver_obj.rotation_euler = (
            math.radians(-3.5),
            math.radians(0),
            math.radians(-90),
        )

        secondary_driver_obj, _ = create_car_obj(
            secondary_driver.team, secondary_driver.last_name
        )
        secondary_driver_obj.location = (-120.7, 0.48, 91.6)
        secondary_driver_obj.rotation_euler = (
            math.radians(-2.5),
            math.radians(0),
            math.radians(-84),
        )

    def _add_camera(self):
        camera = bpy.data.cameras.new(name="CarSideThumbnail Camera")
        camera_obj = bpy.data.objects.new(
            name="CarSideThumbnail Camera", object_data=camera
        )
        bpy.context.scene.camera = camera_obj
        bpy.context.scene.collection.objects.link(camera_obj)

        camera_obj.location = (-152.37, 7.6835, 99.377)
        camera_obj.rotation_euler = (
            math.radians(-103.56),
            math.radians(-180),
            math.radians(71.12),
        )
        camera.lens = 50
