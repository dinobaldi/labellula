"""Registro delle identità dei volti (modulo volti, opzionale).

Sostituisce `people_map.json` del codice legacy. Differenze:
- le chiavi sono gli ID univoci di `labellula.ids` ("percorso/relativo/FOTO.JPG#faceN");
- c'è un'intestazione con versione, data e origine;
- il salvataggio è atomico (file temporaneo e poi rinomina) e, se il file esiste già,
  ne fa prima una copia "<nome>.bak-AAAAMMGG-HHMMSS".

Formato (JSON, UTF-8):
{
  "formato": "labellula-registro-identita",
  "versione": 1,
  "schema_id": "percorso_relativo#faceN",
  "aggiornato": "2026-11-23T23:30:00",
  "origine": "...",
  "assegnati": {"2022/.../DSCF1727.JPG#face1": "Nome Cognome", ...},
  "ignorati": ["2021/.../DJI_0056.JPG#face2", ...],
  "note": {...}
}
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .ids import scomponi_id_volto

FORMATO = "labellula-registro-identita"
VERSIONE = 1
NOME_FILE = "labellula_identita.json"


@dataclass
class Registro:
    assegnati: dict[str, str] = field(default_factory=dict)
    ignorati: set[str] = field(default_factory=set)
    origine: str = ""
    note: dict = field(default_factory=dict)

    def assegna(self, vid: str, persona: str) -> None:
        scomponi_id_volto(vid)  # valida il formato
        self.ignorati.discard(vid)
        self.assegnati[vid] = persona

    def ignora(self, vid: str) -> None:
        scomponi_id_volto(vid)
        self.assegnati.pop(vid, None)
        self.ignorati.add(vid)

    def conteggio_per_persona(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for p in self.assegnati.values():
            out[p] = out.get(p, 0) + 1
        return dict(sorted(out.items(), key=lambda x: (-x[1], x[0])))

    def a_dict(self) -> dict:
        return {
            "formato": FORMATO,
            "versione": VERSIONE,
            "schema_id": "percorso_relativo#faceN",
            "aggiornato": datetime.now().isoformat(timespec="seconds"),
            "origine": self.origine,
            "assegnati": dict(sorted(self.assegnati.items())),
            "ignorati": sorted(self.ignorati),
            "note": self.note,
        }


def carica(percorso: str | Path) -> Registro:
    d = json.loads(Path(percorso).read_text(encoding="utf-8"))
    if d.get("formato") != FORMATO:
        raise ValueError(f"{percorso} non è un registro Labellula (formato={d.get('formato')!r})")
    if int(d.get("versione", 0)) > VERSIONE:
        raise ValueError(f"{percorso}: versione {d['versione']} più recente di questo programma")
    return Registro(
        assegnati=dict(d.get("assegnati", {})),
        ignorati=set(d.get("ignorati", [])),
        origine=d.get("origine", ""),
        note=d.get("note", {}),
    )


def salva(reg: Registro, percorso: str | Path) -> Path | None:
    """Salva in modo atomico. Restituisce il percorso della copia di sicurezza, se fatta."""
    p = Path(percorso)
    backup = None
    if p.exists():
        backup = p.with_name(f"{p.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
        shutil.copy2(p, backup)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(reg.a_dict(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(p)
    return backup
