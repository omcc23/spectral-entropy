import os, json, time, sys
import numpy as np
import spacy
from entropy_core import (
    calculate_hydrodynamic_entropy,
    normalized_entropy,
    smooth_signal,
    clean_text
)

BASE = os.path.dirname(__file__)
ENG_DIR = os.path.join(BASE, "texts", "gutenberg")
MULTI_DIR = os.path.join(BASE, "texts", "gutenberg_multi")

# We fallback naturally, prep_large_models.py installed the best available.
LANG_MODELS = {
    "english": "en_core_web_lg",
    "french": "fr_core_news_lg",
    "german": "de_core_news_lg",
    "spanish": "es_core_news_lg",
    "italian": "it_core_news_lg",
    "portuguese": "pt_core_news_lg",
    "dutch": "nl_core_news_lg",
    "polish": "pl_core_news_lg",
    "finnish": "fi_core_news_lg",
    "swedish": "sv_core_news_lg",
    "russian": "ru_core_news_lg",
}

# The STRICT STANDARD LENGTH for statistically unbiased comparative physics
N_STANDARD = 10_000

def dep_depth(token):
    d = 0
    while token.head != token:
        d += 1
        token = token.head
        if d > 100: break
    return d

def compute_spectrum(signal):
    """Computes the full E(k) spectrum with NO clipping."""
    h, spec = calculate_hydrodynamic_entropy(signal)
    n = len(signal)
    h_norm = normalized_entropy(h, n)
    
    half = len(spec) // 2
    # NO truncation/clipping mapping
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

def process_corpus(dir_path, language, model_name):
    # If lg doesn't exist, try md, then sm
    nlp = None
    sizes = ["lg", "md", "sm"]
    base_name = model_name[:-3] # eg en_core_web_
    
    for size in sizes:
        try:
            name = f"{base_name}_{size}"
            # spacy.require_gpu() # Attempt GPU utilization
            nlp = spacy.load(name)
            nlp.max_length = 300_000
            print(f"[{language}] Loaded model: {name} (GPU: {spacy.prefer_gpu()})")
            break
        except Exception:
            continue
            
    if nlp is None:
        print(f"[{language}] Failed to load any model.")
        print(f"[{language}] Available models: {spacy.util.get_installed_models()}")
        return []

    stats_list = []
    
    files = sorted([f for f in os.listdir(dir_path) if f.endswith(".txt")]) if os.path.exists(dir_path) else []
    for fname in files:
        filepath = os.path.join(dir_path, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        
        # Rigorous prep
        text = clean_text(text)
        
        # Load exactly enough chars to hopefully guarantee N_STANDARD valid tokens.
        # ~10k words usually requires ~60k-80k chars. Let's pull 120k to be safe.
        
        t0 = time.time()
        CHUNK_SIZE = 50_000
        chunks = [text[i:i+CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE) if text[i:i+CHUNK_SIZE].strip()]
        
        depth_signal = []
        # MUST NOT disable parser, as we need token.head
        for doc in nlp.pipe(chunks, batch_size=2, disable=["ner", "lemmatizer", "textcat"]):
            valid = [dep_depth(tok) for tok in doc if tok.pos_ not in ("PUNCT", "SPACE", "X")]
            depth_signal.extend(valid)
            if len(depth_signal) >= N_STANDARD:
                break
        
        if len(depth_signal) < N_STANDARD:
            print(f"[{language}] SKIP {fname}: Too short ({len(depth_signal)} < {N_STANDARD} tokens)")
            continue
            
        # STRICT TRUNCATION TO N_STANDARD
        depth_signal = np.array(depth_signal[:N_STANDARD], dtype=float)
        
        h_norm, slope, intercept, k_arr, e_smooth_arr = compute_spectrum(depth_signal)
        
        mean_d = float(np.mean(depth_signal))
        max_d = int(np.max(depth_signal))
        
        title = os.path.splitext(fname)[0].replace("_", " ").title()[:30]
        elapsed = time.time() - t0
        
        print(f"{language[:3].upper()} | {title:<28} | β:{slope:>7.3f} | H:{h_norm:>6.3f} | D:{mean_d:>5.2f} | {elapsed:>4.1f}s")
        
        stats_list.append({
            "language": language,
            "title": title,
            "filename": fname,
            "h_norm": float(h_norm),
            "slope": float(slope),
            "intercept": float(intercept),
            "mean_depth": mean_d,
            "k_arr": k_arr.tolist(),
            "e_smooth_arr": e_smooth_arr.tolist(),
            "depth_signal": depth_signal.tolist()
        })
        
    return stats_list

def main():
    print("Initiating Large Model Unified Multilingual Analysis with N_STANDARD...")
    all_results = []
    
    # 1. English
    eng_res = process_corpus(ENG_DIR, "english", LANG_MODELS["english"])
    all_results.extend(eng_res)
    
    # 2. Multilingual
    if os.path.exists(MULTI_DIR):
        langs = sorted([d for d in os.listdir(MULTI_DIR) if os.path.isdir(os.path.join(MULTI_DIR, d))])
        for lang in langs:
            lang_dir = os.path.join(MULTI_DIR, lang)
            if lang in LANG_MODELS:
                res = process_corpus(lang_dir, lang, LANG_MODELS.get(lang))
                all_results.extend(res)
    
    # Dump the monster JSON mapping all pre-computed physics.
    out_path = os.path.join(BASE, "data", "master_lg_physics.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with open(out_path, "w") as f:
        json.dump(all_results, f)
        
    print(f"\nCompleted analysis of {len(all_results)} structurally locked (N={N_STANDARD}) datasets.")
    print(f"Data meticulously saved to {out_path}.")

if __name__ == "__main__":
    main()
