"""Part 3: Sentence Length Distribution Shape Control"""
import os, sys, random
import numpy as np
import spacy
sys.path.insert(0, os.path.dirname(__file__))
from entropy_core import calculate_hydrodynamic_entropy, normalized_entropy, smooth_signal
from scipy.stats import skew, kurtosis

BASE = os.path.dirname(__file__)
N = 10000

def dep_depth(tok):
    d = 0
    while tok.head != tok:
        d += 1
        tok = tok.head
        if d > 100: break
    return d

def compute_beta(series):
    if len(series) < 20:
        return 0
    h_raw, energy = calculate_hydrodynamic_entropy(series)
    n = len(energy)
    k = np.arange(1, n//2)
    e = energy[1:n//2]
    e_smooth = smooth_signal(e, window=max(3, len(e)//50))
    valid = (e_smooth > 0) & (k > 0)
    if np.sum(valid) > 10:
        beta, _ = np.polyfit(np.log10(k[valid]), np.log10(e_smooth[valid]), 1)
        return beta
    return 0

nlp = spacy.load('en_core_web_sm')
nlp.max_length = 300_000

fp = os.path.join(BASE, 'texts', 'gutenberg', '1342_pride_and_prejudice.txt')
with open(fp, 'r', encoding='utf-8') as f:
    text = f.read()[:200_000]

doc = nlp(text)
sentences = list(doc.sents)

real_sent_depths = []
for s in sentences:
    depths = [dep_depth(t) for t in s if t.pos_ not in ('PUNCT', 'SPACE')]
    if depths:
        real_sent_depths.append(depths)

real_lens = np.array([len(d) for d in real_sent_depths])

print("="*70)
print("  PART 3: Sentence Length Distribution Shape Control")
print("="*70)
print(f"\n  P&P real sentence length distribution:")
print(f"    N sentences = {len(real_lens)}")
print(f"    Mean = {np.mean(real_lens):.1f}, Std = {np.std(real_lens):.1f}, Median = {np.median(real_lens):.1f}")
print(f"    Skewness = {skew(real_lens):.2f} (long-tailed)")
print(f"    Kurtosis = {kurtosis(real_lens):.2f}")

# Real signal
real_signal = []
for d in real_sent_depths:
    real_signal.extend(d)
real_signal = np.array(real_signal[:N], dtype=float)
b_real = compute_beta(real_signal)

# Gaussian-resampled: keep real sentence grammars, resample lengths from Gaussian
np.random.seed(42)
random.seed(42)
gauss_lens = np.random.normal(np.mean(real_lens), np.std(real_lens), len(real_sent_depths))
gauss_lens = np.clip(gauss_lens, 3, None).astype(int)

gauss_signal = []
for gl in gauss_lens:
    src = random.choice(real_sent_depths)
    if len(src) >= gl:
        gauss_signal.extend(src[:gl])
    else:
        repeated = (src * (gl // len(src) + 1))[:gl]
        gauss_signal.extend(repeated)
gauss_signal = np.array(gauss_signal[:N], dtype=float)
b_gauss = compute_beta(gauss_signal)

# Uniform-resampled: all sentences forced to same length
uniform_len = int(np.mean(real_lens))
uniform_signal = []
random.seed(42)
for _ in range(len(real_sent_depths)):
    src = random.choice(real_sent_depths)
    if len(src) >= uniform_len:
        uniform_signal.extend(src[:uniform_len])
    else:
        repeated = (src * (uniform_len // len(src) + 1))[:uniform_len]
        uniform_signal.extend(repeated)
uniform_signal = np.array(uniform_signal[:N], dtype=float)
b_uniform = compute_beta(uniform_signal)

print(f"\n  β comparison across length distributions:")
print(f"    Real (skew={skew(real_lens):.1f}):     β = {b_real:.3f}")
print(f"    Gaussian (skew={skew(gauss_lens):.1f}):  β = {b_gauss:.3f}  (Δβ = {b_gauss-b_real:+.3f})")
print(f"    Uniform (all len={uniform_len}): β = {b_uniform:.3f}  (Δβ = {b_uniform-b_real:+.3f})")

print(f"\n  Distribution shapes:")
print(f"    Real:     skew={skew(real_lens):.2f}, kurt={kurtosis(real_lens):.2f}")
print(f"    Gaussian: skew={skew(gauss_lens):.2f}, kurt={kurtosis(gauss_lens):.2f}")
print(f"    Uniform:  skew=0.00, kurt=-1.20 (degenerate, all same length)")

if abs(b_gauss - b_real) < 0.1 and abs(b_uniform - b_real) < 0.15:
    print(f"\n  ✓ β is ROBUST to length distribution shape")
    print(f"    Even forcing all sentences to identical length preserves the scaling.")
else:
    print(f"\n  ✗ β is SENSITIVE to length distribution shape")
    print(f"    The tail shape of the length distribution contributes to spectral power.")
