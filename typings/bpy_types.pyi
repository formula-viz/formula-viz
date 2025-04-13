from typing import Any, Generic, List, Optional, TypeVar, Union

T = TypeVar("T")

# Define a dynamic class that accepts any attribute access
class DynamicAttribute:
    def __getattr__(self, name: str) -> "DynamicAttribute": ...
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...
    def __setattr__(self, name: str, value: Any) -> None: ...
    def __getitem__(self, key: Any) -> Any: ...
    def __setitem__(self, key: Any, value: Any) -> None: ...

# Collection type for bpy_prop_collection
class PropertyCollection(Generic[T]):
    def __getitem__(self, key: Union[str, int]) -> T: ...
    def __iter__(self) -> Any: ...
    def __len__(self) -> int: ...
    def get(self, key: str, default: Optional[Any] = None) -> Optional[T]: ...
    def items(self) -> List[tuple[str, T]]: ...
    def keys(self) -> List[str]: ...
    def values(self) -> List[T]: ...
    def new(self, name: str = "", **kwargs: Any) -> T: ...
    def remove(self, item: T) -> None: ...
    def clear(self) -> None: ...
    def find(self, key: str) -> int: ...

# Base structure class
class bpy_struct(DynamicAttribute):
    pass

# Base ID class for all Blender ID types
class ID(bpy_struct):
    name: str
    name_full: str
    library: Any
    is_library_indirect: bool
    preview: Any
    tag: bool
    use_fake_user: bool
    users: int

# Scene class with common properties
class Scene(ID):
    render: "RenderSettings"
    collection: Any
    camera: Optional["Object"]
    display_settings: Any
    view_settings: Any
    cycles: Any
    sequence_editor: Optional["SequenceEditor"]

# RenderSettings class
class RenderSettings(bpy_struct):
    engine: str
    resolution_x: int
    resolution_y: int
    resolution_percentage: int
    filepath: str
    image_settings: Any
    file_format: str
    fps: int

class SequenceEditor(bpy_struct):
    sequences: Any
    active_strip: Any

# Object class
class Object(ID):
    location: tuple[float, float, float]
    rotation_euler: tuple[float, float, float]
    rotation_quaternion: tuple[float, float, float, float]
    scale: tuple[float, float, float]
    dimensions: tuple[float, float, float]
    data: Any
    type: str
    matrix_world: List[List[float]]
    parent: Optional["Object"]
    children: PropertyCollection["Object"]
    modifiers: PropertyCollection["Modifier"]

# Camera class
class Camera(ID):
    lens: float
    clip_start: float
    clip_end: float
    type: str  # 'PERSP', 'ORTHO', 'PANO'

# Light class and its subclasses
class Light(ID):
    type: str
    energy: float
    color: tuple[float, float, float]

class AreaLight(Light):
    shape: str
    size: float
    size_y: float

class PointLight(Light):
    shadow_soft_size: float

class SpotLight(Light):
    spot_size: float
    spot_blend: float
    show_cone: bool

class SunLight(Light):
    angle: float

# Mesh class
class Mesh(ID):
    vertices: Any
    edges: Any
    polygons: Any
    loops: Any
    materials: PropertyCollection["Material"]

# Material class
class Material(ID):
    use_nodes: bool
    node_tree: Optional["NodeTree"]
    diffuse_color: tuple[float, float, float, float]
    metallic: float
    roughness: float

# NodeTree class
class NodeTree(ID):
    nodes: Any
    links: Any

# Modifier class (base class for all modifiers)
class Modifier(bpy_struct):
    name: str
    type: str
    show_viewport: bool
    show_render: bool
    show_in_editmode: bool

# Area class
class Area(bpy_struct):
    type: str
    width: int
    height: int
    spaces: Any

# Region class
class Region(bpy_struct):
    type: str
    width: int
    height: int
    data: Any

# RegionView3D class
class RegionView3D(bpy_struct):
    view_matrix: List[List[float]]
    view_perspective: str
    is_perspective: bool

# Common blender collection types
class BlendDataObjects(PropertyCollection[Object]):
    pass

class BlendDataCameras(PropertyCollection[Camera]):
    pass

class BlendDataLights(PropertyCollection[Light]):
    pass

class BlendDataMeshes(PropertyCollection[Mesh]):
    pass

class BlendDataMaterials(PropertyCollection[Material]):
    pass

class BlendDataScenes(PropertyCollection[Scene]):
    pass
