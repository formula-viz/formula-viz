import pickle
import sys

import bpy

from src.models.track_data import TrackData


# Because the points were originally added by first placing all inner and then all outer,
# we can simply cut in half to separate them.
def extract_track_edges():
    track_obj = bpy.data.objects["MainTrack"]
    mesh = track_obj.data

    # Get total number of vertices
    total_verts = len(mesh.vertices)

    # Since inner vertices were added first, followed by outer vertices,
    # and they should have the same count, we can split them in half
    half_count = total_verts // 2

    # First half are inner vertices - convert to list[tuple[float, float, float]]
    inner_vertices = [
        (mesh.vertices[i].co.x, mesh.vertices[i].co.y, mesh.vertices[i].co.z)
        for i in range(half_count)
    ]

    # Second half are outer vertices - convert to list[tuple[float, float, float]]
    outer_vertices = [
        (mesh.vertices[i].co.x, mesh.vertices[i].co.y, mesh.vertices[i].co.z)
        for i in range(half_count, total_verts)
    ]

    # Validate that inner and outer vertices form pairs along the track
    print("\nValidating vertex pairs...")
    for i, (inner, outer) in enumerate(zip(inner_vertices, outer_vertices)):
        # Calculate the distance between corresponding inner and outer points
        inner_vec = mesh.vertices[i].co
        outer_vec = mesh.vertices[i + half_count].co
        distance = (inner_vec - outer_vec).length
        print(f"Pair {i}: Inner={inner}, Outer={outer}, Distance={distance:.2f}")

    return inner_vertices, outer_vertices


if __name__ == "__main__":
    inner_points, outer_points = extract_track_edges()
    track_data = TrackData(inner_points, None, outer_points, None, None, None)

    filepath = sys.argv[-1]
    with open(filepath, "wb") as f:
        pickle.dump(track_data, f)
