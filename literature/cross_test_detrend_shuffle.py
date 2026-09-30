"""
Cross-test: Detrending × Sentence Shuffle
Compare all 4 combinations to fully decompose the signal.
"""
import os, sys, random
import numpy as np
import spacy
sys.path.insert(0, os.path.dirname(__file__))
from entropy_core import calculate_hydrodynamic_entropy, normalized_entropy, smooth_signal

def dep_depth(tok):
    d = 0
    while tok.head != tok:
        d += 1
        tok = tok.head
        if d > 100: break
    return d

def compute_spectrum(series):
    if len(series) < 20:
        return 0, 0, np.array([]), np.array([]), np.array([])
    h_raw, energy = calculate_hydrodynamic_entropy(series)
    n = len(energy)
    h_norm = normalized_entropy(h_raw, n)
    k = np.arange(1, n//2)
    e = energy[1:n//2]
    e_smooth = smooth_signal(e, window=max(3, len(e)//50))
    valid = (e_smooth > 0) & (k > 0)
    beta = 0.0
    if np.sum(valid) > 10:
        beta, _ = np.polyfit(np.log10(k[valid]), np.log10(e_smooth[valid]), 1)
    return h_norm, beta, k, e, e_smooth

BASE = os.path.dirname(__file__)
fp = os.path.join(BASE, 'texts', 'gutenberg', '1342_pride_and_prejudice.txt')
with open(fp, 'r', encoding='utf-8') as f:
    text = f.read()[:200_000]

nlp = spacy.load("en_core_web_sm")
nlp.max_length = 300_000
doc = nlp(text)
sentences = list(doc.sents)

# Build per-sentence depth arrays
sent_depths = []
for s in sentences:
    depths = [dep_depth(t) for t in s if t.pos_ not in ('PUNCT', 'SPACE')]
    if depths:
        sent_depths.append(depths)

N = 10000

# ── Condition 1: Raw + Linear (baseline) ──
raw_linear = []
for d in sent_depths:
    raw_linear.extend(d)
raw_linear = np.array(raw_linear[:N], dtype=float)

# ── Condition 2: Raw + Shuffled ──
random.seed(42)
shuffled_order = list(sent_depths)
random.shuffle(shuffled_order)
raw_shuffled = []
for d in shuffled_order:
    raw_shuffled.extend(d)
raw_shuffled = np.array(raw_shuffled[:N], dtype=float)

# ── Condition 3: Detrended + Linear ──
det_linear = []
for d in sent_depths:
    m = np.mean(d)
    det_linear.extend([x - m for x in d])
det_linear = np.array(det_linear[:N], dtype=float)

# ── Condition 4: Detrended + Shuffled ──
random.seed(42)
shuffled_order2 = list(sent_depths)
random.shuffle(shuffled_order2)
det_shuffled = []
for d in shuffled_order2:
    m = np.mean(d)
    det_shuffled.extend([x - m for x in d])
det_shuffled = np.array(det_shuffled[:N], dtype=float)

# Compute all spectra
h1, b1, _, _, _ = compute_spectrum(raw_linear)
h2, b2, _, _, _ = compute_spectrum(raw_shuffled)
h3, b3, _, _, _ = compute_spectrum(det_linear)
h4, b4, _, _, _ = compute_spectrum(det_shuffled)

print("="*65)
print("  FULL 2×2 DECOMPOSITION: Detrending × Sentence Shuffle")
print("="*65)
print()
print(f"  {'Condition':<35} {'β':>8} {'H_norm':>8}")
print(f"  {'─'*35} {'─'*8} {'─'*8}")
print(f"  {'1. Raw + Linear (baseline)':<35} {b1:>8.3f} {h1:>8.3f}")
print(f"  {'2. Raw + Shuffled':<35} {b2:>8.3f} {h2:>8.3f}")
print(f"  {'3. Detrended + Linear':<35} {b3:>8.3f} {h3:>8.3f}")
print(f"  {'4. Detrended + Shuffled':<35} {b4:>8.3f} {h4:>8.3f}")
print()
print("  Interpretation:")
print(f"    Shuffle effect on RAW:        Δβ = {b2-b1:+.3f} (should be ~0, no narrative memory)")
print(f"    Shuffle effect on DETRENDED:  Δβ = {b4-b3:+.3f} (should also be ~0)")
print(f"    Detrending effect on LINEAR:  Δβ = {b3-b1:+.3f} (removes sentence-boundary power)")
print(f"    Detrending effect on SHUFFLED:Δβ = {b4-b2:+.3f} (same removal)")
print()
if abs(b3 - b4) < 0.05:
    print("  ✓ Conditions 3 & 4 match: detrended signal is immune to shuffle.")
    print("    This confirms the surviving β is purely intra-sentence structure.")
else:
    print("  ✗ Conditions 3 & 4 differ: unexpected inter-sentence residual correlation.")
