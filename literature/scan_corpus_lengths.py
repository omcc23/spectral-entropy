import os, time
import numpy as np
import spacy
from entropy_core import clean_text

BASE = os.path.dirname(__file__)
ENG_DIR = os.path.join(BASE, "texts", "gutenberg")
MULTI_DIR = os.path.join(BASE, "texts", "gutenberg_multi")

LANG_MODELS = {
    "english": "en_core_web_sm",
    "french": "fr_core_news_sm",
    "german": "de_core_news_sm",
    "spanish": "es_core_news_sm",
    "italian": "it_core_news_sm",
    "portuguese": "pt_core_news_sm",
    "dutch": "nl_core_news_sm",
    "polish": "pl_core_news_sm",
    "finnish": "fi_core_news_sm",
    "swedish": "sv_core_news_sm",
    "russian": "ru_core_news_sm",
}

def get_valid_token_count(text, nlp):
    """Chunks text and processes via pipe to maximize throughput (GPU batching)."""
    CHUNK_SIZE = 100_000
    total_valid = 0
    chunks = []
    
    for i in range(0, len(text), CHUNK_SIZE):
        chunk = text[i:i+CHUNK_SIZE]
        if chunk.strip():
            chunks.append(chunk)
            
    # Disable components we don't need for simple POS counting to exponentially speed up
    for doc in nlp.pipe(chunks, batch_size=50, disable=["ner", "lemmatizer", "parser", "textcat"]):
        valid = [tok for tok in doc if tok.pos_ not in ("PUNCT", "SPACE", "X")]
        total_valid += len(valid)
        
    return total_valid

def scan_lengths():
    print("Beginning comprehensive whole-book length scanning...")
    
    try:
        spacy.require_gpu()
        print("GPU enabled for spaCy length scanning.")
    except Exception as e:
        print(f"GPU not available, falling back to CPU. Exception: {e}")
        
    all_lengths = []
    failed = []

    # English
    try:
        nlp_en = spacy.load("en_core_web_sm")
        files = sorted(os.listdir(ENG_DIR)) if os.path.exists(ENG_DIR) else []
        for f in files:
            with open(os.path.join(ENG_DIR, f), "r", encoding="utf-8") as txt:
                t = clean_text(txt.read())
            l = get_valid_token_count(t, nlp_en)
            all_lengths.append(l)
            print(f"English: {f} -> {l} tokens")
    except Exception as e:
        print(f"Error English: {e}")

    # Multilingual
    if os.path.exists(MULTI_DIR):
        langs = sorted([d for d in os.listdir(MULTI_DIR) if os.path.isdir(os.path.join(MULTI_DIR, d))])
        for lang in langs:
            lang_dir = os.path.join(MULTI_DIR, lang)
            model = LANG_MODELS.get(lang)
            try:
                nlp = spacy.load(model)
            except:
                print(f"SKIP length scan {lang}: model not found.")
                continue
            
            files = sorted(os.listdir(lang_dir))
            for f in files:
                with open(os.path.join(lang_dir, f), "r", encoding="utf-8") as txt:
                    t = clean_text(txt.read())
                l = get_valid_token_count(t, nlp)
                all_lengths.append(l)
                print(f"{lang.capitalize()}: {f} -> {l} tokens")
                
    if not all_lengths:
        print("No texts analyzed.")
        return
        
    l_arr = np.array(all_lengths)
    print("\n--- Structural Array Length Distribution ---")
    print(f"Total Texts Processed: {len(l_arr)}")
    print(f"Minimum Length: {np.min(l_arr):,}")
    print(f"Maximum Length: {np.max(l_arr):,}")
    print(f"Median Length:  {np.median(l_arr):,.0f}")
    print(f"10th Pctile:    {np.percentile(l_arr, 10):,.0f}")
    print(f"25th Pctile:    {np.percentile(l_arr, 25):,.0f}")
    
    # Suggest an optimal N that preserves the majority of texts without 
    # severely crippling large texts, usually p10 or p25.
    suggest = int(np.percentile(l_arr, 10))
    print(f"\n🧠 Recommended Global Truncation Standard (N): {suggest:,}")

if __name__ == "__main__":
    scan_lengths()
