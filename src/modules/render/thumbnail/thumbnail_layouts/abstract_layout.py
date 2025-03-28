from abc import ABC, abstractmethod
import bpy


class LayoutConfigurer(ABC):
    """Abstract base class for thumbnail layout configuration.

    This class defines the interface for positioning elements in a thumbnail scene.
    Concrete implementations must provide specific positioning logic for different
    output formats (standard, shorts, etc.).
    """

    @abstractmethod
    def position_camera(self, camera_obj: bpy.types.Object) -> None:
        """PosiLayoutConfigurertion the camera for the thumbnail and return the camera object.

        Args:
            camera_obj: The camera object to position

        """
        pass

    @abstractmethod
    def position_cars(self, cars: list[bpy.types.Object]) -> None:
        """Position the cars in the thumbnail scene.

        Args:
            cars: List of car objects to position
            drivers: List of Driver objects corresponding to the cars
            colors: List of color hex codes for the cars
        """
        pass

    @abstractmethod
    def position_formula_viz_car(self, formula_viz_car_obj: bpy.types.Object):
        """Position the Formula Viz logo car in the thumbnail scene.

        Args:
            camera: The camera object to parent the logo car to

        Returns:
            bpy.types.Object: The positioned Formula Viz car object
        """
        pass

    @abstractmethod
    def position_driver_image(self, driver_plane: bpy.types.Object):
        """Position the driver image in the thumbnail scene.

        Args:
            camera: The camera object to parent the driver image to
            driver: The Driver object whose image will be displayed

        Returns:
            bpy.types.Object: The positioned driver image object
        """
        pass
