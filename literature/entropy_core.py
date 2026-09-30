"""
entropy_core.py — Shared entropy calculation module.

All entropy-related functions live here. Other scripts import from this module.

POS methods require spaCy:  uv add spacy && uv pip install en_core_web_sm@...

Functions:
    - calculate_shannon_entropy(text)
    - text_to_timeseries(text, method, alpha_only)
    - text_to_wordsum_signal(text)
    - calculate_hydrodynamic_entropy(time_series)
    - calculate_hydrodynamic_entropy_filtered(time_series, filter_type, cutoff_frac)
    - normalized_entropy(entropy_val, n)
    - smooth_signal(signal, window)
    - sliding_window_entropy(text, ...)
    - extract_random_chunks(text, ...)
    - compute_chunk_entropies(chunks, ...)
    - spectral_similarity(spec_a, spec_b)
    - entropy_distance(result_a, result_b)
"""
import math
import re
import random
import collections
import numpy as np

# ─── POS Tag Mapping (Universal POS → integer) ─────────────────────────────
# Grouped loosely: content words (1-4), function words (5-10), other (11-14)
UPOS_MAP = {
    'NOUN': 1, 'PROPN': 1,
    'VERB': 2, 'AUX': 2,
    'ADJ': 3,
    'ADV': 4,
    'PRON': 5,
    'DET': 6,
    'ADP': 7,
    'NUM': 8,
    'CCONJ': 9, 'SCONJ': 9,
    'PART': 10,
    'INTJ': 11,
    'SYM': 12,
    'X': 13,
    'PUNCT': 0, 'SPACE': 0,
}

_spacy_nlp = None  # lazy-loaded

def _get_spacy():
    """Lazy-load spaCy model (en_core_web_sm)."""
    global _spacy_nlp
    if _spacy_nlp is None:
        import spacy
        _spacy_nlp = spacy.load('en_core_web_sm')
        _spacy_nlp.max_length = 2_000_000  # allow long texts
    return _spacy_nlp


def clean_text(text):
    """Strip Gutenberg structural artifacts and bracketed metadata."""
    import re
    text = re.sub(r'\[Illustration:.*?\]', '', text, flags=re.DOTALL)
    text = re.sub(r'\[.*?\]', '', text, flags=re.DOTALL)
    return text





# ─── Core Entropy Functions ─────────────────────────────────────────────────

def calculate_shannon_entropy(text):
    """
    Shannon entropy: H(X) = -Σ p(x) log₂ p(x)
    """
    if not text:
        return 0.0
    counts = collections.Counter(text)
    total = len(text)
    probs = [c / total for c in counts.values()]
    return -sum(p * math.log2(p) for p in probs)


def text_to_timeseries(text, method='ascii', alpha_only=False):
    """
    Convert text to numerical time series.

    Args:
        text: Input text string.
        method:
            'ascii'      — ord(c) for each character (32-126 range)
            'ascii_norm' — ASCII normalized to [0, 1]
            'sequential' — a/A=1, b/B=2, ..., z/Z=26 (pure identity, no encoding bias)
            'frequency'  — map each char to its count in the text
            'wordsum'    — sum of ASCII values per word (one value per word)
            'word_length'— length of each word (one value per word)
            'pos'        — Universal POS tag integer per word (requires spaCy)
            'dep_depth'  — syntactic tree depth per word (requires spaCy)
        alpha_only: If True, strip non-alphabetic characters before mapping.

    Returns:
        np.array of float values.
    """
    if alpha_only:
        text = re.sub(r'[^a-zA-Z]', '', text)

    if method == 'ascii':
        return np.array([ord(c) for c in text], dtype=float)
    elif method == 'ascii_norm':
        vals = np.array([ord(c) for c in text], dtype=float)
        vmin, vmax = vals.min(), vals.max()
        if vmax > vmin:
            vals = (vals - vmin) / (vmax - vmin)
        return vals
    elif method == 'sequential':
        # a/A=1, b/B=2, ..., z/Z=26. Non-alpha chars → 0 (or skipped if alpha_only)
        vals = []
        for c in text:
            if c.isalpha():
                vals.append(ord(c.lower()) - ord('a') + 1)
            else:
                vals.append(0)  # non-alpha placeholder
        return np.array(vals, dtype=float)
    elif method == 'frequency':
        counts = collections.Counter(text)
        return np.array([counts[c] for c in text], dtype=float)
    elif method == 'wordsum':
        return text_to_wordsum_signal(text)[0]
    elif method == 'word_length':
        words = re.findall(r'[a-zA-Z]+', text)
        return np.array([len(w) for w in words], dtype=float) if words else np.array([])
    elif method == 'pos':
        return text_to_pos_signal(text, mode='pos')
    elif method == 'dep_depth':
        return text_to_pos_signal(text, mode='dep_depth')
    else:
        raise ValueError(f"Unknown method: {method}")


def text_to_wordsum_signal(text):
    """
    Sum ASCII values per word → one value per word.
    Captures word-level structure (length + character composition).
    Returns (signal_array, word_list).
    """
    words = re.findall(r'[a-zA-Z]+', text)  # alpha words only
    if not words:
        return np.array([]), []
    signal = np.array([sum(ord(c) for c in w) for w in words], dtype=float)
    return signal, words


def text_to_pos_signal(text, mode='pos'):
    """
    Convert text to a time series based on POS tags or dependency depth.

    Args:
        text: Input text string.
        mode: 'pos'       — map each word to its UPOS integer (NOUN=1, VERB=2, ...)
              'dep_depth' — map each word to its depth in the dependency tree

    Returns:
        np.array of float values (one per non-punctuation token).
    """
    nlp = _get_spacy()
    doc = nlp(text)

    if mode == 'pos':
        # Map each token to its UPOS integer, skip PUNCT/SPACE
        vals = [UPOS_MAP.get(tok.pos_, 13) for tok in doc if tok.pos_ not in ('PUNCT', 'SPACE')]
        return np.array(vals, dtype=float)

    elif mode == 'dep_depth':
        # Compute depth: number of hops to root
        def _depth(token):
            d = 0
            while token.head != token:
                d += 1
                token = token.head
            return d

        vals = [_depth(tok) for tok in doc if tok.pos_ not in ('PUNCT', 'SPACE')] # debug 
        return np.array(vals, dtype=float)

    else:
        raise ValueError(f"Unknown POS mode: {mode}")


def calculate_hydrodynamic_entropy(time_series):
    """
    Hydrodynamic Entropy from DFT energy spectrum:
        S_H = -Σ p_k log₂(p_k)
    where p_k = E(k) / Σ E(k), E(k) = |FFT(k)|²

    Returns: (entropy_float, energy_spectrum_array)
    """
    if len(time_series) == 0:
        return 0.0, np.array([])
    ts = time_series - np.mean(time_series)
    fft_vals = np.fft.fft(ts)
    energy = np.abs(fft_vals) ** 2
    total = np.sum(energy)
    if total == 0:
        return 0.0, energy
    probs = energy / total
    mask = probs > 0
    entropy = -np.sum(probs[mask] * np.log2(probs[mask]))
    return float(entropy), energy


def calculate_hydrodynamic_entropy_filtered(time_series, filter_type='lowpass', cutoff_frac=0.5):
    """
    Hydro Entropy after frequency filtering.

    filter_type: 'lowpass' | 'highpass' | 'bandpass'
    cutoff_frac: fraction of Nyquist frequency (0.0 to 1.0)

    Returns: (entropy, filtered_energy, mask)
    """
    if len(time_series) == 0:
        return 0.0, np.array([]), np.array([])

    ts = time_series - np.mean(time_series)
    fft_vals = np.fft.fft(ts)
    freqs = np.fft.fftfreq(len(fft_vals))
    nyquist = 0.5

    if filter_type == 'lowpass':
        fmask = np.abs(freqs) <= cutoff_frac * nyquist
    elif filter_type == 'highpass':
        fmask = np.abs(freqs) >= cutoff_frac * nyquist
    elif filter_type == 'bandpass':
        low = cutoff_frac * 0.3 * nyquist
        high = cutoff_frac * nyquist
        fmask = (np.abs(freqs) >= low) & (np.abs(freqs) <= high)
    else:
        raise ValueError(f"Unknown filter: {filter_type}")

    fft_filtered = fft_vals * fmask
    energy = np.abs(fft_filtered) ** 2
    total = np.sum(energy)
    if total == 0:
        return 0.0, energy, fmask
    probs = energy / total
    nonzero = probs > 0
    entropy = -np.sum(probs[nonzero] * np.log2(probs[nonzero]))
    return float(entropy), energy, fmask


# ─── Normalization & Smoothing ──────────────────────────────────────────────

def normalized_entropy(entropy_val, n):
    """Normalize entropy by log₂(N) to get a 0-1 value."""
    if n <= 1:
        return 0.0
    return entropy_val / math.log2(n)


def smooth_signal(signal, window=5):
    """
    Simple moving-average smoothing.
    window: number of points to average over (odd recommended).
    """
    if len(signal) < window:
        return signal
    kernel = np.ones(window) / window
    return np.convolve(signal, kernel, mode='same')


# ─── Flow & Chunk Analysis ──────────────────────────────────────────────────

def sliding_window_entropy(text, window_size=5000, step_size=2500,
                           method='ascii', alpha_only=False):
    """
    Compute Shannon and Hydro entropy over sliding windows.
    Returns (positions, shannons, hydros, hydros_norm) arrays.
    """
    positions, shannons, hydros, hydros_norm = [], [], [], []

    for i in range(0, len(text) - window_size, step_size):
        chunk = text[i:i + window_size]
        shannon = calculate_shannon_entropy(chunk)
        ts = text_to_timeseries(chunk, method=method, alpha_only=alpha_only)
        if len(ts) < 2:
            continue
        hydro, _ = calculate_hydrodynamic_entropy(ts)
        h_norm = normalized_entropy(hydro, len(ts))

        positions.append(i + window_size // 2)
        shannons.append(shannon)
        hydros.append(hydro)
        hydros_norm.append(h_norm)

    return (np.array(positions), np.array(shannons),
            np.array(hydros), np.array(hydros_norm))


def extract_random_chunks(text, n_chunks=20, chunk_size=5000, seed=42):
    """Extract random non-overlapping chunks from the text."""
    random.seed(seed)
    max_start = len(text) - chunk_size
    starts = sorted(random.sample(
        range(0, max_start, chunk_size),
        min(n_chunks, max_start // chunk_size)
    ))
    return [(start, text[start:start + chunk_size]) for start in starts]


def compute_chunk_entropies(chunks, method='ascii', alpha_only=False):
    """Compute entropy for each chunk. Returns list of result dicts."""
    results = []
    for start, chunk in chunks:
        shannon = calculate_shannon_entropy(chunk)
        ts = text_to_timeseries(chunk, method=method, alpha_only=alpha_only)
        hydro, spectrum = calculate_hydrodynamic_entropy(ts)
        h_norm = normalized_entropy(hydro, len(ts))
        results.append({
            'start': start,
            'shannon': shannon,
            'hydro': hydro,
            'hydro_norm': h_norm,
            'spectrum': spectrum,
        })
    return results


def spectral_similarity(spec_a, spec_b):
    """Cosine similarity between two energy spectra (handles different lengths)."""
    min_len = min(len(spec_a), len(spec_b))
    a, b = spec_a[:min_len], spec_b[:min_len]
    norm_a = a / (np.linalg.norm(a) + 1e-12)
    norm_b = b / (np.linalg.norm(b) + 1e-12)
    return float(np.dot(norm_a, norm_b))


def entropy_distance(result_a, result_b):
    """Euclidean distance in (Shannon, Hydro_norm) space."""
    return float(np.sqrt(
        (result_a['shannon'] - result_b['shannon']) ** 2 +
        (result_a['hydro_norm'] - result_b['hydro_norm']) ** 2
    ))
