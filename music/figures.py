"""Three-panel figure: mean beta, E_{v^2}(f), hydrodynamic H-tilde."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from scipy.ndimage import gaussian_filter1d

import config
from measure import analysis_band

matplotlib.rcParams.update(config.NATURE_RC)

_SPECTRA: dict | None = None


def pretty(name: str) -> str:
    return config.DISPLAY_NAMES.get(name, str(name))


def _style_ax(ax):
    ax.set_frame_on(True)
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_linewidth(0.7)
        ax.spines[side].set_color("#222222")
    ax.set_axisbelow(True)
    ax.tick_params(direction="out", length=3.0, width=0.7, pad=2.5)
    ax.grid(True, which="major", linestyle="-", alpha=0.10, color="#888")


def _letter(ax, letter: str, *, x: float, y: float):
    ax.text(
        x, y, letter,
        transform=ax.transAxes,
        fontsize=12, fontweight="bold",
        va="bottom", ha="right",
        clip_on=False, color="#111111",
    )


def load_tracks() -> pd.DataFrame:
    path = config.DATA_DIR / "tracks.csv"
    if not path.is_file():
        raise SystemExit(f"Missing {path}")
    df = pd.read_csv(path)
    if "beta" not in df.columns:
        df["beta"] = -df["alpha"]
    if "H_tilde" not in df.columns:
        df["H_tilde"] = df["S_hydro_norm"]
    return df


def _spectra() -> dict:
    global _SPECTRA
    if _SPECTRA is None:
        path = config.DATA_DIR / "spectra.npz"
        if not path.is_file():
            raise SystemExit(f"Missing {path}")
        z = np.load(path, allow_pickle=True)
        _SPECTRA = {
            "freqs": np.asarray(z["freqs"], dtype=np.float64),
            "psd": np.asarray(z["psd"]),
            "groups": np.asarray(z["groups"]).astype(str),
            "files": np.asarray(z["files"]).astype(str),
        }
    return _SPECTRA


def _mean_log_psd(group: str, tracks: pd.DataFrame) -> tuple[np.ndarray, np.ndarray] | None:
    spec = _spectra()
    keep = set(zip(tracks["group"].astype(str), tracks["filename"].astype(str)))
    groups = spec["groups"]
    files = spec["files"]
    mask = np.array(
        [(g == group) and ((g, f) in keep) for g, f in zip(groups, files)],
        dtype=bool,
    )
    if mask.sum() < 1:
        return None
    block = spec["psd"][mask]
    with np.errstate(divide="ignore", invalid="ignore"):
        geo = np.exp(np.nanmean(np.log(np.clip(block, 1e-30, None)), axis=0))
    f = spec["freqs"]
    n = min(f.size, geo.size)
    f, geo = f[:n], geo[:n]
    ok = np.isfinite(geo) & (geo > 0) & (f > 0)
    if ok.sum() < 8:
        return None
    return f[ok], geo[ok]


def _band_normalize(freqs: np.ndarray, psd: np.ndarray) -> np.ndarray:
    mask = analysis_band(freqs)
    df = float(np.median(np.diff(freqs[freqs > 0]))) if freqs.size > 2 else 1.0
    power = float(np.sum(psd[mask]) * df)
    if not np.isfinite(power) or power <= 0:
        return psd
    return psd / power


def _smooth_log(y: np.ndarray, sigma: float = 9.0) -> np.ndarray:
    y = np.asarray(y, dtype=np.float64)
    ok = np.isfinite(y) & (y > 0)
    out = y.copy()
    sig = min(sigma, max(1.0, ok.sum() / 20.0))
    out[ok] = 10.0 ** gaussian_filter1d(np.log10(y[ok]), sigma=sig, mode="nearest")
    return out


def plot_beta_bars(ax, tracks: pd.DataFrame):
    g = (
        tracks.groupby("group")
        .agg(beta=("beta", "mean"), sd=("beta", "std"))
        .reset_index()
        .sort_values("beta", ascending=True)
    )
    y = np.arange(len(g))
    colors = [config.PALETTE.get(x, "#777") for x in g["group"]]
    vals = g["beta"].to_numpy()
    sd = g["sd"].to_numpy()
    ax.axvline(1.0, color="#333", ls=":", lw=0.8, alpha=0.45, zorder=1)
    ax.barh(y, vals, color=colors, edgecolor="#222", height=0.72, linewidth=0.4, zorder=3)
    xerr = np.vstack([np.minimum(vals, sd), sd])
    ax.errorbar(vals, y, xerr=xerr, fmt="none", ecolor="#111", elinewidth=0.7, capsize=1.6, zorder=4, capthick=0.7)
    right = vals + sd
    pad = 0.018
    xs = []
    for yi, v, w in zip(y, vals, right):
        x = float(w) + pad
        xs.append(x)
        ax.text(x, yi, f"{v:.2f}", va="center", ha="left", fontsize=6.5, color="#111", clip_on=False)
    ax.set_yticks(y)
    ax.set_yticklabels([pretty(name) for name in g["group"]], fontsize=9)
    ax.set_xlabel(r"$\beta$")
    ax.set_xlim(0.0, float(np.nanmax(xs)) + 0.18)
    ax.set_ylim(-0.55, len(g) - 0.35)
    _letter(ax, "a", x=0.0, y=1.02)
    _style_ax(ax)
    ax.grid(True, axis="x", linestyle="-", alpha=0.14, color="#888")
    ax.grid(False, axis="y")


def plot_spectra(ax, tracks: pd.DataFrame):
    plotted = []
    for group in config.SV2_REPS:
        pair = _mean_log_psd(group, tracks)
        if pair is None:
            continue
        f, s = pair
        band = (f >= 0.004) & (f <= 8.0) & (s > 0) & np.isfinite(s)
        if band.sum() < 8:
            continue
        f, s = f[band], _smooth_log(_band_normalize(f[band], s[band]))
        plotted.append((group, f, s))

    ax.axvspan(config.BAND_LO_HZ, config.BAND_HI_HZ, color="#8A9199", alpha=0.045, lw=0, zorder=0)
    n = len(plotted)
    offset_curves = []
    for i, (group, f, s) in enumerate(plotted):
        pin = float(np.interp(0.1, f, s)) if (f.min() <= 0.1 <= f.max()) else float(s[0])
        if pin > 0:
            s = s / pin
        s = s * (10.0 ** (1.28 * (n - 1 - i)))
        offset_curves.append((f, s))
        ax.plot(f, s, color=config.PALETTE.get(group, "#444"), lw=1.35, solid_capstyle="round", zorder=3, label=pretty(group))

    if offset_curves:
        peak = 0.0
        for f, s in offset_curves:
            m = (f >= config.BAND_LO_HZ) & (f <= config.BAND_HI_HZ) & np.isfinite(s) & (s > 0)
            if m.any():
                peak = max(peak, float(np.nanmax(s[m] * f[m])))
        if peak > 0:
            ff = np.geomspace(config.BAND_LO_HZ, config.BAND_HI_HZ, 160)
            ax.plot(ff, (peak * 10.0 ** 0.85) / ff, color="#222222", ls="--", lw=1.15, alpha=0.78, zorder=5, label=r"$1/f$")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.0045, 8.0)
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, ymax * (10.0 ** 0.95))
    ax.set_xlabel(r"$f$ (Hz)")
    ax.set_ylabel(r"$E_{v^{2}}(f)$")
    _letter(ax, "b", x=-0.04, y=1.03)
    _style_ax(ax)
    ax.legend(
        loc="upper right", ncol=2, fontsize=5, frameon=True, framealpha=0.96,
        edgecolor="#CCCCCC", fancybox=False, handlelength=1.0, handletextpad=0.3,
        columnspacing=0.7, labelspacing=0.18, borderpad=0.25,
    )


def plot_entropy(ax, tracks: pd.DataFrame):
    order = list(tracks.groupby("group")["H_tilde"].median().sort_values().index)
    data = [tracks.loc[tracks["group"] == g, "H_tilde"].dropna().values for g in order]
    bp = ax.boxplot(
        data, patch_artist=True, widths=0.58,
        medianprops=dict(color="#111", linewidth=1.05),
        whiskerprops=dict(color="#444", linewidth=0.7),
        capprops=dict(color="#444", linewidth=0.7),
        boxprops=dict(linewidth=0.6, edgecolor="#333"),
        flierprops=dict(marker="o", markersize=1.4, alpha=0.22, markerfacecolor="#777", markeredgewidth=0),
    )
    for patch, g in zip(bp["boxes"], order):
        patch.set_facecolor(config.PALETTE.get(g, "#777"))
        patch.set_alpha(0.9)
    ax.set_xticks(np.arange(1, len(order) + 1))
    ax.set_xticklabels([pretty(g) for g in order], rotation=50, ha="right", rotation_mode="anchor", fontsize=8)
    ax.set_ylabel(r"$\tilde{H}$")
    ax.set_xlim(0.35, len(order) + 0.65)
    _letter(ax, "c", x=-0.08, y=1.04)
    _style_ax(ax)


def collage(tracks: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(7.0, 5.25), dpi=300, constrained_layout=False)
    gs_a = GridSpec(1, 1, figure=fig, left=0.115, right=0.42, top=0.94, bottom=0.17)
    gs_r = GridSpec(2, 1, figure=fig, left=0.53, right=0.96, top=0.94, bottom=0.17, hspace=0.40, height_ratios=[2.55, 1.22])
    ax_a = fig.add_subplot(gs_a[0, 0])
    ax_b = fig.add_subplot(gs_r[0, 0])
    ax_c = fig.add_subplot(gs_r[1, 0])
    plot_beta_bars(ax_a, tracks)
    plot_spectra(ax_b, tracks)
    plot_entropy(ax_c, tracks)
    ax_b.yaxis.labelpad = 3
    ax_c.yaxis.labelpad = 3
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    png = config.FIGURES_DIR / "collage_three_panel.png"
    pdf = config.FIGURES_DIR / "collage_three_panel.pdf"
    fig.savefig(png, dpi=300, facecolor="white")
    fig.savefig(pdf, facecolor="white")
    plt.close(fig)
    print(f"Saved {png}")
