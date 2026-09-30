# Spectral entropy of music, DNA, and literature

One repository for the three analyses in the paper. Each folder stands on its own.

| Folder | What it measures |
|---|---|
| [`music/`](music/) | Loudness-envelope spectrum of long music recordings: slope \(\beta\) and hydrodynamic entropy |
| [`literature/`](literature/) | Syntactic hop-depth spectrum of books: slope \(\beta\) and spectral entropy |
| [`dna/`](dna/) | Genomic spectrum and base-composition entropy |

## Music data

The music track table and envelope spectra are not in this repository. They are the Zenodo archive `envelope_spectra_data.zip`. Unpack it so `tracks.csv` and `spectra.npz` are in `music/data/`, then:

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

`dna/genomic_spectral_analysis.py` and `dna/composition_shannon_entropy.py` read a local FASTA file (`diverse_long_genomes_voss.fasta`). That genome file is not included.
