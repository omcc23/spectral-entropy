# Music: envelope-spectrum slope and hydrodynamic entropy

This is the music part of the repository. The measurements are a separate Zenodo dataset
(`envelope_spectra_data.zip`: per-track table and envelope spectra).
This folder rebuilds the category table and the three-panel figure
from that dataset.

Nine categories, 300 recordings each (`N = 2700`). Every excerpt is
`T = 240 s`. Jamendo classical is not included. Western classical is the
concert corpus only.

## What is reported

Each recording is reduced to one loudness-envelope spectrum
`E_{v^2}(f)` on the band `B = [0.01, 1] Hz` (`M = 238` bins).

- **Slope.** Ordinary least squares of `log10 E` against `log10 f` on
  `B` gives slope `α`. The reported exponent is `β = −α`, so a `1/f`
  spectrum has `β = 1`. The number in the table and in panel **a** is
  the **arithmetic mean of the 300 per-track slopes**. Whiskers are one
  standard deviation. `β` is not the slope of an averaged spectrum.
- **Hydrodynamic entropy.** On the same bins,
  `p_k ∝ E_{v^2}(f_k)`,
  `S_H = −Σ p_k log2 p_k` (bits), and
  `H̃ = S_H / log2 M`. Panel **c** shows the distribution of `H̃`.
  The table reports the mean of the 300 track values.
- **Spectra in panel b.** At each frequency the **geometric mean** of
  the track spectra (mean of `log E`, then exp). The curves are
  smoothed, pinned, and offset so the shapes can be compared. The
  dashed line is a `1/f` guide. This average is not used to compute `β`.

## Cohort

| Category | Source | n |
|---|---|---|
| Hiphop, Jazz, Folk, Pop, Rock, Metal | MTG-Jamendo | 300 each |
| Carnatic, Hindustani | Saraga 1.5 concert crops | 300 each |
| W. Classical | Radio Nederland *Concerto Semanal* concert crops | 300 |

Jamendo tags are assigned exclusively (disco, blues, reggae, hiphop,
metal, country, jazz, classical, folk, pop, rock), with at most eight
tracks per artist. Concert crops are non-overlapping 240 s excerpts, at
most four per concert. The balanced sample uses random seed 42.
Carnatic draws on 136 concerts, Hindustani on 72, and W. Classical on 75.

## Measurement

1. Mono audio at 22,050 Hz, peak-normalized, on `[t0, t0+T]`.
2. Zero-phase Butterworth bandpass, order 4, 100 Hz–10 kHz.
3. Instantaneous power `v^2(t)`.
4. Zero-phase Butterworth low-pass at 20 Hz, then decimate by 221
   (`f_env ≈ 99.77 Hz`). Subtract the mean.
5. One-sided Hann periodogram. Frequency resolution `Δf = 1/T ≈ 0.00417 Hz`.
6. Slope and hydrodynamic entropy on `B` only.

`measure.py` is that chain. The released table was produced with it.

## Reproduce the table and figure

Download the Zenodo archive and place `tracks.csv` and `spectra.npz` in `data/`.

```text
pip install -r requirements.txt
python reproduce.py
```

This rewrites `results/category_summary.csv` and
`results/figures/collage_three_panel.png` (and `.pdf`).

## Files

| Path | Contents |
|---|---|
| `measure.py` | Envelope, spectrum, slope, hydrodynamic entropy |
| `figures.py` | The three-panel figure |
| `reproduce.py` | Rebuild the table and the figure |
| `results/figures/collage_three_panel.png` | Panel a mean `β`, panel b `E_{v^2}(f)`, panel c `H̃` |

## Category means

| Category | β | H̃ |
|---|---|---|
| Hiphop | 0.72 | 0.74 |
| Carnatic | 0.73 | 0.85 |
| Jazz | 0.74 | 0.81 |
| Folk | 0.78 | 0.79 |
| Pop | 0.86 | 0.75 |
| Rock | 0.89 | 0.75 |
| Metal | 0.91 | 0.76 |
| Hindustani | 0.97 | 0.84 |
| W. Classical | 1.14 | 0.75 |

## Zenodo dataset

Music, literature, and DNA data are at https://doi.org/10.5281/zenodo.23044174.

Raw audio is not included. Jamendo, Saraga 1.5, and the Radio Nederland
concert broadcasts stay with those collections; `tracks.csv` records the
filename and crop offset.

## References

1. D. Bogdanov, M. Won, P. Tovstogan, A. Porter, and X. Serra, “The MTG-Jamendo dataset for automatic music tagging,” Machine Learning for Music Discovery Workshop, ICML 2019.
2. A. Srinivasamurthy, S. Gulati, R. Caro Repetto, and X. Serra, “Saraga: open datasets for research on Indian art music,” *Empirical Musicology Review* 16, 85–98 (2021).
3. Radio Nederland Wereldomroep, Concerto Semanal.
4. R. F. Voss and J. Clarke, “1/f noise in music and speech,” *Nature* 258, 317–318 (1975).
5. R. F. Voss and J. Clarke, “‘1/f noise’ in music: Music from 1/f noise,” *J. Acoust. Soc. Am.* 63, 258–263 (1978).
6. D. J. Levitin, P. Chordia, and V. Menon, “Musical rhythm spectra from Bach to Joplin obey a 1/f power law,” *Proc. Natl. Acad. Sci. U.S.A.* 109, 3716–3720 (2012).
