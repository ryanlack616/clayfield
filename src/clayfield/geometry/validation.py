"""Mesh validation for printable relief solids."""


from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sparse
import scipy.sparse.csgraph as csgraph
from clayfield.core.cancellation import check_cancelled

from clayfield.geometry.mesh_generator import SolidMesh


@dataclass(frozen=True)
class MeshValidation:
    """Validation report for a generated solid."""

    valid: bool
    watertight: bool
    positive_volume: bool
    finite_coordinates: bool
    bounds_mm: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    message: str
    winding_consistent: bool
    non_degenerate: bool
    edge_manifold: bool
    connected_components: int
    euler_number: int


def _edge_topology(
    vertices_count: int, faces: np.ndarray, cancel_check=None
) -> tuple[bool, bool, int, int]:
    """Return ``(edge_manifold, winding_consistent, components, euler)``.

    A per-edge Python dictionary over every triangle edge costs roughly 25
    times the mesh's own array storage at fabrication resolutions: a 4096x4096
    export has about 201 million directed edges, and each dictionary entry
    carries a tuple, a hash slot and a face index. That made the previous
    implementation need tens of gigabytes to validate a mesh it had just built
    in a couple of gigabytes. Encoding each undirected edge as one int64 key and
    grouping with ``np.unique`` plus a SciPy sparse graph keeps the working set
    proportional to the edge array itself, and lets the manifold, winding and
    connectivity checks share one pass instead of three.
    """
    face_count = len(faces)
    vertices_count = int(vertices_count)
    edge_pairs = np.empty((face_count * 3, 2), dtype=np.int64)
    edge_pairs[0::3, 0] = faces[:, 0]
    edge_pairs[0::3, 1] = faces[:, 1]
    edge_pairs[1::3, 0] = faces[:, 1]
    edge_pairs[1::3, 1] = faces[:, 2]
    edge_pairs[2::3, 0] = faces[:, 2]
    edge_pairs[2::3, 1] = faces[:, 0]
    # Record the traversal direction before sorting destroys it. A consistent
    # closed surface traverses each undirected edge once in each direction, so
    # the signed sum per edge is zero.
    forward = np.where(edge_pairs[:, 0] < edge_pairs[:, 1], 1, -1).astype(np.int8)
    edge_pairs.sort(axis=1)
    check_cancelled(cancel_check)
    edge_keys = edge_pairs[:, 0] * vertices_count + edge_pairs[:, 1]
    del edge_pairs
    unique_keys, inverse, edge_counts = np.unique(
        edge_keys, return_counts=True, return_inverse=True
    )
    del edge_keys
    edge_count = len(unique_keys)
    edge_manifold = bool(np.all(edge_counts == 2))
    # Watertight is the same predicate for a triangle mesh: no boundary edges.
    direction_sums = np.bincount(inverse, weights=forward, minlength=edge_count)
    winding_consistent = bool(np.all(np.abs(direction_sums) < 0.5))
    del direction_sums, edge_counts, forward
    euler_number = int(vertices_count - edge_count + face_count)
    check_cancelled(cancel_check)
    # Bipartite graph: faces and undirected edges are separate node sets. Every
    # manifold edge joins two faces, so bipartite components correspond
    # one-to-one with face components.
    face_ids = np.repeat(np.arange(face_count, dtype=np.int32), 3)
    edge_ids = inverse.astype(np.int32, copy=False)
    edge_ids += np.int32(face_count)
    graph = sparse.coo_matrix(
        (np.ones(len(face_ids), dtype=np.int8), (face_ids, edge_ids)),
        shape=(face_count + edge_count, face_count + edge_count),
    )
    del face_ids, edge_ids
    components, _ = csgraph.connected_components(graph, directed=False)
    return edge_manifold, winding_consistent, int(components), euler_number


def validate_mesh(mesh: SolidMesh, *, cancel_check=None) -> MeshValidation:
    """Validate topology, coordinates, volume, and physical bounds."""
    check_cancelled(cancel_check)
    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)
    finite = bool(np.isfinite(vertices).all())
    if vertices.ndim != 2 or vertices.shape[1] != 3 or faces.ndim != 2 or faces.shape[1] != 3 or not finite or len(vertices) == 0 or len(faces) == 0 or not np.issubdtype(faces.dtype, np.integer) or np.any(faces < 0) or np.any(faces >= len(vertices)):
        return MeshValidation(False, False, False, finite, ((0.0, 0.0),) * 3, "Invalid mesh arrays or non-finite coordinates", False, False, False, 0, 0)
    check_cancelled(cancel_check)
    bounds = tuple((float(low), float(high)) for low, high in zip(vertices.min(axis=0), vertices.max(axis=0)))
    # Signed volume and triangle areas are accumulated in face chunks. Expanding
    # all faces at once would create a second copy of the face array scaled by
    # nine floats, which at 4096x4096 is several gigabytes for no reason.
    volume = 0.0
    non_degenerate = True
    for start in range(0, len(faces), 65536):
        check_cancelled(cancel_check)
        stop = min(len(faces), start + 65536)
        triangles = vertices[faces[start:stop]].astype(np.float64)
        volume += float(np.einsum("ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])).sum() / 6.0)
        areas = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1)
        non_degenerate = non_degenerate and bool(np.isfinite(areas).all() and np.all(areas > 1e-9))
    positive_volume = bool(volume > 0.0)
    check_cancelled(cancel_check)
    edge_manifold, winding_consistent, connected_components, euler_number = _edge_topology(len(vertices), faces, cancel_check=cancel_check)
    watertight = edge_manifold
    check_cancelled(cancel_check)
    valid = watertight and winding_consistent and positive_volume and finite and non_degenerate and edge_manifold and connected_components == 1
    message = "Mesh is watertight and printable" if valid else "Mesh failed closure, manifoldness, winding, volume, connectivity, or degeneracy checks"
    return MeshValidation(valid, watertight, positive_volume, finite, bounds, message, winding_consistent, non_degenerate, edge_manifold, connected_components, euler_number)
