import os
import json
import random
import numpy as np
import spacy
from entropy_core import calculate_hydrodynamic_entropy, normalized_entropy, smooth_signal

def calculate_dep_depth(token):
    d = 0
    while token.head != token:
        d += 1
        token = token.head
        if d > 100: break
    return d

BASE = os.path.dirname(__file__)

def compute_spectrum(signal):
    h, spec = calculate_hydrodynamic_entropy(signal)
    n = len(signal)
    h_norm = normalized_entropy(h, n)
    half = len(spec) // 2
    k_max = int(half)
    k = np.arange(1, k_max + 1)
    e_raw = spec[1 : k_max + 1]
    sm_win = max(3, k_max // 20)
    e_smooth = smooth_signal(e_raw, sm_win)
    valid = e_smooth > 0
    slope, intercept = 0.0, 0.0
    if np.sum(valid) > 10:
        slope, intercept = np.polyfit(np.log10(k[valid]), np.log10(e_smooth[valid]), 1)
    return h_norm, slope, intercept, k, e_smooth

def generate_pink_noise(n, beta=-1.0):
    freqs = np.fft.rfftfreq(n)
    freqs[0] = 1  # avoid div by zero
    power = freqs ** (beta / 2)
    phases = np.exp(1j * np.random.uniform(0, 2*np.pi, len(freqs)))
    return np.fft.irfft(power * phases, n=n)

def run_synthetic_benchmarks():
    print("--- Ablation 3: Synthetic Reference Markers ---")
    n = 10000
    
    # White noise (β ≈ 0)
    white = np.random.randn(n)
    h_w, b_w, _, _, _ = compute_spectrum(white)
    
    # Pink noise (β ≈ -1)
    pink = generate_pink_noise(n, -1.0)
    h_p, b_p, _, _, _ = compute_spectrum(pink)
    
    # Brown noise (β ≈ -2)
    brown = generate_pink_noise(n, -2.0)
    h_b, b_b, _, _, _ = compute_spectrum(brown)
    
    print(f"White Noise: β={b_w:.3f}, H_norm={h_w:.3f}")
    print(f"Pink  Noise: β={b_p:.3f}, H_norm={h_p:.3f}")
    print(f"Brown Noise: β={b_b:.3f}, H_norm={h_b:.3f}\n")
    
    return {
        "white": {"beta": b_w, "h_norm": h_w},
        "pink":  {"beta": b_p, "h_norm": h_p},
        "brown": {"beta": b_b, "h_norm": h_b}
    }

def run_sentence_ablation():
    print("--- Ablation 1: Sentence Shuffle (Structural Memory Collapse) ---")
    
    fp = os.path.join(BASE, 'texts', 'gutenberg', '1342_pride_and_prejudice.txt')
    with open(fp, 'r', encoding='utf-8') as f:
        # Load enough text to safely get 10,000 valid tokens
        text = f.read()[:200_000]
        
    nlp = spacy.load("en_core_web_sm")
    nlp.max_length = 300_000
    doc = nlp(text)
    
    # Extract sentences exactly as parsed computationally
    sentences = list(doc.sents)
    
    # BASELINE: Standard Linear Unfolding
    signal_standard = []
    for s in sentences:
        signal_standard.extend([calculate_dep_depth(t) for t in s if t.pos_ not in ('PUNCT', 'SPACE')])
    
    sig_10k = np.array(signal_standard[:10000], dtype=float)
    h_std, b_std, _, _, _ = compute_spectrum(sig_10k)
    
    # ABLATION: Shuffled Narrative Sequence
    random.seed(42)
    random.shuffle(sentences)
    signal_shuffled = []
    for s in sentences:
        signal_shuffled.extend([calculate_dep_depth(t) for t in s if t.pos_ not in ('PUNCT', 'SPACE')])
        
    sig_shuf_10k = np.array(signal_shuffled[:10000], dtype=float)
    h_shuf, b_shuf, _, _, _ = compute_spectrum(sig_shuf_10k)
    
    print(f"Pride & Prejudice (Linear):   β={b_std:.3f}, H_norm={h_std:.3f}")
    print(f"Pride & Prejudice (Shuffled): β={b_shuf:.3f}, H_norm={h_shuf:.3f}")

def phase_randomise(series):
    ft = np.fft.rfft(series, norm='ortho')
    magnitudes = np.abs(ft)
    random_phases = np.exp(1j * np.random.uniform(0, 2*np.pi, len(ft)))
    surrogate_ft = magnitudes * random_phases
    # Return exactly to specific size
    return np.fft.irfft(surrogate_ft, n=len(series), norm='ortho')

def run_phase_randomization_ablation():
    print("\n--- Ablation 2: Phase Randomization (Surrogate Data) ---")
    fp = os.path.join(BASE, 'texts', 'gutenberg', '1342_pride_and_prejudice.txt')
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()[:200_000]
    nlp = spacy.load("en_core_web_sm")
    nlp.max_length = 300_000
    doc = nlp(text)
    real_series = np.array([calculate_dep_depth(t) for t in doc if t.pos_ not in ('PUNCT', 'SPACE')][:10000], dtype=float)
    
    surrogate_h = []
    print("Generating 100 phase surrogates...")
    for _ in range(100):
        surrogate = phase_randomise(real_series)
        h, _, _, _, _ = compute_spectrum(surrogate)
        surrogate_h.append(h)
        
    real_h, real_b, _, _, _ = compute_spectrum(real_series)
    print(f"P&P (Real Signal):        H_norm={real_h:.3f}, β={real_b:.3f}")
    print(f"P&P (Phase Surrogates):   H_norm={np.mean(surrogate_h):.3f} (Variance is mathematically identical)")

def run_pos_shuffle_ablation():
    print("\n--- Ablation 4: Within-Sentence POS-Constrained Word Shuffle ---")
    fp = os.path.join(BASE, 'texts', 'gutenberg', '1342_pride_and_prejudice.txt')
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()[:50_000]
    nlp = spacy.load("en_core_web_sm")
    nlp.max_length = 300_000
    doc = nlp(text)
    
    sentences = list(doc.sents)[:100] # Take first 100 sentences for speed
    
    print("Parsing identical words into scrambled local grammars...")
    shuf_depth = []
    for s in sentences:
        tokens_by_pos = {}
        for tok in s:
            tokens_by_pos.setdefault(tok.pos_, []).append(tok.text)
        
        for pos in tokens_by_pos:
            random.shuffle(tokens_by_pos[pos])
            
        counters = {pos: 0 for pos in tokens_by_pos}
        new_tokens = []
        for tok in s:
            if tok.pos_ in tokens_by_pos:
                new_tokens.append(tokens_by_pos[tok.pos_][counters[tok.pos_]])
                counters[tok.pos_] += 1
            
        gibberish = " ".join(new_tokens)
        new_doc = nlp(gibberish)
        shuf_depth.extend([calculate_dep_depth(t) for t in new_doc if t.pos_ not in ('PUNCT', 'SPACE')])
        
    # Baseline normal sentences
    std_depth = []
    for s in sentences:
        std_depth.extend([calculate_dep_depth(t) for t in s if t.pos_ not in ('PUNCT', 'SPACE')])
        
    h_std, b_std, _, _, _ = compute_spectrum(np.array(std_depth, dtype=float))
    h_shuf, b_shuf, _, _, _ = compute_spectrum(np.array(shuf_depth, dtype=float))
    
    print(f"P&P (Real Local Grammar):   β={b_std:.3f}, H_norm={h_std:.3f}")
    print(f"P&P (Shuffled POS Grammar): β={b_shuf:.3f}, H_norm={h_shuf:.3f}")

def run_slv_ablation():
    print("\n--- Ablation 5: Sentence Length Variation (SLV) ---")
    fp = os.path.join(BASE, 'texts', 'gutenberg', '1342_pride_and_prejudice.txt')
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()[:500_000] # SLV compresses text severely, load more
    nlp = spacy.load("en_core_web_sm")
    nlp.max_length = 600_000
    doc = nlp(text)
    
    sentences = list(doc.sents)
    if len(sentences) < 100:
        return
        
    # Baseline SLV
    std_slv = np.array([len(s) for s in sentences], dtype=float)
    h_std, b_std, _, _, _ = compute_spectrum(std_slv)
    
    # Shuffled SLV
    np.random.seed(42)
    shuf_slv = np.random.permutation(std_slv)
    h_shuf, b_shuf, _, _, _ = compute_spectrum(shuf_slv)
    
    print(f"P&P SLV (Linear Narrative Sequence):   β={b_std:.3f}, H_norm={h_std:.3f}")
    print(f"P&P SLV (Shuffled Narrative Sequence): β={b_shuf:.3f}, H_norm={h_shuf:.3f}")

def run_detrended_depth_ablation():
    """CRITICAL TEST: Remove the sentence-boundary step function from the depth signal.
    
    If β collapses to ~0, then dep_depth was just measuring sentence boundaries.
    If β remains negative, there is genuine within-sentence fractal structure.
    """
    print("\n--- Ablation 6: Sentence-Detrended Depth Residuals ---")
    fp = os.path.join(BASE, 'texts', 'gutenberg', '1342_pride_and_prejudice.txt')
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()[:200_000]
    nlp = spacy.load("en_core_web_sm")
    nlp.max_length = 300_000
    doc = nlp(text)
    
    sentences = list(doc.sents)
    
    # Build the RAW word-level depth signal
    raw_signal = []
    for s in sentences:
        raw_signal.extend([calculate_dep_depth(t) for t in s if t.pos_ not in ('PUNCT', 'SPACE')])
    raw_signal = np.array(raw_signal[:10000], dtype=float)
    
    # Build the DETRENDED signal: subtract each sentence's mean depth
    # This removes the sentence-boundary step function entirely
    detrended_signal = []
    for s in sentences:
        depths = [calculate_dep_depth(t) for t in s if t.pos_ not in ('PUNCT', 'SPACE')]
        if depths:
            mean_d = np.mean(depths)
            detrended_signal.extend([d - mean_d for d in depths])
    detrended_signal = np.array(detrended_signal[:10000], dtype=float)
    
    h_raw, b_raw, _, _, _ = compute_spectrum(raw_signal)
    h_det, b_det, _, _, _ = compute_spectrum(detrended_signal)
    
    print(f"P&P Dep-Depth (Raw Word-Level):       β={b_raw:.3f}, H_norm={h_raw:.3f}")
    print(f"P&P Dep-Depth (Sentence-Detrended):   β={b_det:.3f}, H_norm={h_det:.3f}")

def run_sentence_mean_depth_ablation():
    """CRITICAL TEST: Compute β on per-sentence MEAN depth (one value per sentence).
    
    If this β matches the word-level β, then dep_depth is dominated by 
    sentence-level means (i.e., it's just a fancy SLV).
    If this β is much weaker, the word-level signal carries genuine
    within-sentence geometric information.
    """
    print("\n--- Ablation 7: Per-Sentence Mean Depth vs. Word-Level Depth ---")
    fp = os.path.join(BASE, 'texts', 'gutenberg', '1342_pride_and_prejudice.txt')
    with open(fp, 'r', encoding='utf-8') as f:
        text = f.read()[:500_000]
    nlp = spacy.load("en_core_web_sm")
    nlp.max_length = 600_000
    doc = nlp(text)
    
    sentences = list(doc.sents)
    
    # Per-sentence mean depth (one scalar per sentence, like SLV)
    mean_depths = []
    for s in sentences:
        depths = [calculate_dep_depth(t) for t in s if t.pos_ not in ('PUNCT', 'SPACE')]
        if depths:
            mean_depths.append(np.mean(depths))
    mean_depths = np.array(mean_depths, dtype=float)
    
    # Word-level depth (one value per word)
    word_depths = []
    for s in sentences:
        word_depths.extend([calculate_dep_depth(t) for t in s if t.pos_ not in ('PUNCT', 'SPACE')])
    word_depths = np.array(word_depths[:10000], dtype=float)
    
    # SLV (one value per sentence)
    slv = np.array([len(s) for s in sentences], dtype=float)
    
    h_word, b_word, _, _, _ = compute_spectrum(word_depths)
    h_mean, b_mean, _, _, _ = compute_spectrum(mean_depths)
    h_slv, b_slv, _, _, _ = compute_spectrum(slv)
    
    print(f"P&P Word-Level Dep-Depth:    β={b_word:.3f}, H_norm={h_word:.3f}  (N={len(word_depths)})")
    print(f"P&P Per-Sentence Mean Depth: β={b_mean:.3f}, H_norm={h_mean:.3f}  (N={len(mean_depths)})")
    print(f"P&P Sentence Length (SLV):   β={b_slv:.3f}, H_norm={h_slv:.3f}  (N={len(slv)})")

if __name__ == "__main__":
    anchors = run_synthetic_benchmarks()
    run_sentence_ablation()
    run_phase_randomization_ablation()
    run_pos_shuffle_ablation()
    run_slv_ablation()
    run_detrended_depth_ablation()
    run_sentence_mean_depth_ablation()
    
    # Save the physics coordinates so the collage app can overlay them!
    with open(os.path.join(BASE, 'data', 'synthetic_anchors.json'), 'w') as f:
        json.dump(anchors, f)
