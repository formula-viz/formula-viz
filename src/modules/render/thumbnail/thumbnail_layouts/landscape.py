import bpy
import math

from py.render.thumbnail.thumbnail_layouts.abstract_layout import LayoutConfigurer

class LandscapeConfigurer(LayoutConfigurer):
    def position_camera(self, camera_obj: bpy.types.Object):
        camera_obj.location = (-7.08, 23.16, 9.08)
        camera_obj.rotation_euler = (
            math.radians(73),
            math.radians(0),
            math.radians(-177),
        )

    def position_cars(self, cars: list[bpy.types.Object]) -> None:
        two_car_positions = [
            (-6.24, 8.65, 5.44),
            (-4, 8.93, 4.23),
        ]
        two_car_rotations = [
            (math.radians(0), math.radians(5), math.radians(-185)),
            (math.radians(0), math.radians(-8), math.radians(-175)),
        ]

        three_car_positions = [
            (-3.46, 8.31, 3.57),
            (-6.52, 9.63, 4.42),
            (-4.9, 9.23, 5.95),
        ]
        three_car_rotations = [
            (math.radians(0), math.radians(-9), math.radians(-172)),
            (0, math.radians(21), math.radians(-185)),
            (math.radians(-2), math.radians(-12), math.radians(-174)),
        ]

        # Set positions and rotations based on number of cars
        if len(cars) == 2:
            for i, car in enumerate(cars):
                car.location = two_car_positions[i]
                car.rotation_euler = two_car_rotations[i]
        else:
            for i, car in enumerate(cars):
                car.location = three_car_positions[i]
                car.rotation_euler = three_car_rotations[i]


    def position_formula_viz_car(self, formula_viz_car_obj: bpy.types.Object):
        formula_viz_car_obj.location = (-0.3, 0.13, -1)
        formula_viz_car_obj.scale = (0.01, 0.01, 0.01)
        formula_viz_car_obj.rotation_euler = (math.radians(-80), 0, 0)

    def position_driver_image(self, driver_plane: bpy.types.Object):
        driver_plane.location = (0.18, -0.04, -0.9)
        driver_plane.rotation_euler = (0, 0, 0)
        driver_plane.scale = (0.45, 0.45, 0.45)
