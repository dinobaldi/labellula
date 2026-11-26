"""Ricerca per significato: vettori (embedding) delle schede calcolati in locale con Ollama.

Ogni scheda diventa un vettore di numeri che ne rappresenta il "senso". Anche la frase
cercata diventa un vettore, e i risultati sono le schede con il senso più vicino
(similarità del coseno). Così "automobile rossa" trova anche "spider color fiamma".

File prodotti nella cartella dati (si possono sempre ricalcolare):
  semantico.npy        matrice N x D (float32, vettori già normalizzati)
  semantico.json       modello usato, elenco id_foto e impronta del testo di ogni scheda

Il calcolo è incrementale: rilanciando, si ricalcolano solo le schede nuove o cambiate.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

import numpy as np
import requests

MODELLO_PREDEFINITO = "bge-m3"
MAX_CARATTERI = 2000


def testo_da_indicizzare(r: dict) -> str:
    parti = [r.get("titolo"), r.get("descrizione"), r.get("testi"), r.get("luogo"), r.get("occasione"), r.get("parole_chiave"),
             r.get("categoria"), (r.get("cartella") or "").replace("/", " ")]
    return "\n".join(p for p in parti if p)[:MAX_CARATTERI]


def _impronta(testo: str) -> str:
    return hashlib.sha1(testo.encode("utf-8")).hexdigest()[:16]


class ClientEmbedding:
    def __init__(self, url: str = "http://localhost:11434", modello: str = MODELLO_PREDEFINITO):
        self.url, self.modello = url.rstrip("/"), modello

    def vettori(self, testi: list[str]) -> np.ndarray:
        r = requests.post(f"{self.url}/api/embed", json={"model": self.modello, "input": testi,
                                                        "keep_alive": "10m"}, timeout=600)
        r.raise_for_status()
        m = np.asarray(r.json()["embeddings"], dtype=np.float32)
        m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-12
        return m


def costruisci(file_indice: Path, cartella_dati: Path, client: ClientEmbedding,
               lotto: int = 32, avanzamento=print) -> dict:
    t0 = time.time()
    con = sqlite3.connect(f"file:{file_indice.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    righe = [dict(r) for r in con.execute(
        "SELECT id_foto, cartella, categoria, titolo, descrizione, testi, luogo, occasione, parole_chiave FROM foto ORDER BY id")]
    con.close()

    f_npy, f_json = cartella_dati / "semantico.npy", cartella_dati / "semantico.json"
    vecchi: dict[str, tuple[str, np.ndarray]] = {}
    if f_npy.exists() and f_json.exists():
        meta = json.loads(f_json.read_text(encoding="utf-8"))
        if meta.get("modello") == client.modello:
            mat = np.load(f_npy)
            vecchi = {i: (h, mat[k]) for k, (i, h) in enumerate(zip(meta["id_foto"], meta["impronte"]))}

    testi = [testo_da_indicizzare(r) for r in righe]
    impronte = [_impronta(t) for t in testi]
    da_fare = [k for k, r in enumerate(righe)
               if r["id_foto"] not in vecchi or vecchi[r["id_foto"]][0] != impronte[k]]
    avanzamento(f"Schede: {len(righe)}, da calcolare: {len(da_fare)} (modello {client.modello})")

    nuovi: dict[int, np.ndarray] = {}
    for n in range(0, len(da_fare), lotto):
        blocco = da_fare[n:n + lotto]
        for k, v in zip(blocco, client.vettori([testi[k] for k in blocco])):
            nuovi[k] = v
        fatti = min(n + lotto, len(da_fare))
        if fatti % (lotto * 25) < lotto or fatti == len(da_fare):
            trascorsi = time.time() - t0
            eta = trascorsi / fatti * (len(da_fare) - fatti)
            avanzamento(f"  {fatti}/{len(da_fare)}  ({trascorsi/60:.1f} min, mancano ~{eta/60:.1f} min)")

    if not righe:
        raise RuntimeError("L'indice non contiene schede: lancia prima 'indicizza'.")
    dim = (next(iter(nuovi.values())) if nuovi else next(iter(vecchi.values()))[1]).shape[0]
    mat = np.zeros((len(righe), dim), dtype=np.float32)
    for k, r in enumerate(righe):
        mat[k] = nuovi[k] if k in nuovi else vecchi[r["id_foto"]][1]

    cartella_dati.mkdir(parents=True, exist_ok=True)
    tmp_npy = cartella_dati / "semantico.tmp.npy"
    np.save(tmp_npy, mat)
    tmp_json = f_json.with_name("semantico.tmp.json")
    tmp_json.write_text(json.dumps({"modello": client.modello, "creato": time.strftime("%Y-%m-%d %H:%M:%S"),
                                    "id_foto": [r["id_foto"] for r in righe], "impronte": impronte},
                                   ensure_ascii=False), encoding="utf-8")
    tmp_npy.replace(f_npy)
    tmp_json.replace(f_json)
    return {"schede": len(righe), "calcolate": len(da_fare), "secondi": round(time.time() - t0, 1)}


class IndiceSemantico:
    def __init__(self, cartella_dati: Path, client: ClientEmbedding):
        f_npy, f_json = cartella_dati / "semantico.npy", cartella_dati / "semantico.json"
        meta = json.loads(f_json.read_text(encoding="utf-8"))
        if meta["modello"] != client.modello:
            raise ValueError(f"I vettori sono stati calcolati con {meta['modello']}, non con {client.modello}")
        self.matrice = np.load(f_npy)
        self.ids = meta["id_foto"]
        self.client = client
        self.creato = meta.get("creato", "")
        self._pos = {i: k for k, i in enumerate(self.ids)}

    def vicini(self, fid: str, limite: int = 60) -> list[str]:
        """Le schede più simili a quella di `fid`, senza chiamare il modello (usa il vettore già calcolato)."""
        k = self._pos.get(fid)
        if k is None:
            return []
        punteggi = self.matrice @ self.matrice[k]
        n = min(limite, len(punteggi))
        migliori = np.argpartition(-punteggi, n - 1)[:n]
        return [self.ids[i] for i in migliori[np.argsort(-punteggi[migliori])]]

    def classifica(self, testo: str, limite: int = 500, soglia: float = 0.0,
                   distacco: float | None = None) -> list[tuple[str, float]]:
        """Le schede più vicine al testo. `distacco`: tiene solo quelle entro questa distanza dalla migliore."""
        q = self.client.vettori([testo])[0]
        punteggi = self.matrice @ q
        k = min(limite, len(punteggi))
        migliori = np.argpartition(-punteggi, k - 1)[:k]
        migliori = migliori[np.argsort(-punteggi[migliori])]
        if distacco is not None and len(migliori):
            soglia = max(soglia, float(punteggi[migliori[0]]) - distacco)
        return [(self.ids[i], float(punteggi[i])) for i in migliori if punteggi[i] >= soglia]
