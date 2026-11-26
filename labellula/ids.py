"""Identificativi stabili e univoci per foto e volti.

Problema del codice legacy: l'ID di un volto era "<nome file senza estensione>_face<N>"
(es. DSCF1727_face1). Le fotocamere riusano i nomi (DSCF0001...DSCF9999), quindi
foto diverse in cartelle diverse avevano lo stesso ID: la seconda veniva saltata
("già presente nel DB") e i suoi volti non venivano mai analizzati.

Nuovo schema: l'ID contiene il percorso della foto RELATIVO alla radice dell'archivio,
con barre "/" e maiuscole/minuscole originali, più l'indice del volto:

    2022/2022-03-19 gara ciclistica Milano San Remo/DSCF1727.JPG#face1

- è univoco per costruzione (due file non possono avere lo stesso percorso);
- è leggibile da una persona (si capisce subito di che foto si tratta);
- non dipende dalla lettera del disco (H:, E:...) né dal sistema operativo.
Limite: se si rinomina o sposta una cartella l'ID cambia; per questo serve
`rinomina_prefisso()` per migrare i registri.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath

SEPARATORE_VOLTO = "#face"


def id_foto(radice: str | Path, foto: str | Path) -> str:
    """Percorso relativo della foto rispetto alla radice, con barre '/'."""
    radice_p, foto_p = Path(radice), Path(foto)
    try:
        rel = foto_p.relative_to(radice_p)
    except ValueError:
        # confronto senza distinzione maiuscole/minuscole (Windows)
        r, f = str(radice_p).rstrip("\\/").lower(), str(foto_p)
        if not f.lower().startswith(r):
            raise ValueError(f"La foto {foto_p} non sta sotto la radice {radice_p}")
        # Percorsi scritti su Windows (es. registri legacy "H:\...") letti su Linux o macOS:
        # lì "\" non è un separatore, quindi va convertito a mano.
        return f[len(r):].lstrip("\\/").replace("\\", "/")
    return PurePosixPath(*rel.parts).as_posix()


def id_volto(radice: str | Path, foto: str | Path, indice: int) -> str:
    """ID univoco del volto numero `indice` (come nei file _faces, di solito da 1)."""
    return f"{id_foto(radice, foto)}{SEPARATORE_VOLTO}{int(indice)}"


def scomponi_id_volto(vid: str) -> tuple[str, int]:
    """'cartella/FOTO.JPG#face2' -> ('cartella/FOTO.JPG', 2)."""
    foto, sep, n = vid.rpartition(SEPARATORE_VOLTO)
    if not sep or not n.isdigit():
        raise ValueError(f"ID volto non valido: {vid!r}")
    return foto, int(n)


def id_legacy(foto: str | Path, indice: int) -> str:
    """Vecchio ID non univoco, usato solo per leggere i registri esistenti."""
    return f"{Path(str(foto).replace(chr(92), '/')).stem}_face{int(indice)}"


def rinomina_prefisso(vid: str, vecchio: str, nuovo: str) -> str:
    """Aggiorna un ID quando una cartella viene rinominata o spostata."""
    vecchio, nuovo = vecchio.strip("/"), nuovo.strip("/")
    if vid == vecchio or vid.startswith(vecchio + "/"):
        return nuovo + vid[len(vecchio):]
    return vid
