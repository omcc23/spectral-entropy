"""
Ablation 6 across all 11 languages: sentence-detrended depth residuals.
Expanded paragraphs (~8 sentences each) for meaningful spectral analysis.
"""
import spacy
import numpy as np

def dep_depth(tok):
    d = 0
    while tok.head != tok:
        d += 1
        tok = tok.head
        if d > 100: break
    return d

PARAGRAPHS = {
    "english": {
        "model": "en_core_web_lg",
        "text": (
            "The old cathedral stood silently against the darkening sky. "
            "Rain fell heavily on the cobblestones below. "
            "Inside the great hall, the priest carefully arranged the heavy wooden chairs "
            "that his grandmother had once carved by hand for the village. "
            "Nobody came to the evening service anymore. "
            "The bells had not rung since the previous winter. "
            "A small bird perched on the windowsill and watched the empty pews. "
            "The candles flickered in the cold draft that swept through the broken door."
        )
    },
    "french": {
        "model": "fr_core_news_lg",
        "text": (
            "Le vieux château se dressait en silence contre le ciel sombre. "
            "La pluie tombait lourdement sur les pavés en dessous. "
            "À l'intérieur de la grande salle, le prêtre arrangeait soigneusement les lourdes chaises en bois "
            "que sa grand-mère avait autrefois sculptées à la main pour le village. "
            "Personne ne venait plus au service du soir. "
            "Les cloches n'avaient pas sonné depuis l'hiver précédent. "
            "Un petit oiseau se perchait sur le rebord de la fenêtre et observait les bancs vides. "
            "Les bougies vacillaient dans le courant d'air froid qui traversait la porte brisée."
        )
    },
    "german": {
        "model": "de_core_news_lg",
        "text": (
            "Die alte Kathedrale stand still gegen den dunklen Himmel. "
            "Regen fiel schwer auf das Kopfsteinpflaster darunter. "
            "In der großen Halle ordnete der Priester sorgfältig die schweren Holzstühle an, "
            "die seine Großmutter einst von Hand für das Dorf geschnitzt hatte. "
            "Niemand kam mehr zum Abendgottesdienst. "
            "Die Glocken hatten seit dem vergangenen Winter nicht mehr geläutet. "
            "Ein kleiner Vogel saß auf dem Fensterbrett und beobachtete die leeren Bänke. "
            "Die Kerzen flackerten im kalten Luftzug, der durch die zerbrochene Tür wehte."
        )
    },
    "spanish": {
        "model": "es_core_news_lg",
        "text": (
            "La vieja catedral se alzaba en silencio contra el cielo oscuro. "
            "La lluvia caía con fuerza sobre los adoquines de abajo. "
            "Dentro del gran salón, el sacerdote colocaba cuidadosamente las pesadas sillas de madera "
            "que su abuela había tallado a mano para el pueblo. "
            "Nadie venía ya al servicio de la tarde. "
            "Las campanas no habían sonado desde el invierno pasado. "
            "Un pequeño pájaro se posó en el alféizar de la ventana y observó los bancos vacíos. "
            "Las velas parpadeaban en la corriente de aire frío que atravesaba la puerta rota."
        )
    },
    "italian": {
        "model": "it_core_news_lg",
        "text": (
            "La vecchia cattedrale si ergeva in silenzio contro il cielo scuro. "
            "La pioggia cadeva pesantemente sulle pietre del selciato. "
            "All'interno della grande sala, il prete disponeva con cura le pesanti sedie di legno "
            "che sua nonna aveva un tempo intagliato a mano per il villaggio. "
            "Nessuno veniva più alla funzione serale. "
            "Le campane non suonavano dall'inverno precedente. "
            "Un piccolo uccello si posò sul davanzale della finestra e osservò le panche vuote. "
            "Le candele tremavano nella corrente di aria fredda che attraversava la porta rotta."
        )
    },
    "portuguese": {
        "model": "pt_core_news_lg",
        "text": (
            "A velha catedral erguia-se em silêncio contra o céu escuro. "
            "A chuva caía pesadamente sobre as pedras da calçada. "
            "Dentro do grande salão, o padre arrumava cuidadosamente as pesadas cadeiras de madeira "
            "que sua avó havia entalhado à mão para a aldeia. "
            "Ninguém mais vinha ao serviço da noite. "
            "Os sinos não tocavam desde o inverno passado. "
            "Um pequeno pássaro pousou no parapeito da janela e observou os bancos vazios. "
            "As velas tremulavam na corrente de ar frio que atravessava a porta quebrada."
        )
    },
    "dutch": {
        "model": "nl_core_news_lg",
        "text": (
            "De oude kathedraal stond stil tegen de donkere hemel. "
            "Regen viel zwaar op de kasseien eronder. "
            "In de grote zaal schikte de priester zorgvuldig de zware houten stoelen "
            "die zijn grootmoeder ooit met de hand voor het dorp had gesneden. "
            "Niemand kwam nog naar de avonddienst. "
            "De klokken hadden niet meer geluid sinds de afgelopen winter. "
            "Een kleine vogel zat op de vensterbank en keek naar de lege banken. "
            "De kaarsen flikkerden in de koude tocht die door de gebroken deur woei."
        )
    },
    "polish": {
        "model": "pl_core_news_lg",
        "text": (
            "Stara katedra stała w ciszy naprzeciwko ciemniejącego nieba. "
            "Deszcz padał ciężko na bruk poniżej. "
            "Wewnątrz wielkiej sali ksiądz starannie układał ciężkie drewniane krzesła, "
            "które jego babcia kiedyś rzeźbiła ręcznie dla wioski. "
            "Nikt już nie przychodził na wieczorne nabożeństwo. "
            "Dzwony nie dzwoniły od poprzedniej zimy. "
            "Mały ptak usiadł na parapecie okna i obserwował puste ławki. "
            "Świece migotały w zimnym przeciągu, który wiał przez złamane drzwi."
        )
    },
    "finnish": {
        "model": "fi_core_news_lg",
        "text": (
            "Vanha katedraali seisoi hiljaa tummuvaa taivasta vasten. "
            "Sade putosi raskaasti mukulakivien päälle. "
            "Suuren salin sisällä pappi järjesti huolellisesti raskaat puiset tuolit, "
            "jotka hänen isoäitinsä oli kerran veistänyt käsin kylää varten. "
            "Kukaan ei enää tullut iltajumalanpalvelukseen. "
            "Kellot eivät olleet soineet edellisestä talvesta lähtien. "
            "Pieni lintu istui ikkunalaudalle ja katseli tyhjiä penkkejä. "
            "Kynttilät välkkyivät kylmässä vedossa, joka puhalsi rikkinäisen oven läpi."
        )
    },
    "swedish": {
        "model": "sv_core_news_lg",
        "text": (
            "Den gamla katedralen stod tyst mot den mörka himlen. "
            "Regnet föll tungt på kullerstenarna nedanför. "
            "Inne i den stora salen ordnade prästen noggrant de tunga trästolarna "
            "som hans mormor en gång hade sniddat för hand åt byn. "
            "Ingen kom längre till kvällsgudstjänsten. "
            "Klockorna hade inte ringt sedan förra vintern. "
            "En liten fågel satt på fönsterbrädan och tittade på de tomma bänkarna. "
            "Ljusen fladdrade i det kalla draget som blåste genom den trasiga dörren."
        )
    },
    "russian": {
        "model": "ru_core_news_lg",
        "text": (
            "Старый собор стоял молча на фоне темнеющего неба. "
            "Дождь тяжело падал на мостовую внизу. "
            "Внутри большого зала священник аккуратно расставлял тяжёлые деревянные стулья, "
            "которые его бабушка когда-то вырезала вручную для деревни. "
            "Никто больше не приходил на вечернюю службу. "
            "Колокола не звонили с прошлой зимы. "
            "Маленькая птица села на подоконник и наблюдала за пустыми скамьями. "
            "Свечи мерцали в холодном сквозняке, который дул через сломанную дверь."
        )
    },
}

print("="*70)
print("ABLATION 6: Sentence-Detrended Depth Residuals — All Languages")
print("="*70)

results = []

for lang, info in PARAGRAPHS.items():
    try:
        nlp = spacy.load(info["model"])
    except OSError:
        print(f"\n{lang.upper()}: ⚠ Model not installed, skipping.")
        continue
    
    doc = nlp(info["text"])
    sentences = list(doc.sents)
    
    # Build RAW signal
    raw_signal = []
    sentence_groups = []
    for s in sentences:
        depths = [dep_depth(t) for t in s if t.pos_ not in ('PUNCT', 'SPACE')]
        sentence_groups.append(depths)
        raw_signal.extend(depths)
    raw = np.array(raw_signal, dtype=float)
    
    # Build DETRENDED signal
    detrended = []
    for depths in sentence_groups:
        if depths:
            m = np.mean(depths)
            detrended.extend([d - m for d in depths])
    det = np.array(detrended, dtype=float)
    
    # Compute per-sentence means
    means = [np.mean(d) if d else 0 for d in sentence_groups]
    
    print(f"\n{'─'*70}")
    print(f"  {lang.upper()} ({info['model']}) — {len(sentences)} sentences, {len(raw)} content words")
    print(f"{'─'*70}")
    
    # Show per-sentence breakdown
    for i, (s, depths) in enumerate(zip(sentences, sentence_groups)):
        sent_text = s.text.strip()[:60] + ("..." if len(s.text.strip()) > 60 else "")
        print(f"  S{i+1}: [{len(depths):>2} words] mean={means[i]:.2f}  \"{sent_text}\"")
    
    # Show the key numbers
    raw_var = np.var(raw)
    det_var = np.var(det)
    retained = (det_var / raw_var * 100) if raw_var > 0 else 0
    
    print(f"\n  Raw signal:       mean={np.mean(raw):.2f}, var={raw_var:.3f}")
    print(f"  Detrended signal: mean={np.mean(det):.4f}, var={det_var:.3f}")
    print(f"  Variance retained after detrending: {retained:.1f}%")
    print(f"  ↑ Higher % = more within-sentence structure, less sentence-boundary artifact")
    
    results.append({
        "lang": lang,
        "n_sents": len(sentences),
        "n_words": len(raw),
        "raw_mean": np.mean(raw),
        "raw_var": raw_var,
        "det_var": det_var,
        "retained_pct": retained,
    })

# Final summary table
print(f"\n{'='*70}")
print("SUMMARY TABLE")
print(f"{'='*70}")
print(f"  {'Language':<12} {'Sents':>5} {'Words':>5} {'Raw Var':>8} {'Det Var':>8} {'Retained':>9}")
print(f"  {'─'*12} {'─'*5} {'─'*5} {'─'*8} {'─'*8} {'─'*9}")
for r in results:
    print(f"  {r['lang']:<12} {r['n_sents']:>5} {r['n_words']:>5} {r['raw_var']:>8.3f} {r['det_var']:>8.3f} {r['retained_pct']:>8.1f}%")

avg_retained = np.mean([r['retained_pct'] for r in results])
print(f"\n  Average variance retained across all languages: {avg_retained:.1f}%")
