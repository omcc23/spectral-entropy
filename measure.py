"""
Envelope spectrum, slope, and hydrodynamic entropy.

1. Peak-normalize a mono excerpt.
2. Bandpass 100 Hz–10 kHz (Butterworth 4, zero-phase).
3. Instantaneous power v^2(t).
4. Low-pass at 20 Hz and decimate to the loudness envelope.
5. Remove the mean and form a one-sided Hann PSD, E_{v^2}(f).
6. On B = [0.01, 1] Hz: ordinary-least-squares slope and hydrodynamic entropy.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt

import config


def bandpass(y: np.ndarray, *, sr: int = config.SR) -> np.ndarray:
    nyq = 0.5 * float(sr)
    lo = max(1.0, float(config.BP_LO_HZ))
    hi = min(float(config.BP_HI_HZ), nyq * 0.99)
    sos = butter(config.FILTER_ORDER, [lo, hi], btype="band", fs=sr, output="sos")
    return sosfiltfilt(sos, np.asarray(y, dtype=np.float64))


def loudness_envelope(y: np.ndarray, *, sr: int = config.SR) -> tuple[np.ndarray, float]:
    v2 = bandpass(y, sr=sr) ** 2
    nyq = 0.5 * float(sr)
    cut = min(float(config.LPF_HZ), nyq * 0.49)
    sos = butter(config.FILTER_ORDER, cut, btype="low", fs=sr, output="sos")
    p = sosfiltfilt(sos, v2.astype(np.float64))
    p_ds = np.asarray(p[:: config.DECIM], dtype=np.float64)
    f_env = float(sr) / float(config.DECIM)
    return p_ds, f_env


def onesided_psd(signal: np.ndarray, *, sample_rate: float) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(signal, dtype=np.float64)
    n = x.size
    if n < 4:
        raise ValueError("signal too short for a spectrum")
    w = np.hanning(n)
    scale = float(sample_rate) * float(np.sum(w ** 2))
    spec = np.fft.rfft(x * w)
    psd = (np.abs(spec) ** 2) / scale
    if psd.size > 2:
        psd[1:-1] *= 2.0
    freqs = np.fft.rfftfreq(n, d=1.0 / float(sample_rate))
    return freqs, psd


def analysis_band(freqs: np.ndarray) -> np.ndarray:
    f = np.asarray(freqs, dtype=np.float64)
    return (f >= config.BAND_LO_HZ) & (f <= config.BAND_HI_HZ)


def hydrodynamic_entropy(freqs: np.ndarray, psd: np.ndarray) -> dict[str, float]:
    """p ∝ E_{v^2}(f) on B. Returns bits and the unit-interval score."""
    mask = analysis_band(freqs)
    s = np.asarray(psd, dtype=np.float64)[mask]
    s = s[np.isfinite(s) & (s > 0)]
    m = int(s.size)
    empty = {
        "M_bins": m,
        "S_hydro": float("nan"),
        "H_tilde": float("nan"),
        "f_min_hz": float("nan"),
    }
    if m < 2:
        return empty
    p = s / s.sum()
    s_h = float(-np.sum(p * np.log2(p)))
    return {
        "M_bins": m,
        "S_hydro": s_h,
        "H_tilde": s_h / float(np.log2(m)),
        "f_min_hz": float(np.min(freqs[mask])),
    }


def loglog_slope(freqs: np.ndarray, psd: np.ndarray) -> tuple[float, float]:
    """OLS of log10 E vs log10 f on B. Returns (alpha, r2). beta = -alpha."""
    mask = analysis_band(freqs)
    f = np.asarray(freqs, dtype=np.float64)[mask]
    s = np.asarray(psd, dtype=np.float64)[mask]
    ok = (f > 0) & (s > 0) & np.isfinite(s)
    if np.count_nonzero(ok) < 3:
        return float("nan"), float("nan")
    log_f = np.log10(f[ok])
    log_s = np.log10(s[ok])
    slope, intercept = np.polyfit(log_f, log_s, 1)
    yhat = slope * log_f + intercept
    ss_res = float(np.sum((log_s - yhat) ** 2))
    ss_tot = float(np.sum((log_s - np.mean(log_s)) ** 2))
    r2 = 1.0 - ss_res / (ss_tot + 1e-12)
    return float(slope), float(r2)


def metrics_from_envelope(envelope: np.ndarray, f_env: float) -> dict:
    p = np.asarray(envelope, dtype=np.float64)
    p = p - np.mean(p)
    freqs, psd = onesided_psd(p, sample_rate=float(f_env))
    alpha, r2 = loglog_slope(freqs, psd)
    out = hydrodynamic_entropy(freqs, psd)
    out.update(
        {
            "T_s": p.size / float(f_env),
            "f_env": float(f_env),
            "freqs": freqs,
            "psd": psd,
            "alpha": alpha,
            "beta": -alpha if np.isfinite(alpha) else float("nan"),
            "alpha_r2": r2,
        }
    )
    return out


def analyze_waveform(y: np.ndarray, *, sr: int = config.SR) -> dict:
    """Peak-normalize, then measure the loudness-envelope spectrum."""
    y = np.asarray(y, dtype=np.float64)
    peak = float(np.max(np.abs(y))) if y.size else 0.0
    if peak > 0:
        y = y / peak
    envelope, f_env = loudness_envelope(y, sr=sr)
    return metrics_from_envelope(envelope, f_env)
