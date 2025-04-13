import math

import bpy

from src.modules.render.add_funcs.add_driver_objects import create_car_obj
from src.modules.render.thumbnails.base_thumbnail_renderer import BaseThumbnailRenderer


class CarSideThumbnail(BaseThumbnailRenderer):
    def _add_objects(self):
        load_data = self.state.load_data
        assert load_data is not None
        focused_driver = load_data.run_drivers.focused_driver

        driver_obj, _ = create_car_obj(focused_driver.team, focused_driver.last_name)

        driver_obj.location = (-126.8, 3.58, 91.79)
        driver_obj.rotation_euler = (
            math.radians(-4),
            math.radians(1),
            math.radians(-90),
        )

    def _add_camera(self):
        camera = bpy.data.cameras.new(name="CarSideThumbnail Camera")
        camera_obj = bpy.data.objects.new(
            name="CarSideThumbnail Camera", object_data=camera
        )
        bpy.context.scene.camera = camera_obj
        bpy.context.scene.collection.objects.link(camera_obj)

        camera_obj.location = (-130.2, 13.227, 95.456)
        camera_obj.rotation_euler = (
            math.radians(-105),
            math.radians(-180),
            math.radians(0),
        )
        camera.lens = 31
