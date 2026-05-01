import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import seaborn as sns

# ── Colour constants ─────────────────────────────────────────────────────────
_NO_IMAGE  = "#2c2c2c"   # near-black  → tile not acquired on that date
_FULL      = "#27ae60"   # green       → all tiles clear
_PARTIAL   = "#e67e22"   # orange      → some tiles missing / too cloudy
_MISSING   = "#c0392b"   # red         → no usable tile at all


def plot_coverage_heatmap(coverage_results, max_cloud=20, satellite="Sentinel-2"):
    """
    Tile × Date heatmap showing cloud cover and per-date coverage status.

    Rows      = tile IDs (MGRS for Sentinel-2, WRS Path/Row for Landsat).
    Columns   = dates in the queried range.
    Cell colour:
        Green  → cloud % at or below the threshold (usable)
        Yellow → cloud % just above the threshold
        Red    → heavily cloudy
        ██ Dark / near-black → tile NOT acquired on that date (no pass)
    Status bar (top strip):
        Green = full coverage  |  Orange = partial  |  Red = missing
    """
    cov = [c for c in coverage_results if c.satellite == satellite]
    if not cov:
        print(f"No coverage data found for '{satellite}'.")
        return None

    all_tiles = sorted({t for c in cov for t in c.required_tiles})
    all_dates  = sorted({c.date for c in cov})
    n_tiles, n_dates = len(all_tiles), len(all_dates)

    # ── Cloud cover matrix (tiles × dates) ──────────────────────────────────
    matrix = pd.DataFrame(np.nan, index=all_tiles, columns=all_dates)
    for c in cov:
        for tr in c.tile_details:
            if tr.tile_id in matrix.index and tr.cloud_cover != -1:
                matrix.loc[tr.tile_id, c.date] = tr.cloud_cover

    # ── Status strip (1 × n_dates): 2 = full, 1 = partial, 0 = missing ─────
    _sv = {"full": 2, "partial": 1, "missing": 0}
    date_status = {c.date: _sv[c.status] for c in cov}
    status_row  = np.array([[date_status.get(d, 0) for d in all_dates]], dtype=float)

    n_full    = sum(1 for v in date_status.values() if v == 2)
    n_partial = sum(1 for v in date_status.values() if v == 1)
    n_missing = sum(1 for v in date_status.values() if v == 0)

    # ── Figure sizing ────────────────────────────────────────────────────────
    cell_w = max(0.40, min(1.1, 15 / n_dates))
    cell_h = max(0.30, min(0.70, 10 / n_tiles))
    fig_w  = max(13, n_dates * cell_w + 4)
    fig_h  = max(6,  n_tiles * cell_h + 4)

    fig, (ax_top, ax_main) = plt.subplots(
        2, 1,
        figsize=(fig_w, fig_h),
        gridspec_kw={"height_ratios": [1, n_tiles]},
        layout="constrained",
    )

    # ── Main heatmap colormap ────────────────────────────────────────────────
    # RdYlGn_r: green (0 %) → yellow → red (100 %)
    # TwoSlopeNorm pins white at the cloud threshold so usable = green side.
    # Near-black (#2c2c2c) marks cells where no image was acquired at all.
    cmap = plt.cm.RdYlGn_r.copy()
    cmap.set_bad(_NO_IMAGE)
    vcenter = max(1, min(max_cloud, 99))
    norm    = mcolors.TwoSlopeNorm(vmin=0, vcenter=vcenter, vmax=100)

    annotate = (n_tiles * n_dates) <= 300   # skip numbers when grid is too dense

    sns.heatmap(
        matrix,
        ax=ax_main,
        cmap=cmap,
        norm=norm,
        linewidths=0.4,
        linecolor="#ffffff",
        annot=annotate,
        fmt=".0f",
        annot_kws={"size": 7, "color": "black"},
        cbar_kws={
            "shrink": 0.60,
            "aspect": 25,
            "pad": 0.02,
        },
    )

    # Label colorbar and mark the threshold with a dashed line
    cbar = ax_main.collections[0].colorbar
    cbar.set_label("Cloud Cover (%)", fontsize=9)
    cbar.ax.axhline(y=max_cloud, color="black", linestyle="--", linewidth=1.5)
    cbar.ax.text(
        1.25, max_cloud, f"← {max_cloud}% threshold",
        va="center", ha="left", fontsize=7.5, color="black",
        transform=cbar.ax.get_yaxis_transform(),
    )

    # If annotating, also write "—" in no-image cells so they are unambiguous
    if annotate:
        for i, tile in enumerate(all_tiles):
            for j, date in enumerate(all_dates):
                if pd.isna(matrix.loc[tile, date]):
                    ax_main.text(
                        j + 0.5, i + 0.5, "—",
                        ha="center", va="center",
                        fontsize=8, color="#aaaaaa", fontweight="bold",
                    )

    # X-axis: short date labels; bold green for fully covered dates
    full_dates  = {c.date for c in cov if c.status == "full"}
    date_labels = [pd.Timestamp(d).strftime("%b %d") for d in all_dates]
    ax_main.set_xticklabels(date_labels, rotation=45, ha="right", fontsize=8)
    for tick, date in zip(ax_main.get_xticklabels(), all_dates):
        if date in full_dates:
            tick.set_color("#1a6e1a")
            tick.set_fontweight("bold")

    ax_main.set_yticklabels(ax_main.get_yticklabels(), rotation=0, fontsize=8)
    ax_main.set_xlabel("Date  (bold green = fully covered)", fontsize=9, labelpad=5)
    ax_main.set_ylabel("Tile ID", fontsize=9, labelpad=5)

    # ── Status strip ─────────────────────────────────────────────────────────
    s_cmap = mcolors.ListedColormap([_MISSING, _PARTIAL, _FULL])
    s_norm = mcolors.BoundaryNorm([0, 1, 2, 3], 3)
    xlim   = ax_main.get_xlim()

    ax_top.imshow(
        status_row, aspect="auto",
        cmap=s_cmap, norm=s_norm,
        extent=[xlim[0], xlim[1], 0, 1],
    )
    ax_top.set_xlim(xlim)
    ax_top.set_yticks([0.5])
    ax_top.set_yticklabels(["Date\nstatus"], fontsize=8)
    ax_top.set_xticks([])
    for sp in ax_top.spines.values():
        sp.set_visible(False)

    # ── Legend (inside the status strip, right side) ─────────────────────────
    legend_patches = [
        mpatches.Patch(facecolor=_FULL,     label=f"Full — all {n_tiles} tiles ≤ {max_cloud}% cloud  ({n_full} dates)"),
        mpatches.Patch(facecolor=_PARTIAL,  label=f"Partial — some tiles cloudy or absent  ({n_partial} dates)"),
        mpatches.Patch(facecolor=_MISSING,  label=f"Missing — zero usable tiles  ({n_missing} dates)"),
        mpatches.Patch(facecolor=_NO_IMAGE, label="No image — satellite did not acquire this tile on that date"),
    ]
    ax_top.legend(
        handles=legend_patches,
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        fontsize=8,
        framealpha=0.95,
        edgecolor="#bbbbbb",
        handlelength=1.5,
        handleheight=1.2,
    )

    # ── Title ────────────────────────────────────────────────────────────────
    fig.suptitle(
        f"{satellite}  ·  Tile Coverage  ·  "
        f"{all_dates[0]} → {all_dates[-1]}  ·  "
        f"{n_tiles} tiles  ·  max cloud {max_cloud}%",
        fontsize=11, fontweight="bold",
    )

    return fig
