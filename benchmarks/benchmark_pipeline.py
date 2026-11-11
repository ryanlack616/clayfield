"""Reproducible local image/mesh timing and peak-RSS benchmark."""

import argparse
import platform
import resource
import time

import numpy as np

from clayfield.geometry.estimates import estimate_solid_mesh
from clayfield.geometry.mesh_generator import generate_solid_mesh
from clayfield.image.pipeline import AdjustmentCache


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-size", type=int, default=2048)
    parser.add_argument("--mesh-size", type=int, default=1024)
    args = parser.parse_args()
    if min(args.image_size, args.mesh_size) < 2:
        parser.error("sizes must be at least 2")
    image = np.random.default_rng(17).random((args.image_size, args.image_size), dtype=np.float32)
    cache = AdjustmentCache()
    points = [(0.0, 0.0), (0.4, 0.6), (1.0, 1.0)]
    start = time.perf_counter()
    cache.apply(image, {"Brightness": 0.1, "Blur": 1.0}, points)
    cold = time.perf_counter() - start
    start = time.perf_counter()
    cache.apply(image, {"Brightness": 0.1, "Blur": 1.2}, points)
    warm = time.perf_counter() - start
    source = np.resize(image, (args.mesh_size, args.mesh_size))
    start = time.perf_counter()
    mesh = generate_solid_mesh(source, 100, 100, 5)
    mesh_time = time.perf_counter() - start
    estimate = estimate_solid_mesh(args.mesh_size, args.mesh_size)
    print(f"Host: {platform.system()} {platform.machine()}, Python {platform.python_version()}")
    print(f"Image {image.shape}: cold {cold:.3f}s; blur-only edit {warm:.3f}s")
    print(f"Mesh {source.shape}: {len(mesh.faces):,} triangles in {mesh_time:.3f}s")
    print(
        f"Mesh working-set estimate: {estimate.working_mebibytes:.1f} MiB; process peak RSS: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.1f} MiB"
    )


if __name__ == "__main__":
    main()
