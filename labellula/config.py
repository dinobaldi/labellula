"""Lettura della configurazione (config.yaml) con valori predefiniti.

Uso:
    from labellula.config import carica_config
    cfg = carica_config()            # cerca config.yaml nella cartella corrente
    cfg = carica_config("altro.yaml")
    cfg.radice_archivio              # Path
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path

import yaml

PREDEFINITI = {
    "archivio": {
        "radice": None,
        "estensioni": [".jpg", ".jpeg", ".jfif", ".png", ".heic", ".heif"],
        "salta_cartelle": ["$recycle.bin", "system volume information"],
    },
    "schede": {"cartella_txt": "_txt", "cartella_volti": "_faces"},
    "modello": {
        "ollama_url": "http://localhost:11434",
        "motore": "ollama",
        "nome": "qwen3-vl:8b-instruct",
        "lato_massimo_px": 1344,
        "embedding": "bge-m3",
    },
    "descrizione": {"contesto": "", "categorie": None, "percorso_al_remoto": False, "lingua": "it"},
    "interfaccia": {"lingua": ""},
    "volti": {"attivo": False, "cartella_db": None, "dimensione_minima_px": 80},
    "dati": {"cartella": "dati"},
    "server": {"indirizzo": "127.0.0.1", "porta": 8765, "password_hash": ""},
    "servizio": {"url_acquisto": "", "url_donazioni": "https://ctrlalt.museum/ctrlalter/"},
}


def _unisci(base: dict, sopra: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (sopra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _unisci(out[k], v)
        else:
            out[k] = v
    return out


@dataclass
class Config:
    dati: dict
    cartella_base: Path
    file: Path | None = None          # il config.yaml letto (per salvarlo dall'interfaccia)

    def _percorso(self, valore) -> Path | None:
        if not valore:
            return None
        p = Path(valore)
        return p if p.is_absolute() else (self.cartella_base / p)

    @property
    def radice_archivio(self) -> Path:
        """La cartella dell'archivio. Se manca, o è un percorso Windows (C:/...) su Mac o Linux,
        si usa la cartella Immagini dell'utente."""
        import os
        import re
        valore = str(self.dati["archivio"]["radice"] or "").strip()
        if not valore or (os.name != "nt" and re.match(r"^[A-Za-z]:[\\/]", valore)):
            immagini = Path.home() / "Pictures"
            return immagini if immagini.is_dir() else Path.home()
        return self._percorso(valore)

    @property
    def cartella_db_volti(self) -> Path | None:
        return self._percorso(self.dati["volti"]["cartella_db"])

    @property
    def cartella_dati(self) -> Path:
        """Indice di ricerca e cache delle miniature (si possono sempre ricreare)."""
        return self._percorso(self.dati["dati"]["cartella"]) or (self.cartella_base / "dati")

    def __getitem__(self, chiave):
        return self.dati[chiave]


def carica_config(percorso: str | Path = "config.yaml") -> Config:
    p = Path(percorso)
    if not p.exists():
        raise FileNotFoundError(
            f"File di configurazione non trovato: {p.resolve()}\n"
            "Copia config.example.yaml come config.yaml e adatta i percorsi."
        )
    with p.open(encoding="utf-8") as f:
        utente = yaml.safe_load(f) or {}
    dati = _unisci(PREDEFINITI, utente)
    est = [e.lower() for e in dati["archivio"]["estensioni"]]
    for e in (".heic", ".heif"):          # le foto dei telefoni ci sono sempre, anche nei config.yaml più vecchi
        if e not in est:
            dati["archivio"]["estensioni"].append(e)
    return Config(dati=dati, cartella_base=p.resolve().parent, file=p.resolve())


def imposta_valore(file: Path, sezione: str, chiave: str, valore) -> bool:
    """Scrive `chiave: valore` dentro `sezione:` di config.yaml lasciando intatti commenti e ordine.
    Fa prima una copia .bak con data e ora. Restituisce True se il file è cambiato."""
    import json
    import re
    import time
    testo = file.read_text(encoding="utf-8")
    righe = testo.splitlines(keepends=True)
    nuova = f"  {chiave}: {json.dumps(valore, ensure_ascii=False)}\n"
    inizio = next((i for i, r in enumerate(righe) if re.match(rf"^{re.escape(sezione)}:\s*(#.*)?$", r)), None)
    if inizio is None:
        righe += ["\n" if righe and not righe[-1].endswith("\n\n") else "", f"{sezione}:\n", nuova]
    else:
        fine = next((i for i in range(inizio + 1, len(righe)) if re.match(r"^\S", righe[i])), len(righe))
        pos = next((i for i in range(inizio + 1, fine) if re.match(rf"^\s+{re.escape(chiave)}:", righe[i])), None)
        if pos is not None:
            if righe[pos] == nuova:
                return False
            righe[pos] = nuova
        else:
            righe.insert(inizio + 1, nuova)
    file.with_name(file.name + time.strftime(".bak-%Y%m%d-%H%M%S")).write_text(testo, encoding="utf-8")
    file.write_text("".join(righe), encoding="utf-8")
    return True
