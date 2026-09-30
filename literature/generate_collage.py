"""
Research Collage Figure — 5-panel publication-quality composite.

Layout: mean dependency depth (full-height left); E(f), β, H_norm panels on the right.
Loads pre-computed Large Model (LG) physics data from data/master_lg_physics.json.
"""
import os, json
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from matplotlib.ticker import FormatStrFormatter, MultipleLocator
from scipy.stats import pearsonr

BASE = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE, 'data', 'master_lg_physics.json')
# FFT length used in analyze_all_lg.py — mode index k → frequency f = k / N
N_SIGNAL = 10_000
EXCLUDE_LANGS = {'dutch', 'russian'}

# Nature double-column artwork: 183 mm wide, ≤247 mm tall; sans-serif 6–8 pt
NATURE_W_MM = 183.0
NATURE_H_MAX_MM = 247.0
MM = 25.4  # mm per inch

# ─── Styling (Nature final-artwork guide) ───────────────────────────────────
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 7.2,
    'axes.labelsize': 7.2,
    'axes.titlesize': 8.4,
    'axes.linewidth': 0.6,
    'axes.grid': False,
    'legend.fontsize': 6.2,
    'xtick.labelsize': 5.8,
    'ytick.labelsize': 5.6,
    'lines.linewidth': 0.8,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'text.antialiased': True,
    'mathtext.default': 'regular',
    'mathtext.fontset': 'dejavusans',
})

def frame_axes(ax, lw=0.6, color='#222222'):
    """Ensure a full rectangular border on all four sides; no gridlines."""
    for side in ('top', 'right', 'bottom', 'left'):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_linewidth(lw)
        ax.spines[side].set_color(color)
    ax.tick_params(which='both', direction='out', length=2.5, width=0.5, pad=1.5)
    ax.grid(False)
    ax.minorticks_off()

LANG_COLORS = {
    'english': '#1976D2', 'french': '#E53935', 'german': '#388E3C',
    'spanish': '#FF9800', 'italian': '#9C27B0', 'portuguese': '#00BCD4',
    'dutch': '#795548', 'polish': '#607D8B', 'finnish': '#E91E63',
    'swedish': '#CDDC39', 'russian': '#FF5722',
}

LANG_SHORT = {
    'portuguese': 'Port.',
}

def lang_display(name):
    """Canonical display label (Portuguese → Port.)."""
    key = name.lower()
    return LANG_SHORT.get(key, name.capitalize())

def lang_color(name):
    return LANG_COLORS.get(name.lower(), '#666666')

def beta_pos(slope):
    """Convention E(f) ∝ f^{-β} so β = −slope (stored slope is log–log)."""
    return -float(slope)

def panel_label(fig, ax, letter):
    """Nature-style panel tag: bold letter outside axes (no parentheses)."""
    bbox = ax.get_position()
    fig.text(
        bbox.x0, bbox.y1 + 0.006, letter,
        transform=fig.transFigure,
        fontsize=9.2, fontweight='bold', fontstyle='italic',
        va='bottom', ha='left', color='#111111',
    )


def annotate_row_values(ax, positions, values, x_vals, fmt='{:.2f}', dx=0.04):
    """Numeric labels to the right of each row, so y-ticks stay language names only."""
    for y, val, x in zip(positions, values, x_vals):
        ax.text(
            x + dx, y, fmt.format(val),
            ha='left', va='center', fontsize=5.2, color='#111111',
            fontweight='bold', clip_on=True, zorder=5,
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.75, pad=0.4),
        )

def load_data():
    if not os.path.exists(DATA_PATH):
        print(f"ERROR: No data found at {DATA_PATH}. Run analyze_all_lg.py first.")
        return []
    with open(DATA_PATH, 'r') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} items. Quarantining texts with mean depth >= 5.0 (Parser Failures)...")
    clean_data = [
        d for d in data
        if d.get('mean_depth', 0) < 5.0
        and d.get('language', '').lower() not in EXCLUDE_LANGS
    ]
    dropped = len(data) - len(clean_data)
    print(f"Filtered {dropped} items (parser failures and {sorted(EXCLUDE_LANGS)}).")
    print(f"Kept {len(clean_data)} texts in {sorted({d['language'] for d in clean_data})}.")
    return clean_data

# ════════════════════════════════════════════════════════════════════════════
#  PANEL (a): Dep-Depth E(k) Spectra Across Languages
# ════════════════════════════════════════════════════════════════════════════
def panel_dep_spectra(ax, data):
    REPRESENTATIVE = {
        'english': 'Pride And Prejudice',
        'french': 'Les Miserables Tome I ',
        'german': 'Faust I',
        'spanish': 'La Regenta Tomo Ii',
        'italian': 'La Divina Commedia',
        'polish': 'Quo Vadis',
        'swedish': 'Nils Holgerssons Underba',
        'portuguese': 'Os Lusiadas',
        'finnish': 'Rautatie',
    }

    # One representative spectrum per language — colors from LANG_COLORS
    curves = []
    plotted_langs = set()
    for item in data:
        lang = item['language'].lower()
        if lang in REPRESENTATIVE and lang not in plotted_langs:
            if REPRESENTATIVE[lang].lower() in item['title'].lower():
                k = np.array(item['k_arr'], dtype=float)
                e = np.array(item['e_smooth_arr'], dtype=float)
                n = len(item.get('depth_signal', [])) or N_SIGNAL
                if len(k) > 0 and len(e) > 0:
                    f = k / float(n)
                    ax.loglog(f, e, lw=0.9, color=lang_color(lang), alpha=0.85, zorder=2)
                    curves.append({
                        'f': f, 'e': e, 'n': float(n),
                        'slope': float(item['slope']),
                        'intercept': float(item['intercept']),
                    })
                    plotted_langs.add(lang)

    if curves:
        c_min = min(curves, key=lambda c: c['slope'])
        c_max = max(curves, key=lambda c: c['slope'])
        f_lo = min(c['f'].min() for c in curves)
        f_hi = max(c['f'].max() for c in curves)
        f_guide = np.logspace(np.log10(f_lo), np.log10(f_hi), 400)

        for c, label in (
            (c_min, f"$\\beta_{{\\max}}={beta_pos(c_min['slope']):.2f}$"),
            (c_max, f"$\\beta_{{\\min}}={beta_pos(c_max['slope']):.2f}$"),
        ):
            fit = (10 ** c['intercept']) * ((c['n'] * f_guide) ** c['slope'])
            e_parent = np.interp(f_guide, c['f'], c['e'])
            keep = fit <= e_parent
            if np.any(keep):
                ax.loglog(f_guide[keep], fit[keep], color='#757575', linestyle='--',
                          lw=1.0, alpha=0.85, zorder=3, label=label)

        leg = ax.legend(loc='lower left', fontsize=6.9, framealpha=0.92,
                        title='slope guides', title_fontsize=6.9,
                        handlelength=1.4, borderpad=0.25, labelspacing=0.2)
        leg.get_frame().set_linewidth(0.6)

        e_all = np.concatenate([c['e'] for c in curves])
        e_lo, e_hi = float(np.min(e_all)), float(np.max(e_all))
        pad = 10 ** 0.08
        ax.set_ylim(e_lo / pad, e_hi * pad)

    ax.set_xlabel('f (frequency)')
    ax.set_ylabel('E(f)')
    ax.yaxis.set_label_coords(-0.16, 0.5)
    ax.tick_params(axis='y', pad=1.2, labelsize=5.6)
    # Major grid only (no minor mesh)
    ax.grid(True, which='major', axis='both', alpha=0.28, linestyle='-', linewidth=0.35)
    ax.grid(False, which='minor')

# ════════════════════════════════════════════════════════════════════════════
#  PANEL (b): Cross-Language Slope Box Plot
# ════════════════════════════════════════════════════════════════════════════
def panel_crosslang_box(ax, data):
    by_lang = defaultdict(list)
    for item in data:
        by_lang[item['language'].lower()].append(beta_pos(item['slope']))

    # Largest β (steepest decay) at bottom — same language order as negative-slope era
    langs_sorted = sorted(by_lang.keys(), key=lambda l: np.median(by_lang[l]), reverse=True)
    plot_data = [by_lang[l] for l in langs_sorted]
    colors = [lang_color(l) for l in langs_sorted]

    bp = ax.boxplot(plot_data, patch_artist=True, widths=0.6, showfliers=True,
                    orientation='horizontal',
                    flierprops=dict(marker='.', markersize=2, alpha=0.5))

    for patch, c in zip(bp['boxes'], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.7)
    for median in bp['medians']:
        median.set_color('black')
        median.set_linewidth(0.9)

    ax.set_yticks(range(1, len(langs_sorted) + 1))
    ax.set_yticklabels([lang_display(l) for l in langs_sorted], fontsize=5.6)
    ax.set_xlabel(r'$\beta$')
    ax.tick_params(axis='y', pad=1.2, labelsize=5.6)
    ax.axvline(x=1.0, color='gray', ls=':', lw=0.5, alpha=0.6)
    ax.axvline(x=0.5, color='gray', ls=':', lw=0.5, alpha=0.6)

    medians = [float(np.median(d)) for d in plot_data]
    x_right = [float(np.max(d)) for d in plot_data]
    annotate_row_values(ax, range(1, len(langs_sorted) + 1), medians, x_right, dx=0.05)
    ax.set_xlim(ax.get_xlim()[0], max(x_right) + 0.22)

# ════════════════════════════════════════════════════════════════════════════
#  PANEL (c): Global β Distribution
# ════════════════════════════════════════════════════════════════════════════
def panel_beta_histogram(ax, data):
    # Plot English vs Non-English to emphasize distribution
    en_slopes = [x['slope'] for x in data if x['language'] == 'english']
    non_en_slopes = [x['slope'] for x in data if x['language'] != 'english']

    ax.hist(en_slopes, bins=20, alpha=0.7, color='#1976D2', label=f'English (μ={np.mean(en_slopes):.2f})', edgecolor='white', lw=0.5)
    ax.hist(non_en_slopes, bins=20, alpha=0.5, color='#E53935', label=f'Other (μ={np.mean(non_en_slopes):.2f})', edgecolor='white', lw=0.5)
    
    ax.axvline(x=np.mean(en_slopes), color='#1976D2', ls='--', lw=1.2)
    if non_en_slopes:
        ax.axvline(x=np.mean(non_en_slopes), color='#E53935', ls='--', lw=1.2)
        
    ax.set_xlabel('Scaling Exponent (β)')
    ax.set_ylabel('Count')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.15, axis='y')

# ════════════════════════════════════════════════════════════════════════════
#  PANEL (d): Language Depth Bar Chart
# ════════════════════════════════════════════════════════════════════════════
def panel_depth_bar(ax, data):
    by_lang = defaultdict(list)
    for item in data:
        by_lang[item['language'].lower()].append(item['mean_depth'])

    langs_sorted = sorted(by_lang.keys(), key=lambda l: np.mean(by_lang[l]), reverse=True)
    means = [np.mean(by_lang[l]) for l in langs_sorted]
    stds = [np.std(by_lang[l]) for l in langs_sorted]
    colors = [lang_color(l) for l in langs_sorted]

    ax.barh(range(len(langs_sorted)), means, xerr=stds, color=colors,
                   alpha=0.8, edgecolor='white', lw=0.3, capsize=1.5)
    ax.set_yticks(range(len(langs_sorted)))
    ax.set_yticklabels([lang_display(l) for l in langs_sorted], fontsize=6.0)
    ax.set_xlabel('Mean Dependency Depth')
    ax.tick_params(axis='y', pad=1.6, labelsize=6.0)
    ax.invert_yaxis()

    x_right = max(m + s for m, s in zip(means, stds)) + 0.55
    ax.set_xlim(0, x_right)
    for i, (m, s) in enumerate(zip(means, stds)):
        ax.text(m + s + 0.08, i, f'{m:.2f}', va='center', ha='left',
                fontsize=5.8, color='#333', clip_on=True)

# ════════════════════════════════════════════════════════════════════════════
#  PANEL (e): Anti-Correlation: Mean Depth vs H_norm
# ════════════════════════════════════════════════════════════════════════════
def panel_anti_correlation(ax, data):
    x_val = []
    y_val = []
    colors = []

    for item in data:
        x_val.append(item['mean_depth'])
        y_val.append(item['h_norm'])
        colors.append(lang_color(item['language']))

    ax.scatter(x_val, y_val, c=colors, alpha=0.85, s=8, edgecolors='none', zorder=3)

    if len(x_val) > 1:
        corr, _ = pearsonr(x_val, y_val)
        m, b = np.polyfit(x_val, y_val, 1)
        ax.plot(np.unique(x_val), m * np.unique(x_val) + b, color='#111111', ls='--', lw=0.8, alpha=0.85)
        ax.text(0.04, 0.12, f'Pearson r: {corr:.2f}', transform=ax.transAxes,
                fontsize=6.4, fontweight='bold', color='#111111',
                bbox=dict(facecolor='white', alpha=0.9, edgecolor='none', pad=0.8))

    y_lo = float(np.percentile(y_val, 1))
    y_hi = float(np.percentile(y_val, 99))
    pad_x = 0.06 * (max(x_val) - min(x_val))
    pad_y = 0.04 * (y_hi - y_lo) if y_hi > y_lo else 0.015
    ax.set_xlim(min(x_val) - pad_x, max(x_val) + pad_x)
    ax.set_ylim(y_lo - pad_y, min(1.0, y_hi + pad_y))

    ax.set_xlabel('Mean Dependency Depth')
    ax.set_ylabel(r'$\tilde{H}$')
    ax.yaxis.set_label_coords(-0.16, 0.5)
    ax.yaxis.set_major_locator(MultipleLocator(0.05))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax.tick_params(axis='y', pad=1.2, labelsize=5.6)

# ════════════════════════════════════════════════════════════════════════════
#  PANEL (f): Centerpiece H_norm Phase Space Box Plot
# ════════════════════════════════════════════════════════════════════════════
def panel_h_norm_centerpiece(ax, data):
    by_lang = defaultdict(list)
    for item in data:
        by_lang[item['language'].lower()].append(item['h_norm'])

    langs_sorted = sorted(by_lang.keys(), key=lambda l: np.median(by_lang[l]))
    plot_data = [by_lang[l] for l in langs_sorted]
    colors = [lang_color(l) for l in langs_sorted]

    all_h = [item['h_norm'] for item in data]
    x_lo, x_hi = max(0.65, min(all_h) - 0.02), min(1.0, max(all_h) + 0.02)

    for i, (lang_data, c) in enumerate(zip(plot_data, colors)):
        jitter = np.random.default_rng(42).uniform(-0.18, 0.18, len(lang_data))
        ax.scatter(lang_data, np.full(len(lang_data), i) + jitter,
                   s=6, color=c, alpha=0.72, edgecolors='none', zorder=3)

    bp = ax.boxplot(plot_data, positions=range(len(langs_sorted)), orientation='horizontal',
                    patch_artist=True, widths=0.45, showfliers=False,
                    boxprops=dict(lw=0.6, facecolor='white', edgecolor='#333333'),
                    whiskerprops=dict(lw=0.6, color='#333333'),
                    capprops=dict(lw=0.6, color='#333333'),
                    medianprops=dict(color='black', lw=1.0))

    ax.set_xlim(x_lo, x_hi)
    ax.set_yticks(range(len(langs_sorted)))
    ax.set_yticklabels([lang_display(l) for l in langs_sorted], fontsize=5.6, color='#111111')
    ax.set_xlabel(r'$\tilde{H}$', fontsize=7.2, color='#111111')
    ax.tick_params(axis='y', pad=1.2, labelsize=5.6)
    ax.xaxis.set_major_locator(MultipleLocator(0.05))
    ax.xaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax.invert_yaxis()

    medians = [float(np.median(d)) for d in plot_data]
    x_right = [float(np.max(d)) for d in plot_data]
    annotate_row_values(ax, range(len(langs_sorted)), medians, x_right, dx=0.012)
    ax.set_xlim(x_lo, max(x_hi, max(x_right) + 0.045))


# ════════════════════════════════════════════════════════════════════════════
#  MAIN — Compose 
# ════════════════════════════════════════════════════════════════════════════
def main():
    data = load_data()
    if not data:
        return

    # Nature double-column: 183 mm wide; lock prior height (~125 mm).
    fig_w = NATURE_W_MM / MM
    fig_h = 125.05 / MM
    margin_l, margin_r = 0.55, 0.12
    margin_b, margin_t = 0.38, 0.42
    left_w = 1.70
    mid_gap = 0.48
    gap_x, gap_y = 0.59, 0.40
    # S from fixed height so output height stays stable
    S = (fig_h - margin_b - gap_y - margin_t) / 2.0
    # Horizontal: shrink left strip slightly if needed to fit width
    used = margin_l + mid_gap + gap_x + margin_r + 2 * S
    left_w = max(1.45, fig_w - used)

    right_w = 2 * S + gap_x
    right_h = 2 * S + gap_y
    fig_h_mm = fig_h * MM
    if fig_h_mm > NATURE_H_MAX_MM:
        raise RuntimeError(f'Figure height {fig_h_mm:.1f} mm exceeds Nature max {NATURE_H_MAX_MM} mm')

    fig = plt.figure(figsize=(fig_w, fig_h), dpi=300)

    def inches_to_fig(x_in, y_in, w_in, h_in):
        return [x_in / fig_w, y_in / fig_h, w_in / fig_w, h_in / fig_h]

    ax_depth = fig.add_axes(inches_to_fig(margin_l, margin_b, left_w, right_h))

    x0 = margin_l + left_w + mid_gap
    y0 = margin_b
    ax_anti = fig.add_axes(inches_to_fig(x0, y0, S, S))
    ax_hnorm = fig.add_axes(inches_to_fig(x0 + S + gap_x, y0, S, S))
    ax_spectra = fig.add_axes(inches_to_fig(x0, y0 + S + gap_y, S, S))
    ax_beta = fig.add_axes(inches_to_fig(x0 + S + gap_x, y0 + S + gap_y, S, S))

    # No figure title (Nature multi-panel: letters only)

    print(f"Generating Nature-sized collage using {len(data)} fully parsed _lg texts...")
    print(f"  {fig_w * MM:.1f} × {fig_h_mm:.1f} mm  "
          f"({fig_w:.2f}\" × {fig_h:.2f}\")  |  right panels {S * MM:.1f} mm squares")

    panel_depth_bar(ax_depth, data)
    panel_dep_spectra(ax_spectra, data)
    panel_crosslang_box(ax_beta, data)
    panel_anti_correlation(ax_anti, data)
    panel_h_norm_centerpiece(ax_hnorm, data)

    for ax in (ax_depth, ax_spectra, ax_beta, ax_anti, ax_hnorm):
        frame_axes(ax)
        if ax is not ax_spectra:
            ax.grid(False)
            ax.minorticks_off()
        ax.xaxis.label.set_color('#111111')
        ax.yaxis.label.set_color('#111111')
        ax.tick_params(axis='both', colors='#111111')
        for lab in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            lab.set_color('#111111')

    # (b) major grid only — no minor mesh
    ax_spectra.minorticks_on()
    ax_spectra.grid(True, which='major', axis='both', alpha=0.28, linestyle='-', linewidth=0.35)
    ax_spectra.grid(False, which='minor')

    # Panel tags outside axes: (a) depth, (b) spectra, (c) β, (d) anti-corr, (e) H_norm
    panel_label(fig, ax_depth, 'a')
    panel_label(fig, ax_spectra, 'b')
    panel_label(fig, ax_beta, 'c')
    panel_label(fig, ax_anti, 'd')
    panel_label(fig, ax_hnorm, 'e')

    out_png = os.path.join(BASE, 'images', 'research_collage_final.png')
    out_pdf = os.path.join(BASE, 'images', 'research_collage_final.pdf')
    out_svg = os.path.join(BASE, 'images', 'research_collage_final.svg')
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    fig.savefig(out_png, dpi=300, facecolor='white')
    fig.savefig(out_pdf, facecolor='white')
    fig.savefig(out_svg, facecolor='white')
    print(f"\n✓ Saved: {out_png}")
    print(f"✓ Saved: {out_pdf}")
    print(f"✓ Saved: {out_svg}")
    print(f"  Nature double-column width 183 mm; height {fig_h_mm:.1f} mm (max 247 mm)")
    plt.close()

if __name__ == '__main__':
    main()
