#!/usr/bin/env python3
"""Crea il nuovo registro identità (labellula_identita.json) a partire da people_map.json.

- people_map.json e il DB ChromaDB NON vengono modificati (il DB è aperto in sola lettura).
- Il nuovo file viene scritto accanto a people_map.json, nella radice dell'archivio.
- Se il nuovo file esiste già, lo script si ferma, a meno di --sovrascrivi
  (in quel caso ne fa prima una copia .bak).
- Con --prova non scrive niente: mostra solo cosa farebbe.

Uso (PowerShell, dalla cartella del repository):
  python -m tools.migra_registro_legacy --config config.yaml --prova
  python -m tools.migra_registro_legacy --config config.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from labellula.config import carica_config  # noqa: E402
from labellula.migrazione_legacy import leggi_percorsi_chroma, migra  # noqa: E402
from labellula.registro import NOME_FILE, carica, salva  # noqa: E402


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--prova", action="store_true", help="non scrive niente")
    ap.add_argument("--sovrascrivi", action="store_true", help="sostituisce un registro nuovo già esistente (con backup)")
    args = ap.parse_args()

    cfg = carica_config(args.config)
    radice = cfg.radice_archivio
    pm_file = radice / "people_map.json"
    db_file = (cfg.cartella_db_volti or Path(".")) / "chroma.sqlite3"
    dest = radice / NOME_FILE

    print(f"Registro legacy : {pm_file}")
    print(f"DB volti (lett.): {db_file}")
    print(f"Nuovo registro  : {dest}")
    people_map = json.loads(pm_file.read_text(encoding="utf-8"))
    reg, res = migra(people_map, leggi_percorsi_chroma(db_file), radice)

    print(f"\nAssegnazioni: {res['assegnati_migrati']} migrate su {res['assegnati_legacy']}"
          f" (non migrabili: {len(res['assegnati_non_migrati'])})")
    print(f"Volti ignorati: {res['ignorati_migrati']} migrati su {res['ignorati_legacy']}"
          f" (senza impronta nel DB: {len(res['ignorati_non_migrati'])};"
          f" segnati come ignorati ma anche assegnati a una persona, vince l'assegnazione:"
          f" {len(res['ignorati_ma_assegnati'])})")
    print("\nVolti per persona:")
    for persona, n in reg.conteggio_per_persona().items():
        print(f"  {persona:<30} {n:5d}")

    if args.prova:
        print("\n[PROVA] Nessun file scritto.")
        return 0
    if dest.exists() and not args.sovrascrivi:
        print(f"\n[FERMO] {dest.name} esiste già. Usa --sovrascrivi per sostituirlo (con backup).")
        return 1
    backup = salva(reg, dest)
    if backup:
        print(f"\nCopia di sicurezza del registro precedente: {backup}")
    # verifica: rilettura
    riletto = carica(dest)
    ok = riletto.assegnati == reg.assegnati and riletto.ignorati == reg.ignorati
    print(f"Scritto {dest} — verifica rilettura: {'OK' if ok else 'ERRORE'}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
