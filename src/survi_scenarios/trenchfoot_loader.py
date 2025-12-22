# ABOUTME: Loader for trenchfoot trench mesh scenarios as SDF surfaces.
# ABOUTME: Provides list/load functions for trenchfoot package integration.
"""Trenchfoot scenario loader integration.

Loads trench mesh scenarios from the trenchfoot package as SDFSurface objects.
Requires the [trenchfoot] optional dependency.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from .types import SDFSurface

_trenchfoot = None
_trimesh = None
_trenchfoot_import_error: Exception | None = None
_trimesh_import_error: Exception | None = None


def _ensure_trenchfoot() -> None:
    """Lazy import trenchfoot and trimesh."""
    global _trenchfoot, _trimesh, _trenchfoot_import_error, _trimesh_import_error

    if _trenchfoot_import_error is not None:
        raise _trenchfoot_import_error
    if _trimesh_import_error is not None:
        raise _trimesh_import_error

    if _trenchfoot is None:
        try:
            import trenchfoot as tf
            _trenchfoot = tf
        except ImportError as exc:
            err = ImportError(
                "trenchfoot is required for trench scenarios. "
                "Install with: pip install surface-scenarios[trenchfoot]"
            )
            err.__cause__ = exc
            _trenchfoot_import_error = err
            raise err

    if _trimesh is None:
        try:
            import trimesh
            _trimesh = trimesh
        except ImportError as exc:
            err = ImportError(
                "trimesh is required for trench scenarios. "
                "Install with: pip install surface-scenarios[trenchfoot]"
            )
            err.__cause__ = exc
            _trimesh_import_error = err
            raise err


def _get_scenarios_path() -> Path:
    """Get the path to bundled trenchfoot scenarios."""
    _ensure_trenchfoot()
    from importlib import resources
    # trenchfoot bundles scenarios in its package
    return Path(resources.files("trenchfoot") / "scenarios")


def list_trenchfoot_scenarios() -> list[str]:
    """List available trenchfoot scenario names.

    Returns:
        List of scenario names (e.g., ['S01_straight_vwalls', ...])

    Raises:
        ImportError: If trenchfoot is not installed.
    """
    _ensure_trenchfoot()
    scenarios_path = _get_scenarios_path()
    if not scenarios_path.exists():
        return []

    names = []
    for child in scenarios_path.iterdir():
        if child.is_dir() and (child / "trench_scene.obj").exists():
            names.append(child.name)
    return sorted(names)


def load_trenchfoot_scenario(
    name: str,
    *,
    mesh_variant: str = "trench_scene.obj",
) -> SDFSurface:
    """Load a trenchfoot scenario as an SDFSurface.

    The trenchfoot mesh is loaded via trimesh, and SDF values are computed
    using trimesh's proximity queries.

    Args:
        name: Scenario name (e.g., 'S01_straight_vwalls')
        mesh_variant: Which mesh file to load. Options:
            - 'trench_scene.obj' (default): Full scene mesh
            - 'meshes/trench_scene_culled.obj': Culled mesh variant

    Returns:
        SDFSurface with the mesh vertices as raw_surface and SDF truth functions.

    Raises:
        ImportError: If trenchfoot or trimesh is not installed.
        ValueError: If the scenario or mesh file is not found.
    """
    _ensure_trenchfoot()
    scenarios_path = _get_scenarios_path()
    scenario_dir = scenarios_path / name

    if not scenario_dir.exists():
        available = list_trenchfoot_scenarios()
        raise ValueError(
            f"Unknown trenchfoot scenario '{name}'. Available: {available}"
        )

    mesh_path = scenario_dir / mesh_variant
    if not mesh_path.exists():
        raise ValueError(
            f"Mesh file not found: {mesh_path}. "
            f"Available variants: trench_scene.obj, meshes/trench_scene_culled.obj"
        )

    mesh = _trimesh.load(str(mesh_path), force="mesh")

    # Ensure normals are consistent
    mesh.fix_normals()

    # Build surface dataframe from mesh vertices
    vertices = mesh.vertices
    vertex_normals = mesh.vertex_normals

    surface_df = pd.DataFrame({
        "x": vertices[:, 0],
        "y": vertices[:, 1],
        "z": vertices[:, 2],
        "nx": vertex_normals[:, 0],
        "ny": vertex_normals[:, 1],
        "nz": vertex_normals[:, 2],
        "is_surface": True,
        "source": f"trenchfoot:{name}",
    })

    # Compute bounds with padding
    padding = 0.15
    coords = vertices
    low = np.min(coords, axis=0) - padding
    high = np.max(coords, axis=0) + padding

    # Build SDF truth functions using trimesh proximity
    def _phi_fn(points: np.ndarray) -> np.ndarray:
        """Compute signed distance to mesh surface."""
        pts = np.asarray(points, dtype=float)
        closest_pts, distances, _ = _trimesh.proximity.closest_point(mesh, pts)
        distances = np.asarray(distances, dtype=float)

        # Determine sign based on whether points are inside or outside the mesh
        # Use ray casting to determine inside/outside
        contains = mesh.contains(pts)
        sign = np.where(contains, -1.0, 1.0)

        return distances * sign

    def _normals_fn(points: np.ndarray) -> np.ndarray:
        """Compute surface normals at closest points."""
        pts = np.asarray(points, dtype=float)
        closest_pts, _, tri_idx = _trimesh.proximity.closest_point(mesh, pts)
        tri_idx = np.asarray(tri_idx, dtype=int)

        # Get face normals at closest triangles
        normals = mesh.face_normals[np.clip(tri_idx, 0, mesh.face_normals.shape[0] - 1)].copy()

        # Flip normals for points inside the mesh
        delta = pts - closest_pts
        flip = np.sum(delta * normals, axis=1) < 0.0
        normals[flip] *= -1.0

        # Handle missing triangles
        missing = tri_idx < 0
        if np.any(missing):
            fallback = delta[missing]
            fallback_norm = np.linalg.norm(fallback, axis=1, keepdims=True)
            normals[missing] = fallback / np.clip(fallback_norm, 1e-9, None)

        return normals

    # Load metadata from scene.json if available
    metadata: dict = {
        "source": "trenchfoot",
        "scenario": name,
        "mesh_variant": mesh_variant,
        "mesh_path": str(mesh_path),
        "vertex_count": len(vertices),
        "face_count": len(mesh.faces),
    }

    scene_json = scenario_dir / "scene.json"
    if scene_json.exists():
        import json
        try:
            with scene_json.open("r", encoding="utf-8") as fh:
                spec = json.load(fh)
            metadata["scene_spec"] = spec
        except Exception:
            pass

    metrics_json = scenario_dir / "metrics.json"
    if metrics_json.exists():
        import json
        try:
            with metrics_json.open("r", encoding="utf-8") as fh:
                metrics = json.load(fh)
            metadata["metrics"] = metrics
        except Exception:
            pass

    return SDFSurface(
        name=name,
        raw_surface=surface_df,
        truth_phi=_phi_fn,
        truth_normals=_normals_fn,
        bounds=(low, high),
        description=f"Trenchfoot scenario '{name}' loaded as SDF surface.",
        metadata=metadata,
    )


__all__ = ["list_trenchfoot_scenarios", "load_trenchfoot_scenario"]
