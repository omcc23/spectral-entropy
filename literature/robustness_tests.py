"""
Reviewer-required ablation robustness tests:
1. Multi-text 2×2 decomposition with error bars (10+ texts)
2. Sentence shuffle on structurally heterogeneous texts (Shakespeare, Faust)
3. Sentence length distribution shape control (Gaussian resampling)
4. Mean sentence length statistics for k-range justification
"""
import os, sys, random
import numpy as np
import spacy
sys.path.insert(0, os.path.dirname(__file__))
from entropy_core import calculate_hydrodynamic_entropy, normalized_entropy, smooth_signal

BASE = os.path.dirname(__file__)
N = 10000

def dep_depth(tok):
    d = 0
    while tok.head != tok:
        d += 1
        tok = tok.head
        if d > 100: break
    return d

def compute_spectrum(series):
    if len(series) < 20:
        return 0, 0
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
    return h_norm, beta

def decompose_text(doc, n_words=10000):
    """Run full 2×2 decomposition on a parsed spaCy doc. Returns dict."""
    sentences = list(doc.sents)
    
    # Build per-sentence depth arrays
    sent_depths = []
    for s in sentences:
        depths = [dep_depth(t) for t in s if t.pos_ not in ('PUNCT', 'SPACE')]
        if depths:
            sent_depths.append(depths)
    
    if len(sent_depths) < 10:
        return None
    
    # Condition 1: Raw + Linear
    raw_lin = []
    for d in sent_depths:
        raw_lin.extend(d)
    raw_lin = np.array(raw_lin[:n_words], dtype=float)
    
    # Condition 2: Raw + Shuffled
    shuf_order = list(sent_depths)
    random.shuffle(shuf_order)
    raw_shuf = []
    for d in shuf_order:
        raw_shuf.extend(d)
    raw_shuf = np.array(raw_shuf[:n_words], dtype=float)
    
    # Condition 3: Detrended + Linear
    det_lin = []
    for d in sent_depths:
        m = np.mean(d)
        det_lin.extend([x - m for x in d])
    det_lin = np.array(det_lin[:n_words], dtype=float)
    
    # Condition 4: Detrended + Shuffled
    det_shuf = []
    for d in shuf_order:
        m = np.mean(d)
        det_shuf.extend([x - m for x in d])
    det_shuf = np.array(det_shuf[:n_words], dtype=float)
    
    h1, b1 = compute_spectrum(raw_lin)
    h2, b2 = compute_spectrum(raw_shuf)
    h3, b3 = compute_spectrum(det_lin)
    h4, b4 = compute_spectrum(det_shuf)
    
    # Compute sentence length stats
    sent_lens = [len(d) for d in sent_depths]
    
    # Percentage decomposition
    total_shift = abs(b1)
    slv_pct = abs(b1 - b3) / total_shift * 100 if total_shift > 0 else 0
    envelope_pct = abs(b3 - b4) / total_shift * 100 if total_shift > 0 else 0
    intra_pct = 100 - slv_pct - envelope_pct
    
    return {
        'b_raw_lin': b1, 'b_raw_shuf': b2,
        'b_det_lin': b3, 'b_det_shuf': b4,
        'slv_pct': slv_pct, 'envelope_pct': envelope_pct, 'intra_pct': intra_pct,
        'n_sents': len(sent_depths), 'n_words': len(raw_lin),
        'mean_sent_len': np.mean(sent_lens), 'std_sent_len': np.std(sent_lens),
        'median_sent_len': np.median(sent_lens),
    }

# ═══════════════════════════════════════════════════════════════════
# PART 1: Multi-text 2×2 replication (English, 12+ texts)
# ═══════════════════════════════════════════════════════════════════
TEXTS = [
    ("Pride & Prejudice", "1342_pride_and_prejudice.txt"),
    ("Frankenstein", "84_frankenstein.txt"),
    ("Dracula", "345_dracula.txt"),
    ("Alice in Wonderland", "11_alice_in_wonderland.txt"),
    ("Tale of Two Cities", "98_a_tale_of_two_cities.txt"),
    ("Huckleberry Finn", "76_huckleberry_finn.txt"),
    ("Oliver Twist", "730_oliver_twist.txt"),
    ("Dorian Gray", "174_the_picture_of_dorian_gray.txt"),
    ("Little Women", "514_little_women.txt"),
    ("Call of the Wild", "215_the_call_of_the_wild.txt"),
    ("War of the Worlds", "36_the_war_of_the_worlds.txt"),
    ("Shakespeare (Complete)", "100_complete_works_of_shakespeare.txt"),
]

print("="*80)
print("  PART 1: Multi-Text 2×2 Decomposition (Error Bars on 78% Figure)")
print("="*80)

nlp = spacy.load("en_core_web_sm")
nlp.max_length = 6_000_000

results = []
print(f"\n  {'Text':<25} {'β_raw':>6} {'β_det':>6} {'β_d+s':>6} {'SLV%':>5} {'Env%':>5} {'Intra%':>6} {'Mean SL':>7}")
print(f"  {'─'*25} {'─'*6} {'─'*6} {'─'*6} {'─'*5} {'─'*5} {'─'*6} {'─'*7}")

for name, fname in TEXTS:
    fp = os.path.join(BASE, 'texts', 'gutenberg', fname)
    if not os.path.exists(fp):
        print(f"  {name:<25} MISSING")
        continue
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()[:500_000]
    
    random.seed(42)
    doc = nlp(text)
    r = decompose_text(doc, n_words=N)
    if r is None:
        print(f"  {name:<25} TOO SHORT")
        continue
    
    results.append({'name': name, **r})
    print(f"  {name:<25} {r['b_raw_lin']:>6.3f} {r['b_det_lin']:>6.3f} {r['b_det_shuf']:>6.3f} "
          f"{r['slv_pct']:>5.1f} {r['envelope_pct']:>5.1f} {r['intra_pct']:>6.1f} {r['mean_sent_len']:>7.1f}")

# Summary statistics
if results:
    intra_vals = [r['intra_pct'] for r in results]
    slv_vals = [r['slv_pct'] for r in results]
    env_vals = [r['envelope_pct'] for r in results]
    sent_lens = [r['mean_sent_len'] for r in results]
    
    print(f"\n  SUMMARY (n={len(results)} texts):")
    print(f"    Intra-sentence:   {np.mean(intra_vals):.1f}% ± {np.std(intra_vals):.1f}%  (range: {min(intra_vals):.1f}–{max(intra_vals):.1f}%)")
    print(f"    SLV boundary:     {np.mean(slv_vals):.1f}% ± {np.std(slv_vals):.1f}%")
    print(f"    Envelope:         {np.mean(env_vals):.1f}% ± {np.std(env_vals):.1f}%")
    print(f"    Mean sentence len:{np.mean(sent_lens):.1f} ± {np.std(sent_lens):.1f} words")
    print(f"    k-range for sentence arcs: k ≈ {N/np.max(sent_lens):.0f}–{N/np.min(sent_lens):.0f}")

# ═══════════════════════════════════════════════════════════════════
# PART 2: Heterogeneous text shuffle (Shakespeare)
# ═══════════════════════════════════════════════════════════════════
print(f"\n{'='*80}")
print("  PART 2: Sentence Shuffle on Structurally Heterogeneous Text")
print("="*80)

# Shakespeare has sonnets, plays (prose + verse), dramatically different registers
fp = os.path.join(BASE, 'texts', 'gutenberg', '100_complete_works_of_shakespeare.txt')
if os.path.exists(fp):
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()[:500_000]
    random.seed(42)
    doc = nlp(text)
    r = decompose_text(doc, n_words=N)
    if r:
        print(f"\n  Shakespeare (Complete Works) — {r['n_sents']} sentences, {r['n_words']} words")
        print(f"    Sentence length: mean={r['mean_sent_len']:.1f}, std={r['std_sent_len']:.1f}, median={r['median_sent_len']:.1f}")
        print(f"    Raw + Linear:     β = {r['b_raw_lin']:.3f}")
        print(f"    Raw + Shuffled:   β = {r['b_raw_shuf']:.3f}  (Δβ = {r['b_raw_shuf']-r['b_raw_lin']:+.3f})")
        print(f"    Detrended + Lin:  β = {r['b_det_lin']:.3f}")
        print(f"    Detrended + Shuf: β = {r['b_det_shuf']:.3f}")
        print(f"    Intra-sentence:   {r['intra_pct']:.1f}%")

# ═══════════════════════════════════════════════════════════════════
# PART 3: Sentence Length Distribution Shape Control
# ═══════════════════════════════════════════════════════════════════
print(f"\n{'='*80}")
print("  PART 3: Sentence Length Distribution Shape Control")
print("="*80)

# Use P&P: keep real sentence grammars but resample their lengths from Gaussian
fp = os.path.join(BASE, 'texts', 'gutenberg', '1342_pride_and_prejudice.txt')
with open(fp, 'r', encoding='utf-8') as f:
    text = f.read()[:200_000]

random.seed(42)
doc = nlp(text)
sentences = list(doc.sents)

# Extract real sentence depth arrays
real_sent_depths = []
for s in sentences:
    depths = [dep_depth(t) for t in s if t.pos_ not in ('PUNCT', 'SPACE')]
    if depths:
        real_sent_depths.append(depths)

real_lens = np.array([len(d) for d in real_sent_depths])
print(f"\n  P&P real sentence length distribution:")
print(f"    Mean={np.mean(real_lens):.1f}, Std={np.std(real_lens):.1f}, Median={np.median(real_lens):.1f}")
skew_val = np.mean(((real_lens - np.mean(real_lens))/np.std(real_lens))**3) if len(real_lens)>0 else 0
print(f"    Skewness={skew_val:.2f}")

# Generate Gaussian-resampled: pair real sentence grammars with Gaussian lengths
np.random.seed(42)
gauss_lens = np.random.normal(np.mean(real_lens), np.std(real_lens), len(real_sent_depths))
gauss_lens = np.clip(gauss_lens, 3, None).astype(int)  # min 3 words

# For each Gaussian length, take a random real sentence and truncate/pad its depth array
gauss_signal = []
for gl in gauss_lens:
    # Pick a random real sentence
    src = random.choice(real_sent_depths)
    if len(src) >= gl:
        gauss_signal.extend(src[:gl])
    else:
        # Repeat the sentence's depths cyclically to reach target length
        repeated = (src * (gl // len(src) + 1))[:gl]
        gauss_signal.extend(repeated)

gauss_signal = np.array(gauss_signal[:N], dtype=float)

# Real signal (original length distribution)
real_signal = []
for d in real_sent_depths:
    real_signal.extend(d)
real_signal = np.array(real_signal[:N], dtype=float)

h_real, b_real = compute_spectrum(real_signal)
h_gauss, b_gauss = compute_spectrum(gauss_signal)

print(f"\n  β comparison:")
print(f"    Real length distribution (long-tailed):  β = {b_real:.3f}")
print(f"    Gaussian length distribution (matched μ,σ): β = {b_gauss:.3f}")
print(f"    Difference: Δβ = {b_gauss - b_real:+.3f}")

if abs(b_gauss - b_real) < 0.1:
    print(f"    ✓ β is robust to length distribution shape (Δβ < 0.1)")
else:
    print(f"    ✗ β is sensitive to length distribution shape — needs covariate")

# Skewness comparison
from scipy.stats import skew, kurtosis
print(f"\n  Distribution shape comparison:")
print(f"    Real:     skew={skew(real_lens):.2f}, kurtosis={kurtosis(real_lens):.2f}")
print(f"    Gaussian: skew={skew(gauss_lens):.2f}, kurtosis={kurtosis(gauss_lens):.2f}")
