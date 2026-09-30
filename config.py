"""Constants for the published long-track envelope analysis."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"

SR = 22050
BP_LO_HZ = 100.0
BP_HI_HZ = 10000.0
LPF_HZ = 20.0
ENV_TARGET_SR = 100.0
DECIM = max(1, int(round(SR / ENV_TARGET_SR)))  # 221
FILTER_ORDER = 4

BAND_LO_HZ = 0.01
BAND_HI_HZ = 1.0
T_S = 240.0
N_PER_GROUP = 300

GROUPS = (
    "hiphop",
    "carnatic",
    "jazz",
    "folk",
    "pop",
    "rock",
    "metal",
    "hindustani",
    "western_classical",
)

DISPLAY_NAMES = {
    "hiphop": "Hiphop",
    "carnatic": "Carnatic",
    "jazz": "Jazz",
    "folk": "Folk",
    "pop": "Pop",
    "rock": "Rock",
    "metal": "Metal",
    "hindustani": "Hindustani",
    "western_classical": "W. Classical",
}

# Traces drawn in panel b, top to bottom.
SV2_REPS = (
    "western_classical",
    "hindustani",
    "carnatic",
    "jazz",
    "rock",
    "hiphop",
)

PALETTE = {
    "western_classical": "#9B5858",
    "hindustani": "#B06A42",
    "metal": "#7A6A48",
    "rock": "#3D5A6C",
    "pop": "#8A6A7A",
    "folk": "#5E8A62",
    "hiphop": "#5A4A6A",
    "jazz": "#4A6A7A",
    "carnatic": "#3A5A8A",
}

NATURE_RC = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 9.5,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 8,
    "axes.linewidth": 0.7,
    "figure.dpi": 300,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}
