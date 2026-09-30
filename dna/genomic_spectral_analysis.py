import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import LogLocator, MaxNLocator
from Bio import Entrez, SeqIO
from collections import defaultdict
import os
import gc
import re
from openpyxl import Workbook
# Print-ready figure typography.
plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 10,
        "axes.labelsize": 8,
        "xtick.labelsize": 6,
        "ytick.labelsize": 6,
        "legend.fontsize": 6,
        "figure.titlesize": 14,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)
# PARAMETERS
# DIVERSE FASTA FILE
FASTA_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "diverse_long_genomes_voss.fasta",
)
# NCBI email required by Entrez
Entrez.email = "your_actual_email@gmail.com"
# NCBI FALLBACK FOR BACTERIA ENTROPY REPRESENTATIVE
BACTERIA_ENTROPY_QUERY = (
    "(bacteria[Organism]) "
    "AND (complete genome[Title] OR chromosome[Title]) "
    "AND biomol_genomic[PROP] "
    "AND 10000000:30000000[SLEN] "
    "NOT biomol_mrna[PROP] "
    "NOT plasmid[Title]"
)
BACTERIA_NCBI_RETMAX = 500
# MAIN VOSS SETTINGS
NFFT = 65536
N_GENOMES = 50
MIN_LENGTH = 1_000_000
GROUPS = ["Bacteria", "Plants", "Mammals", "Insects", "Worms", "ColdBlooded"]
# CONSISTENT KINGDOM COLOURS The same colour represents a kingdom in every figure.
VIBGYOR_COLORS = [
    "#6B4E82",  # muted plum/violet
    "#3F5E8C",  # slate indigo-blue
    "#4D7A8C",  # steel teal-blue
    "#6FA073",  # sage green
    "#B08D3E",  # muted gold/olive
    "#C97A3D",  # burnt orange
    "#A9555D",  # dusty brick red
]
KINGDOM_COLORS = {group: "#808080" for group in GROUPS}

def set_kingdom_colors_from_beta(beta_by_group):
    """Assign one VIBGYOR colour per kingdom, ordered by increasing beta."""
    ordered_groups = [
        group
        for group, beta in sorted(beta_by_group.items(), key=lambda item: item[1])
        if np.isfinite(beta)
    ]
    if len(ordered_groups) == 0:
        return
    cmap = LinearSegmentedColormap.from_list("vibgyor_beta", VIBGYOR_COLORS)
    positions = np.linspace(0, 1, len(ordered_groups))
    for group, position in zip(ordered_groups, positions):
        KINGDOM_COLORS[group] = cmap(position)
    print("VIBGYOR kingdom colours (increasing beta):")
    for group in ordered_groups:
        print(f"  {group}: beta = {beta_by_group[group]:.3f}")

def set_kingdom_colors_from_results(results):
    """Derive the shared colour order from the main low-k beta fits."""
    beta_by_group = {}
    for group in GROUPS:
        if group not in results:
            continue
        fit = best_fit_loglog(
            results[group]["f"], results[group]["Delta"], max_x=FIT_MAX_K / NFFT, verbose=False
        )
        if fit is not None:
            beta_by_group[group] = fit[2]
    set_kingdom_colors_from_beta(beta_by_group)
# SEPARATE CACHE PREFIX
RESULT_PREFIX = "DiverseVoss"
# SCRIPT DIRECTORY
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# PUBLICATION FIGURE EXPORT
FIGURE_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "figures")

def export_figure(fig, name, exact_size=False):
    """Save a high-resolution PNG and an editable vector PDF."""
    os.makedirs(FIGURE_OUTPUT_DIR, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")
    png_filename = os.path.join(FIGURE_OUTPUT_DIR, f"{safe_name}.png")
    pdf_filename = os.path.join(FIGURE_OUTPUT_DIR, f"{safe_name}.pdf")
    if exact_size:
        export_options = {}  # no cropping, keep the figure's own figsize
    else:
        export_options = {
            "bbox_inches": "tight",
            "pad_inches": 0.05,
        }
    fig.savefig(png_filename, dpi=600, **export_options)
    fig.savefig(pdf_filename, **export_options)
    print("Exported:", png_filename)
    print("Exported:", pdf_filename)
# FIXED BEST-FIT SETTINGS
# Same fixed low-wave-number range for all kingdoms. Fits use k = 2 through FIT_MAX_K inclusive.
FIT_MAX_K = 300
# PER-GENOME BETA DISTRIBUTION SETTINGS
# One beta per genome, then the kingdom mean and spread.
BETA_N_GENOMES = 50
BETA_CACHE_PREFIX = f"{RESULT_PREFIX}_beta_all{BETA_N_GENOMES}_fresh_" f"nfft{NFFT}_k2to{FIT_MAX_K}"
BETA_CHECKPOINT_DIR = os.path.join(SCRIPT_DIR, f"{BETA_CACHE_PREFIX}_checkpoints")
# SPECTRAL ENTROPY PROFILE SETTINGS
# Boxplot entropy uses the same window as the main Voss analysis.
ENTROPY_WINDOW = NFFT
ENTROPY_STRIDE = NFFT
# REPRESENTATIVE SPECTRAL ENTROPY PROFILE SETTINGS These are used ONLY for the six
PROFILE_WINDOW = NFFT
# EXACTLY THE SAME WINDOWING AS E(k) vs k: non-overlapping NFFT-length windows.
PROFILE_STRIDE = NFFT
# ENTROPY REPRESENTATIVE SIZE RANGE ONLY ANY genome from 10 Mb to 30 Mb is acceptable.
ENTROPY_MIN_LENGTH = 10_000_000
ENTROPY_MAX_LENGTH = 30_000_000
# Profile and boxplot use the same spectral range.
ENTROPY_MUTE_FRACTION = 0.01
# Spectral cutoff for entropy: only FFT wave-number bins k <= 300 contribute to entropy.
K_MAX_ENTROPY = 300
# Representative spectral-entropy profile: use k = 2 .
PROFILE_MIN_K = 2
# Smoothing applied only for visualization.
ENTROPY_SMOOTH_WINDOW = 15
# BOXplot settings
# The boxplot uses every genome; the profile uses one.
# CURRENT BOXplot RUN: Calculate a fresh set of 50 genomes per kingdom at 65536/65536.
BOXPLOT_N_GENOMES = 50
BOXPLOT_MIN_K = PROFILE_MIN_K
# A fresh 50-genome cache, separate from every previous 20-genome run.
BOXPLOT_CACHE_PREFIX = (
    f"{RESULT_PREFIX}_entropy_boxplot_all{BOXPLOT_N_GENOMES}_fresh_"
    f"{ENTROPY_WINDOW}_{ENTROPY_STRIDE}_k{BOXPLOT_MIN_K}to{K_MAX_ENTROPY}"
)
# Use a new checkpoint directory rather than reusing the prior directory.
BOXPLOT_CHECKPOINT_PREFIX = (
    f"{RESULT_PREFIX}_entropy_boxplot_all{BOXPLOT_N_GENOMES}_fresh_"
    f"{ENTROPY_WINDOW}_{ENTROPY_STRIDE}_k{BOXPLOT_MIN_K}to{K_MAX_ENTROPY}"
)
# BOXplot per-genome CHECKPOINTS
# Each completed genome gets its own NPZ checkpoint.
BOXPLOT_CHECKPOINT_DIR = os.path.join(SCRIPT_DIR, f"{BOXPLOT_CHECKPOINT_PREFIX}_checkpoints")
# FASTA GROUP IDENTIFICATION

def get_group(record_id):
    if record_id.startswith("ColdBlooded"):
        return "ColdBlooded"
    for group in GROUPS:
        if record_id.startswith(group):
            return group
    return None
# MAIN VOSS RESULT FILE NAME

def result_filename(group):
    return os.path.join(SCRIPT_DIR, f"{RESULT_PREFIX}_{group}_voss_result.npz")
# ENTROPY RESULT FILE NAME New filename so previous entropy caches are NOT reused.

def entropy_filename(group):
    return os.path.join(
        SCRIPT_DIR,
        f"{RESULT_PREFIX}_{group}_entropy_10to30Mb_first_"
        f"w{PROFILE_WINDOW}_s{PROFILE_STRIDE}_"
        f"k{PROFILE_MIN_K}to{K_MAX_ENTROPY}.npz",
    )
# READ FASTA CATEGORY-WISE ONLY USED IF A MAIN VOSS NPZ IS MISSING

def read_fasta_categories():
    categories = defaultdict(list)
    print()
    print("========================================")
    print("READING DIVERSE FASTA")
    print("========================================")
    print("File:", FASTA_FILE)
    count = 0
    for record in SeqIO.parse(FASTA_FILE, "fasta"):
        count += 1
        if count % 10 == 0:
            print("Read records:", count)
        group = get_group(record.id)
        if group is None:
            continue
        # Already enough genomes for this group
        if len(categories[group]) >= N_GENOMES:
            continue
        seq = str(record.seq).upper()
        if len(seq) < MIN_LENGTH:
            continue
        if len(seq) >= NFFT:
            categories[group].append(seq)
        # Stop once all six groups have enough genomes
        done = True
        for g in GROUPS:
            if len(categories[g]) < N_GENOMES:
                done = False
                break
        if done:
            print("\nAll six groups collected.")
            break
    print("\nFinished FASTA reading.")
    return categories
# VOSS FFT

def voss_genome_windows(seq):
    """Process one genome using NFFT-length windows."""
    n_sections = len(seq) // NFFT
    if n_sections == 0:
        return None
    freq = np.fft.rfftfreq(NFFT)[1:]
    # WHOLE-GENOME BASE COMPOSITION
    x_full = np.frombuffer(seq.encode(), dtype="S1")
    p = np.array([np.mean(x_full == b) for b in (b"A", b"C", b"G", b"T")])
    S_inf = np.sum(p * (1 - p))
    # RUNNING SPECTRUM SUM
    S_sum = np.zeros(len(freq), dtype=np.float64)
    # PROCESS ALL WINDOWS
    for i in range(n_sections):
        window = seq[i * NFFT : (i + 1) * NFFT]
        x = np.frombuffer(window.encode(), dtype="S1")
        S_total = np.zeros(len(freq), dtype=np.float64)
        # VOSS FOUR-CHANNEL ENCODING
        for base in (b"A", b"C", b"G", b"T"):
            U = (x == base).astype(np.float32)
            F = np.fft.rfft(U)
            S_total += np.abs(F[1:]) ** 2
        S_sum += S_total
    return (freq, S_sum, n_sections, S_inf)
# PROCESS ONE CATEGORY

def category_voss(sequences, name):
    print()
    print("========================================")
    print("Processing:", name)
    print("Genomes:", len(sequences))
    print("========================================")
    freq = None
    S_sum_total = None
    n_windows_total = 0
    S_inf_sum = 0.0
    n_genomes_used = 0
    # Sequential processing This avoids the Windows memory issue encountered earlier.
    for i, seq in enumerate(sequences, start=1):
        print(name, "processing genome", i, "/", len(sequences))
        result = voss_genome_windows(seq)
        if result is None:
            continue
        f, S_sum, n_sections, S_inf = result
        freq = f
        if S_sum_total is None:
            S_sum_total = np.zeros_like(S_sum)
        S_sum_total += S_sum
        n_windows_total += n_sections
        S_inf_sum += S_inf
        n_genomes_used += 1
        print(name, "completed genome", i, "| windows:", n_sections)
        gc.collect()
    # Safety check
    if n_windows_total == 0:
        return None
    # AVERAGE ACROSS ALL WINDOWS
    S_avg = S_sum_total / n_windows_total
    S_inf_avg = S_inf_sum / n_genomes_used
    Delta = S_avg - S_inf_avg
    # SAVE MAIN VOSS RESULT
    filename = result_filename(name)
    np.savez(
        filename,
        dataset=RESULT_PREFIX,
        fasta=FASTA_FILE,
        nfft=NFFT,
        f=freq,
        S=S_avg,
        Delta=Delta,
        n_windows=n_windows_total,
        n_genomes=n_genomes_used,
    )
    print("Saved:", os.path.basename(filename))
    return (freq, S_avg, Delta)
# LOAD CACHED MAIN VOSS RESULT

def load_cached_result(filename):
    print("Loading cached:", os.path.basename(filename))
    data = np.load(filename)
    # Verify dataset
    if "dataset" in data:
        dataset = str(data["dataset"])
        if dataset != RESULT_PREFIX:
            raise ValueError("Wrong dataset in cached NPZ: " + filename)
    # Verify NFFT
    if "nfft" in data:
        stored_nfft = int(data["nfft"])
        if stored_nfft != NFFT:
            raise ValueError(f"NPZ NFFT={stored_nfft}, " f"current NFFT={NFFT}")
    result = {"f": data["f"], "S": data["S"], "Delta": data["Delta"]}
    if "n_windows" in data:
        result["n_windows"] = int(data["n_windows"])
    if "n_genomes" in data:
        result["n_genomes"] = int(data["n_genomes"])
    return result
# FIXED BEST-FIT LINE SAME LOW-K RANGE FOR ALL KINGDOMS

def best_fit_loglog(x, y, max_x, verbose=True):
    # Keep valid values only
    valid = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    x = x[valid]
    y = y[valid]
    if len(x) < 30:
        return None
    # Start from SECOND valid point
    x_work = x[1:]
    y_work = y[1:]
    # FIXED UPPER FIT LIMIT
    selected = x_work <= max_x
    x_selected = x_work[selected]
    y_selected = y_work[selected]
    if len(x_selected) < 5:
        return None
    # LINEAR REGRESSION IN LOG-LOG SPACE
    slope, intercept = np.polyfit(np.log10(x_selected), np.log10(y_selected), 1)
    beta = -slope
    if verbose:
        print(f"    Fixed upper fit limit = " f"{max_x:.6g}")
        print(f"    Fit range: " f"{x_selected[0]:.6g}" f" -> " f"{x_selected[-1]:.6g}")
        print(f"    Slope = " f"{slope:.6f}")
        print(f"    Beta = " f"{beta:.6f}")
    return (slope, intercept, beta, x_selected, y_selected)

def fit_loglog_fixed_beta(x, y, max_x, beta):
    """Fit intercept in log-log space with fixed beta (slope = -beta)."""
    valid = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    x = x[valid]
    y = y[valid]
    if len(x) < 30:
        return None
    x_work = x[1:]
    y_work = y[1:]
    selected = x_work <= max_x
    x_selected = x_work[selected]
    y_selected = y_work[selected]
    if len(x_selected) < 5:
        return None
    slope = -beta
    intercept = np.mean(np.log10(y_selected) - slope * np.log10(x_selected))
    return (slope, intercept, beta, x_selected, y_selected)
# One entropy representative per kingdom, any genome from 10 to 30 Mb.

def get_entropy_representatives(required_groups):
    print()
    print("========================================")
    print("SEARCHING EXISTING DIVERSE FASTA")
    print("FOR MISSING ENTROPY REPRESENTATIVES")
    print("========================================")
    print("Need representatives for:", required_groups)
    print("Allowed size:", f"{ENTROPY_MIN_LENGTH:,}", "to", f"{ENTROPY_MAX_LENGTH:,}", "bp")
    print("Selection rule:", "FIRST qualifying genome per missing kingdom")
    representative = {}
    required_groups = set(required_groups)
    # FIRST: SEARCH THE EXISTING DIVERSE FASTA
    for record in SeqIO.parse(FASTA_FILE, "fasta"):
        group = get_group(record.id)
        if group not in required_groups:
            continue
        if group in representative:
            continue
        raw_length = len(record.seq)
        if raw_length < ENTROPY_MIN_LENGTH or raw_length > ENTROPY_MAX_LENGTH:
            continue
        print(
            f"[{group}] candidate: " f"{record.id} | " f"raw length = " f"{raw_length:,} bp",
            flush=True,
        )
        seq = str(record.seq).upper()
        seq = "".join(b for b in seq if b in "ACGT")
        cleaned_length = len(seq)
        if cleaned_length < ENTROPY_MIN_LENGTH or cleaned_length > ENTROPY_MAX_LENGTH:
            print("    Rejected after A/C/G/T filtering.", flush=True)
            continue
        representative[group] = {
            "id": record.id,
            "sequence": seq,
            "length": cleaned_length,
            "source": "existing_fasta",
        }
        print(
            f"[{group}] ACCEPTED FROM EXISTING FASTA: " f"{record.id} | " f"{cleaned_length:,} bp",
            flush=True,
        )
        print(
            f"    Found "
            f"{len(representative)}/"
            f"{len(required_groups)} "
            f"missing representatives",
            flush=True,
        )
        if len(representative) == len(required_groups):
            print("\nAll missing entropy representatives found " "in existing FASTA.", flush=True)
            break
    # SECOND: NCBI FALLBACK At present this is intentionally used only for Bacteria.
    missing_after_fasta = required_groups - set(representative.keys())
    if "Bacteria" in missing_after_fasta:
        print()
        print("========================================")
        print("BACTERIA NCBI FALLBACK")
        print("========================================")
        print("No 10–30 Mb Bacteria record was found " "in the existing diverse FASTA.")
        print("Searching NCBI with sequence-length restriction " "10–30 Mb...")
        try:
            search_handle = Entrez.esearch(
                db="nucleotide",
                term=BACTERIA_ENTROPY_QUERY,
                retmax=BACTERIA_NCBI_RETMAX,
                sort="relevance",
            )
            ids = Entrez.read(search_handle)["IdList"]
            search_handle.close()
            print("NCBI candidates:", len(ids))
            for i, uid in enumerate(ids, start=1):
                print(f"\n[NCBI Bacteria] " f"Trying {i}/{len(ids)}", flush=True)
                try:
                    handle = Entrez.efetch(db="nucleotide", id=uid, rettype="fasta", retmode="text")
                    record = SeqIO.read(handle, "fasta")
                    handle.close()
                    raw_length = len(record.seq)
                    print("    Accession:", record.id, flush=True)
                    print("    Raw length:", f"{raw_length:,}", "bp", flush=True)
                    # Extra safety check after fetching
                    if raw_length < ENTROPY_MIN_LENGTH or raw_length > ENTROPY_MAX_LENGTH:
                        print("    Rejected size.", flush=True)
                        continue
                    seq = str(record.seq).upper()
                    seq = "".join(b for b in seq if b in "ACGT")
                    cleaned_length = len(seq)
                    print("    A/C/G/T length:", f"{cleaned_length:,}", "bp", flush=True)
                    if cleaned_length < ENTROPY_MIN_LENGTH or cleaned_length > ENTROPY_MAX_LENGTH:
                        print("    Rejected after A/C/G/T filtering.", flush=True)
                        continue
                    representative["Bacteria"] = {
                        "id": record.id,
                        "sequence": seq,
                        "length": cleaned_length,
                        "source": "NCBI",
                    }
                    print(
                        f"    ACCEPTED FROM NCBI: " f"{record.id} | " f"{cleaned_length:,} bp",
                        flush=True,
                    )
                    break
                except Exception as e:
                    print("    Failed:", e, flush=True)
                # Be polite to NCBI
                import time
                time.sleep(0.4)
        except Exception as e:
            print("NCBI Bacteria search failed:", e, flush=True)
    # SUMMARY
    print()
    print("========================================")
    print("NEW ENTROPY REPRESENTATIVES")
    print("========================================")
    for group in required_groups:
        if group not in representative:
            print(f"{group}: " f"NO 10–30 Mb GENOME FOUND")
        else:
            source = representative[group].get("source", "unknown")
            print(
                f"{group}: "
                f"{representative[group]['id']} "
                f"({representative[group]['length']:,} bp) "
                f"[source: {source}]"
            )
    return representative
# VOSS SPECTRAL ENTROPY PROFILE

def voss_spectral_entropy_profile(
    seq, window_size=ENTROPY_WINDOW, stride=ENTROPY_STRIDE, min_k=None
):
    """Calculate normalized Shannon spectral entropy after Voss four-channel encoding."""
    if len(seq) < window_size:
        return None
    print("    Building Voss channels...")
    # VOSS FOUR-CHANNEL ENCODING
    seq_bytes = np.frombuffer(seq.encode(), dtype=np.uint8)
    A = (seq_bytes == ord("A")).astype(np.float32)
    C = (seq_bytes == ord("C")).astype(np.float32)
    G = (seq_bytes == ord("G")).astype(np.float32)
    T = (seq_bytes == ord("T")).astype(np.float32)
    signals = [A, C, G, T]
    # FREQUENCY SETTINGS
    half = window_size // 2
    # Lower-k cutoff If min_k is supplied, use that exact wave-number cutoff.
    if min_k is None:
        mute_bins = max(1, int(ENTROPY_MUTE_FRACTION * window_size))
    else:
        mute_bins = max(0, int(min_k))
    # New upper spectral cutoff The FFT window determines the available k bins.
    k_max = min(K_MAX_ENTROPY, half - 1)
    if k_max < mute_bins:
        return None
    # Number of spectral bins actually used for Shannon entropy: k = mute_bins ... k_max
    usable_bins = k_max - mute_bins + 1
    max_entropy = np.log2(usable_bins)
    # KAISER WINDOW
    kaiser = np.kaiser(window_size, 3.5)
    positions = []
    entropy_values = []
    # NUMBER OF LOCAL WINDOWS
    n_windows = ((len(seq) - window_size) // stride) + 1
    print("    Entropy windows:", f"{n_windows:,}")
    # SLIDING ENTROPY WINDOWS
    for window_index, start in enumerate(range(0, len(seq) - window_size + 1, stride), start=1):
        if window_index % 250 == 0:
            print(f"    Entropy window " f"{window_index:,}/" f"{n_windows:,}", flush=True)
        # Four-channel Voss power spectrum
        total_power_spectrum = np.zeros(half, dtype=np.float64)
        for signal in signals:
            segment = signal[start : start + window_size]
            windowed = segment * kaiser
            fft = np.fft.rfft(windowed)
            total_power_spectrum += np.abs(fft[:half]) ** 2
        # Keep only: mute_bins <= k <= k_max Lower k bins are muted as before, and all bins above
        total_power_spectrum[:mute_bins] = 0
        total_power_spectrum[k_max + 1 :] = 0
        total_power = np.sum(total_power_spectrum)
        # SHANNON SPECTRAL ENTROPY
        if total_power <= 1e-12:
            entropy = 1.0
        else:
            # Convert power into probability distribution
            p = total_power_spectrum / total_power
            p = p[p > 0]
            # Shannon entropy: H = -sum p log2(p) Normalize to [0,1]
            entropy = -np.sum(p * np.log2(p)) / max_entropy
        # Store center position
        positions.append(start + window_size // 2)
        entropy_values.append(entropy)
    positions = np.asarray(positions)
    entropy_values = np.asarray(entropy_values)
    # Smooth the profile for display.
    smooth = smooth_entropy_for_display(entropy_values)
    return (positions, entropy_values, smooth)

def smooth_entropy_for_display(entropy_values):
    """Return a centered moving average without zero-padded endpoints."""
    if len(entropy_values) < ENTROPY_SMOOTH_WINDOW:
        return entropy_values.copy()
    kernel = np.ones(ENTROPY_SMOOTH_WINDOW) / ENTROPY_SMOOTH_WINDOW
    left_pad = ENTROPY_SMOOTH_WINDOW // 2
    right_pad = ENTROPY_SMOOTH_WINDOW - 1 - left_pad
    padded = np.pad(entropy_values, (left_pad, right_pad), mode="edge")
    return np.convolve(padded, kernel, mode="valid")
# SAVE ENTROPY PROFILE

def save_entropy_profile(
    group,
    record_id,
    genome_length,
    positions,
    entropy,
    smooth,
    profiles_source,
    min_k,
    profile_window,
    profile_stride,
):
    filename = entropy_filename(group)
    np.savez(
        filename,
        dataset=RESULT_PREFIX,
        group=group,
        record_id=record_id,
        genome_length=genome_length,
        source=profiles_source,
        nfft=NFFT,
        k_min=min_k,
        k_max=K_MAX_ENTROPY,
        mute_fraction=ENTROPY_MUTE_FRACTION,
        window_size=profile_window,
        stride=profile_stride,
        min_length=ENTROPY_MIN_LENGTH,
        max_length=ENTROPY_MAX_LENGTH,
        position=positions,
        entropy=entropy,
        entropy_smooth=smooth,
    )
    print("    Saved entropy cache:", os.path.basename(filename))
# LOAD ENTROPY PROFILE

def load_entropy_profile(filename):
    data = np.load(filename)
    # Dataset check
    if "dataset" in data:
        dataset = str(data["dataset"])
        if dataset != RESULT_PREFIX:
            raise ValueError("Wrong dataset in entropy cache: " + filename)
    # Verify entropy spectral cutoff
    if "k_max" in data:
        stored_kmax = int(data["k_max"])
        if stored_kmax != K_MAX_ENTROPY:
            raise ValueError(f"Entropy k_max={stored_kmax}, " f"current k_max={K_MAX_ENTROPY}")
    # Verify representative profile minimum k
    if "k_min" in data:
        stored_kmin = int(data["k_min"])
        if stored_kmin != PROFILE_MIN_K:
            raise ValueError(
                f"Entropy k_min={stored_kmin}, " f"current profile k_min={PROFILE_MIN_K}"
            )
    # Verify low-k mute setting
    if "mute_fraction" in data:
        stored_mute = float(data["mute_fraction"])
        if not np.isclose(stored_mute, ENTROPY_MUTE_FRACTION):
            raise ValueError("Entropy mute fraction mismatch.")
    # Verify entropy window
    if "window_size" in data:
        stored_window = int(data["window_size"])
        if stored_window != PROFILE_WINDOW:
            raise ValueError("Entropy window mismatch.")
    # Verify stride
    if "stride" in data:
        stored_stride = int(data["stride"])
        if stored_stride != PROFILE_STRIDE:
            raise ValueError("Entropy stride mismatch.")
    # Verify size range
    if "min_length" in data:
        if int(data["min_length"]) != ENTROPY_MIN_LENGTH:
            raise ValueError("Entropy minimum length mismatch.")
    if "max_length" in data:
        if int(data["max_length"]) != ENTROPY_MAX_LENGTH:
            raise ValueError("Entropy maximum length mismatch.")
    return {
        "record_id": str(data["record_id"]),
        "genome_length": int(data["genome_length"]),
        "source": str(data["source"]) if "source" in data else "unknown",
        "position": data["position"],
        "entropy": data["entropy"],
        "smooth":
        # Rebuild the display-only smoothing from the raw values.
        smooth_entropy_for_display(data["entropy"]),
    }
# BOX PLOT CACHE FILE NAME

def boxplot_entropy_filename(group):
    return os.path.join(SCRIPT_DIR, f"{BOXPLOT_CACHE_PREFIX}_{group}.npz")
# PER-GENOME BOXPLOT CHECKPOINT HELPERS

def boxplot_checkpoint_filename(group, record_id):
    """Return a stable checkpoint filename based on the FASTA record ID."""
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(record_id))
    return os.path.join(BOXPLOT_CHECKPOINT_DIR, f"{group}__{safe_id}.npz")

def ensure_boxplot_checkpoint_dir():
    os.makedirs(BOXPLOT_CHECKPOINT_DIR, exist_ok=True)

def save_boxplot_genome_checkpoint(group, record_id, genome_length, entropy):
    """Save one completed genome immediately."""
    ensure_boxplot_checkpoint_dir()
    filename = boxplot_checkpoint_filename(group, record_id)
    temp_filename = filename + ".tmp.npz"
    np.savez(
        temp_filename,
        dataset=RESULT_PREFIX,
        group=group,
        record_id=record_id,
        genome_length=genome_length,
        k_min=BOXPLOT_MIN_K,
        k_max=K_MAX_ENTROPY,
        window_size=ENTROPY_WINDOW,
        stride=ENTROPY_STRIDE,
        entropy=entropy,
    )
    os.replace(temp_filename, filename)
    print("    Saved checkpoint:", os.path.basename(filename), flush=True)

def load_boxplot_checkpoints(group):
    """Load all completed genome checkpoints for one kingdom."""
    ensure_boxplot_checkpoint_dir()
    pattern = re.compile(rf"^{re.escape(group)}__.*\.npz$")
    checkpoints = {}
    for filename in os.listdir(BOXPLOT_CHECKPOINT_DIR):
        if not pattern.match(filename):
            continue
        full_path = os.path.join(BOXPLOT_CHECKPOINT_DIR, filename)
        try:
            data = np.load(full_path)
            if "dataset" in data:
                dataset = str(data["dataset"])
                if dataset != RESULT_PREFIX:
                    raise ValueError("Wrong dataset.")
            if "group" in data:
                stored_group = str(data["group"])
                if stored_group != group:
                    raise ValueError("Wrong group.")
            if "k_max" in data:
                if int(data["k_max"]) != K_MAX_ENTROPY:
                    raise ValueError("Wrong k_max.")
            if "k_min" in data:
                if int(data["k_min"]) != BOXPLOT_MIN_K:
                    raise ValueError("Wrong k_min.")
            if "window_size" in data:
                if int(data["window_size"]) != ENTROPY_WINDOW:
                    raise ValueError("Wrong entropy window.")
            if "stride" in data:
                if int(data["stride"]) != ENTROPY_STRIDE:
                    raise ValueError("Wrong entropy stride.")
            record_id = str(data["record_id"])
            checkpoints[record_id] = {
                "record_id": record_id,
                "genome_length": int(data["genome_length"]),
                "entropy": data["entropy"],
            }
        except Exception as e:
            print("[INVALID BOXPLOT CHECKPOINT]", os.path.basename(filename))
            print("Reason:", e)
    return checkpoints

def finalize_boxplot_group_from_checkpoints(group, checkpoints):
    """Combine per-genome checkpoint arrays into the final per-kingdom boxplot cache."""
    if len(checkpoints) < BOXPLOT_N_GENOMES:
        return None
    # Keep a deterministic order.
    records = sorted(checkpoints.values(), key=lambda item: item["record_id"])
    records = records[:BOXPLOT_N_GENOMES]
    values = np.concatenate([item["entropy"] for item in records]).astype(np.float64)
    filename = boxplot_entropy_filename(group)
    np.savez(
        filename,
        dataset=RESULT_PREFIX,
        group=group,
        k_min=BOXPLOT_MIN_K,
        k_max=K_MAX_ENTROPY,
        window_size=ENTROPY_WINDOW,
        stride=ENTROPY_STRIDE,
        min_length=ENTROPY_MIN_LENGTH,
        max_length=ENTROPY_MAX_LENGTH,
        n_genomes=len(records),
        entropy=values,
    )
    print(
        "Saved final boxplot cache:",
        os.path.basename(filename),
        "| genomes:",
        len(records),
        "| entropy values:",
        f"{len(values):,}",
        flush=True,
    )
    n_samples = sum(len(item["entropy"]) for item in records)
    return {"entropy": values, "n_genomes": len(records), "n_samples": n_samples}
# PROCESS ALL 50 GENOMES FOR BOX PLOT IMPORTANT: - Uses ALL 50 genomes in each kingdom.

def build_entropy_boxplot_data(required_groups):
    print()
    print("========================================")
    print("BUILDING ALL-GENOME ENTROPY BOXPLOT DATA")
    print("========================================")
    required_groups = set(required_groups)
    boxplot_data = {}
    missing_groups = []
    # FIRST: load final boxplot caches
    for group in GROUPS:
        if group not in required_groups:
            continue
        filename = boxplot_entropy_filename(group)
        if os.path.exists(filename):
            print("[BOXPLOT CACHE FOUND]", os.path.basename(filename))
            try:
                data = np.load(filename)
                # Compatibility checks
                if "dataset" in data:
                    dataset = str(data["dataset"])
                    if dataset != RESULT_PREFIX:
                        raise ValueError("Wrong dataset in boxplot cache.")
                if "k_max" in data:
                    if int(data["k_max"]) != K_MAX_ENTROPY:
                        raise ValueError("Boxplot entropy k_max mismatch.")
                if "k_min" in data:
                    if int(data["k_min"]) != BOXPLOT_MIN_K:
                        raise ValueError("Boxplot entropy k_min mismatch.")
                if "window_size" in data:
                    if int(data["window_size"]) != ENTROPY_WINDOW:
                        raise ValueError("Entropy window mismatch.")
                if "stride" in data:
                    if int(data["stride"]) != ENTROPY_STRIDE:
                        raise ValueError("Entropy stride mismatch.")
                if "n_genomes" in data:
                    if int(data["n_genomes"]) != BOXPLOT_N_GENOMES:
                        raise ValueError("Boxplot genome count mismatch.")
                boxplot_data[group] = {
                    "entropy": data["entropy"],
                    "n_genomes": int(data["n_genomes"]) if "n_genomes" in data else None,
                }
            except Exception as e:
                print("[INVALID BOXplot CACHE]", group)
                print("Reason:", e)
                missing_groups.append(group)
        else:
            print("[BOXPLOT CACHE MISSING]", group)
            missing_groups.append(group)
    # Nothing to calculate
    if len(missing_groups) == 0:
        print("\nAll six all-genome boxplot caches found.")
        return boxplot_data
    # Check per-genome checkpoints BEFORE scanning FASTA.
    print()
    print("Checking per-genome boxplot checkpoints...")
    print(f"Using up to {BOXPLOT_N_GENOMES} completed " "genome checkpoints per kingdom.")
    checkpoint_data = {}
    still_missing = []
    for group in missing_groups:
        checkpoints = load_boxplot_checkpoints(group)
        checkpoint_data[group] = checkpoints
        print(
            f"[{group}] completed checkpoints: " f"{len(checkpoints)}/{BOXPLOT_N_GENOMES}",
            flush=True,
        )
        # If all 50 are already checkpointed, there is no need to read the FASTA for this kingdom at all.
        if len(checkpoints) >= BOXPLOT_N_GENOMES:
            finalized = finalize_boxplot_group_from_checkpoints(group, checkpoints)
            if finalized is not None:
                boxplot_data[group] = finalized
                continue
        still_missing.append(group)
    missing_groups = still_missing
    # Nothing left after checkpoint recovery
    if len(missing_groups) == 0:
        print("\nAll missing boxplot data recovered " "from per-genome checkpoints.")
        return boxplot_data
    # Need FASTA for groups that are still incomplete.
    print()
    print("Need to process missing/incomplete groups:", missing_groups)
    print("Reading existing diverse FASTA...")
    print("Completed genomes will be SKIPPED using checkpoints.")
    # Sequential FASTA scan. Only one genome sequence is held in memory at a time.
    for record in SeqIO.parse(FASTA_FILE, "fasta"):
        group = get_group(record.id)
        if group not in missing_groups:
            continue
        checkpoints = checkpoint_data[group]
        # Reuse this genome's checkpoint instead of recalculating it.
        if record.id in checkpoints:
            print(
                f"[{group}] "
                f"checkpoint already exists: "
                f"{record.id} "
                f"-> skipping recalculation",
                flush=True,
            )
            continue
        # We count completed checkpoints, not FASTA records.
        completed_count = len(checkpoints)
        if completed_count >= BOXPLOT_N_GENOMES:
            continue
        print(
            f"\n[{group}] "
            f"boxplot genome "
            f"{completed_count + 1}/"
            f"{BOXPLOT_N_GENOMES}: "
            f"{record.id}",
            flush=True,
        )
        # Clean sequence
        seq = str(record.seq).upper()
        seq = "".join(b for b in seq if b in "ACGT")
        if len(seq) < ENTROPY_WINDOW:
            print("    Rejected: shorter than entropy window.")
            continue
        # Calculate local entropy for this genome
        result = voss_spectral_entropy_profile(
            seq, window_size=ENTROPY_WINDOW, stride=ENTROPY_STRIDE, min_k=BOXPLOT_MIN_K
        )
        if result is None:
            continue
        positions, entropy, smooth = result
        del positions
        del smooth
        # SAVE THIS GENOME IMMEDIATELY. This is the critical new checkpoint.
        save_boxplot_genome_checkpoint(
            group=group, record_id=record.id, genome_length=len(seq), entropy=entropy
        )
        # Add checkpoint to current in-memory state.
        checkpoints[record.id] = {
            "record_id": record.id,
            "genome_length": len(seq),
            "entropy": entropy,
        }
        print(
            f"    Completed genome "
            f"{len(checkpoints)}/"
            f"{BOXPLOT_N_GENOMES}"
            f" | entropy windows: "
            f"{len(entropy):,}",
            flush=True,
        )
        del entropy
        del result
        del seq
        gc.collect()
        # As soon as a kingdom reaches 50, create its final boxplot cache immediately.
        if len(checkpoints) >= BOXPLOT_N_GENOMES:
            finalized = finalize_boxplot_group_from_checkpoints(group, checkpoints)
            if finalized is not None:
                boxplot_data[group] = finalized
            # Remove this group from the active FASTA work.
            missing_groups.remove(group)
            print(
                f"\n[{group}] "
                f"FINAL boxplot cache created."
                f" No more calculation needed for this kingdom.",
                flush=True,
            )
        # Stop once every required group is complete.
        if len(missing_groups) == 0:
            print("\nAll missing boxplot genomes processed.", flush=True)
            break
    # Finalize groups already completed through checkpoints.
    for group in required_groups:
        if group in boxplot_data:
            continue
        checkpoints = checkpoint_data.get(group, {})
        if len(checkpoints) >= BOXPLOT_N_GENOMES:
            finalized = finalize_boxplot_group_from_checkpoints(group, checkpoints)
            if finalized is not None:
                boxplot_data[group] = finalized
    return boxplot_data
# PLOT ALL-GENOME ENTROPY BOXPLOT

def plot_entropy_boxplot(boxplot_data):
    print()
    print("========================================")
    print("PLOTTING ALL-GENOME ENTROPY BOXPLOT")
    print("========================================")
    data = []
    labels = []
    for group in GROUPS:
        if group not in boxplot_data:
            continue
        values = boxplot_data[group]["entropy"]
        if len(values) == 0:
            continue
        data.append(values)
        labels.append(group)
        print(
            f"{group}: "
            f"{boxplot_data[group].get('n_genomes', '?')} genomes | "
            f"{len(values):,} entropy observations"
        )
    if len(data) == 0:
        print("No boxplot data available.")
        return
    plt.figure(figsize=(11, 7))
    entropy_box = plt.boxplot(data, tick_labels=labels, showfliers=False, patch_artist=True)
    for patch, group in zip(entropy_box["boxes"], labels):
        patch.set_facecolor(KINGDOM_COLORS[group])
        patch.set_alpha(0.9)
    plt.xlabel("Kingdom")
    plt.ylabel("Normalized Shannon spectral entropy")
    plt.title(
        "Voss Shannon Spectral Entropy Distribution\n"
        f"First {BOXPLOT_N_GENOMES} completed genomes per kingdom, "
        f"k = {BOXPLOT_MIN_K}–{K_MAX_ENTROPY}"
    )
    # Let Matplotlib include the full range of all six distributions.
    plt.margins(y=0.05)
    plt.tight_layout()
    export_figure(plt.gcf(), "voss_shannon_spectral_entropy_distribution")
# BUILD / LOAD ENTROPY PROFILES

def build_entropy_profiles():
    print()
    print("========================================")
    print("SPECTRAL ENTROPY PROFILES")
    print("========================================")
    profiles = {}
    missing_groups = []
    # FIRST CHECK NEW ENTROPY CACHE FILES
    for group in GROUPS:
        filename = entropy_filename(group)
        if os.path.exists(filename):
            print("[ENTROPY CACHE FOUND]", os.path.basename(filename))
            try:
                profiles[group] = load_entropy_profile(filename)
            except Exception as e:
                print("[INVALID ENTROPY CACHE]", group)
                print("Reason:", e)
                missing_groups.append(group)
        else:
            print("[ENTROPY CACHE MISSING]", group)
            missing_groups.append(group)
    # ALL ENTROPY PROFILES CACHED
    if len(missing_groups) == 0:
        print("\nAll six 10–30 Mb entropy " "profiles are cached.")
        return profiles
    # FIND REPRESENTATIVES
    print("\nNeed representatives for:", missing_groups)
    representatives = get_entropy_representatives(missing_groups)
    # PROCESS ONLY MISSING GROUPS
    for group in missing_groups:
        if group not in representatives:
            print("Could not find a qualifying " "10–30 Mb genome for", group)
            continue
        record_id = representatives[group]["id"]
        seq = representatives[group]["sequence"]
        genome_length = representatives[group]["length"]
        print()
        print("----------------------------------------")
        print("Calculating entropy:", group)
        print("Representative:", record_id)
        print("Genome length:", f"{genome_length:,}", "bp")
        result = voss_spectral_entropy_profile(
            seq, window_size=PROFILE_WINDOW, stride=PROFILE_STRIDE, min_k=PROFILE_MIN_K
        )
        if result is None:
            continue
        positions, entropy, smooth = result
        profiles[group] = {
            "record_id": record_id,
            "genome_length": genome_length,
            "source": representatives[group]["source"],
            "position": positions,
            "entropy": entropy,
            "smooth": smooth,
        }
        save_entropy_profile(
            group,
            record_id,
            genome_length,
            positions,
            entropy,
            smooth,
            representatives[group]["source"],
            PROFILE_MIN_K,
            PROFILE_WINDOW,
            PROFILE_STRIDE,
        )
        # Free the large representative sequence
        del seq
        gc.collect()
    return profiles
# PLOT SPECTRAL ENTROPY PROFILE

def plot_spectral_entropy_profiles(profiles):
    print()
    print("========================================")
    print("PLOTTING VOSS SPECTRAL ENTROPY PROFILE")
    print("========================================")
    plt.figure(figsize=(12, 7))
    for group in GROUPS:
        if group not in profiles:
            continue
        profile = profiles[group]
        position = profile["position"]
        smooth = profile["smooth"]
        genome_length = profile["genome_length"]
        print(f"{group}: " f"{genome_length:,} bp")
        plt.plot(position, smooth, linewidth=1.5, color=KINGDOM_COLORS[group], label=group)
    plt.xlabel("Genomic position (bp)")
    plt.ylabel("Normalized Shannon spectral entropy")
    plt.title(
        "Voss Spectral Entropy Profile\n"
        f"Representative genomes: "
        f"10–30 Mb, first qualifying genome\n"
        f"Window = {PROFILE_WINDOW:,} bp, "
        f"Stride = {PROFILE_STRIDE:,} bp, "
        f"k = {PROFILE_MIN_K}–{K_MAX_ENTROPY}"
    )
    plt.ylim(0, 1.05)
    plt.legend(fontsize=11)
    plt.tight_layout()
    export_figure(plt.gcf(), "voss_spectral_entropy_profiles")
# KEEP ONLY THREE MAJOR Y-AXIS LABELS

def set_three_log_y_labels():
    ax = plt.gca()
    ymin, ymax = ax.get_ylim()
    # Choose three powers of ten inside the actual visible range.
    lo = int(np.ceil(np.log10(max(ymin, 1e-300))))
    hi = int(np.floor(np.log10(max(ymax, 1e-300))))
    if hi < lo:
        lo = int(np.floor(np.log10(max(ymin, 1e-300))))
        hi = lo + 2
    if hi - lo < 2:
        center = (lo + hi) // 2
        exponents = np.array([center - 1, center, center + 1])
    else:
        exponents = np.array([lo, int(np.round((lo + hi) / 2)), hi])
        # Ensure three distinct labels.
        if len(np.unique(exponents)) < 3:
            exponents = np.array([lo, lo + 1, hi])
    ticks = 10.0**exponents
    ax.set_yticks(ticks)
    ax.set_yticklabels([rf"$10^{{{e}}}$" for e in exponents], fontsize=8)
# DNA BETA EXPONENT SUMMARY

def plot_dna_beta(results):
    """Plot the fitted low-k spectral exponent for each DNA kingdom."""
    # Support this legacy standalone figure as well as the main workflow.
    set_kingdom_colors_from_results(results)
    beta_summary = []
    for group in GROUPS:
        if group not in results:
            continue
        k = results[group]["f"] * NFFT
        delta_energy = results[group]["Delta"]
        fit = best_fit_loglog(k, delta_energy, max_x=FIT_MAX_K)
        if fit is None:
            continue
        slope, intercept, beta, k_fit, energy_fit = fit
        log_k = np.log10(k_fit)
        log_energy = np.log10(energy_fit)
        residuals = log_energy - (slope * log_k + intercept)
        degrees_of_freedom = len(log_k) - 2
        denominator = np.sum((log_k - np.mean(log_k)) ** 2)
        if degrees_of_freedom > 0 and denominator > 0:
            beta_error = np.sqrt(np.sum(residuals**2) / degrees_of_freedom / denominator)
        else:
            beta_error = 0.0
        beta_summary.append((group, beta, beta_error))
    if len(beta_summary) == 0:
        print("No valid beta fits available.")
        return
    # Match the reference-style ranking: largest beta at the top.
    beta_summary.sort(key=lambda item: item[1], reverse=True)
    labels = [item[0] for item in beta_summary]
    beta_values = np.asarray([item[1] for item in beta_summary])
    beta_errors = np.asarray([item[2] for item in beta_summary])
    fig, ax = plt.subplots(figsize=(7, 6))
    bars = ax.barh(
        labels,
        beta_values,
        xerr=beta_errors,
        color=[KINGDOM_COLORS[group] for group in labels],
        capsize=4,
        error_kw={"ecolor": "black", "linewidth": 1},
    )
    ax.invert_yaxis()
    ax.set_xlabel(r"$\beta$ in $\Delta E(k) \propto k^{-\beta}$")
    ax.set_title("DNA Voss Spectral Exponent by Kingdom\n" f"Low-k log-log fit: k = 2–{FIT_MAX_K}")
    label_offset = max(0.01, 0.02 * (np.max(beta_values) - np.min(beta_values) + 1e-12))
    for bar, beta, error in zip(bars, beta_values, beta_errors):
        ax.text(
            beta + error + label_offset,
            bar.get_y() + bar.get_height() / 2,
            f"{beta:.3f}",
            va="center",
            fontsize=5,
        )
    plt.tight_layout()
    export_figure(fig, "voss_spectral_exponent_by_kingdom")
# PER-GENOME BETA CHECKPOINTS AND DISTRIBUTION

def beta_cache_filename(group):
    return os.path.join(SCRIPT_DIR, f"{BETA_CACHE_PREFIX}_{group}.npz")

def beta_checkpoint_filename(group, record_id):
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(record_id))
    return os.path.join(BETA_CHECKPOINT_DIR, f"{group}__{safe_id}.npz")

def save_beta_checkpoint(group, record_id, genome_length, beta):
    os.makedirs(BETA_CHECKPOINT_DIR, exist_ok=True)
    filename = beta_checkpoint_filename(group, record_id)
    temporary_filename = filename + ".tmp.npz"
    np.savez(
        temporary_filename,
        dataset=RESULT_PREFIX,
        group=group,
        record_id=record_id,
        genome_length=genome_length,
        nfft=NFFT,
        k_min=2,
        k_max=FIT_MAX_K,
        beta=beta,
    )
    os.replace(temporary_filename, filename)

def load_beta_checkpoints(group):
    os.makedirs(BETA_CHECKPOINT_DIR, exist_ok=True)
    checkpoints = {}
    pattern = re.compile(rf"^{re.escape(group)}__.*\.npz$")
    for filename in os.listdir(BETA_CHECKPOINT_DIR):
        if not pattern.match(filename):
            continue
        full_path = os.path.join(BETA_CHECKPOINT_DIR, filename)
        try:
            with np.load(full_path) as data:
                if str(data["dataset"]) != RESULT_PREFIX:
                    raise ValueError("wrong dataset")
                if str(data["group"]) != group:
                    raise ValueError("wrong group")
                if int(data["nfft"]) != NFFT:
                    raise ValueError("wrong NFFT")
                if int(data["k_min"]) != 2:
                    raise ValueError("wrong minimum k")
                if int(data["k_max"]) != FIT_MAX_K:
                    raise ValueError("wrong maximum k")
                record_id = str(data["record_id"])
                checkpoints[record_id] = float(data["beta"])
        except Exception as error:
            print("[INVALID BETA CHECKPOINT]", filename, "|", error)
    return checkpoints

def save_beta_group_cache(group, checkpoints):
    records = sorted(checkpoints.items())[:BETA_N_GENOMES]
    beta_values = np.asarray([beta for _, beta in records], dtype=np.float64)
    np.savez(
        beta_cache_filename(group),
        dataset=RESULT_PREFIX,
        group=group,
        nfft=NFFT,
        k_min=2,
        k_max=FIT_MAX_K,
        n_genomes=len(records),
        record_ids=np.asarray([record_id for record_id, _ in records]),
        beta=beta_values,
    )
    print(
        "Saved beta cache:",
        os.path.basename(beta_cache_filename(group)),
        f"| genomes: {len(records)}",
    )
    return beta_values

def load_beta_group_cache(group):
    filename = beta_cache_filename(group)
    if not os.path.exists(filename):
        return None
    try:
        with np.load(filename) as data:
            if str(data["dataset"]) != RESULT_PREFIX:
                raise ValueError("wrong dataset")
            if str(data["group"]) != group:
                raise ValueError("wrong group")
            if int(data["nfft"]) != NFFT:
                raise ValueError("wrong NFFT")
            if int(data["k_min"]) != 2 or int(data["k_max"]) != FIT_MAX_K:
                raise ValueError("wrong fit range")
            if int(data["n_genomes"]) != BETA_N_GENOMES:
                raise ValueError("wrong genome count")
            return data["beta"]
    except Exception as error:
        print("[INVALID BETA CACHE]", group, "|", error)
        return None

def build_beta_distribution_data():
    """Fit beta separately for 20 genomes per kingdom, with resuming."""
    print()
    print("========================================")
    print("BUILDING PER-GENOME BETA DISTRIBUTIONS")
    print("========================================")
    beta_data = {}
    checkpoints_by_group = {}
    missing_groups = []
    for group in GROUPS:
        cached_values = load_beta_group_cache(group)
        if cached_values is not None:
            beta_data[group] = cached_values
            print(f"[{group}] beta cache found: " f"{len(cached_values)}/{BETA_N_GENOMES} genomes")
            continue
        checkpoints = load_beta_checkpoints(group)
        checkpoints_by_group[group] = checkpoints
        print(f"[{group}] beta checkpoints: " f"{len(checkpoints)}/{BETA_N_GENOMES}", flush=True)
        if len(checkpoints) >= BETA_N_GENOMES:
            beta_data[group] = save_beta_group_cache(group, checkpoints)
        else:
            missing_groups.append(group)
    if len(missing_groups) == 0:
        return beta_data
    for record in SeqIO.parse(FASTA_FILE, "fasta"):
        if len(missing_groups) == 0:
            break
        group = get_group(record.id)
        if group not in missing_groups:
            continue
        checkpoints = checkpoints_by_group[group]
        if record.id in checkpoints:
            continue
        if len(checkpoints) >= BETA_N_GENOMES:
            continue
        seq = str(record.seq).upper()
        if len(seq) < max(MIN_LENGTH, NFFT):
            continue
        print(
            f"[{group}] beta genome " f"{len(checkpoints) + 1}/{BETA_N_GENOMES}: " f"{record.id}",
            flush=True,
        )
        result = voss_genome_windows(seq)
        if result is None:
            continue
        frequency, spectrum_sum, n_sections, s_inf = result
        delta_energy = spectrum_sum / n_sections - s_inf
        wave_number = frequency * NFFT
        fit = best_fit_loglog(wave_number, delta_energy, max_x=FIT_MAX_K, verbose=False)
        if fit is None:
            print("    Skipped: no valid k = 2–300 beta fit.")
            continue
        _, _, beta, _, _ = fit
        save_beta_checkpoint(group, record.id, len(seq), beta)
        checkpoints[record.id] = beta
        print(f"    Saved beta = {beta:.5f}", flush=True)
        if len(checkpoints) >= BETA_N_GENOMES:
            beta_data[group] = save_beta_group_cache(group, checkpoints)
            missing_groups.remove(group)
        gc.collect()
    for group in missing_groups:
        checkpoints = checkpoints_by_group[group]
        if len(checkpoints) >= BETA_N_GENOMES:
            beta_data[group] = save_beta_group_cache(group, checkpoints)
        else:
            print(
                f"[INCOMPLETE BETA DATA] {group}: " f"{len(checkpoints)}/{BETA_N_GENOMES} genomes"
            )
    return beta_data

def plot_dna_beta_distribution(beta_data):
    """Plot the mean and actual across-genome beta spread per kingdom."""
    # When this figure is called on its own, initialise the shared palette from its displayed beta means.
    if all(KINGDOM_COLORS[group] == "#808080" for group in GROUPS):
        set_kingdom_colors_from_beta(
            {group: np.mean(values) for group, values in beta_data.items() if len(values) > 0}
        )
    summary = []
    for group in GROUPS:
        if group not in beta_data:
            continue
        values = np.asarray(beta_data[group], dtype=np.float64)
        if len(values) == 0:
            continue
        spread = np.std(values, ddof=1) if len(values) > 1 else 0.0
        summary.append((group, values, np.mean(values), spread))
    if len(summary) == 0:
        print("No per-genome beta data available.")
        return
    summary.sort(key=lambda item: item[2], reverse=True)
    labels = [item[0] for item in summary]
    means = np.asarray([item[2] for item in summary])
    standard_deviations = np.asarray([item[3] for item in summary])
    fig, ax = plt.subplots(figsize=(7, 6))
    colors = [KINGDOM_COLORS[group] for group in labels]
    bars = ax.barh(
        labels,
        means,
        xerr=standard_deviations,
        color=colors,
        capsize=4,
        error_kw={"ecolor": "black", "linewidth": 1},
    )
    for index, (_, values, mean, _) in enumerate(summary):
        ax.text(
            mean + standard_deviations[index],
            bars[index].get_y() + bars[index].get_height() / 2,
            f"  {mean:.3f}",
            va="center",
            fontsize=8,
        )
    ax.invert_yaxis()
    ax.set_xlabel(r"$\beta$ in $\Delta E(k) \propto k^{-\beta}$")
    ax.set_title(
        "DNA Voss Spectral Exponent by Kingdom\n"
        f"Mean ± 1 SD across {BETA_N_GENOMES} genomes; k = 2–{FIT_MAX_K}"
    )
    ax.grid(axis="x", alpha=0.25)
    plt.tight_layout()
    export_figure(fig, "voss_spectral_exponent_distribution")
# Sample-size summary for the manuscript table.
SAMPLE_SIZE_TEX_FILE = "kingdom_sample_sizes.tex"

def collect_sample_sizes(results, beta_data, boxplot_data):
    """Gather per-kingdom genome and window counts for every panel."""
    rows = []
    for group in GROUPS:
        spectrum = results.get(group, {})
        entropy = boxplot_data.get(group, {})
        entropy_values = entropy.get("entropy")
        rows.append(
            {
                "group": group,
                "spectrum_genomes": spectrum.get("n_genomes"),
                "spectrum_windows": spectrum.get("n_windows"),
                "beta_genomes": len(beta_data[group]) if group in beta_data else None,
                "entropy_genomes": entropy.get("n_genomes"),
                "entropy_windows": len(entropy_values) if entropy_values is not None else None,
            }
        )
    return rows

def format_count(value):
    """Render a count for console output, or a dash when unavailable."""
    if value is None:
        return "-"
    return f"{value:,}"

def report_sample_sizes(results, beta_data, boxplot_data):
    """Print per-kingdom sample sizes and export a LaTeX table body."""
    print()
    print("========================================")
    print("SAMPLE SIZES PER KINGDOM")
    print("========================================")
    print(f"One sample = one non-overlapping {NFFT:,} bp window.")
    print(f"Entropy windows use window = stride = {ENTROPY_WINDOW:,} bp " f"(no overlap).")
    rows = collect_sample_sizes(results, beta_data, boxplot_data)
    header = (
        f"{'Kingdom':<14}"
        f"{'beta n':>10}"
        f"{'spec genomes':>15}"
        f"{'spec windows':>15}"
        f"{'ent genomes':>14}"
        f"{'ent windows':>14}"
        f"{'ent win/genome':>17}"
    )
    print()
    print(header)
    print("-" * len(header))
    for row in rows:
        if row["entropy_windows"] is not None and row["entropy_genomes"]:
            windows_per_genome = f"{row['entropy_windows'] / row['entropy_genomes']:,.1f}"
        else:
            windows_per_genome = "-"
        print(
            f"{row['group']:<14}"
            f"{format_count(row['beta_genomes']):>10}"
            f"{format_count(row['spectrum_genomes']):>15}"
            f"{format_count(row['spectrum_windows']):>15}"
            f"{format_count(row['entropy_genomes']):>14}"
            f"{format_count(row['entropy_windows']):>14}"
            f"{windows_per_genome:>17}"
        )
    # Column totals across every kingdom
    totals = {}
    for key in (
        "beta_genomes",
        "spectrum_genomes",
        "spectrum_windows",
        "entropy_genomes",
        "entropy_windows",
    ):
        present = [row[key] for row in rows if row[key] is not None]
        totals[key] = sum(present) if len(present) > 0 else None
    print("-" * len(header))
    print(
        f"{'TOTAL':<14}"
        f"{format_count(totals['beta_genomes']):>10}"
        f"{format_count(totals['spectrum_genomes']):>15}"
        f"{format_count(totals['spectrum_windows']):>15}"
        f"{format_count(totals['entropy_genomes']):>14}"
        f"{format_count(totals['entropy_windows']):>14}"
        f"{'':>17}"
    )
    write_sample_size_tex(rows, totals)
    return rows

def write_sample_size_tex(rows, totals):
    """Write a LaTeX tabular body that can be \\input into the manuscript."""
    os.makedirs(FIGURE_OUTPUT_DIR, exist_ok=True)
    filename = os.path.join(FIGURE_OUTPUT_DIR, SAMPLE_SIZE_TEX_FILE)
    def tex_count(value):
        # Plain digits so the LaTeX table stays usable.
        return str(value) if value is not None else "--"
    lines = [
        "% Auto-generated by genomic_spectral_analysis.py -- do not edit by hand.",
        f"% One sample = one non-overlapping {NFFT} bp window.",
        f"% Entropy windows: window = stride = {ENTROPY_WINDOW} bp, "
        f"k = {BOXPLOT_MIN_K}--{K_MAX_ENTROPY}.",
        f"% Beta fits: k = 2--{FIT_MAX_K}, NFFT = {NFFT}.",
        r"\begin{tabular}{lrrrr}",
        r"\hline",
        r"Kingdom & Genomes & Spectrum windows & " r"$\beta$ fits & Entropy windows \\",
        r"\hline",
    ]
    for row in rows:
        lines.append(
            f"{row['group']} & "
            f"{tex_count(row['entropy_genomes'])} & "
            f"{tex_count(row['spectrum_windows'])} & "
            f"{tex_count(row['beta_genomes'])} & "
            f"{tex_count(row['entropy_windows'])} "
            r"\\"
        )
    lines.extend(
        [
            r"\hline",
            f"Total & "
            f"{tex_count(totals['entropy_genomes'])} & "
            f"{tex_count(totals['spectrum_windows'])} & "
            f"{tex_count(totals['beta_genomes'])} & "
            f"{tex_count(totals['entropy_windows'])} "
            r"\\",
            r"\hline",
            r"\end{tabular}",
        ]
    )
    with open(filename, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print()
    print("Exported LaTeX sample-size table:", filename)
# COMBINED MULTI-PANEL SUMMARY FIGURE

def add_panel_label(ax, letter):
    ax.text(
        -0.12,
        1.0,
        letter,
        transform=ax.transAxes,
        fontsize=8,
        fontweight="bold",
        va="top",
        ha="left",
    )

def plot_combined_figure(results, beta_distribution_data, boxplot_data):
    """Publication-style summary: A = beta distribution summary B = Voss equal-symbol spectrum ΔS(f) C = entropy distribution"""
    fig = plt.figure(figsize=(7.2, 4.5))
    grid = fig.add_gridspec(
        2, 2, width_ratios=[1, 1.4], height_ratios=[1, 1], wspace=0.22, hspace=0.28
    )
    ax_beta = fig.add_subplot(grid[:, 0])
    ax_sf = fig.add_subplot(grid[0, 1])
    ax_entropy = fig.add_subplot(grid[1, 1])
    # Keep the beta-ranked VIBGYOR colour assignment consistent with all standalone figures.
    kingdom_colors = KINGDOM_COLORS
    # Panel A: mean beta ± sample SD across genomes
    beta_summary = []
    for group in GROUPS:
        if group not in beta_distribution_data:
            continue
        values = np.asarray(beta_distribution_data[group], dtype=np.float64)
        if len(values) == 0:
            continue
        beta_summary.append(
            (group, np.mean(values), np.std(values, ddof=1) if len(values) > 1 else 0.0)
        )
    beta_summary.sort(key=lambda item: item[1], reverse=True)
    beta_labels = [item[0] for item in beta_summary]
    beta_means_by_group = {group: mean for group, mean, _ in beta_summary}
    beta_means = np.asarray([item[1] for item in beta_summary])
    beta_stds = np.asarray([item[2] for item in beta_summary])
    beta_bars = ax_beta.barh(
        beta_labels,
        beta_means,
        xerr=beta_stds,
        color=[kingdom_colors[group] for group in beta_labels],
        capsize=4,
        error_kw={"ecolor": "black", "linewidth": 1},
    )
    ax_beta.tick_params(axis="y", labelsize=7)  # default ytick.labelsize is 6, +1
    ax_beta.invert_yaxis()
    ax_beta.set_xlabel(r"$\beta$")
    ax_beta.set_xlim(0, 0.8)
    ax_beta.xaxis.set_major_locator(MaxNLocator(nbins=4))
    ax_beta.tick_params(axis="x", labelsize=8)  # default xtick.labelsize is 6, +1
    for bar, mean, std in zip(beta_bars, beta_means, beta_stds):
        ax_beta.text(
            mean + std + 0.02,
            bar.get_y() + bar.get_height() / 2,
            f"{mean:.2f}",
            va="center",
            fontsize=6,
        )
    add_panel_label(ax_beta, "a")
    # Panel B: Voss equal-symbol spectrum ΔS(f)
    # Panel B offsets follow the SAME ordering as Panel A
    spectrum_offsets = {group: 10 ** (-2 * i) for i, group in enumerate(beta_labels)}
    spectrum_beta_labels = []
    for group in beta_labels:
        if group not in results:
            continue
        frequency = results[group]["f"]
        delta_spectrum = results[group]["Delta"]
        beta = beta_means_by_group[group]
        fit = fit_loglog_fixed_beta(frequency, delta_spectrum, max_x=FIT_MAX_K / NFFT, beta=beta)
        if fit is None:
            continue
        (slope, intercept, _, frequency_fit, _) = fit
        offset = spectrum_offsets[group]
        ax_sf.loglog(
            frequency,
            delta_spectrum * offset,
            ".",
            markersize=3,
            color=kingdom_colors[group],
            alpha=0.6,  # add this
        )
        fit_frequency = np.logspace(np.log10(frequency_fit[0]), np.log10(frequency_fit[-1]), 200)
        fit_spectrum = 10**intercept * fit_frequency**slope
        ax_sf.loglog(
            fit_frequency,
            fit_spectrum * offset,
            linewidth=1,
            color=kingdom_colors[group],
            alpha=0.65,
        )
        label_frequency = np.sqrt(frequency_fit[0] * frequency_fit[-1])
        label_spectrum = 10**intercept * label_frequency**slope * offset
        spectrum_beta_labels.append(
            (
                beta,
                slope,
                frequency_fit[0],
                frequency_fit[-1],
                intercept,
                offset,
                label_frequency,
                label_spectrum,
            )
        )
    ax_sf.set_xlabel("")
    fig.canvas.draw()
    bbox_b = ax_sf.get_position()
    bbox_c = ax_entropy.get_position()
    gap = bbox_b.y0 - bbox_c.y1
    axes_height = bbox_b.y1 - bbox_b.y0
    y_offset = -(0.5 * gap) / axes_height
    ax_sf.text(
        0.5,
        y_offset,
        r"$f$ (base$^{-1}$)",
        transform=ax_sf.transAxes,
        ha="center",
        va="top",
        fontsize=8.5,
    )
    ax_sf.set_ylabel(r"$E(f)$", labelpad=2, fontsize=9)  # was default (~4-6 depending on rcParams)
    spectrum_ymin, spectrum_ymax = ax_sf.get_ylim()
    ax_sf.set_ylim(spectrum_ymin * 0.85, spectrum_ymax * 1.15)
    plt.sca(ax_sf)
    set_three_log_y_labels()
    xmin, xmax = ax_sf.get_xlim()
    log_min = np.ceil(np.log10(xmin))
    log_max = np.floor(np.log10(xmax))
    tick_exponents = np.linspace(log_min, log_max, 3)
    tick_exponents = np.round(tick_exponents).astype(int)
    ax_sf.set_xticks(10.0**tick_exponents)
    ax_sf.tick_params(axis="x", labelsize=8)
    add_panel_label(ax_sf, "b")
    # Panel C: spectral entropy distribution by kingdom
    entropy_data = []
    entropy_labels = []
    for group in beta_labels:
        if group not in boxplot_data:
            continue
        values = boxplot_data[group]["entropy"]
        if len(values) == 0:
            continue
        entropy_data.append(values)
        entropy_labels.append(group)
    # Export the same entropy values shown in panel C.
    # Draw the boxplot median in black.
    entropy_box = ax_entropy.boxplot(
        entropy_data,
        tick_labels=entropy_labels,
        showfliers=False,
        patch_artist=True,
        medianprops={"color": "black", "linewidth": 1},
    )
    ax_entropy.tick_params(axis="x", labelsize=7)  # default is 6, +1
    entropy_colors = [kingdom_colors[group] for group in entropy_labels]
    for patch, color in zip(entropy_box["boxes"], entropy_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.9)
    ax_entropy.set_ylabel(r"$\tilde{H}$", fontsize=9)
    ax_entropy.yaxis.set_major_locator(MaxNLocator(nbins=4))
    ax_entropy.margins(y=0.05)
    ax_entropy.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:.2f}"))
    ax_entropy.tick_params(axis="y", labelsize=8)
    add_panel_label(ax_entropy, "c")
    # Set the figure margins explicitly.
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.14, top=0.94, wspace=0.22, hspace=0.28)
    # Export average spectral entropy and sample size.
    entropy_xlsx_path = os.path.join(
        FIGURE_OUTPUT_DIR, "hydrodynamic_spectral_entropy_averages.xlsx"
    )
    wb_entropy = Workbook()
    ws_entropy = wb_entropy.active
    ws_entropy.title = "Entropy Summary"
    ws_entropy.append(
        [
            "Group",
            "Number of genomes",
            "Number of 65,536-bp entropy windows",
            "Average hydrodynamic spectral entropy",
        ]
    )
    for group in beta_labels:
        if group not in boxplot_data:
            continue
        values = np.asarray(boxplot_data[group]["entropy"], dtype=np.float64)
        if len(values) == 0:
            continue
        n_genomes = boxplot_data[group].get("n_genomes", "")
        n_samples = boxplot_data[group].get("n_samples", len(values))
        average_entropy = float(np.mean(values))
        ws_entropy.append([group, n_genomes, n_samples, average_entropy])
    wb_entropy.save(entropy_xlsx_path)
    print("Exported entropy summary:", entropy_xlsx_path)
    fig.canvas.draw()
    for (
        beta,
        slope,
        frequency_start,
        frequency_end,
        intercept,
        offset,
        label_frequency,
        label_spectrum,
    ) in spectrum_beta_labels:
        point_start = ax_sf.transData.transform(
            [frequency_start, 10**intercept * frequency_start**slope * offset]
        )
        point_end = ax_sf.transData.transform(
            [frequency_end, 10**intercept * frequency_end**slope * offset]
        )
        angle = np.degrees(np.arctan2(point_end[1] - point_start[1], point_end[0] - point_start[0]))
        # Offset perpendicular to the line in screen space.
        angle_rad = np.radians(angle)
        label_offset_pts = 6.0
        offset_x = label_offset_pts * (-np.sin(angle_rad))
        offset_y = label_offset_pts * np.cos(angle_rad)
        if offset_y < 0:
            offset_x = -offset_x
            offset_y = -offset_y
        ax_sf.annotate(
            rf"$\beta$ = {beta:.2f}",
            xy=(label_frequency, label_spectrum),
            xytext=(offset_x, offset_y),
            textcoords="offset points",
            fontsize=6,
            color="black",
            ha="center",
            va="center",
            rotation=angle,
            rotation_mode="anchor",
        )
    export_figure(fig, "diverse_voss_spectral_analysis_summary", exact_size=True)
    return fig
# MAIN
if __name__ == "__main__":
    print()
    print("========================================")
    print("DIVERSE VOSS DATASET ANALYSIS")
    print("========================================")
    print("FASTA:", FASTA_FILE)
    print("Dataset prefix:", RESULT_PREFIX)
    print("NFFT:", NFFT)
    print("Target genomes/group:", N_GENOMES)
    print("Current boxplot genomes/group:", BOXPLOT_N_GENOMES)
    print("Boxplot entropy window:", ENTROPY_WINDOW)
    print("Boxplot entropy stride:", ENTROPY_STRIDE)
    print("Representative profile window:", PROFILE_WINDOW)
    print("Representative profile stride:", PROFILE_STRIDE)
    print("Representative entropy range:", f"k = {PROFILE_MIN_K} to {K_MAX_ENTROPY}")
    print("Representative profile minimum k:", PROFILE_MIN_K)
    print("Boxplot low-k mute remains:", f"{ENTROPY_MUTE_FRACTION:.2%}")
    print("Boxplot checkpoint directory:", BOXPLOT_CHECKPOINT_DIR)
    print("Entropy size range:", f"{ENTROPY_MIN_LENGTH:,}", "to", f"{ENTROPY_MAX_LENGTH:,}", "bp")
    # STEP 1: CHECK MAIN VOSS NPZ FILES FIRST
    print()
    print("========================================")
    print("CHECKING DIVERSE VOSS NPZ CACHE")
    print("========================================")
    results = {}
    missing_groups = []
    for group in GROUPS:
        filename = result_filename(group)
        if os.path.exists(filename):
            print("[FOUND]", os.path.basename(filename))
            try:
                results[group] = load_cached_result(filename)
                if "n_windows" in results[group]:
                    print("       windows:", results[group]["n_windows"])
                if "n_genomes" in results[group]:
                    print("       genomes:", results[group]["n_genomes"])
            except Exception as e:
                print("[INVALID CACHE]", os.path.basename(filename))
                print("Reason:", e)
                missing_groups.append(group)
        else:
            print("[MISSING]", os.path.basename(filename))
            missing_groups.append(group)
    # STEP 2: MAIN VOSS RESULTS
    if len(missing_groups) == 0:
        print()
        print("All six main Voss NPZ files found.")
        print("Skipping expensive 50-genome Voss FFT.")
    else:
        print()
        print("Missing main Voss results:", missing_groups)
        categories = read_fasta_categories()
        print()
        print("DIVERSE GENOME COUNTS")
        for group in GROUPS:
            print(f"{group:15s}: " f"{len(categories[group])}")
        for group in missing_groups:
            if len(categories[group]) == 0:
                continue
            out = category_voss(categories[group], group)
            if out is not None:
                f, S, D = out
                results[group] = {"f": f, "S": S, "Delta": D}
        del categories
        gc.collect()
    # Derive one shared VIBGYOR mapping before any figures are drawn.
    set_kingdom_colors_from_results(results)
    # STEP 3: MAIN VOSS ΔS(f)
    print()
    print("Creating Voss ΔS(f)...")
    plt.figure(figsize=(10, 10))
    slope_labels_s = []
    for i, group in enumerate(GROUPS):
        if group not in results:
            continue
        f = results[group]["f"]
        D = results[group]["Delta"]
        fit = best_fit_loglog(f, D, max_x=FIT_MAX_K / NFFT)
        if fit is None:
            continue
        (slope, intercept, beta, x_fit, y_fit) = fit
        # Explicit vertical separation so spectra do not overlap.
        OFFSET = {
            "Bacteria": 1e0,
            "Plants": 1e-2,
            "Mammals": 1e-4,
            "Insects": 1e-6,
            "Worms": 1e-8,
            "ColdBlooded": 1e-10,
        }
        offset = OFFSET[group]
        # Complete spectrum
        plt.loglog(f, D * offset, ".", markersize=3, color=KINGDOM_COLORS[group])
        # Fixed 100-point best-fit line
        xx = np.logspace(np.log10(x_fit[0]), np.log10(x_fit[-1]), 200)
        yy = 10**intercept * xx**slope
        plt.loglog(xx, yy * offset, linewidth=1, color=KINGDOM_COLORS[group], alpha=0.65)
        # Save slope-label information.
        x_label = np.sqrt(x_fit[0] * x_fit[-1])
        y_line = 10**intercept * x_label**slope * offset
        slope_labels_s.append((slope, x_fit[0], x_fit[-1], intercept, offset, x_label, y_line))
    plt.xlabel("f (base$^{-1}$)")
    plt.ylabel(r"$\Delta S_\Sigma(f)$ (offset)")
    plt.title("Diverse Voss Equal-Symbol Spectrum\n" f"NFFT={NFFT}, 50 genomes/group")
    # Tighten the visible y-range around the actual plotted spectra.
    ax = plt.gca()
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin * 0.85, ymax * 1.15)
    # Show only three major y-axis labels.
    set_three_log_y_labels()
    # Finish the layout FIRST.
    plt.tight_layout()
    fig = plt.gcf()
    fig.canvas.draw()
    # Add slope labels using the actual final display angle of each fitted line.
    for slope, x0, x1, intercept, offset, x_label, y_line in slope_labels_s:
        p0 = ax.transData.transform([x0, 10**intercept * x0**slope * offset])
        p1 = ax.transData.transform([x1, 10**intercept * x1**slope * offset])
        angle = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
        plt.annotate(
            f"slope = {slope:.3f}",
            xy=(x_label, y_line),
            xytext=(0, 8),
            textcoords="offset points",
            fontsize=11,
            color="black",
            ha="center",
            va="bottom",
            rotation=angle,
            rotation_mode="anchor",
        )
    export_figure(fig, "diverse_voss_equal_symbol_spectrum")
    # STEP 4: MAIN VOSS ΔE(k)
    print()
    print("Creating Voss ΔE(k)...")
    plt.figure(figsize=(10, 10))
    slope_labels_k = []
    for i, group in enumerate(GROUPS):
        if group not in results:
            continue
        k = results[group]["f"] * NFFT
        D = results[group]["Delta"]
        fit = best_fit_loglog(k, D, max_x=FIT_MAX_K)
        if fit is None:
            continue
        (slope, intercept, beta, k_fit, D_fit) = fit
        # Explicit vertical separation so spectra do not overlap.
        OFFSET = {
            "Bacteria": 1e0,
            "Plants": 1e-2,
            "Mammals": 1e-4,
            "Insects": 1e-6,
            "Worms": 1e-8,
            "ColdBlooded": 1e-10,
        }
        offset = OFFSET[group]
        # Complete spectrum
        plt.loglog(k, D * offset, ".", markersize=3, color=KINGDOM_COLORS[group])
        # Fixed 100-point best-fit line
        kk = np.logspace(np.log10(k_fit[0]), np.log10(k_fit[-1]), 200)
        yy = 10**intercept * kk**slope
        plt.loglog(kk, yy * offset, linewidth=1, color=KINGDOM_COLORS[group], alpha=0.65)
        # Save slope-label information.
        k_label = np.sqrt(k_fit[0] * k_fit[-1])
        y_line = 10**intercept * k_label**slope * offset
        slope_labels_k.append((slope, k_fit[0], k_fit[-1], intercept, offset, k_label, y_line))
    plt.xlabel("wave number k")
    plt.ylabel(r"$\Delta E(k)$ (offset)")
    plt.title("Diverse Voss Equal-Symbol Energy Spectrum\n" f"NFFT={NFFT}, 50 genomes/group")
    # Tighten the visible y-range around the actual plotted spectra.
    ax = plt.gca()
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin * 0.85, ymax * 1.15)
    # Show only three major y-axis labels.
    set_three_log_y_labels()
    # Finish layout BEFORE measuring the visual angle.
    plt.tight_layout()
    fig = plt.gcf()
    fig.canvas.draw()
    # Add slope labels using the actual final display angle of each fitted line.
    for slope, x0, x1, intercept, offset, x_label, y_line in slope_labels_k:
        p0 = ax.transData.transform([x0, 10**intercept * x0**slope * offset])
        p1 = ax.transData.transform([x1, 10**intercept * x1**slope * offset])
        angle = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
        plt.annotate(
            f"slope = {slope:.3f}",
            xy=(x_label, y_line),
            xytext=(0, 8),
            textcoords="offset points",
            fontsize=11,
            color="black",
            ha="center",
            va="bottom",
            rotation=angle,
            rotation_mode="anchor",
        )
    export_figure(fig, "diverse_voss_equal_symbol_energy_spectrum")
    # STEP 5: PER-GENOME DNA BETA DISTRIBUTION
    beta_distribution_data = build_beta_distribution_data()
    if len(beta_distribution_data) > 0:
        plot_dna_beta_distribution(beta_distribution_data)
    # Step 6: one spectral-entropy profile per kingdom.
    profiles = build_entropy_profiles()
    # STEP 7: PLOT ENTROPY PROFILE
    if len(profiles) > 0:
        plot_spectral_entropy_profiles(profiles)
    # Step 8: entropy boxplot for every genome.
    boxplot_required_groups = GROUPS
    boxplot_data = build_entropy_boxplot_data(boxplot_required_groups)
    if len(boxplot_data) > 0:
        plot_entropy_boxplot(boxplot_data)
    # Step 8b: sample sizes for the manuscript table.
    report_sample_sizes(results, beta_distribution_data, boxplot_data)
    # STEP 9: COMBINED MULTI-PANEL SUMMARY
    if len(beta_distribution_data) > 0 and len(boxplot_data) > 0:
        plot_combined_figure(results, beta_distribution_data, boxplot_data)
    # DONE
    print()
    print("========================================")
    print("DIVERSE VOSS ANALYSIS COMPLETE")
    print("========================================")
