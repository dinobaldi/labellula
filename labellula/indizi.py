"""Indizi dal percorso: cosa dicono il nome delle cartelle e il nome del file, e quanto ci si può fidare.

In molti archivi le cartelle sono la catalogazione fatta a mano dal fotografo, per esempio
`2022/2022-03-20 Castel San Giovanni - 18 compleanno Anna` o
`2024/2024-08-11 vacanza Olanda Belgio Francia/2024-08-23 Ginevra`.
Sono informazioni preziose: questo modulo le estrae e le **confronta** con EXIF e GPS,
così il modello riceve indizi già pesati ("confermato", "presunto", "in contrasto")
invece di doverli indovinare.
"""
from __future__ import annotations

import csv
import math
import re
import unicodedata
from functools import lru_cache
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

_RE_DATA_CARTELLA = re.compile(
    r"^\s*((?:19|20)\d\d)(?:[-_. ]?(0[1-9]|1[0-2])(?:[-_. ]?(0[1-9]|[12]\d|3[01]))?)?(?!\d)[\s\-_.]*")
# Nomi di file assegnati dalla fotocamera o dal telefono: non dicono niente del soggetto
_RE_NOME_GENERICO = re.compile(
    r"^(dscf?|dscn|dsc|img|imgp|mvimg|pxl|sany|dji|gopr|gp|para|pano|p|vid|photo|foto|image|scan|cimg|pict|_)?"
    r"[\s_\-]*[\d_\-\s]*(lowres|edit|hdr|pano|burst\w*|cover|\(\d+\))?[\s_\-\d]*$", re.I)
_PAROLE_VUOTE = {"con", "del", "della", "dei", "delle", "alla", "alle", "agli", "per", "tra", "fra",
                 "and", "the", "di", "da", "in", "a", "al", "e", "il", "la", "le", "lo", "gli", "un", "una"}
MAX_GIORNI_VIAGGIO = 45   # foto fino a 45 giorni dopo la data della cartella: viaggio o evento lungo
MAX_GIORNI_PRIMA = 15     # ...o fino a 15 giorni prima (la cartella prende la data di archiviazione)
MAX_KM_CONFERMA = 30      # distanza massima tra luogo della cartella e GPS per dirlo "confermato"
# Parole con l'iniziale maiuscola nelle cartelle che sono anche nomi di località da qualche parte nel mondo
PAROLE_NON_LUOGO = {"casa", "centro", "gara", "festa", "prove", "test", "museo", "mare", "lago", "monte", "porto",
                    "parco", "foto", "varie", "natale", "pasqua", "compleanno", "vacanza", "vacanze", "viaggio",
                    "gita", "giro", "evento", "corso", "concerto", "scuola", "lavoro", "ufficio", "giardino",
                    "fiori", "alba", "tramonto", "notte", "luna", "sole", "neve", "campo", "chiesa", "san", "santa",
                    "villa", "castello", "torre", "ponte", "isola", "valle", "bosco", "spiaggia", "inverno",
                    "estate", "primavera", "autunno", "auguri", "amici", "famiglia", "nonni", "zio", "zia"}
# reverse_geocoder usa nomi inglesi o locali: nomi italiani di paesi e città, per il confronto con le cartelle
PAESI = {"IT": "Italia", "CH": "Svizzera", "FR": "Francia", "DE": "Germania", "NL": "Olanda Paesi Bassi",
         "BE": "Belgio", "AT": "Austria", "ES": "Spagna", "PT": "Portogallo", "GB": "Inghilterra Regno Unito Scozia",
         "IE": "Irlanda", "PL": "Polonia", "CZ": "Repubblica Ceca", "HU": "Ungheria", "HR": "Croazia",
         "SI": "Slovenia", "GR": "Grecia", "MV": "Maldive", "US": "Stati Uniti America", "SM": "San Marino",
         "VA": "Vaticano", "MC": "Monaco", "LU": "Lussemburgo", "DK": "Danimarca", "SE": "Svezia",
         "NO": "Norvegia", "FI": "Finlandia", "MT": "Malta", "TR": "Turchia", "EG": "Egitto", "TN": "Tunisia"}
ESONIMI = {"geneva": "ginevra", "turin": "torino", "milan": "milano", "florence": "firenze", "venice": "venezia",
           "rome": "roma", "naples": "napoli", "genoa": "genova", "padua": "padova", "mantua": "mantova",
           "lucerne": "lucerna", "zurich": "zurigo", "basel": "basilea", "bern": "berna", "munich": "monaco di baviera",
           "cologne": "colonia", "paris": "parigi", "nice": "nizza", "marseille": "marsiglia", "lyon": "lione",
           "brussels": "bruxelles", "london": "londra", "warsaw": "varsavia", "prague": "praga", "vienna": "vienna",
           "lisbon": "lisbona", "athens": "atene", "seville": "siviglia", "barcelona": "barcellona",
           "piedmont": "piemonte", "lombardy": "lombardia", "tuscany": "toscana", "liguria": "liguria",
           "sicily": "sicilia", "sardinia": "sardegna", "ticino": "ticino", "aosta": "aosta",
           "geneve": "ginevra", "luzern": "lucerna", "antwerpen": "anversa", "gent": "gand",
           "strasbourg": "strasburgo", "brugge": "bruges", "munchen": "monaco di baviera"}
# Nomi propri comuni che esistono anche come località (Anna in Spagna, Marco in Francia...): da soli non sono luoghi
NOMI_PROPRI = set("""
alessandro alessandra alberto alice andrea angela anna antonio arianna aurora beatrice benedetta bruno camilla carla
carlo carlos caterina chiara claudia claudio cristina daniele daniela davide diego elena elisa emma enrico federica
federico filippo francesca francesco gabriele giacomo gianni giorgia giorgio giovanna giovanni giulia giuseppe giada
greta irene laura lorenzo luca lucia luigi luisa marco margherita maria mario marta martina massimo matilde matteo
mattia michele monica nicola nicolo noemi paola paolo pietro riccardo roberta roberto rosa samuele sara silvia simone
sofia stefano tommaso valentina valerio vittoria
""".split())
# Grafie diverse dello stesso luogo, usate nelle cartelle ma non nell'elenco delle località
ALIAS = {"albissola": "albisola marina", "albissola marina": "albisola marina",
         "albissola superiore": "albisola superiore"}   # una cartella "2024-08-11 vacanza ..." può contenere foto delle settimane dopo


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


def _parole(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", _norm(s)) if w not in _PAROLE_VUOTE}


@dataclass
class Indizi:
    cartelle: list[str] = field(default_factory=list)   # descrizioni testuali delle cartelle, dalla più esterna
    data_cartella: date | None = None
    precisione_data: str = ""                            # "giorno", "mese", "anno"
    nome_file: str = ""                                  # parte descrittiva del nome del file ("" se generico)
    verifica_data: str = ""
    verifica_luogo: str = ""
    luoghi: list[str] = field(default_factory=list)       # luoghi delle cartelle trovati nell'elenco delle località

    @property
    def vuoti(self) -> bool:
        return not (self.cartelle or self.data_cartella or self.nome_file)

    def data_testo(self) -> str:
        d = self.data_cartella
        if not d:
            return ""
        return {"giorno": d.strftime("%d/%m/%Y"), "mese": d.strftime("%m/%Y")}.get(self.precisione_data, str(d.year))

    def righe_prompt(self) -> list[str]:
        """Le righe da dare al modello, già con il livello di affidabilità."""
        r = []
        if self.cartelle:
            r.append("- Cartelle (scritte a mano dal fotografo, dalla più generale alla più specifica): "
                     + " > ".join(f'"{c}"' for c in self.cartelle))
        if self.data_cartella:
            r.append(f"- Data nel nome della cartella: {self.data_testo()} ({self.verifica_data or 'non verificabile, presunta valida'})")
        if self.luoghi:
            r.append(f"- Luogo indicato dalle cartelle: {'; '.join(self.luoghi)} ("
                     + (self.verifica_luogo or "riconosciuto nell'elenco delle località, senza GPS: presunto valido, "
                        "usalo come luogo") + ")")
        elif self.cartelle:
            r.append("- Luogo ed evento dalle cartelle: "
                     + (self.verifica_luogo or "non verificabili, presunti validi. Se una parola delle cartelle è un "
                        "luogo (città, località, nome di un locale, di un'azienda o di una manifestazione) "
                        "usala come luogo probabile"))
        if self.nome_file:
            r.append(f'- Nome del file, descrittivo: "{self.nome_file}" (presunto valido)')
        return r

    def riga_piede(self) -> str:
        parti = []
        if self.data_cartella:
            parti.append(f"data {self.data_testo()} ({self.verifica_data or 'presunta'})")
        if self.luoghi:
            parti.append(f"luogo {'; '.join(self.luoghi)} ({self.verifica_luogo or 'presunto'})")
        elif self.cartelle and self.verifica_luogo:
            parti.append(f"luogo/evento {self.verifica_luogo}")
        return "; ".join(parti)


def scomponi_cartella(nome: str) -> tuple[date | None, str, str]:
    """'2022-03-20 Castel San Giovanni - 18 compleanno Anna' -> (2022-03-20, 'giorno', 'Castel San Giovanni - 18 compleanno Anna')."""
    m = _RE_DATA_CARTELLA.match(nome)
    if not m:
        return None, "", _pulisci(nome)
    a, me, g = m.group(1), m.group(2), m.group(3)
    try:
        d = date(int(a), int(me or 1), int(g or 1))
    except ValueError:
        return None, "", _pulisci(nome)
    return d, ("giorno" if g else "mese" if me else "anno"), _pulisci(nome[m.end():])


def _pulisci(s: str) -> str:
    s = s.strip(" -_.")
    if "-" in s and " " not in s:          # "San-Martino-Campo-test"
        s = s.replace("-", " ")
    return re.sub(r"[_\s]+", " ", s).strip()


def descrizione_nome_file(nome: str) -> str:
    stem = Path(nome).stem
    if _RE_NOME_GENERICO.match(stem):
        return ""
    _, _, testo = scomponi_cartella(stem)
    testo = re.sub(r"\b(dscf?|dscn|img|imgp|pxl|dji)[\s_\-]*\d+\b", "", testo, flags=re.I)
    testo = re.sub(r"\b\d+\b", "", testo)
    testo = _pulisci(testo)
    return testo if len(re.sub(r"[^A-Za-zÀ-ÿ]", "", testo)) >= 3 else ""


def raccogli(foto: Path, radice: Path | None, data_exif: datetime | None, gps: dict | None) -> Indizi:
    """`gps` è il risultato di reverse_geocoder ({'name','admin1','admin2','cc'}) o None."""
    try:
        parti = foto.parent.relative_to(radice).parts if radice else foto.parent.parts[-3:]
    except ValueError:
        parti = foto.parent.parts[-3:]
    ind = Indizi()
    for p in parti:
        if p.startswith("_"):
            continue
        d, prec, testo = scomponi_cartella(p)
        if d and _ORDINE[prec] >= _ORDINE[ind.precisione_data]:   # vince la più precisa, a pari precisione la più interna
            ind.data_cartella, ind.precisione_data = d, prec
        if testo:
            ind.cartelle.append(testo)
    ind.nome_file = descrizione_nome_file(foto.name)
    ind.verifica_data = _verifica_data(ind, data_exif)
    trovati = cerca_luoghi(" ".join(ind.cartelle), gps)
    ind.luoghi = [_nome_luogo(x) for x in trovati]
    ind.verifica_luogo = _verifica_luogo(ind, gps, trovati)
    return ind


_ORDINE = {"": 0, "anno": 1, "mese": 2, "giorno": 3}


def _verifica_data(ind: Indizi, exif: datetime | None) -> str:
    if not ind.data_cartella or not exif:
        return ""
    e = exif.date()
    if ind.precisione_data == "anno":
        return "confermata dall'EXIF" if e.year == ind.data_cartella.year else f"in contrasto con l'EXIF ({e.year})"
    if ind.precisione_data == "mese":
        ok = (e.year, e.month) == (ind.data_cartella.year, ind.data_cartella.month)
        return "confermata dall'EXIF" if ok else f"in contrasto con l'EXIF ({e:%m/%Y})"
    giorni = (e - ind.data_cartella).days
    if giorni == 0:
        return "confermata dall'EXIF"
    if 0 < giorni <= MAX_GIORNI_VIAGGIO:
        return f"coerente: l'EXIF è di {giorni} giorni dopo, probabilmente un viaggio o un evento di più giorni"
    if -MAX_GIORNI_PRIMA <= giorni < 0:
        return f"coerente: l'EXIF è di {-giorni} giorni prima, la cartella ha probabilmente la data di archiviazione"
    return (f"in contrasto con l'EXIF ({e:%d/%m/%Y}): l'orologio della fotocamera potrebbe essere sbagliato "
            "o la foto è stata archiviata in un'altra occasione")


def _verifica_luogo(ind: Indizi, gps: dict | None, trovati=()) -> str:
    if not gps or not ind.cartelle:
        return ""
    for x in trovati:
        if _km(x, gps) <= MAX_KM_CONFERMA:
            return f"confermato dal GPS, a {_km(x, gps):.0f} km"
    luoghi = _parole(" ".join(str(gps.get(k, "")) for k in ("name", "admin1", "admin2")))
    luoghi |= {p for w in list(luoghi) if w in ESONIMI for p in _parole(ESONIMI[w])}
    paese = _parole(PAESI.get(gps.get("cc", ""), ""))
    cartella = _parole(" ".join(ind.cartelle))
    nome = ESONIMI.get(_norm(str(gps.get("name", ""))), "").capitalize() or gps.get("name")
    vicino = f"{nome}, {gps.get('admin2') or gps.get('admin1')}, {PAESI.get(gps.get('cc', ''), gps.get('cc', '')).split(' ')[0]}"
    if luoghi & cartella:
        return f"confermati dal GPS ({vicino})"
    if paese & cartella:
        return f"paese confermato dal GPS ({vicino}); la località precisa della cartella non è verificabile"
    return (f"il GPS indica {vicino}: il nome della cartella potrebbe indicare l'evento più che il luogo, "
            "oppure un luogo vicino")


# ------------------------------------------------- elenco delle località (offline)
_PREFERENZA_PAESI = ["IT", "CH", "SM", "VA", "FR", "AT", "DE", "SI", "ES", "PT", "BE", "NL", "LU", "GB", "IE",
                     "HR", "GR", "CZ", "PL", "HU", "DK", "SE", "NO", "FI", "MT"]
_ESONIMI_INVERSI: dict[str, list[str]] = {}
for _en, _it in ESONIMI.items():
    _ESONIMI_INVERSI.setdefault(_it, []).append(_en)


@lru_cache(maxsize=1)
def _localita() -> dict[str, list[dict]]:
    """Nome normalizzato -> località (rg_cities1000.csv di reverse_geocoder: ~145.000 località con più di 1000 abitanti)."""
    try:
        import reverse_geocoder
        f = Path(reverse_geocoder.__file__).with_name("rg_cities1000.csv")
        out: dict[str, list[dict]] = {}
        with f.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                out.setdefault(_norm(r["name"]), []).append(r)
        return out
    except Exception:
        return {}


def _km(a: dict, b: dict) -> float:
    try:
        la1, lo1, la2, lo2 = map(math.radians, map(float, (a["lat"], a["lon"], b["lat"], b["lon"])))
    except (KeyError, TypeError, ValueError):
        return float("inf")
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _nome_luogo(r: dict) -> str:
    nome = ESONIMI.get(_norm(r["name"]), "").capitalize() or r["name"]
    regione = ESONIMI.get(_norm(r["admin1"]), "").capitalize() or r["admin1"]
    paese = PAESI.get(r["cc"], r["cc"]).split(" ")[0]
    prov = r.get("admin2", "") if r["cc"] == "IT" else ""
    return ", ".join(x for x in (nome, prov, regione, paese) if x)


def cerca_luoghi(testo: str, gps: dict | None = None) -> list[dict]:
    """Località scritte con l'iniziale maiuscola, anche di 2-3 parole ("Castel San Giovanni")."""
    loc = _localita()
    if not loc or not testo:
        return []
    parole = re.findall(r"[A-Za-zÀ-ÿ']+", testo)
    ordine = {cc: k for k, cc in enumerate(_PREFERENZA_PAESI)}
    trovati, ambigui, usate = [], [], set()
    for n in (3, 2, 1):
        for i in range(len(parole) - n + 1):
            if any(k in usate for k in range(i, i + n)):
                continue
            pezzo = parole[i:i + n]
            if not pezzo[0][:1].isupper():
                continue
            if n == 1 and (len(pezzo[0]) < 4 or _norm(pezzo[0]) in PAROLE_NON_LUOGO or _norm(pezzo[0]) in NOMI_PROPRI):
                continue
            chiave = ALIAS.get(_norm(" ".join(pezzo)), _norm(" ".join(pezzo)))
            cand = [r for k in [chiave, *_ESONIMI_INVERSI.get(chiave, [])] for r in loc.get(k, [])]
            if not cand:
                continue
            usate.update(range(i, i + n))
            if gps and gps.get("lat"):
                trovati.append(min(cand, key=lambda r: _km(r, gps)))
                continue
            migliore = min(ordine.get(r["cc"], 99) for r in cand)
            if migliore == 99:
                continue            # esiste solo lontano dall'Europa: probabile falso positivo (nome di persona)
            cand = [r for r in cand if ordine.get(r["cc"], 99) == migliore]
            (trovati if len(cand) == 1 else ambigui).append(cand if len(cand) > 1 else cand[0])
    # nomi ambigui (es. 4 "San Martino" in Italia): si tiene quello vicino a un altro luogo certo della cartella
    for cand in ambigui:
        vicini = [(min(_km(r, x) for x in trovati), r) for r in cand] if trovati else []
        if vicini and min(vicini, key=lambda v: v[0])[0] <= 60:
            trovati.append(min(vicini, key=lambda v: v[0])[1])
    return trovati
