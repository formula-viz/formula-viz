from typing import Any, List, Optional

# Define a dynamic class that accepts any attribute access
class DynamicAttribute:
    def __getattr__(self, name: str) -> "DynamicAttribute": ...
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...
    def __setattr__(self, name: str, value: Any) -> None: ...
    def __getitem__(self, key: Any) -> Any: ...
    def __setitem__(self, key: Any, value: Any) -> None: ...

# Base structure class
class bpy_struct(DynamicAttribute):
    pass

# Base ID class for all Blender ID types
class ID(bpy_struct):
    name: str
    name_full: str
    library: Optional["Library"]
    is_library_indirect: bool
    preview: Any
    tag: bool
    use_fake_user: bool
    users: int

# Forward references to Blender types
class Object(ID): ...
class Camera(ID): ...
class Scene(ID): ...
class Material(ID): ...
class Mesh(ID): ...
class Light(ID): ...
class Collection(ID): ...
class Region(bpy_struct): ...
class RegionView3D(bpy_struct): ...
class Area(bpy_struct): ...
class ViewLayer(bpy_struct): ...
class Library(ID): ...
class SequenceEditor(bpy_struct): ...

# Types class that contains all type classes as attributes
class Types:
    Object: Any
    Camera: type[Camera]
    Scene: type[Scene]
    Material: type[Material]
    Mesh: type[Mesh]
    Light: type[Light]
    Collection: type[Collection]
    Region: type[Region]
    RegionView3D: type[RegionView3D]
    Area: type[Area]
    ViewLayer: type[ViewLayer]
    ID: type[ID]
    bpy_struct: type[bpy_struct]
    Library: type[Library]
    SequenceEditor: type[SequenceEditor]
    # Add more types here as needed
    def __getattr__(self, name: str) -> Any: ...

# Main module exports
class Context(bpy_struct):
    scene: Scene
    view_layer: ViewLayer
    space_data: Any
    area: Optional[Area]
    region: Optional[Region]
    region_data: Optional[RegionView3D]
    selected_objects: List[Object]
    active_object: Optional[Object]
    mode: str
    preferences: Any
    window: Any
    workspace: Any

    def __getattr__(self, name: str) -> Any: ...

class BlendData(bpy_struct):
    objects: Any
    cameras: Any
    lights: Any
    meshes: Any
    materials: Any
    scenes: Any
    collections: Any
    images: Any
    textures: Any
    node_groups: Any

    def __getattr__(self, name: str) -> Any: ...

class Operators(DynamicAttribute):
    object: Any
    mesh: Any
    material: Any
    render: Any
    scene: Any
    screen: Any
    file: Any
    export_scene: Any
    import_scene: Any
    wm: Any

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...
    def __getattr__(self, name: str) -> Any: ...

# Module-level attributes
context: Context
data: BlendData
ops: Operators
app: Any
utils: Any
path: Any
types: Types
props: Any
