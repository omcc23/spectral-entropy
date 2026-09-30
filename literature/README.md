# Hop-depth spectra and spectral entropy of literary syntax

Code, public-domain texts, and precomputed spectra for the literature half of:

> Om, Shreyas, Rishi, M. K. Verma. *Spectral Entropy of Music, DNA, and Literature: Signatures of Non-Equilibrium Order.*

We map each book to a **syntactic hop-depth** time series ( Universal Dependencies parse; hops from a content word to the sentence root ), take a single unwindowed DFT, and report:

- the scaling exponent **β** from Eq. (3) of the paper (`log10 E(f) = −β log10 f + c`)
- spectral entropy **H** from Eq. (1) with mass function `P_f = E(f) / Σ E(f)`
- the unit-interval score **H̃** from Eq. (2)
- composition Shannon **S** on Unicode characters, and the normalized score **S̃ = S / log2 A**

## What is in this deposit

| Path | Contents |
| --- | --- |
| `entropy_core.py` | Shannon / hydrodynamic entropy, FFT, smoothing |
| `analyze_all_lg.py` | Parse every book to *N* = 10,000 hop-depths and save spectra |
| `generate_collage.py` | Nature-sized 5-panel figure from cached spectra |
| `fetch_gutenberg.py`, `fetch_gutenberg_multilingual.py`, `new_catalog.py` | Download + curated Gutenberg IDs |
| `prep_large_models.py`, `install_spacy_models.py` | spaCy UD models |
| `run_ablations.py`, `robustness_tests.py`, `crossling_decomposition.py`, `part3_length_control.py`, `cross_test_detrend_shuffle.py`, `ablation6_all_langs.py` | Controls reported in Methods |
| `texts/gutenberg/` | 101 English public-domain books |
| `texts/gutenberg_multi/` | French, German, Spanish, Italian, Portuguese, Polish, Finnish, Swedish, Dutch, Russian |
| `texts/gita_*.txt` | Bhagavad Gita (Sanskrit, Hindi, Telugu, two English translations) |
| `data/master_lg_physics.json` | Per-book *H̃*, β, mean hop-depth, *E(f)* (large-model parses) |
| `data/book_summary.csv` | Same scalars without the long arrays |
| `images/research_collage_final.{png,pdf,svg}` | Figure used in the paper |
| `methodology.pdf` | Methods write-up |

The spectral set used in the paper is **267 books in 9 languages** (English 98, French 27, Spanish 26, German 26, Italian 25, Polish 19, Portuguese 19, Swedish 14, Finnish 13). Dutch and Russian parses and two Spanish books with mean hop-depth ≥ 5 are stored but excluded from the figure (parser failures).

## Pipeline constants (do not change if you want the published numbers)

| Symbol | Value | Role |
| --- | --- | --- |
| *C*min | 500 characters | Drop empty / banner-only files |
| *K* | 50,000 characters | spaCy chunk size |
| *N*content | 10,000 | Content tokens per book (PUNCT / SPACE / X dropped) |
| Depth cap | 100 | Guard on a looping parse; not a linguistic ceiling |

Frequency is *f* = *n* / *N* in cycles per word. The series is mean-centred; *E(f) = \|X(f)\|²*.

## Reproduce the figure (no parser, ~1 minute)

```bash
python -m venv .venv && source .venv/bin/activate
pip install numpy scipy matplotlib
python generate_collage.py
# writes images/research_collage_final.png
```

Needs `data/master_lg_physics.json` from this deposit.

## Re-parse the corpus (slow; needs spaCy large models)

```bash
pip install -r requirements.txt
python prep_large_models.py          # lg models where available
python analyze_all_lg.py             # writes data/master_lg_physics.json
python generate_collage.py
```

GPU is optional. English uses `en_core_web_lg`; other languages use `{lang}_core_news_lg` (or `md` / `sm` if `lg` is missing).

## Re-fetch texts

```bash
python fetch_gutenberg.py
python fetch_gutenberg_multilingual.py
```

Project Gutenberg URLs change; the copies in `texts/` are the ones we analyzed.

## License

- **Code** — MIT (`LICENSE`)
- **Texts** — public-domain Project Gutenberg works; not MIT-licensed. See https://www.gutenberg.org/policy/license.html

## Contact

Rishi Kirti `<rishikirti534@gmail.com>` · M. K. Verma `<mkv@iitk.ac.in>` · Department of Physics, IIT Kanpur.
