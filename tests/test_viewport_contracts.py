from pathlib import Path

RESOURCE_DIR = Path(__file__).parents[1] / "src" / "clayfield" / "resources"


def test_viewport_shaders_expose_height_coloring_contract():
    vertex = (RESOURCE_DIR / "test_grid.vert").read_text()
    fragment = (RESOURCE_DIR / "test_grid.frag").read_text()

    assert "out float surface_height" in vertex
    assert "uniform bool height_coloring" in fragment
    assert "uniform float height_min" in fragment
    assert "uniform float height_max" in fragment
    assert "surface_height" in fragment


def test_viewport_shaders_preserve_displacement_and_lighting_paths():
    vertex = (RESOURCE_DIR / "test_grid.vert").read_text()
    fragment = (RESOURCE_DIR / "test_grid.frag").read_text()

    assert "gpu_displacement" in vertex
    assert "height_texture" in vertex
    assert "lit_surface" in fragment
    assert "height_coloring" in fragment


def test_viewport_uses_physical_height_range_and_preview_limits():
    viewport = (Path(__file__).parents[1] / "src" / "clayfield" / "ui" / "viewport.py").read_text()

    assert "height_min_mm" in viewport
    assert "height_max_mm" in viewport
    assert "preview_limit = 512" in viewport
    assert "Height bounds must be finite" in viewport
    assert "Viewport dimensions must be finite and positive" in viewport
    assert "Heightfield values must be finite" in viewport
