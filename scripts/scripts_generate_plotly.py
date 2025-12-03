import numpy as np
import plotly.graph_objects as go
from pathlib import Path
from survi_scenarios import load_elevation_scenario, load_sdf_scenario
from plotly.subplots import make_subplots

OUT = Path("docs")
OUT.mkdir(exist_ok=True)

# Elevation surfaces --------------------------------------------------------
for name, outfile in [
    ("mountainous_600x400", OUT / "elev_mountainous.png"),
    ("alpine_ridge_long", OUT / "elev_alpine.png"),
]:
    ds = load_elevation_scenario(name)
    grid = ds.samples.pivot(index="y", columns="x", values="z")
    xs = grid.columns.to_numpy()
    ys = grid.index.to_numpy()
    Z = grid.to_numpy()
    fig = go.Figure(
        go.Surface(x=xs, y=ys, z=Z, colorscale="Viridis", showscale=True)
    )
    fig.update_layout(title=name, scene=dict(xaxis_title="x", yaxis_title="y", zaxis_title="z"))
    fig.write_image(str(outfile), scale=2)
    print(f"wrote {outfile}")

# SDF isosurfaces -----------------------------------------------------------
def make_iso(name: str, outfile: Path, grid_res: int = 36, band: float = 0.0):
    sdf = load_sdf_scenario(name, seed=0)
    low, high = sdf.bounds
    low = np.asarray(low, dtype=float)
    high = np.asarray(high, dtype=float)
    xs = np.linspace(low[0], high[0], grid_res)
    ys = np.linspace(low[1], high[1], grid_res)
    zs = np.linspace(low[2], high[2], grid_res)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="xy")
    pts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    phi = sdf.truth_phi(pts).reshape(X.shape)
    fig = go.Figure(
        go.Isosurface(
            x=X.ravel(),
            y=Y.ravel(),
            z=Z.ravel(),
            value=phi.ravel(),
            isomin=band,
            isomax=band,
            caps=dict(x_show=False, y_show=False, z_show=False),
            surface_count=1,
            colorscale="RdBu",
        )
    )
    fig.update_layout(title=f"Isosurface: {name}", scene=dict(xaxis_title="x", yaxis_title="y", zaxis_title="z"))
    fig.write_image(str(outfile), scale=2)
    print(f"wrote {outfile}")

for name, outfile, res in [
    ("torus_compact", OUT / "sdf_torus.png", 40),
    ("cave_network_dense", OUT / "sdf_cave.png", 32),
]:
    make_iso(name, outfile, grid_res=res)

# Combined 2x2 panel -------------------------------------------------------
fig = make_subplots(
    rows=2,
    cols=2,
    specs=[[{"type": "surface"}, {"type": "surface"}],
           [{"type": "scene"}, {"type": "scene"}]],
    subplot_titles=["mountainous_600x400", "alpine_ridge_long", "torus_compact iso", "cave_network_dense iso"],
)

# elevation panels
for idx, name in enumerate(["mountainous_600x400", "alpine_ridge_long"], start=1):
    ds = load_elevation_scenario(name)
    grid = ds.samples.pivot(index="y", columns="x", values="z")
    xs = grid.columns.to_numpy()
    ys = grid.index.to_numpy()
    Z = grid.to_numpy()
    fig.add_trace(go.Surface(x=xs, y=ys, z=Z, colorscale="Viridis", showscale=False), row=1, col=idx)

# sdf panels
for (name, row_col) in [("torus_compact", (2, 1)), ("cave_network_dense", (2, 2))]:
    sdf = load_sdf_scenario(name, seed=0)
    low, high = sdf.bounds
    low = np.asarray(low, dtype=float)
    high = np.asarray(high, dtype=float)
    xs = np.linspace(low[0], high[0], 38)
    ys = np.linspace(low[1], high[1], 38)
    zs = np.linspace(low[2], high[2], 38)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="xy")
    pts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    phi = sdf.truth_phi(pts).reshape(X.shape)
    fig.add_trace(
        go.Isosurface(
            x=X.ravel(),
            y=Y.ravel(),
            z=Z.ravel(),
            value=phi.ravel(),
            isomin=0.0,
            isomax=0.0,
            caps=dict(x_show=False, y_show=False, z_show=False),
            surface_count=1,
            colorscale="RdBu",
            showscale=False,
        ),
        row=row_col[0],
        col=row_col[1],
    )

fig.update_layout(height=900, width=1100, title="Plotly panel: elevation + SDF isosurfaces")
fig.write_image(str(OUT / "plotly_panel.png"), scale=2)
print("wrote", OUT / "plotly_panel.png")
