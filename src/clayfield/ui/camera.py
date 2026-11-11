"""Orbit camera for the ClayField viewport."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from PySide6.QtGui import QMatrix4x4, QVector3D


@dataclass
class OrbitCamera:
    """Simple orbit camera with bounded zoom and elevation."""

    distance: float = 6.0
    azimuth: float = 35.0
    elevation: float = 28.0
    target: QVector3D = field(default_factory=QVector3D)

    def view_matrix(self) -> QMatrix4x4:
        matrix = QMatrix4x4()
        matrix.translate(0.0, 0.0, -self.distance)
        matrix.rotate(-self.elevation, 1.0, 0.0, 0.0)
        matrix.rotate(-self.azimuth, 0.0, 1.0, 0.0)
        matrix.translate(-self.target)
        return matrix

    def reset(self) -> None:
        self.distance, self.azimuth, self.elevation = 6.0, 35.0, 28.0

    def top_view(self) -> None:
        self.distance, self.azimuth, self.elevation = 6.0, 0.0, 89.0

    def front_view(self) -> None:
        self.distance, self.azimuth, self.elevation = 6.0, 0.0, 0.0

    def side_view(self) -> None:
        self.distance, self.azimuth, self.elevation = 6.0, 90.0, 0.0

    def isometric_view(self) -> None:
        self.distance, self.azimuth, self.elevation = 6.0, 35.0, 28.0

    def fit_distance(self, width: float, depth: float, height: float = 0.0, aspect: float = 1.0) -> None:
        """Choose a camera distance that contains the supplied model bounds."""
        radius = max(0.05, math.sqrt(width * width + depth * depth + height * height) / 40.0)
        vertical_half_angle = math.radians(22.5)
        horizontal_half_angle = math.atan(math.tan(vertical_half_angle) * max(aspect, 0.01))
        self.distance = max(0.1, radius * 1.1 / math.sin(min(vertical_half_angle, horizontal_half_angle)))

    def orbit(self, dx: float, dy: float) -> None:
        self.azimuth += dx * 0.35
        self.elevation = max(-85.0, min(85.0, self.elevation + dy * 0.35))

    def pan(self, dx: float, dy: float, viewport_height: float = 600.0) -> None:
        """Translate the camera target in view-plane world units."""
        scale = self.distance / max(1.0, viewport_height)
        azimuth, elevation = math.radians(self.azimuth), math.radians(self.elevation)
        right = QVector3D(math.cos(azimuth), 0.0, -math.sin(azimuth))
        up = QVector3D(math.sin(azimuth) * math.sin(elevation), math.cos(elevation), math.cos(azimuth) * math.sin(elevation))
        self.target += right * (-dx * scale) + up * (dy * scale)

    def zoom(self, steps: float) -> None:
        self.distance = max(0.1, min(10000.0, self.distance * (0.85 ** steps)))
