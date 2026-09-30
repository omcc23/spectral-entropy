"""
Cross-linguistic dependency parse sanity check.
One representative paragraph per language, parsed with the _lg model.
"""
import spacy

PARAGRAPHS = {
    "english": {
        "model": "en_core_web_lg",
        "text": "The old cathedral stood silently against the darkening sky. Rain fell. Nobody came."
    },
    "french": {
        "model": "fr_core_news_lg",
        "text": "Le vieux château se dressait en silence contre le ciel sombre. La pluie tombait. Personne ne venait."
    },
    "german": {
        "model": "de_core_news_lg",
        "text": "Die alte Kathedrale stand still gegen den dunklen Himmel. Regen fiel. Niemand kam."
    },
    "spanish": {
        "model": "es_core_news_lg",
        "text": "La vieja catedral se alzaba en silencio contra el cielo oscuro. Llovía. Nadie vino."
    },
    "italian": {
        "model": "it_core_news_lg",
        "text": "La vecchia cattedrale si ergeva in silenzio contro il cielo scuro. Pioveva. Nessuno venne."
    },
    "portuguese": {
        "model": "pt_core_news_lg",
        "text": "A velha catedral erguia-se em silêncio contra o céu escuro. A chuva caía. Ninguém veio."
    },
    "dutch": {
        "model": "nl_core_news_lg",
        "text": "De oude kathedraal stond stil tegen de donkere hemel. Regen viel. Niemand kwam."
    },
    "polish": {
        "model": "pl_core_news_lg",
        "text": "Stara katedra stała w ciszy naprzeciwko ciemniejącego nieba. Padał deszcz. Nikt nie przyszedł."
    },
    "finnish": {
        "model": "fi_core_news_lg",
        "text": "Vanha katedraali seisoi hiljaa tummuvaa taivasta vasten. Satoi. Kukaan ei tullut."
    },
    "swedish": {
        "model": "sv_core_news_lg",
        "text": "Den gamla katedralen stod tyst mot den mörka himlen. Regnet föll. Ingen kom."
    },
    "russian": {
        "model": "ru_core_news_lg",
        "text": "Старый собор стоял молча на фоне темнеющего неба. Шёл дождь. Никто не пришёл."
    },
}

def dep_depth(tok):
    d = 0
    while tok.head != tok:
        d += 1
        tok = tok.head
        if d > 100: break
    return d

for lang, info in PARAGRAPHS.items():
    print(f"\n{'='*70}")
    print(f"  {lang.upper()} — Model: {info['model']}")
    print(f"{'='*70}")
    
    try:
        nlp = spacy.load(info["model"])
    except OSError:
        print(f"  ⚠ Model not installed, skipping.")
        continue
    
    doc = nlp(info["text"])
    
    for sent in doc.sents:
        print(f"\n  \"{sent.text.strip()}\"")
        print(f"  {'Token':<18} {'POS':<7} {'Dep':<12} {'Head':<18} {'Depth':>5}")
        print(f"  {'─'*18} {'─'*7} {'─'*12} {'─'*18} {'─'*5}")
        
        for tok in sent:
            head_text = tok.head.text if tok.head != tok else "ROOT"
            d = dep_depth(tok)
            print(f"  {tok.text:<18} {tok.pos_:<7} {tok.dep_:<12} {head_text:<18} {d:>5}")
    
    # Summary stats
    depths = [dep_depth(t) for t in doc if t.pos_ not in ('PUNCT', 'SPACE')]
    print(f"\n  Summary: {len(depths)} content words, mean depth={sum(depths)/len(depths):.2f}, max={max(depths)}")
    
    # Verify ROOT count matches sentence count
    roots = [t for t in doc if t.dep_ == 'ROOT']
    sents = list(doc.sents)
    root_ok = "✓" if len(roots) == len(sents) else "✗"
    print(f"  Sentences: {len(sents)}, ROOTs found: {len(roots)} {root_ok}")
