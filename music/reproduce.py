"""Rebuild the category table and the three-panel figure from data/."""

from __future__ import annotations

import pandas as pd

import config
import figures


def category_summary(tracks: pd.DataFrame) -> pd.DataFrame:
    summary = (
        tracks.groupby("group", as_index=False)
        .agg(
            n=("beta", "size"),
            T_s=("T_s", "mean"),
            M_bins=("M_bins", "median"),
            beta_mean=("beta", "mean"),
            beta_sd=("beta", "std"),
            S_hydro_mean=("S_hydro", "mean"),
            H_tilde_mean=("H_tilde", "mean"),
            H_tilde_sd=("H_tilde", "std"),
        )
        .sort_values("beta_mean")
    )
    summary.insert(0, "category", summary["group"].map(config.DISPLAY_NAMES))
    return summary


def main() -> None:
    tracks = figures.load_tracks()
    summary = category_summary(tracks)
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.RESULTS_DIR / "category_summary.csv"
    summary.to_csv(path, index=False)
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"Wrote {path}")
    figures.collage(tracks)


if __name__ == "__main__":
    main()
