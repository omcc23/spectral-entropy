# Spectral entropy of music, DNA, and literature

One repository for the three analyses in the paper. Each folder stands on its own.

| Folder | What it measures |
|---|---|
| [`music/`](music/) | Loudness-envelope spectrum of long music recordings: slope \(\beta\) and hydrodynamic entropy |
| [`literature/`](literature/) | Syntactic hop-depth spectrum of books: slope \(\beta\) and spectral entropy |
| [`dna/`](dna/) | Genomic spectrum and base-composition entropy |

## Data

The measurements, texts, and genome FASTA are deposited on Zenodo, not in this repository:

https://doi.org/10.5281/zenodo.23044174

That record holds the music track table and envelope spectra, the literary texts and hop-depth spectra, and the DNA FASTA. For the music figure, place `tracks.csv` and `spectra.npz` in `music/data/`, then:

```text
cd music
pip install -r requirements.txt
python reproduce.py
```

## Literature figure

The published literature figure is rebuilt from the cached spectra, without re-parsing the books:

```text
cd literature
pip install numpy scipy matplotlib
python generate_collage.py
```

## DNA

`dna/genomic_spectral_analysis.py` and `dna/composition_shannon_entropy.py` read `diverse_long_genomes_voss.fasta` from the Zenodo record. Place that file next to the scripts.
