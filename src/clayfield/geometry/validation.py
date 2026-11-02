"""Mesh validation for printable relief solids."""


from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh
from clayfield.app.cancellation import check_cancelled

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
    self_intersection_status: str = "not_checked"


def validate_mesh(mesh: SolidMesh, *, cancel_check=None) -> MeshValidation:
    """Validate topology, coordinates, volume, and physical bounds."""
    check_cancelled(cancel_check)
    vertices = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)
    finite = bool(np.isfinite(vertices).all())
    if vertices.ndim != 2 or vertices.shape[1] != 3 or faces.ndim != 2 or faces.shape[1] != 3 or not finite or len(vertices) == 0 or len(faces) == 0 or not np.issubdtype(faces.dtype, np.integer) or np.any(faces < 0) or np.any(faces >= len(vertices)):
        return MeshValidation(False, False, False, finite, ((0.0, 0.0),) * 3, "Invalid mesh arrays or non-finite coordinates", False, False, False, 0, 0)
    trimesh_mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    bounds = tuple((float(low), float(high)) for low, high in zip(*trimesh_mesh.bounds))
    watertight = bool(trimesh_mesh.is_watertight)
    check_cancelled(cancel_check)
    winding_consistent = bool(trimesh_mesh.is_winding_consistent)
    check_cancelled(cancel_check)
    positive_volume = bool(trimesh_mesh.volume > 0.0)
    check_cancelled(cancel_check)
    non_degenerate = bool(np.isfinite(trimesh_mesh.area_faces).all() and np.all(trimesh_mesh.area_faces > 1e-9))
    check_cancelled(cancel_check)
    edge_pairs = np.sort(np.concatenate((faces[:, (0, 1)], faces[:, (1, 2)], faces[:, (2, 0)]), axis=0), axis=1)
    _, edge_counts = np.unique(edge_pairs, axis=0, return_counts=True)
    edge_manifold = bool(np.all(edge_counts == 2))
    parent = np.arange(len(faces), dtype=np.intp)

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left, right):
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    edge_faces: dict[tuple[int, int], int] = {}
    for face_index, face in enumerate(faces):
        for edge in ((int(face[0]), int(face[1])), (int(face[1]), int(face[2])), (int(face[2]), int(face[0]))):
            key = tuple(sorted(edge))
            previous = edge_faces.get(key)
            if previous is None:
                edge_faces[key] = face_index
            else:
                union(face_index, previous)
    connected_components = len({find(index) for index in range(len(faces))})
    euler_number = int(trimesh_mesh.euler_number)
    check_cancelled(cancel_check)
    valid = watertight and winding_consistent and positive_volume and finite and non_degenerate and edge_manifold and connected_components == 1
    message = "Mesh is watertight and printable" if valid else "Mesh failed closure, manifoldness, winding, volume, connectivity, or degeneracy checks"
    return MeshValidation(valid, watertight, positive_volume, finite, bounds, message, winding_consistent, non_degenerate, edge_manifold, connected_components, euler_number)
