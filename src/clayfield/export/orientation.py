"""Convert ClayField's Y-up coordinates to a slicer's Z-up build plate."""

import numpy as np

from clayfield.geometry.mesh_generator import SolidMesh


def orient_for_print(mesh: SolidMesh) -> SolidMesh:
    """Rotate a solid without reflection and place its bottom at Z=0 mm."""
    source = mesh.vertices
    vertices = np.empty_like(source)
    vertices[:, 0] = source[:, 0] - source[:, 0].min()
    vertices[:, 1] = source[:, 2].max() - source[:, 2]
    vertices[:, 2] = source[:, 1] - source[:, 1].min()
    return SolidMesh(vertices, mesh.faces)
