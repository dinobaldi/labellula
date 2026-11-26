"""Lettura delle schede descrittive .txt prodotte dal modulo di descrizione.

Formato (prompt v3/v4; il v5 aggiunge TITOLO, OCCASIONE, ASPETTI FOTOGRAFICI e DUBBI):

    DESCRIZIONE: ...
    TESTI VISIBILI: ...
    LUOGO E PERIODO: ...
    CATEGORIA: ...
    PERSONE: ...
    PAROLE CHIAVE: a, b, c

    ---
    File: DSCF1727.JPG
    Cartella: ...
    Data: 19/03/2022 12:05 (da EXIF)
    ...

Le sezioni possono andare a capo su più righe. Eventuali blocchi aggiunti dal codice
legacy dopo il piè di pagina ("NUMERO PERSONE RILEVATE", "RICONOSCIMENTO BIOMETRICO")
vengono ignorati: le identità si leggono dal registro, non dalle schede.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

SEZIONI = {
    "TITOLO": "titolo",
    "DESCRIZIONE": "descrizione",
    "TESTI VISIBILI": "testi",
    "LUOGO E PERIODO": "luogo",
    "CATEGORIA": "categoria",
    "OCCASIONE": "occasione",
    "PERSONE": "persone",
    "ASPETTI FOTOGRAFICI": "fotografia",
    "PAROLE CHIAVE": "parole_chiave",
    "DUBBI": "dubbi",
    # schede in inglese, francese, tedesco e spagnolo: intestazioni in inglese
    "TITLE": "titolo",
    "DESCRIPTION": "descrizione",
    "VISIBLE TEXT": "testi",
    "PLACE AND DATE": "luogo",
    "OCCASION": "occasione",
    "CATEGORY": "categoria",
    "PEOPLE": "persone",
    "PHOTOGRAPHIC ASPECTS": "fotografia",
    "KEYWORDS": "parole_chiave",
    "DOUBTS": "dubbi",
}
_RE_SEZIONE = re.compile(r"^\s*(" + "|".join(SEZIONI) + r")\s*:\s*(.*)$", re.I)
_RE_PIEDE = re.compile(r"^([A-Za-zÀ-ÿ ()]+):\s*(.*)$")
_RE_DATA = re.compile(r"(\d{1,2})/(\d{1,2})/((?:19|20)\d\d)")
_RE_ANNO = re.compile(r"(?<!\d)((?:19|20)\d\d)(?!\d)")
_BLOCCHI_LEGACY = ("NUMERO PERSONE RILEVATE", "RICONOSCIMENTO BIOMETRICO", "NUMBER OF PERSONS", "BIOMETRIC IDENTITY")


@dataclass
class Scheda:
    titolo: str = ""          # dal prompt v5 in poi
    descrizione: str = ""
    testi: str = ""
    luogo: str = ""
    categoria: str = ""
    persone: str = ""
    parole_chiave: str = ""
    occasione: str = ""       # v5
    fotografia: str = ""      # v5: aspetti fotografici
    dubbi: str = ""           # v5
    piede: dict = field(default_factory=dict)
    avviso: bool = False

    @property
    def data_iso(self) -> str:
        """'2022-03-19' se la data è nota, altrimenti ''."""
        m = _RE_DATA.search(self.piede.get("Data", ""))
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else ""

    def anno(self, cartella_relativa: str = "") -> int | None:
        if self.data_iso:
            return int(self.data_iso[:4])
        m = _RE_ANNO.search(cartella_relativa)
        return int(m.group(1)) if m else None

    @property
    def modello(self) -> str:
        return self.piede.get("Generato con", "")


def leggi_testo(testo: str) -> Scheda:
    s = Scheda()
    corpo, sep, piede = testo.partition("\n---\n")
    if not sep:
        corpo, piede = testo, ""
    s.avviso = corpo.lstrip().startswith("[ATTENZIONE")

    corrente = None
    valori: dict[str, list[str]] = {}
    for riga in corpo.splitlines():
        m = _RE_SEZIONE.match(riga)
        if m:
            corrente = SEZIONI[m.group(1).upper()]
            valori[corrente] = [m.group(2).strip()]
        elif corrente and riga.strip():
            valori[corrente].append(riga.strip())
    for campo, righe in valori.items():
        setattr(s, campo, " ".join(x for x in righe if x).strip())
    s.categoria = s.categoria.strip(" .,;").lower()

    for riga in piede.splitlines():
        if riga.strip().upper().startswith(_BLOCCHI_LEGACY):
            break
        m = _RE_PIEDE.match(riga.strip())
        if m:
            s.piede[m.group(1).strip()] = m.group(2).strip()
    return s


def leggi_file(percorso: str | Path) -> Scheda:
    return leggi_testo(Path(percorso).read_text(encoding="utf-8", errors="replace"))
