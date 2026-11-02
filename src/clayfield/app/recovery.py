"""Autosave and recovery helpers for ClayField projects."""

from __future__ import annotations

import tempfile
import hashlib
import os
from pathlib import Path

from clayfield.app.project_io import ProjectIOError, autosave_project
from clayfield.app.project_state import ProjectState
from clayfield.field.persistence import SourceDescriptor


def recovery_directory() -> Path:
    """Return the per-user directory used for recovery snapshots."""
    directory = Path.home() / ".local" / "state" / "clayfield" / "recovery"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def recovery_path(project_path: Path | None) -> Path:
    """Return a stable recovery path for the active project."""
    if project_path is not None:
        resolved = str(project_path.expanduser().resolve())
        digest = hashlib.sha256(resolved.encode()).hexdigest()[:12]
        name = f"{project_path.stem}-{digest}"
    else:
        name = "untitled"
    return recovery_directory() / f"{name}.clayfield"


def write_recovery_snapshot(state: ProjectState) -> Path:
    """Write a recovery snapshot for a dirty project."""
    if not state.dirty:
        raise ProjectIOError("A dirty project is required for recovery")
    _validate_recoverable_source(state)
    target = recovery_path(state.project_path)
    fd, name = tempfile.mkstemp(prefix=".recovery-", suffix=".clayfield", dir=target.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        autosave_project(state, temporary)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def prepare_recovery_snapshot(state: ProjectState) -> tuple[Path, Path]:
    """Write a hidden snapshot for the GUI to publish only if still current."""
    _validate_recoverable_source(state)
    target = recovery_path(state.project_path)
    fd, name = tempfile.mkstemp(prefix=".pending-", suffix=".clayfield", dir=target.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        autosave_project(state, temporary)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return temporary, target


def _validate_recoverable_source(state: ProjectState) -> None:
    """Ensure autosave can persist either source kind."""
    if state.source_type == "image":
        if state.source_image is None or state.source_path is None:
            raise ProjectIOError("An image source requires pixels and a source path for recovery")
        return
    try:
        SourceDescriptor.from_dict(state.source_descriptor)
    except (TypeError, ValueError) as error:
        raise ProjectIOError(f"Invalid procedural source for recovery: {error}") from error


def discard_recovery_snapshot(project_path: Path | None) -> None:
    """Remove the recovery snapshot associated with a project."""
    recovery_path(project_path).unlink(missing_ok=True)


def find_recovery_snapshots() -> list[Path]:
    """Return available recovery snapshots, newest first."""
    directory = recovery_directory()
    snapshots = []
    for path in directory.glob("*.clayfield"):
        if path.name.startswith("."):
            continue
        try:
            snapshots.append((path.stat().st_mtime, path))
        except FileNotFoundError:
            continue
    return [path for _, path in sorted(snapshots, key=lambda item: item[0], reverse=True)]
