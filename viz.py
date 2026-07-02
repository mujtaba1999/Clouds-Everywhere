import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import seaborn as sns

# ── Palette ───────────────────────────────────────────────────────────────────
_NO_IMAGE = "#d0d0d0"   # light grey   → tile not acquired
_FULL     = "#2ecc71"   # green        → all tiles clear
_PARTIAL  = "#f39c12"   # amber        → some tiles missing / too cloudy
_MISSING  = "#e74c3c"   # red          → no usable tile at all

_STYLE = {
    "font.family":      "DejaVu Sans",
    "axes.facecolor":   "#fafafa",
    "figure.facecolor": "white",
    "axes.grid":        False,
    "axes.spines.top":  False,
    "axes.spines.right":False,
}


# ── 1. Tile × Date heatmap ────────────────────────────────────────────────────

def plot_coverage_heatmap(coverage_results, max_cloud=20, satellite="Sentinel-2"):
    """
    Tile × Date grid showing cloud cover per tile.

    Rows    = tile IDs   |   Columns = dates
    Colour  = cloud cover % (green → usable, red → cloudy, grey → no pass)
    Top strip shows per-date coverage status (full / partial / missing).
    """
    cov = [c for c in coverage_results if c.satellite == satellite]
    if not cov:
        print(f"No coverage data for '{satellite}'.")
        return None

    all_tiles = sorted({t for c in cov for t in c.required_tiles})
    all_dates = sorted({c.date for c in cov})
    n_tiles, n_dates = len(all_tiles), len(all_dates)

    # cloud cover matrix
    matrix = pd.DataFrame(np.nan, index=all_tiles, columns=all_dates)
    for c in cov:
        for tr in c.tile_details:
            if tr.tile_id in matrix.index and tr.cloud_cover != -1:
                matrix.loc[tr.tile_id, c.date] = tr.cloud_cover

    # status strip
    _sv = {"full": 2, "partial": 1, "missing": 0}
    date_status = {c.date: _sv[c.status] for c in cov}
    status_row  = np.array([[date_status.get(d, 0) for d in all_dates]], dtype=float)

    n_full    = sum(1 for v in date_status.values() if v == 2)
    n_partial = sum(1 for v in date_status.values() if v == 1)
    n_missing = sum(1 for v in date_status.values() if v == 0)

    # figure sizing
    cell_w = max(0.45, min(1.2, 16 / max(n_dates, 1)))
    cell_h = max(0.35, min(0.75, 10 / max(n_tiles, 1)))
    fig_w  = max(14, n_dates * cell_w + 5)
    fig_h  = max(6,  n_tiles * cell_h + 3)

    with plt.rc_context(_STYLE):
        fig, (ax_top, ax_main) = plt.subplots(
            2, 1,
            figsize=(fig_w, fig_h),
            gridspec_kw={"height_ratios": [1.4, n_tiles]},
            layout="constrained",
        )

        # ── main heatmap ─────────────────────────────────────────────────────
        cmap = plt.cm.RdYlGn_r.copy()
        cmap.set_bad(_NO_IMAGE)
        vcenter = max(1, min(max_cloud, 99))
        norm    = mcolors.TwoSlopeNorm(vmin=0, vcenter=vcenter, vmax=100)

        annotate = (n_tiles * n_dates) <= 250

        sns.heatmap(
            matrix,
            ax=ax_main,
            cmap=cmap,
            norm=norm,
            linewidths=0.5,
            linecolor="white",
            annot=annotate,
            fmt=".0f",
            annot_kws={"size": 7.5, "color": "#333333", "weight": "bold"},
            cbar_kws={"shrink": 0.55, "aspect": 22, "pad": 0.02},
        )

        # colorbar styling
        cbar = ax_main.collections[0].colorbar
        cbar.set_label("Cloud cover (%)", fontsize=9, labelpad=8)
        cbar.ax.tick_params(labelsize=8)
        cbar.ax.axhline(y=max_cloud, color="#333", linestyle="--", linewidth=1.8)
        cbar.ax.text(
            1.35, max_cloud, f"← {max_cloud}%",
            va="center", ha="left", fontsize=8, color="#333",
            transform=cbar.ax.get_yaxis_transform(),
        )

        # dash in no-image cells
        if annotate:
            for i, tile in enumerate(all_tiles):
                for j, date in enumerate(all_dates):
                    if pd.isna(matrix.loc[tile, date]):
                        ax_main.text(
                            j + 0.5, i + 0.5, "—",
                            ha="center", va="center",
                            fontsize=8, color="#aaaaaa",
                        )

        # x-axis labels — bold green on fully covered dates
        full_dates_set = {c.date for c in cov if c.status == "full"}
        labels = [pd.Timestamp(d).strftime("%b %d") for d in all_dates]
        ax_main.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        for tick, date in zip(ax_main.get_xticklabels(), all_dates):
            if date in full_dates_set:
                tick.set_color("#1a7a3a")
                tick.set_fontweight("bold")

        ax_main.set_yticklabels(ax_main.get_yticklabels(), rotation=0, fontsize=8.5)
        ax_main.set_xlabel("Date  (bold = fully covered)", fontsize=9, labelpad=6)
        ax_main.set_ylabel("Tile ID", fontsize=9, labelpad=6)

        # ── status strip ─────────────────────────────────────────────────────
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
        ax_top.set_yticklabels(["Status"], fontsize=9, fontweight="bold")
        ax_top.set_xticks([])
        for sp in ax_top.spines.values():
            sp.set_visible(False)
        ax_top.set_facecolor("white")

        # legend
        patches = [
            mpatches.Patch(facecolor=_FULL,     label=f"Full — all {n_tiles} tiles clear  ({n_full}d)"),
            mpatches.Patch(facecolor=_PARTIAL,  label=f"Partial — some tiles cloudy  ({n_partial}d)"),
            mpatches.Patch(facecolor=_MISSING,  label=f"Missing — zero usable tiles  ({n_missing}d)"),
            mpatches.Patch(facecolor=_NO_IMAGE, label="No pass — satellite didn't image this tile"),
        ]
        ax_top.legend(
            handles=patches,
            loc="center left",
            bbox_to_anchor=(1.01, 0.5),
            fontsize=8.5,
            framealpha=0.0,
            edgecolor="none",
            handlelength=1.4,
            handleheight=1.3,
        )

        fig.suptitle(
            f"{satellite}  ·  Tile Coverage  ·  "
            f"{all_dates[0]} → {all_dates[-1]}  ·  "
            f"{n_tiles} tiles  ·  ≤{max_cloud}% cloud threshold",
            fontsize=11, fontweight="bold", y=1.01,
        )

    return fig


# ── 2. Cloud % timeline per tile ──────────────────────────────────────────────

def plot_cloud_timeline(coverage_results, max_cloud=20, satellite="Sentinel-2"):
    """
    Line chart: cloud cover % for each tile over the date range.
    A shaded band marks the usable zone (≤ max_cloud %).
    Gaps where no image exists appear as breaks in the line.
    """
    cov = [c for c in coverage_results if c.satellite == satellite]
    if not cov:
        print(f"No coverage data for '{satellite}'.")
        return None

    all_tiles = sorted({t for c in cov for t in c.required_tiles})
    all_dates = sorted({c.date for c in cov})
    n_tiles   = len(all_tiles)

    matrix = pd.DataFrame(np.nan, index=all_tiles, columns=all_dates)
    for c in cov:
        for tr in c.tile_details:
            if tr.tile_id in matrix.index and tr.cloud_cover != -1:
                matrix.loc[tr.tile_id, c.date] = tr.cloud_cover

    dates_ts = pd.to_datetime(all_dates)

    with plt.rc_context(_STYLE):
        fig_h = max(4, min(3 + n_tiles * 0.35, 12))
        fig, ax = plt.subplots(figsize=(14, fig_h))

        palette = plt.cm.tab20.colors
        for i, tile in enumerate(all_tiles):
            vals = matrix.loc[tile].values.astype(float)
            color = palette[i % len(palette)]
            ax.plot(dates_ts, vals, marker="o", markersize=4,
                    linewidth=1.4, color=color, label=tile, zorder=3)

        # usable zone band
        ax.axhspan(0, max_cloud, alpha=0.08, color="#2ecc71", zorder=0)
        ax.axhline(max_cloud, color="#2ecc71", linewidth=1.5,
                   linestyle="--", label=f"{max_cloud}% threshold", zorder=2)

        ax.set_ylim(0, 100)
        ax.set_xlim(dates_ts[0], dates_ts[-1])
        ax.set_ylabel("Cloud cover (%)", fontsize=10)
        ax.set_xlabel("Date", fontsize=10)
        ax.tick_params(axis="x", rotation=35, labelsize=8)
        ax.tick_params(axis="y", labelsize=9)

        ax.legend(
            loc="upper left",
            bbox_to_anchor=(1.01, 1),
            fontsize=8,
            title="Tile ID",
            title_fontsize=9,
            framealpha=0.9,
            edgecolor="#dddddd",
        )

        fig.suptitle(
            f"{satellite}  ·  Cloud cover per tile  ·  "
            f"{all_dates[0]} → {all_dates[-1]}",
            fontsize=11, fontweight="bold",
        )
        fig.tight_layout()

    return fig


# ── 3. Satellite comparison bar chart ─────────────────────────────────────────

def plot_satellite_comparison(coverage_results, max_cloud=20):
    """
    Grouped bar chart: for each satellite, how many dates are full / partial / missing.
    """
    satellites = sorted({c.satellite for c in coverage_results})
    if not satellites:
        return None

    counts = {s: {"full": 0, "partial": 0, "missing": 0} for s in satellites}
    for c in coverage_results:
        counts[c.satellite][c.status] += 1

    x       = np.arange(len(satellites))
    width   = 0.25
    labels  = ["full", "partial", "missing"]
    colors  = [_FULL, _PARTIAL, _MISSING]

    with plt.rc_context(_STYLE):
        fig, ax = plt.subplots(figsize=(max(6, len(satellites) * 2.5), 5))

        for i, (status, color) in enumerate(zip(labels, colors)):
            vals = [counts[s][status] for s in satellites]
            bars = ax.bar(x + (i - 1) * width, vals, width,
                          color=color, label=status.capitalize(), zorder=3)
            for bar, v in zip(bars, vals):
                if v:
                    ax.text(bar.get_x() + bar.get_width() / 2,
                            bar.get_height() + 0.15, str(v),
                            ha="center", va="bottom", fontsize=9, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(satellites, fontsize=10)
        ax.set_ylabel("Number of dates", fontsize=10)
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        ax.legend(fontsize=9, framealpha=0.9, edgecolor="#dddddd")
        ax.set_facecolor("#fafafa")
        ax.axhline(0, color="#ccc", linewidth=0.8)

        fig.suptitle(
            f"Coverage status by satellite  ·  ≤{max_cloud}% cloud threshold",
            fontsize=11, fontweight="bold",
        )
        fig.tight_layout()

    return fig
