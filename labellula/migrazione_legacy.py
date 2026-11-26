"""Conversione del registro legacy (people_map.json) nel nuovo registro con ID univoci.

Il vecchio ID "DSCF1727_face1" non dice in quale cartella sta la foto, ma il DB
ChromaDB legacy conserva, per ogni vecchio ID, il percorso completo della foto
che lo ha "preso" (una sola, perché le altre venivano saltate). Quindi la
conversione è esatta: vecchio ID -> percorso nel DB -> nuovo ID.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from .ids import id_volto
from .registro import Registro


def leggi_percorsi_chroma(db_file: str | Path) -> dict[str, str]:
    """vecchio ID -> percorso assoluto della foto, leggendo chroma.sqlite3 in SOLA LETTURA."""
    uri = f"file:{Path(db_file).as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        righe = con.execute(
            "select e.embedding_id, m.string_value from embeddings e "
            "join embedding_metadata m on m.id = e.id where m.key = 'file_path'"
        ).fetchall()
    finally:
        con.close()
    return dict(righe)


_cache_cartelle: dict[str, dict[str, str]] = {}


def percorso_reale(p: str | Path) -> str:
    """Corregge maiuscole/minuscole del percorso con quelle effettive sul disco.

    Su Windows "DSCN1203.jpg" e "DSCN1203.JPG" sono lo stesso file, ma negli ID devono
    coincidere carattere per carattere. Il DB legacy a volte ha salvato la grafia sbagliata.
    Se il file non esiste, restituisce il percorso invariato.
    """
    p = Path(p)
    if not p.exists():
        return str(p)
    parti = [p.anchor]
    corrente = Path(p.anchor)
    for nome in p.parts[1:]:
        chiave = str(corrente)
        if chiave not in _cache_cartelle:
            try:
                _cache_cartelle[chiave] = {n.lower(): n for n in os.listdir(corrente)}
            except OSError:
                _cache_cartelle[chiave] = {}
        nome = _cache_cartelle[chiave].get(nome.lower(), nome)
        corrente = corrente / nome
        parti.append(nome)
    return str(Path(*parti))


def indice_da_id_legacy(vecchio: str) -> int:
    stem, sep, n = vecchio.rpartition("_face")
    if not sep or not n.isdigit():
        raise ValueError(f"ID legacy non valido: {vecchio!r}")
    return int(n)


def migra(people_map: dict, percorsi_db: dict[str, str], radice: str | Path) -> tuple[Registro, dict]:
    """Restituisce il nuovo registro e un resoconto con ciò che non è stato possibile convertire."""
    assegnati = people_map.get("vector_map", {}) or {}
    ign = people_map.get("ignored_map", {}) or {}
    ignorati = list(ign if isinstance(ign, list) else ign.keys())

    reg = Registro(origine="migrazione da people_map.json (ID legacy nome_file_faceN) tramite chroma.sqlite3")
    non_assegnati, non_ignorati, ignorati_e_assegnati = [], [], []

    for vecchio, persona in assegnati.items():
        p = percorsi_db.get(vecchio)
        if p is None:
            non_assegnati.append((vecchio, persona))
            continue
        reg.assegna(id_volto(radice, percorso_reale(p), indice_da_id_legacy(vecchio)), persona)

    for vecchio in ignorati:
        p = percorsi_db.get(vecchio)
        if p is None:
            non_ignorati.append(vecchio)
            continue
        nuovo = id_volto(radice, percorso_reale(p), indice_da_id_legacy(vecchio))
        if nuovo in reg.assegnati:  # un'assegnazione vince su un vecchio "ignora"
            ignorati_e_assegnati.append(vecchio)
        else:
            reg.ignora(nuovo)

    resoconto = {
        "assegnati_legacy": len(assegnati),
        "assegnati_migrati": len(reg.assegnati),
        "assegnati_non_migrati": non_assegnati,
        "ignorati_legacy": len(ignorati),
        "ignorati_migrati": len(reg.ignorati),
        "ignorati_non_migrati": non_ignorati,
        "ignorati_ma_assegnati": ignorati_e_assegnati,
    }
    reg.note = {
        "ignorati_legacy_senza_impronta_nel_db": non_ignorati,
        "assegnati_legacy_senza_impronta_nel_db": [v for v, _ in non_assegnati],
        "ignorati_legacy_poi_assegnati": ignorati_e_assegnati,
    }
    return reg, resoconto
