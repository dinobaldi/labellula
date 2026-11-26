#!/usr/bin/env python3
"""Analisi in SOLA LETTURA del modulo volti legacy, in vista della migrazione agli ID univoci.

Legge:
  - i file <cartella_volti>/*.json accanto alle foto (rilevamenti YuNet);
  - il database ChromaDB legacy (chroma.sqlite3, aperto in sola lettura, senza la libreria chromadb);
  - people_map.json nella radice dell'archivio (vector_map e ignored_map).

Scrive nella cartella --out (che NON deve stare dentro il repository: contiene percorsi e nomi):
  - mappa_id.csv        : per ogni volto nel DB, vecchio ID -> nuovo ID univoco, persona assegnata o "ignorato"
  - volti_oscurati.csv  : volti validi mai analizzati perché un'altra foto aveva lo stesso vecchio ID
  - riepilogo.txt       : i conteggi

Non modifica nulla né su H: né nel database.

Uso (PowerShell, dalla cartella del repository):
  python -m tools.analizza_volti_legacy --config config.yaml --out "..\\report_volti"
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from labellula.config import carica_config  # noqa: E402
from labellula.ids import id_legacy, id_volto  # noqa: E402


def leggi_chroma_sola_lettura(db_file: Path) -> dict[str, str]:
    """vecchio ID -> percorso assoluto della foto, dal chroma.sqlite3 legacy."""
    uri = f"file:{db_file.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        righe = con.execute(
            "select e.embedding_id, m.string_value from embeddings e "
            "join embedding_metadata m on m.id = e.id where m.key = 'file_path'"
        ).fetchall()
    finally:
        con.close()
    return {vid: path for vid, path in righe}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--out", required=True, help="cartella dei risultati (fuori dal repository)")
    args = ap.parse_args()

    cfg = carica_config(args.config)
    radice = cfg.radice_archivio
    cart_volti = cfg["schede"]["cartella_volti"]
    min_px = int(cfg["volti"]["dimensione_minima_px"])
    db_file = (cfg.cartella_db_volti or Path(".")) / "chroma.sqlite3"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Lettura DB volti (sola lettura): {db_file}")
    nel_db = leggi_chroma_sola_lettura(db_file)
    print(f"  {len(nel_db)} impronte nel DB")

    pm = json.loads((radice / "people_map.json").read_text(encoding="utf-8"))
    assegnati: dict[str, str] = pm.get("vector_map", {})
    ignorati = pm.get("ignored_map", {})
    ignorati = set(ignorati if isinstance(ignorati, (list, set)) else ignorati.keys())

    conteggi = collections.Counter()
    oscurati = []
    mappa = []
    print(f"Scansione dei file {cart_volti}\\*.json in {radice} ...")
    n_json = 0
    for dirpath, dirs, files in os.walk(radice):
        if Path(dirpath).name != cart_volti:
            continue
        for f in sorted(files):
            if not f.endswith(".json"):
                continue
            n_json += 1
            if n_json % 2000 == 0:
                print(f"  {n_json} file letti...", flush=True)
            d = json.loads((Path(dirpath) / f).read_text(encoding="utf-8"))
            foto = Path(dirpath).parent / d["file"]
            for volto in d.get("faces", []):
                b = volto.get("bbox", [0, 0, 0, 0])
                if b[2] < min_px or b[3] < min_px:
                    conteggi["volti piccoli (sotto soglia)"] += 1
                    continue
                if len(volto.get("landmarks") or {}) < 5:
                    conteggi["volti senza 5 punti di riferimento"] += 1
                    continue
                vecchio = id_legacy(foto, volto["face_id"])
                nuovo = id_volto(radice, foto, volto["face_id"])
                path_db = nel_db.get(vecchio)
                if path_db is None:
                    conteggi["volti validi scartati (filtro pelle o errore)"] += 1
                elif os.path.normcase(path_db) == os.path.normcase(str(foto)):
                    conteggi["volti nel DB, foto corretta"] += 1
                    stato = (assegnati.get(vecchio) or ("ignorato" if vecchio in ignorati else ""))
                    mappa.append((vecchio, nuovo, stato))
                else:
                    conteggi["volti OSCURATI (ID già usato da un'altra foto)"] += 1
                    oscurati.append((nuovo, vecchio, id_volto(radice, path_db, volto["face_id"])))

    with (out / "mappa_id.csv").open("w", newline="", encoding="utf-8-sig") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(["id_vecchio", "id_nuovo", "persona_o_stato"])
        w.writerows(mappa)
    with (out / "volti_oscurati.csv").open("w", newline="", encoding="utf-8-sig") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(["volto_mai_analizzato", "id_vecchio_conteso", "foto_che_ha_preso_l_id"])
        w.writerows(oscurati)

    n_ass = sum(1 for _, _, s in mappa if s and s != "ignorato")
    n_ign = sum(1 for _, _, s in mappa if s == "ignorato")
    orfani = [k for k in assegnati if k not in nel_db]
    righe = [
        f"File {cart_volti} letti: {n_json}",
        *(f"{k}: {v}" for k, v in conteggi.most_common()),
        f"Foto con almeno un volto oscurato: {len({o[0].rsplit('#', 1)[0] for o in oscurati})}",
        f"Assegnazioni people_map: {len(assegnati)} (migrabili: {n_ass}; senza impronta nel DB: {len(orfani)})",
        f"Volti ignorati migrabili: {n_ign} su {len(ignorati)}",
    ]
    (out / "riepilogo.txt").write_text("\n".join(righe) + "\n", encoding="utf-8")
    print("\n".join(righe))
    print(f"\nRisultati in: {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
