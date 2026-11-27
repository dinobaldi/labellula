"""Descrizione delle foto: per ogni immagine scrive una scheda .txt nella sottocartella `_txt`.

    python -m labellula descrivi [--cartella X] [--limite N] [--rifai]

Il formato della scheda è lo stesso del codice legacy (prompt v4), così le schede vecchie e nuove
si leggono e si cercano allo stesso modo (vedi schede.py). Il lavoro si può interrompere e riprendere:
le foto che hanno già una scheda vengono saltate.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import foto as F
from .indice import trova_foto
from .motori import Risposta

VERSIONE_PROMPT = "v5"   # predefinita; "v4" resta per confronto e compatibilità
# Etichetta scritta nelle schede: cambia a ogni modifica del testo del prompt, così si sa sempre cosa ha generato cosa
ETICHETTE = {"v4": "v4", "v5": "v5.2"}


LINGUE = {"it": "italiano", "en": "English", "fr": "français", "de": "Deutsch", "es": "español"}
NOMI_IN_INGLESE = {"it": "Italian", "en": "English", "fr": "French", "de": "German", "es": "Spanish"}


def etichetta(versione: str, lingua: str = "it") -> str:
    """'v5.2' per l'italiano, 'v5.2-en' ecc. per le altre lingue: cambiare lingua = schede da aggiornare."""
    e = ETICHETTE.get(versione, versione)
    return e if lingua in ("", "it") or versione == "v4" else f"{e}-{lingua}"

CATEGORIE_PREDEFINITE = [
    "lavoro", "hardware-vintage", "famiglia-e-amici", "viaggi-e-vacanze",
    "insetti-e-natura", "astronomia", "documenti-e-libri", "altro",
]
CATEGORIE_PER_LINGUA = {
    "en": ["work", "vintage-hardware", "family-and-friends", "travel", "insects-and-nature", "astronomy",
           "documents-and-books", "other"],
    "fr": ["travail", "materiel-ancien", "famille-et-amis", "voyages", "insectes-et-nature", "astronomie",
           "documents-et-livres", "autre"],
    "de": ["arbeit", "historische-computer", "familie-und-freunde", "reisen", "insekten-und-natur", "astronomie",
           "dokumente-und-buecher", "sonstiges"],
    "es": ["trabajo", "hardware-antiguo", "familia-y-amigos", "viajes", "insectos-y-naturaleza", "astronomia",
           "documentos-y-libros", "otros"],
}

PROMPT = """Sei un archivista di fotografie. Descrivi in italiano, nel modo più dettagliato e fedele possibile, questa immagine.

Contesto (serve solo a orientarti: NON è scritto nell'immagine e NON va copiato nelle trascrizioni o nelle parole chiave, a meno che tu lo veda davvero):
{contesto}
Rispondi con testo semplice, senza markdown e senza asterischi, in queste sei sezioni:
DESCRIZIONE: soggetto principale, oggetti, ambiente, colori, azione in corso. Se ci sono persone, specifica se indossano divise scout, magliette di eventi (es. CoderDojo, fiere) o abbigliamenti particolari legati al contesto.
TESTI VISIBILI: trascrivi lettera per lettera scritte, marche, modelli ed etichette realmente leggibili. Sulle schede elettroniche NON trascrivere le serigrafie dei componenti minuscoli generici (es. CF1, R12, C3), ma solo i testi e le marche principali dei chip. Se non ce ne sono scrivi "nessuno".
LUOGO E PERIODO: dove e quando è stata scattata la foto. Nelle foto astronomiche, se è presente una cornice con testi (nome target, tempo di posa, coordinate), trascrivili fedelmente qui. Se non determinabile scrivi "non determinabile".
CATEGORIA: scegli una sola etichetta tra questo elenco fisso, scrivendola esattamente così: {categorie}
PERSONE: se non ci sono persone scrivi "nessuna". Se ci sono, scrivi solo quante e se i volti sono ben visibili. Non provare a indovinare chi sono e non inventare nomi.
PAROLE CHIAVE: da 8 a 15 parole chiave separate da virgole, solo su ciò che è nell'immagine. Niente parole generiche come "fotografia" o "archivio".

Regole:
- Descrivi solo ciò che vedi. Se un dettaglio non è chiaro, dillo invece di inventare.
- Parla dello stato di conservazione solo per oggetti e hardware vintage.
- Se c'è un carrello elevatore: marca, modello, portata, cabina, tipo di montante e targhetta.
- Se c'è hardware vintage: marca, modello esatto e periferiche. Specifica se sembra in fase di restauro (smontato, cavi a vista, ambiente da laboratorio) o in esposizione (stile museale o evento pubblico).
- Se c'è un insetto/animale: famiglia o ordine, ambiente.
- Se è una foto astronomica: soggetto, e se leggibili i dati strumentali in sovrimpressione.
- Non indovinare marche o modelli che non sono scritti o inequivocabili."""

PROMPT_V5 = """Sei un archivista fotografico esperto. Scrivi in italiano la scheda di catalogo di questa immagine: precisa, ricca di dettagli verificabili, utile a ritrovarla tra decine di migliaia di foto.

INFORMAZIONI SULLA FOTO (non sono scritte nell'immagine):
{contesto}
Come usarle:
- Le cartelle sono state scritte a mano dal fotografo: per luogo, data, evento e persone presenti sono di solito la fonte più affidabile. Usale, indicando sempre la fonte tra parentesi.
- Quando l'informazione è "confermata" puoi darla per certa. Quando è "presunta" usala come probabile. Quando è "in contrasto", riporta entrambe le versioni.
- Il profilo del fotografo dice cosa fotografa DI SOLITO: non usarlo per decidere cosa c'è in QUESTA foto.
- Se l'immagine contraddice le informazioni (per esempio la cartella dice "mare" ma vedi montagne), fidati dell'immagine e segnalalo in DUBBI.
- Se le informazioni danno un luogo, anche solo presunto, scrivilo in LUOGO E PERIODO: non scrivere "non determinabile" per il fatto che non lo vedi nell'immagine.
- Se il luogo preciso non è noto ma le cartelle o l'immagine indicano il tipo di luogo (casa, giardino, museo, palestra, aeroporto, cucina...), scrivi il tipo di luogo con la fonte, per esempio "casa del fotografo (dalla cartella)", invece di "non determinabile".
- Scrivi "confermato" solo se qui sopra c'è scritto "confermato". Non dire mai che il GPS conferma qualcosa se il GPS non è indicato.

Rispondi con testo semplice, senza markdown e senza asterischi, con queste dieci sezioni nell'ordine, ognuna che inizia con il nome della sezione seguito da due punti:
TITOLO: una riga di al massimo 12 parole: soggetto principale e, se noti, occasione e luogo. Esempio: "Commodore PET 2001 in esposizione a una mostra di computer storici".
DESCRIZIONE: da 4 a 8 frasi. Prima il soggetto principale, poi gli altri elementi dal primo piano allo sfondo, l'ambiente (interno o esterno, tipo di luogo), i colori dominanti, la luce, il momento della giornata e la stagione se riconoscibili, il meteo, l'azione in corso. Dai numeri quando puoi (quanti oggetti, quante persone). Nomina gli oggetti con il termine più preciso che sei sicuro di conoscere ("macchina da scrivere Olivetti" invece di "oggetto", "Vespa" solo se è chiaramente una Vespa).
TESTI VISIBILI: trascrivi fedelmente, separati da virgole, scritte, insegne, marche, modelli, cartelli di musei ed etichette realmente leggibili. Non trascrivere le sigle minuscole dei componenti elettronici (R12, C3). Se una scritta è leggibile solo in parte, scrivi la parte certa e "[...]". Se non ce ne sono: "nessuno".
LUOGO E PERIODO: dove e quando (data e ora esatte se note, più il momento della giornata), con la fonte tra parentesi per ogni informazione: (dalla cartella), (dalla cartella, confermato dal GPS), (dal GPS), (da EXIF), (dal nome del file), (dedotto dall'immagine). Esempio: "Torino, Piemonte (dalla cartella, confermato dal GPS); 4 febbraio 2024, mattina (da EXIF); palazzetto dello sport (dedotto dall'immagine)". Se niente è determinabile: "non determinabile".
OCCASIONE: l'evento o l'attività (gara, compleanno, vacanza, visita a un museo, lavoro, restauro, esperimento...), con la fonte tra parentesi. Se non si capisce: "non determinabile".
CATEGORIA: una sola etichetta di questo elenco, scritta esattamente così: {categorie}
PERSONE: "nessuna" se non ci sono persone. Altrimenti: quante sono, età approssimativa (bambino, ragazzo, adulto, anziano), cosa fanno, abbigliamento (divise, maglie di squadre o di eventi), se i volti sono ben visibili. Non riconoscere nessuno dal volto e non attribuire nomi a persone specifiche. Se le cartelle contengono nomi propri di persona, aggiungi alla fine "Le cartelle citano: ..." (es. "Le cartelle citano: Anna"); se non ne contengono non aggiungere niente.
ASPETTI FOTOGRAFICI: tipo di scatto (ritratto, panorama, macro, foto da drone, notturna, lunga esposizione, controluce, scansione di una stampa o di un documento, foto di uno schermo...), inquadratura e punto di vista, messa a fuoco, difetti evidenti (mossa, sfocata, sovraesposta, sottoesposta).
PAROLE CHIAVE: da 10 a 20 parole chiave separate da virgole: oggetti, marche e modelli, luogo, occasione, ambiente, colori principali. Comprendi il luogo e l'occasione delle cartelle se coerenti con l'immagine. Niente parole generiche come "fotografia", "immagine" o "archivio".
DUBBI: cosa non è sicuro o è in contrasto (immagine contro cartella, scritte poco leggibili, modello incerto). Se non ce ne sono: "nessuno".

Regole:
- Descrivi solo ciò che vedi o che le informazioni dichiarano, sempre con la fonte. Mai inventare.
- Scrivi tutto in italiano, anche i nomi degli animali e degli oggetti comuni (volpe, non fox).
- Non indovinare marche o modelli che non sono scritti o inequivocabili: scrivi "probabilmente" o descrivi la forma.
- Hardware e oggetti vintage: marca, modello esatto se leggibile, periferiche, stato di conservazione; specifica se sembra in restauro (smontato, cavi a vista, banco da laboratorio) o in esposizione (museo, fiera, evento pubblico).
- Veicoli, carrelli elevatori e macchinari: marca, modello, tipo, colore, targhe o targhette leggibili.
- Animali, insetti e piante: il nome comune e, se sicuro, la famiglia o l'ordine; l'ambiente.
- Astronomia: soggetto (Luna, pianeta, nebulosa, galassia, via lattea, scie di stelle) e i dati in sovrimpressione se leggibili.
- Documenti, libri e schermi: titolo, autore o editore se leggibili, lingua, tipo di documento. Non trascrivere dati personali come indirizzi, codici fiscali o numeri di documenti: scrivi "[dato personale]"."""

PROMPT_V5_EN = """You are an expert photo archivist. Write the catalogue record of this image in {lingua}: precise, rich in verifiable details, useful to find it again among tens of thousands of photos.

INFORMATION ABOUT THE PHOTO (not written in the image; some lines may be in Italian, read them as information):
{contesto}
How to use it:
- The folder names were written by hand by the photographer: for place, date, event and people present they are usually the most reliable source. Use them, always giving the source in brackets.
- When information is marked "confermata/confermato" (confirmed) you can treat it as certain. "Presunta/presunto" (presumed) means probable. "In contrasto" (conflicting) means you must report both versions.
- The photographer's profile says what they USUALLY photograph: do not use it to decide what is in THIS photo.
- If the image contradicts the information (for example the folder says "sea" but you see mountains), trust the image and say so in DOUBTS.
- If the information gives a place, even only presumed, write it in PLACE AND DATE: do not write "not determinable" just because you do not see it in the image.
- If the exact place is unknown but the folders or the image show the kind of place (home, garden, museum, gym, airport, kitchen...), write the kind of place with its source, for example "photographer's home (from the folder)".
- Write "confirmed" only if it says so above. Never say that GPS confirms something if no GPS is given.

Answer in plain text, no markdown and no asterisks, with these ten sections in this order. Keep the section names in English exactly as written; write the content in {lingua}:
TITLE: one line of at most 12 words: main subject and, if known, occasion and place.
DESCRIPTION: 4 to 8 sentences. First the main subject, then the other elements from foreground to background, the setting (indoors or outdoors, kind of place), dominant colours, light, time of day and season if recognisable, weather, the action taking place. Give numbers when you can. Name objects with the most precise term you are sure of.
VISIBLE TEXT: faithfully transcribe, separated by commas, the writings, signs, brands, models, museum labels and tags that are really legible. Do not transcribe the tiny codes of electronic components. If a writing is only partly legible, write the certain part and "[...]". If there is none: the word for "none" in {lingua}.
PLACE AND DATE: where and when (exact date and time if known, plus the time of day), with the source in brackets for each piece of information: (from the folder), (from the folder, confirmed by GPS), (from GPS), (from EXIF), (from the file name), (deduced from the image) – translated into {lingua}. If nothing can be determined, say so in {lingua}.
OCCASION: the event or activity, with the source in brackets. If unclear, say so in {lingua}.
CATEGORY: exactly one label from this fixed list, written exactly like this: {categorie}
PEOPLE: "none" (in {lingua}) if there are no people. Otherwise: how many, approximate age (child, young person, adult, elderly), what they are doing, clothing, whether faces are clearly visible. Do not recognise anyone by their face and do not attribute names to specific people. If the folders contain people's first names, add at the end the equivalent of "The folders mention: ..."; if they do not, add nothing.
PHOTOGRAPHIC ASPECTS: kind of shot (portrait, landscape, macro, drone photo, night, long exposure, backlight, scan of a print or document, photo of a screen...), framing and point of view, focus, obvious defects (blurred, out of focus, over- or underexposed).
KEYWORDS: 10 to 20 keywords separated by commas, in {lingua}: objects, brands and models, place, occasion, setting, main colours. Include the place and occasion from the folders if consistent with the image. No generic words like "photo", "image" or "archive".
DOUBTS: what is uncertain or conflicting. If nothing, the word for "none" in {lingua}.

Rules:
- Describe only what you see or what the information states, always with the source. Never invent.
- Write everything in {lingua}, including the names of animals and common objects.
- Do not guess brands or models that are not written or unmistakable: say "probably" or describe the shape.
- Vintage hardware and objects: brand, exact model if legible, peripherals, condition; say whether it looks under restoration or on display (museum, fair, public event).
- Vehicles and machinery: brand, model, type, colour, legible plates or tags.
- Animals, insects and plants: common name and, if sure, family or order; the environment.
- Astronomy: subject and the overlaid data if legible.
- Documents, books and screens: title, author or publisher if legible, language, kind of document. Do not transcribe personal data such as addresses or ID numbers: write "[personal data]"."""

AVVISO_RIPETIZIONE = (
    "[ATTENZIONE: il modello ha ripetuto una frase all'infinito e la risposta "
    "è stata troncata. Descrizione probabilmente incompleta, da rigenerare o "
    "controllare a mano.]\n\n"
)


# ---------------------------------------------------------------- prompt
def componi_prompt(foto: Path, info: F.InfoFoto, contesto_fotografo: str, categorie: list[str],
                   con_percorso: bool = True, versione: str = "v4", luoghi_noti: dict | None = None,
                   lingua: str = "it") -> str:
    """`con_percorso=False` toglie cartella, nome del file e luogo: da usare con un motore remoto
    se l'utente non vuole che quei dati escano dal PC. `lingua`: lingua della scheda (solo prompt v5)."""
    if versione == "v5":
        return _prompt_v5(info, contesto_fotografo, categorie, con_percorso, luoghi_noti, lingua)
    righe = []
    if contesto_fotografo:
        righe.append(f"- Il fotografo: {contesto_fotografo}")
    if con_percorso:
        try:
            cartella = foto.parent.relative_to(foto.anchor).as_posix() or "(radice)"
        except ValueError:
            cartella = str(foto.parent)
        righe += [f"- Cartella: {cartella}", f"- Nome del file: {foto.name}"]
    righe.append(f"- Data: {info.quando}")
    if con_percorso:
        righe.append(f"- Luogo GPS: {info.luogo or 'non disponibile'}")
    return PROMPT.format(contesto="\n".join(righe) + "\n", categorie=", ".join(categorie))


def luoghi_noti_citati(indizi, luoghi_noti: dict) -> list[str]:
    """Voci del dizionario personale (config: descrizione.luoghi_noti) che compaiono nelle cartelle."""
    if not indizi or not luoghi_noti:
        return []
    import re
    testo = " ".join(indizi.cartelle).lower()
    return [f'"{k}" = {v}' for k, v in luoghi_noti.items()
            if re.search(r"(?<!\w)" + re.escape(str(k).lower()) + r"(?!\w)", testo)]


def ripulisci(testo: str) -> str:
    """Toglie le frasi vuote che il modello aggiunge nonostante le istruzioni."""
    import re
    testo = re.sub(r"\s*Le cartelle citano:\s*(nessun[oa]?|non |\"|')[^\n]*", "", testo, flags=re.I)
    return re.sub(r"\s*The folders mention:\s*(none|no |nothing|\"|')[^\n]*", "", testo, flags=re.I)


def _prompt_v5(info: F.InfoFoto, contesto_fotografo: str, categorie: list[str], con_percorso: bool,
               luoghi_noti: dict | None = None, lingua: str = "it") -> str:
    r = []
    if contesto_fotografo:
        r.append(f"- Profilo del fotografo: {contesto_fotografo}")
    if con_percorso and info.indizi and not info.indizi.vuoti:
        r += info.indizi.righe_prompt()
        noti = luoghi_noti_citati(info.indizi, luoghi_noti or {})
        if noti:
            r.append("- Nomi delle cartelle spiegati dal fotografo (affidabili): " + "; ".join(noti))
    r.append(f"- Data e ora dello scatto: {info.quando}")
    lat = info.exif.get("GPSLatitude") if isinstance(info.exif.get("GPSLatitude"), (int, float)) else None
    sm = F.stagione_momento(F.data_exif(info.exif), lat)
    if sm:
        r.append(f"- Stagione e momento della giornata dalla data EXIF: {sm} (presunti: l'orologio della "
                 "fotocamera può essere sbagliato, controlla con luce, ombre e vegetazione e segnala in DUBBI se non tornano)")
    if con_percorso and info.luogo:
        r.append(f"- Luogo dal GPS: {info.luogo}")
    camera = " ".join(str(x) for x in (info.exif.get("Make"), info.exif.get("Model")) if x)
    tecnica = " · ".join(str(x) for x in (camera, info.exif.get("LensModel"), F.scatto(info.exif)) if x)
    if tecnica:
        r.append(f"- Fotocamera e scatto: {tecnica}")
    if lingua not in ("", "it"):
        return PROMPT_V5_EN.format(contesto="\n".join(r) + "\n", categorie=", ".join(categorie),
                                   lingua=NOMI_IN_INGLESE.get(lingua, "English"))
    return PROMPT_V5.format(contesto="\n".join(r) + "\n", categorie=", ".join(categorie))


def degenerata(testo: str) -> bool:
    """True se il modello si è incantato (stessa frase ripetuta o elenchi infiniti di sigle)."""
    import re
    frasi = [r.strip() for r in re.split(r"[.\n]", testo) if len(r.strip()) > 8]
    if frasi:
        conta: dict[str, int] = {}
        for r in frasi:
            conta[r] = conta.get(r, 0) + 1
        if max(conta.values()) >= 4:
            return True
    return len(re.findall(r"\b[A-Z]{1,4}\d{1,4}\b", testo)) > 20


# ---------------------------------------------------------------- scheda
def cartella_relativa(foto: Path, radice: Path | None) -> str:
    """Cartella della foto rispetto alla radice dell'archivio, con barre "/" ("." se è la radice).
    Nella scheda non finisce il percorso completo del disco (nome utente, lettere di unità): la scheda
    resta valida se l'archivio si sposta e si può condividere senza rivelare com'è fatto il computer."""
    if radice is not None:
        try:
            return foto.parent.resolve().relative_to(Path(radice).resolve()).as_posix() or "."
        except (ValueError, OSError):
            pass
    return foto.parent.name or "."


def piede(foto: Path, info: F.InfoFoto, modello: str, versione: str = "v4", lingua: str = "it",
          radice: Path | None = None) -> list[str]:
    e, m = info.exif, info.metriche
    righe = [f"File: {foto.name}", f"Cartella: {cartella_relativa(foto, radice)}", f"Data: {info.quando}"]
    if info.luogo:
        righe.append(f"Luogo GPS: {info.luogo}")
    camera = " ".join(str(x) for x in (e.get("Make"), e.get("Model")) if x)
    if camera:
        righe.append("Fotocamera: " + camera + (f" · {e['LensModel']}" if e.get("LensModel") else ""))
    software = e.get("Software") or e.get("ProcessingSoftware")
    if software:
        righe.append(f"Software: {software}")
    s = F.scatto(e)
    if s:
        righe.append(f"Scatto: {s}")
    righe.append(f"Dimensioni: {m['larghezza']}x{m['altezza']} px ({m['formato']})")
    righe.append(f"Peso file: {m['peso_mb']:.2f} MB")
    righe.append(f"Luminosità media: {m['luminosita']:.1f}/255")
    if "phash" in m:
        righe.append(f"Hash percettivo: {m['phash']}")
    if "nitidezza" in m:
        righe.append(f"Nitidezza (indice): {m['nitidezza']:.1f}")
    if info.indizi and info.indizi.riga_piede():
        righe.append(f"Indizi dalle cartelle: {info.indizi.riga_piede()}")
    righe.append(f"Generato con: {modello} (prompt {etichetta(versione, lingua)})")
    return righe


def file_scheda(foto: Path, cartella_txt: str) -> Path:
    return foto.parent / cartella_txt / (foto.stem + ".txt")


def scrivi_scheda(dest: Path, testo: str, righe_piede: list[str]) -> None:
    dest.parent.mkdir(exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(testo + "\n\n---\n" + "\n".join(righe_piede) + "\n", encoding="utf-8")
    tmp.replace(dest)  # scrittura atomica: mai schede a metà


def descrivi_foto(foto: Path, motore, opzioni: "Opzioni") -> tuple[Path, bool, str]:
    """Descrive una foto e scrive la scheda. Restituisce (file scheda, da_verificare, titolo)."""
    info, im = F.analizza(foto, opzioni.radice)
    prompt = componi_prompt(foto, info, opzioni.contesto, opzioni.categorie,
                            con_percorso=motore.locale or opzioni.percorso_al_remoto, versione=opzioni.versione,
                            luoghi_noti=opzioni.luoghi_noti, lingua=opzioni.lingua)
    jpeg = F.copia_ridotta(im, opzioni.lato_massimo)
    lunghezza = 900 if opzioni.versione == "v4" else 1500
    r: Risposta = motore.descrivi(jpeg, prompt, lunghezza=lunghezza)
    if len(r.testo) < 20:
        raise RuntimeError("risposta vuota o troppo corta dal modello")
    da_verificare = False
    if r.troncata or degenerata(r.testo):
        r = motore.descrivi(jpeg, prompt, ripetizioni=1.5, lunghezza=lunghezza)
        da_verificare = r.troncata or degenerata(r.testo)
    testo = (AVVISO_RIPETIZIONE if da_verificare else "") + ripulisci(r.testo)
    dest = file_scheda(foto, opzioni.cartella_txt)
    scrivi_scheda(dest, testo, piede(foto, info, motore.nome, opzioni.versione, opzioni.lingua, opzioni.radice))
    import re
    m = re.search(r"^\s*(?:TITOLO|TITLE):\s*(.+)$", testo, re.M)
    return dest, da_verificare, (m.group(1).strip() if m else "")


# ---------------------------------------------------------------- lotto
@dataclass
class Opzioni:
    cartella_txt: str = "_txt"
    lato_massimo: int = 1344
    contesto: str = ""
    categorie: list[str] = field(default_factory=lambda: list(CATEGORIE_PREDEFINITE))
    percorso_al_remoto: bool = False
    versione: str = VERSIONE_PROMPT
    radice: Path | None = None        # radice dell'archivio: le cartelle sotto di lei sono indizi
    luoghi_noti: dict = field(default_factory=dict)   # "Casa" -> "abitazione del fotografo a ..."
    lingua: str = "it"                                 # lingua delle schede: it, en, fr, de, es

    @classmethod
    def da_config(cls, cfg) -> "Opzioni":
        d = cfg.dati.get("descrizione") or {}
        return cls(cartella_txt=cfg["schede"]["cartella_txt"],
                   lato_massimo=int(cfg["modello"]["lato_massimo_px"]),
                   contesto=(d.get("contesto") or "").strip(),
                   categorie=_categorie(d.get("categorie"), str(d.get("lingua") or "it")),
                   lingua=str(d.get("lingua") or "it") if str(d.get("lingua") or "it") in LINGUE else "it",
                   percorso_al_remoto=bool(d.get("percorso_al_remoto", False)),
                   versione=str(d.get("prompt") or VERSIONE_PROMPT),
                   luoghi_noti={str(k): str(v) for k, v in (d.get("luoghi_noti") or {}).items()})


def generata_con(scheda: Path) -> str:
    """'(prompt v5.1)' o simile, letto dalla fine della scheda ('' se non c'è)."""
    try:
        with scheda.open("rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 1500))
            coda = fh.read().decode("utf-8", "replace")
    except OSError:
        return ""
    import re
    m = re.search(r"Generato con: .*\(prompt ([^)]+)\)", coda)
    return m.group(1) if m else ""


def _categorie(da_config, lingua: str) -> list[str]:
    """Le categorie del config; se sono quelle predefinite italiane e la lingua è un'altra, quelle della lingua."""
    lista = list(da_config or CATEGORIE_PREDEFINITE)
    if lingua in CATEGORIE_PER_LINGUA and lista == CATEGORIE_PREDEFINITE:
        return list(CATEGORIE_PER_LINGUA[lingua])
    return lista


def da_fare(radice: Path, estensioni, salta_cartelle, cartella_txt: str, rifai: bool = False,
            aggiorna_a: str | None = None, ricorsiva: bool = True):
    """(totale foto, foto da descrivere, foto con lo stesso nome di un'altra nella stessa cartella).

    `aggiorna_a="v5.1"`: rifà solo le schede generate con un prompt diverso (si riprende da dove si era)."""
    totale, visti, lista, doppi = 0, set(), [], []
    for f in trova_foto(radice, estensioni, salta_cartelle, ricorsiva):
        totale += 1
        dest = file_scheda(f, cartella_txt)
        if dest in visti:   # es. IMG_1.jpg e IMG_1.png: una sola scheda possibile (limite del formato)
            doppi.append(f)
            continue
        visti.add(dest)
        if rifai or not dest.exists() or (aggiorna_a and generata_con(dest) != aggiorna_a):
            lista.append(f)
    return totale, lista, doppi


def esegui(radice: Path, motore, opzioni: Opzioni, estensioni, salta_cartelle, cartella_log: Path,
           limite: int = 0, rifai: bool = False, stampa: Callable[[str], None] = print, aggiorna: bool = False,
           avanzamento: Callable[[dict], None] | None = None, fermati: Callable[[], bool] | None = None,
           ricorsiva: bool = True) -> dict:
    """`avanzamento` riceve un dizionario dopo ogni foto; se `fermati()` diventa vero il lotto si ferma
    alla foto successiva (le schede già scritte restano). `ricorsiva=False`: solo le foto direttamente
    nella cartella, non quelle delle sottocartelle."""
    motore.controlla()
    if opzioni.radice is None:          # copia: le opzioni di chi chiama restano com'erano
        opzioni = replace(opzioni, radice=radice)
    stampa(f"Cerco le foto in {radice} ... (modello {motore.nome}, prompt {etichetta(opzioni.versione, opzioni.lingua)})")
    totale, lista, doppi = da_fare(radice, estensioni, salta_cartelle, opzioni.cartella_txt, rifai,
                                   aggiorna_a=etichetta(opzioni.versione, opzioni.lingua) if aggiorna else None,
                                   ricorsiva=ricorsiva)
    stampa(f"Trovate {totale} foto, da descrivere: {len(lista)}"
           + (f" ({len(doppi)} saltate perché hanno lo stesso nome di un'altra)" if doppi else ""))
    if limite:
        lista = lista[:limite]
        stampa(f"(limite: ne descrivo {len(lista)})")

    cartella_log.mkdir(parents=True, exist_ok=True)
    log_errori = cartella_log / "descrizione_errori.log"
    log_verifica = cartella_log / "descrizione_da_verificare.txt"
    t0, fatte, errori, verificare = time.time(), 0, 0, 0
    if avanzamento:
        avanzamento({"fatte": 0, "totale": len(lista), "foto": "", "esito": "", "secondi_mancanti": None,
                     "modello": motore.nome, "prompt": etichetta(opzioni.versione, opzioni.lingua), "titolo": "",
                     "in_corso": lista[0].name if lista else ""})
    try:
        for i, f in enumerate(lista, 1):
            if fermati and fermati():
                stampa("Fermato su richiesta.")
                break
            t1 = time.time()
            titolo = ""
            if avanzamento:
                avanzamento({"in_corso": f.name, "cartella_in_corso": f.parent.name})
            try:
                _, dubbio, titolo = descrivi_foto(f, motore, opzioni)
                fatte += 1
                esito = "OK"
                if dubbio:
                    verificare += 1
                    esito = "OK, da verificare (ripetizioni)"
                    with log_verifica.open("a", encoding="utf-8") as fh:
                        fh.write(f"{f}\n")
            except Exception as ex:
                errori += 1
                esito = f"ERRORE: {ex}"
                with log_errori.open("a", encoding="utf-8") as fh:
                    fh.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\t{f}\t{ex}\n")
            media = (time.time() - t0) / i
            resto = media * (len(lista) - i)
            stampa(f"[{i}/{len(lista)}] {time.time() - t1:4.1f}s  mancano ~{resto / 60:.0f} min  {esito}  {f.name}")
            if avanzamento:
                avanzamento({"fatte": i, "totale": len(lista), "foto": f.name, "esito": esito, "titolo": titolo,
                             "secondi_mancanti": round(resto), "errori": errori, "da_verificare": verificare,
                             "secondi_foto": round(time.time() - t1, 1)})
    except KeyboardInterrupt:
        stampa("Interrotto. Rilancia lo stesso comando per riprendere da dove eri.")
    secondi = round(time.time() - t0, 1)
    stampa(f"Fine: {fatte} schede scritte ({verificare} da verificare), {errori} errori, in {secondi} s.")
    if errori:
        stampa(f"Errori in {log_errori}")
    if verificare:
        stampa(f"Da controllare: {log_verifica}")
    stampa("Per cercarle: python -m labellula indicizza (e vettori, per la ricerca per significato).")
    return {"totale": totale, "fatte": fatte, "errori": errori, "da_verificare": verificare, "secondi": secondi}
