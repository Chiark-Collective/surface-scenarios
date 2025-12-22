# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`surface-scenarios` is a standalone synthetic elevation and 3D SDF (Signed Distance Field) scenario library. It provides procedural generators, bundled manifests, and lightweight loaders that return pandas DataFrames plus analytic truth functions.

**PyPI package**: `surface-scenarios`
**Python import**: `survi_scenarios` (for compatibility)

## Commands

```bash
# Run tests
PYTHONPATH=src pytest tests -q

# Run a single test
PYTHONPATH=src pytest tests/test_synthetic.py::test_name -v

# Install in development mode
pip install -e .

# Install with mesh support (trimesh)
pip install -e ".[mesh]"

# Install with trenchfoot trench scenarios (requires Python 3.12+)
pip install -e ".[trenchfoot]"
```

## Architecture

### Two Surface Types

1. **Elevation surfaces (2.5D)**: Grid-based heightfields with (x, y, z) samples
   - Entry: `load_elevation_scenario(name)` → `ElevationSurface`
   - Truth function: `truth_z(xy_points)` for analytic elevation lookup

2. **SDF surfaces (3D)**: Signed distance field volumes with analytic distance functions
   - Entry: `load_sdf_scenario(name, seed)` → `SDFSurface`
   - Truth functions: `truth_phi(xyz_points)` for signed distance, `truth_normals(xyz_points)` for gradients

### Module Structure

- **`loaders.py`**: Public API - `list_*_scenarios()` and `load_*_scenario()` functions. Routes between manifest-defined scenarios and synthetic factories.

- **`synthetic.py`**: 2.5D surface generation via `SurfaceParams`. Supports slopes, ripples (single or multi-angle), Gaussian bumps, and noise. Outputs gridded DataFrames.

- **`synthetic_3d.py`**: 3D SDF primitives (`Sphere`, `Box`, `Torus`) with CSG operations (`Union`, `Intersection`, `Difference`). Pre-built factories: `make_asteroid_field`, `make_cave_network`, `make_canal_maze`, `make_torus`.

- **`suite.py`**: Manifest-based scenario configuration. `ScenarioSuite` loads JSON manifests; `Scenario` materializes configs into grids and sampled points.

- **`types.py`**: Core dataclasses `ElevationSurface` and `SDFSurface` - thin wrappers around samples DataFrame + truth callables.

- **`geom.py`**: Grid generation and nearest-neighbour lookups. Uses scipy.spatial.cKDTree when available.

- **`rng.py`**: Deterministic RNG via `numpy_rng(seed, namespace)`. Respects `SURVI_SEED` and `SURVI_DETERMINISTIC` env vars.

- **`trenchfoot_loader.py`**: Optional integration with the `trenchfoot` package. Loads trench mesh scenarios as `SDFSurface` objects using trimesh for SDF computation. Entry points: `list_trenchfoot_scenarios()`, `load_trenchfoot_scenario(name)`.

### Data Flow

```
JSON manifests (data/scenarios/, data/scenarios_3d/)
         ↓
    loaders.py (routing)
         ↓
    ┌────┴────┐
    ↓         ↓
suite.py   synthetic_3d.py
    ↓         ↓
synthetic.py  SDF primitives
    ↓         ↓
    └────┬────┘
         ↓
  ElevationSurface / SDFSurface
  (samples DataFrame + truth callables)
```

### Heightfield-to-SDF Bridge

`load_sdf_scenario()` can load elevation scenarios as SDF surfaces by building a trimesh from the heightfield. Requires the `[mesh]` optional dependency.

## Environment Variables

- `SURVI_SCENARIO_MANIFEST`: Override elevation suite manifest path
- `SURVI_SDF_MANIFEST`: Override SDF manifest path
- `SURVI_SEED`: Base seed for deterministic RNG
- `SURVI_DETERMINISTIC`: Enable deterministic mode (`1`/`true`/`yes`/`on`)

## Key Patterns

- All scenario configs are frozen dataclasses with `to_dict()`/`from_dict()` for JSON serialization
- Truth functions are closures that capture grid/factory state for analytic evaluation
- SDF nodes implement `phi(points)` and `gradient(points)` for distance and normal evaluation
- Manifests are cached via `@lru_cache` for repeated loads
