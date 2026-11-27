"""Indice di ricerca locale (SQLite con FTS5) costruito dalle schede .txt.

L'indice è un solo file (`indice.sqlite3`) nella cartella dati di Labellula, e si
può sempre ricostruire da zero: la fonte di verità restano le schede accanto alle foto.

Ricerca:
- parole libere su descrizione, testi letti, luogo, parole chiave, nome cartella e
  (se il modulo volti è attivo) persone riconosciute;
- senza distinzione di accenti e maiuscole ("citta" trova "Città");
- ogni parola vale anche come inizio di parola ("commod" trova "Commodore");
- filtri per categoria, intervallo di anni, persona.
"""
from __future__ import annotations

import os
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from .ids import id_foto
from .schede import leggi_file

SCHEMA = """
CREATE TABLE foto (
    id INTEGER PRIMARY KEY,
    id_foto TEXT UNIQUE NOT NULL,
    cartella TEXT, nome TEXT, anno INTEGER, data TEXT,
    categoria TEXT, descrizione TEXT, testi TEXT, luogo TEXT,
    persone_testo TEXT, parole_chiave TEXT, persone_riconosciute TEXT,
    modello TEXT, avviso INTEGER,
    titolo TEXT, occasione TEXT, fotografia TEXT, dubbi TEXT
);
CREATE INDEX foto_anno ON foto(anno);
CREATE INDEX foto_categoria ON foto(categoria);
CREATE VIRTUAL TABLE fts USING fts5(
    descrizione, testi, luogo, parole_chiave, cartella, persone_riconosciute,
    titolo, occasione, fotografia,
    content='foto', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE TABLE info (chiave TEXT PRIMARY KEY, valore TEXT);
"""
PESI_BM25 = "3.0, 2.0, 1.5, 2.0, 1.0, 2.0, 3.0, 2.0, 1.0"
SOGLIA_SIGNIFICATO = 0.45  # similarità minima (bge-m3) per tenere un risultato "per significato"
DISTACCO_SIGNIFICATO = 0.10  # ...e non più lontano di così dal risultato migliore
CAMPI_RISULTATO = "id_foto, cartella, nome, anno, data, categoria, descrizione, persone_riconosciute, titolo"


def trova_foto(radice: Path, estensioni, salta_cartelle, ricorsiva: bool = True):
    """Le foto sotto `radice` (con `ricorsiva=False` solo quelle direttamente dentro)."""
    est = {e.lower() for e in estensioni}
    salta = {s.lower() for s in salta_cartelle}
    for dirpath, dirs, files in os.walk(radice):
        dirs[:] = sorted(d for d in dirs if d.lower() not in salta
                         and not d.startswith(("_", ".")) and not d.lower().startswith("txt_")) if ricorsiva else []
        for f in sorted(files):
            if Path(f).suffix.lower() in est and not f.startswith("._"):
                yield Path(dirpath) / f


def persone_per_foto(registro_file: Path | None) -> dict[str, list[str]]:
    if not registro_file or not registro_file.exists():
        return {}
    from .registro import carica
    out: dict[str, set[str]] = {}
    for vid, persona in carica(registro_file).assegnati.items():
        out.setdefault(vid.rsplit("#face", 1)[0], set()).add(persona)
    return {k: sorted(v) for k, v in out.items()}


def costruisci(radice: Path, file_indice: Path, cartella_txt: str = "_txt",
               estensioni=(".jpg", ".jpeg", ".jfif", ".png"), salta_cartelle=(),
               registro_file: Path | None = None, avanzamento=print) -> dict:
    """Ricostruisce l'indice da zero (scrive su un file temporaneo e poi lo sostituisce)."""
    t0 = time.time()
    file_indice.parent.mkdir(parents=True, exist_ok=True)
    tmp = file_indice.with_name(file_indice.name + ".tmp")
    if tmp.exists():
        tmp.unlink()
    persone = persone_per_foto(registro_file)
    con = sqlite3.connect(tmp)
    con.executescript(SCHEMA)
    n_foto = n_schede = 0
    righe = []
    for foto in trova_foto(radice, estensioni, salta_cartelle):
        n_foto += 1
        txt = foto.parent / cartella_txt / (foto.stem + ".txt")
        if not txt.exists():
            continue
        s = leggi_file(txt)
        fid = id_foto(radice, foto)
        cartella = fid.rsplit("/", 1)[0] if "/" in fid else ""
        righe.append((
            fid, cartella, foto.name, s.anno(cartella), s.data_iso, s.categoria,
            s.descrizione, s.testi, s.luogo, s.persone, s.parole_chiave,
            " | ".join(persone.get(fid, [])), s.modello, int(s.avviso),
            s.titolo, s.occasione, s.fotografia, s.dubbi,
        ))
        n_schede += 1
        if n_schede % 2000 == 0:
            avanzamento(f"  {n_schede} schede lette...")
    con.executemany(
        "INSERT INTO foto (id_foto, cartella, nome, anno, data, categoria, descrizione, testi, luogo,"
        " persone_testo, parole_chiave, persone_riconosciute, modello, avviso,"
        " titolo, occasione, fotografia, dubbi)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", righe)
    con.execute("INSERT INTO fts(fts) VALUES ('rebuild')")
    info = {"radice": str(radice), "creato": time.strftime("%Y-%m-%d %H:%M:%S"),
            "foto": str(n_foto), "schede": str(n_schede), "volti": "1" if persone else "0"}
    con.executemany("INSERT INTO info VALUES (?,?)", info.items())
    con.commit()
    con.close()
    tmp.replace(file_indice)
    return {"foto_trovate": n_foto, "schede_indicizzate": n_schede,
            "foto_con_persone": len(persone), "secondi": round(time.time() - t0, 1)}


#  Sinonimi: gruppi di parole equivalenti per la ricerca (si possono ampliare).
SINONIMI = [
    {"auto", "automobile", "macchina", "vettura", "autovettura"},
    {"moto", "motocicletta", "motociclo"},
    {"bici", "bicicletta"},
    {"barca", "imbarcazione", "battello", "nave"},
    {"chiesa", "cattedrale", "duomo", "basilica"},
    {"computer", "pc", "calcolatore", "elaboratore"},
    {"bambino", "bimbo", "bambina", "bimba"},
    {"cane", "cucciolo"},
]
_VOCALI = "aeiouàèéìòù"


def _radice(parola: str) -> str:
    """Radice approssimativa per l'italiano: 'rossa' -> 'ross', così trova rosso/rossa/rossi/rosse.

    Solo per parole di almeno 5 lettere che finiscono in vocale (le parole brevi restano
    come sono, per non allargare troppo: 'mare' non deve trovare 'marrone')."""
    p = parola.lower()
    if len(p) >= 5 and p[-1] in _VOCALI:
        p = p[:-1]
        if p.endswith(("ch", "gh")):  # barche -> barc, laghi -> lag
            p = p[:-1]
    return p


def _termine(parola: str, esatto_se_breve: bool = False) -> str:
    r = _radice(parola)
    if esatto_se_breve and len(r) <= 4:
        return f'"{r}"'  # 'auto' come sinonimo non deve trovare 'autostrada'
    return f'"{r}"*'


#  Parole troppo comuni per essere utili ("barca a vela" -> barca, vela)
PAROLE_VUOTE = set(
    "a ad al alla alle allo ai agli c che con col da dal dalla dalle dai dagli dei del della delle"
    " dello degli di e ed fra gli i il in l la le lo nel nella nelle nello nei negli o od per sul"
    " sulla sulle sullo sui sugli su tra un una uno".split()
)


def _gruppi_termini(testo: str) -> list[list[str]]:
    """Per ogni parola cercata, l'elenco dei termini equivalenti (radice e sinonimi)."""
    gruppi = []
    parole = re.findall(r"\w+", testo, flags=re.UNICODE)
    utili = [p for p in parole if p.lower() not in PAROLE_VUOTE]
    for p in (utili or parole):
        gruppo = next((g for g in SINONIMI if p.lower() in g), None)
        if gruppo:
            gruppi.append(sorted({_termine(p)} | {_termine(s, esatto_se_breve=True) for s in gruppo if s != p.lower()}))
        else:
            gruppi.append([_termine(p)])
    return gruppi


def _query_fts(testo: str) -> str:
    """Ogni parola cercata diventa: (radice* OR sinonimi*), e le parole vanno tutte trovate."""
    return " AND ".join(g[0] if len(g) == 1 else "(" + " OR ".join(g) + ")" for g in _gruppi_termini(testo))


def _query_vicinanza(testo: str, distanza: int = 4, massimo: int = 40) -> str:
    """Stesse parole ma vicine tra loro (es. 'vettura sportiva rossa'): serve a metterle in cima.

    FTS5 non accetta OR dentro NEAR, quindi si elencano le combinazioni (se non sono troppe)."""
    import itertools
    gruppi = _gruppi_termini(testo)
    if len(gruppi) < 2:
        return ""
    combinazioni = list(itertools.islice(itertools.product(*gruppi), massimo + 1))
    if len(combinazioni) > massimo:
        return ""
    return " OR ".join(f"NEAR({' '.join(c)}, {distanza})" for c in combinazioni)


@dataclass
class Filtri:
    testo: str = ""
    categoria: str = ""
    anno_da: int | None = None
    anno_a: int | None = None
    persona: str = ""
    cartella: str = ""          # id della cartella (relativo alla radice): include le sottocartelle
    da_verificare: bool = False  # solo schede con avviso o con dubbi dichiarati dal modello


class Indice:
    def __init__(self, file_indice: Path):
        if not file_indice.exists():
            raise FileNotFoundError(f"Indice non trovato: {file_indice}. Lancia prima 'indicizza'.")
        self.file = file_indice
        self._con = sqlite3.connect(f"file:{file_indice.as_posix()}?mode=ro", uri=True,
                                    check_same_thread=False)
        self._con.row_factory = sqlite3.Row

    def chiudi(self) -> None:
        self._con.close()

    def info(self) -> dict:
        return {r["chiave"]: r["valore"] for r in self._con.execute("SELECT * FROM info")}

    def valori_filtri(self) -> dict:
        c = self._con
        cat = [dict(r) for r in c.execute(
            "SELECT categoria AS valore, count(*) AS n FROM foto GROUP BY categoria ORDER BY n DESC")]
        anni = [r[0] for r in c.execute(
            "SELECT DISTINCT anno FROM foto WHERE anno IS NOT NULL ORDER BY anno")]
        conteggio: dict[str, int] = {}
        for (v,) in c.execute("SELECT persone_riconosciute FROM foto WHERE persone_riconosciute != ''"):
            for p in v.split(" | "):
                conteggio[p] = conteggio.get(p, 0) + 1
        persone = [{"valore": k, "n": n} for k, n in sorted(conteggio.items(), key=lambda x: -x[1])]
        return {"categorie": cat, "anni": anni, "persone": persone}

    @staticmethod
    def _filtri_sql(f: Filtri) -> tuple[list[str], list]:
        where, par = [], []
        if f.categoria:
            where.append("foto.categoria = ?")
            par.append(f.categoria)
        if f.anno_da:
            where.append("foto.anno >= ?")
            par.append(int(f.anno_da))
        if f.anno_a:
            where.append("foto.anno <= ?")
            par.append(int(f.anno_a))
        if f.persona:
            where.append("(' | ' || foto.persone_riconosciute || ' | ') LIKE ?")
            par.append(f"% | {f.persona} | %")
        if f.cartella:
            where.append("(foto.cartella = ? OR substr(foto.cartella, 1, ?) = ?)")
            par += [f.cartella, len(f.cartella) + 1, f.cartella + "/"]
        if f.da_verificare:
            where.append("(foto.avviso = 1 OR (coalesce(foto.dubbi, '') != '' "
                         "AND lower(foto.dubbi) NOT LIKE 'nessun%' AND lower(foto.dubbi) NOT LIKE 'non ce ne%'))")
        return where, par

    def _righe(self, ids: list[str]) -> list[dict]:
        """Righe dei risultati nell'ordine dato."""
        if not ids:
            return []
        campi = ", ".join(c.strip() for c in CAMPI_RISULTATO.split(","))
        segnaposto = ",".join("?" * len(ids))
        per_id = {r["id_foto"]: dict(r) for r in self._con.execute(
            f"SELECT {campi} FROM foto WHERE id_foto IN ({segnaposto})", ids)}
        return [per_id[i] for i in ids if i in per_id]

    def cerca(self, f: Filtri, pagina: int = 1, per_pagina: int = 60,
              semantico=None, modo: str = "misto") -> dict:
        """modo: 'parole' (solo testo), 'significato' (solo vettori) o 'misto' (le due classifiche fuse).

        I modi con il significato si usano solo se c'è un testo e l'indice semantico è disponibile."""
        pagina = max(1, int(pagina))
        if f.testo.strip() and semantico is not None and modo in ("misto", "significato"):
            return self._cerca_significato(f, pagina, per_pagina, semantico, modo)
        return self._cerca_parole(f, pagina, per_pagina)

    def _ids_parole(self, f: Filtri, limite: int = 3000) -> list[str]:
        q = _query_fts(f.testo)
        if not q:
            return []
        where, par = self._filtri_sql(f)
        cond = " AND ".join(["fts MATCH ?"] + where)
        ordine, par_ordine = f"bm25(fts, {PESI_BM25})", []
        vicini = _query_vicinanza(f.testo)
        if vicini:
            ordine = "CASE WHEN foto.id IN (SELECT rowid FROM fts WHERE fts MATCH ?) THEN 0 ELSE 1 END, " + ordine
            par_ordine = [vicini]
        return [r[0] for r in self._con.execute(
            f"SELECT foto.id_foto FROM foto JOIN fts ON fts.rowid = foto.id WHERE {cond} ORDER BY {ordine} LIMIT ?",
            [q] + par + par_ordine + [limite])]

    def _cerca_significato(self, f: Filtri, pagina, per_pagina, semantico, modo) -> dict:
        # soglia: sotto questa similarità i risultati "per significato" sono quasi sempre fuori tema
        sem = semantico.classifica(f.testo, limite=600, soglia=SOGLIA_SIGNIFICATO, distacco=DISTACCO_SIGNIFICATO)
        sem_ids = [i for i, _ in sem]
        where, par = self._filtri_sql(f)
        if where and sem_ids:  # applica categoria/anni/persona anche ai risultati per significato
            ammessi = set()
            for n in range(0, len(sem_ids), 500):
                blocco = sem_ids[n:n + 500]
                ammessi |= {r[0] for r in self._con.execute(
                    f"SELECT id_foto FROM foto WHERE id_foto IN ({','.join('?' * len(blocco))}) AND "
                    + " AND ".join(where), blocco + par)}
            sem_ids = [i for i in sem_ids if i in ammessi]
        if modo == "significato":
            ordinati = sem_ids
        else:  # fusione delle due classifiche (Reciprocal Rank Fusion)
            punteggio: dict[str, float] = {}
            for lista in (self._ids_parole(f), sem_ids):
                for pos, i in enumerate(lista):
                    punteggio[i] = punteggio.get(i, 0.0) + 1.0 / (60 + pos)
            ordinati = sorted(punteggio, key=lambda i: -punteggio[i])
        inizio = (pagina - 1) * per_pagina
        return {"totale": len(ordinati), "pagina": pagina, "per_pagina": per_pagina, "modo": modo,
                "risultati": self._righe(ordinati[inizio:inizio + per_pagina])}

    def _cerca_parole(self, f: Filtri, pagina: int, per_pagina: int) -> dict:
        where, par = self._filtri_sql(f)
        q = _query_fts(f.testo)
        if q:
            where.insert(0, "fts MATCH ?")
            par.insert(0, q)
        base = "FROM foto JOIN fts ON fts.rowid = foto.id" if q else "FROM foto"
        cond = (" WHERE " + " AND ".join(where)) if where else ""
        ordine = f"bm25(fts, {PESI_BM25})" if q else "foto.data DESC, foto.id_foto"
        vicini = _query_vicinanza(f.testo) if q else ""
        par_ordine = []
        if vicini:
            ordine = "CASE WHEN foto.id IN (SELECT rowid FROM fts WHERE fts MATCH ?) THEN 0 ELSE 1 END, " + ordine
            par_ordine = [vicini]
        totale = self._con.execute(f"SELECT count(*) {base}{cond}", par).fetchone()[0]
        sql = (f"SELECT {', '.join('foto.' + c.strip() for c in CAMPI_RISULTATO.split(','))} "
               f"{base}{cond} ORDER BY {ordine} LIMIT ? OFFSET ?")
        righe = [dict(r) for r in self._con.execute(sql, par + par_ordine + [per_pagina, (pagina - 1) * per_pagina])]
        return {"totale": totale, "pagina": pagina, "per_pagina": per_pagina, "modo": "parole", "risultati": righe}

    def statistiche(self) -> dict:
        c = self._con
        tot = c.execute("SELECT count(*) FROM foto").fetchone()[0]
        per_anno = [dict(r) for r in c.execute(
            "SELECT anno, count(*) AS n FROM foto WHERE anno IS NOT NULL GROUP BY anno ORDER BY anno")]
        modelli = [dict(r) for r in c.execute(
            "SELECT modello, count(*) AS n FROM foto GROUP BY modello ORDER BY n DESC")]
        verificare = self.cerca(Filtri(da_verificare=True), per_pagina=1)["totale"]
        return {"schede": tot, "per_anno": per_anno, "modelli": modelli, "da_verificare": verificare,
                "foto": int(self.info().get("foto", tot))}

    def tutte(self, f: Filtri, semantico=None, modo: str = "misto", massimo: int = 50000) -> list[dict]:
        """Tutti i risultati di una ricerca con tutti i campi (per l'esportazione)."""
        r = self.cerca(f, per_pagina=massimo, semantico=semantico, modo=modo)
        ids = [x["id_foto"] for x in r["risultati"]]
        out = []
        for n in range(0, len(ids), 500):
            blocco = ids[n:n + 500]
            per_id = {x["id_foto"]: dict(x) for x in self._con.execute(
                f"SELECT * FROM foto WHERE id_foto IN ({','.join('?' * len(blocco))})", blocco)}
            out += [per_id[i] for i in blocco if i in per_id]
        return out

    def simili(self, fid: str, semantico, limite: int = 60) -> list[dict]:
        """Foto con la scheda più vicina per significato a quella data (serve l'indice semantico)."""
        ids = semantico.vicini(fid, limite + 1)
        return self._righe([i for i in ids if i != fid][:limite])

    def scheda(self, fid: str) -> dict | None:
        r = self._con.execute("SELECT * FROM foto WHERE id_foto = ?", (fid,)).fetchone()
        return dict(r) if r else None
