import matplotlib.pyplot as plt
from survi_scenarios import load_elevation_scenario

names = [
    "flat_rect_small",
    "sloped_rotated_rect",
    "ripples_two_angles",
    "mountainous_600x400",
]

fig, axes = plt.subplots(2, 2, figsize=(10, 8))
for ax, name in zip(axes.ravel(), names):
    ds = load_elevation_scenario(name)
    grid = ds.samples.pivot(index="y", columns="x", values="z")
    im = ax.imshow(
        grid.values,
        origin="lower",
        extent=[grid.columns.min(), grid.columns.max(), grid.index.min(), grid.index.max()],
        cmap="viridis",
    )
    ax.set_title(name)

fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.65, label="z (m)")
plt.tight_layout()
plt.savefig("docs/scenario_panel.png", dpi=160)
