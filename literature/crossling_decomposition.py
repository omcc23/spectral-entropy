"""
Full-text cross-linguistic 2×2 decomposition.
One full text per language, _lg models, N=10000 tokens.
"""
import os, sys, random, glob
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

def compute_beta(series):
    if len(series) < 50:
        return 0.0
    h_raw, energy = calculate_hydrodynamic_entropy(series)
    n = len(energy)
    k = np.arange(1, n//2)
    e = energy[1:n//2]
    e_smooth = smooth_signal(e, window=max(3, len(e)//50))
    valid = (e_smooth > 0) & (k > 0)
    if np.sum(valid) > 10:
        beta, _ = np.polyfit(np.log10(k[valid]), np.log10(e_smooth[valid]), 1)
        return beta
    return 0.0

LANGUAGES = {
    "french":     {"model": "fr_core_news_lg"},
    "german":     {"model": "de_core_news_lg"},
    "spanish":    {"model": "es_core_news_lg"},
    "italian":    {"model": "it_core_news_lg"},
    "portuguese": {"model": "pt_core_news_lg"},
    "dutch":      {"model": "nl_core_news_lg"},
    "polish":     {"model": "pl_core_news_lg"},
    "finnish":    {"model": "fi_core_news_lg"},
    "swedish":    {"model": "sv_core_news_lg"},
    "russian":    {"model": "ru_core_news_lg"},
}

print("="*85)
print("  CROSS-LINGUISTIC 2×2 DECOMPOSITION — Full Texts, _lg Models")
print("="*85)

results = []

for lang, info in LANGUAGES.items():
    lang_dir = os.path.join(BASE, "texts", "gutenberg_multi", lang)
    txt_files = sorted(glob.glob(os.path.join(lang_dir, "*.txt")))
    if not txt_files:
        print(f"\n  {lang.upper()}: No texts found, skipping.")
        continue
    
    # Pick the largest text for best spectral coverage
    txt_files_sized = [(f, os.path.getsize(f)) for f in txt_files]
    txt_files_sized.sort(key=lambda x: -x[1])
    chosen_file = txt_files_sized[0][0]
    fname = os.path.basename(chosen_file)
    
    try:
        nlp = spacy.load(info["model"])
    except OSError:
        print(f"\n  {lang.upper()}: Model {info['model']} not installed, skipping.")
        continue
    
    nlp.max_length = 1_500_000
    
    with open(chosen_file, 'r', encoding='utf-8') as f:
        text = f.read()[:500_000]
    
    print(f"\n  {lang.upper()} — {fname} ({len(text)//1000}k chars)")
    
    doc = nlp(text)
    sentences = list(doc.sents)
    
    # Build per-sentence depth arrays
    sent_depths = []
    for s in sentences:
        depths = [dep_depth(t) for t in s if t.pos_ not in ('PUNCT', 'SPACE')]
        if depths:
            sent_depths.append(depths)
    
    total_words = sum(len(d) for d in sent_depths)
    if total_words < N // 2:
        print(f"    ⚠ Only {total_words} content words, too short.")
        continue
    
    random.seed(42)
    
    # Condition 1: Raw + Linear
    raw_lin = []
    for d in sent_depths:
        raw_lin.extend(d)
    raw_lin = np.array(raw_lin[:N], dtype=float)
    
    # Condition 2: Raw + Shuffled
    shuf = list(sent_depths)
    random.shuffle(shuf)
    raw_shuf = []
    for d in shuf:
        raw_shuf.extend(d)
    raw_shuf = np.array(raw_shuf[:N], dtype=float)
    
    # Condition 3: Detrended + Linear
    det_lin = []
    for d in sent_depths:
        m = np.mean(d)
        det_lin.extend([x - m for x in d])
    det_lin = np.array(det_lin[:N], dtype=float)
    
    # Condition 4: Detrended + Shuffled
    det_shuf = []
    for d in shuf:
        m = np.mean(d)
        det_shuf.extend([x - m for x in d])
    det_shuf = np.array(det_shuf[:N], dtype=float)
    
    b1 = compute_beta(raw_lin)
    b2 = compute_beta(raw_shuf)
    b3 = compute_beta(det_lin)
    b4 = compute_beta(det_shuf)
    
    total_shift = abs(b1)
    slv_pct = abs(b1 - b3) / total_shift * 100 if total_shift > 0 else 0
    env_pct = abs(b3 - b4) / total_shift * 100 if total_shift > 0 else 0
    intra_pct = 100 - slv_pct - env_pct
    
    sent_lens = [len(d) for d in sent_depths]
    
    r = {
        'lang': lang, 'file': fname,
        'n_sents': len(sent_depths), 'n_words': len(raw_lin),
        'b_raw': b1, 'b_det': b3, 'b_det_shuf': b4,
        'slv_pct': slv_pct, 'env_pct': env_pct, 'intra_pct': intra_pct,
        'mean_sl': np.mean(sent_lens), 'std_sl': np.std(sent_lens),
        'mean_depth': np.mean(raw_lin),
    }
    results.append(r)
    
    print(f"    {len(sent_depths)} sents, {len(raw_lin)} words, mean SL={np.mean(sent_lens):.1f}")
    print(f"    β_raw={b1:.3f}  β_det={b3:.3f}  β_det+shuf={b4:.3f}")
    print(f"    SLV={slv_pct:.1f}%  Env={env_pct:.1f}%  Intra={intra_pct:.1f}%")

# Summary
print(f"\n{'='*85}")
print("  SUMMARY TABLE")
print(f"{'='*85}")
print(f"  {'Language':<12} {'β_raw':>6} {'β_det':>6} {'β_d+s':>6} {'SLV%':>5} {'Env%':>5} {'Intra%':>6} {'MeanSL':>7} {'MeanD':>6}")
print(f"  {'─'*12} {'─'*6} {'─'*6} {'─'*6} {'─'*5} {'─'*5} {'─'*6} {'─'*7} {'─'*6}")
for r in results:
    print(f"  {r['lang']:<12} {r['b_raw']:>6.3f} {r['b_det']:>6.3f} {r['b_det_shuf']:>6.3f} "
          f"{r['slv_pct']:>5.1f} {r['env_pct']:>5.1f} {r['intra_pct']:>6.1f} {r['mean_sl']:>7.1f} {r['mean_depth']:>6.2f}")

if results:
    intra_vals = [r['intra_pct'] for r in results]
    slv_vals = [r['slv_pct'] for r in results]
    env_vals = [r['env_pct'] for r in results]
    depths = [r['mean_depth'] for r in results]
    
    print(f"\n  Cross-linguistic statistics (n={len(results)} languages):")
    print(f"    Intra-sentence: {np.mean(intra_vals):.1f}% ± {np.std(intra_vals):.1f}%  (range: {min(intra_vals):.1f}–{max(intra_vals):.1f}%)")
    print(f"    SLV boundary:   {np.mean(slv_vals):.1f}% ± {np.std(slv_vals):.1f}%")
    print(f"    Envelope:       {np.mean(env_vals):.1f}% ± {np.std(env_vals):.1f}%")
    print(f"    Mean dep depth: {np.mean(depths):.2f} ± {np.std(depths):.2f}")
    
    # Correlations with intra%
    from scipy.stats import pearsonr
    r_depth, p_depth = pearsonr([r['mean_depth'] for r in results], intra_vals)
    r_sl, p_sl = pearsonr([r['mean_sl'] for r in results], intra_vals)
    print(f"\n  Correlations with intra-sentence %:")
    print(f"    vs Mean Depth:      r={r_depth:.3f}, p={p_depth:.3f}")
    print(f"    vs Mean Sent Len:   r={r_sl:.3f}, p={p_sl:.3f}")
