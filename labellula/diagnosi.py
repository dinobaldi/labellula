"""Diagnosi: cosa c'è e cosa manca su questo computer, in un colpo solo (da fotografare e mandare).

    python -m labellula diagnosi [--cartella X]
"""
from __future__ import annotations

import platform
import sys
import tempfile
from pathlib import Path


def _riga(nome: str, valore: str, ok: bool | None = None) -> str:
    segno = {True: "OK ", False: "NO ", None: "   "}[ok]
    return f"[{segno}] {nome:<22} {valore}"


def controlla_heic() -> tuple[bool, str]:
    try:
        import pillow_heif
    except Exception as ex:                          # ImportError o librerie di sistema mancanti
        return False, f"pillow-heif non disponibile ({type(ex).__name__}: {ex}). Rilancia l'installatore."
    try:
        from PIL import Image
        from . import foto  # noqa: F401  (registra l'apertura delle HEIC)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "prova.heic"
            Image.new("RGB", (64, 48), (200, 50, 50)).save(f, format="HEIF")
            with Image.open(f) as im:
                im.load()
                return True, f"pillow-heif {pillow_heif.__version__}: scrittura e lettura di una HEIC riuscite"
    except Exception as ex:
        return False, f"pillow-heif {getattr(pillow_heif, '__version__', '?')} presente ma non funziona: {ex}"


def conta_formati(cartella: Path, limite: int = 20000) -> dict:
    conta: dict[str, int] = {}
    segnaposto = 0
    for i, f in enumerate(cartella.rglob("*")):
        if i > limite:
            break
        if f.name.endswith(".icloud"):               # file di iCloud non scaricati sul Mac
            segnaposto += 1
            continue
        if f.is_file() and not f.name.startswith("._"):
            e = f.suffix.lower()
            if e in (".jpg", ".jpeg", ".png", ".heic", ".heif", ".jfif", ".dng", ".raf", ".cr2", ".nef", ".arw", ".mov", ".mp4"):
                conta[e] = conta.get(e, 0) + 1
    if segnaposto:
        conta["(segnaposto iCloud non scaricati)"] = segnaposto
    return conta


def esegui(cfg, cartella: Path | None = None) -> str:
    import PIL
    from .server import firma_codice
    righe = ["Labellula – diagnosi", ""]
    righe.append(_riga("Sistema", f"{platform.system()} {platform.release()} ({platform.machine()})"))
    righe.append(_riga("Python", f"{sys.version.split()[0]} in {sys.executable}", sys.version_info >= (3, 10)))
    righe.append(_riga("Codice di Labellula", f"firma {firma_codice()} in {Path(__file__).resolve().parent}"))
    righe.append(_riga("Pillow", PIL.__version__, True))
    ok, msg = controlla_heic()
    righe.append(_riga("Foto HEIC", msg, ok))
    est = cfg["archivio"]["estensioni"]
    righe.append(_riga("Estensioni cercate", ", ".join(est), ".heic" in [e.lower() for e in est]))
    radice = cfg.radice_archivio
    righe.append(_riga("Archivio", str(radice), radice.is_dir()))
    righe.append(_riga("Ollama", cfg["modello"]["ollama_url"] + f" (motore {cfg['modello'].get('motore', 'ollama')}, "
                                  f"modello {cfg['modello']['nome']})"))
    try:
        import requests
        v = requests.get(cfg["modello"]["ollama_url"].rstrip("/") + "/api/version", timeout=4).json().get("version")
        righe.append(_riga("Ollama risponde", f"versione {v}", True))
    except Exception as ex:
        righe.append(_riga("Ollama risponde", f"no ({type(ex).__name__})", False))
    try:
        import json
        import urllib.request
        d = json.load(urllib.request.urlopen(f"http://127.0.0.1:{cfg['server']['porta']}/api/info", timeout=2))
        aggiornato = d.get("firma") == firma_codice()
        righe.append(_riga("Server della pagina", f"aperto, firma {d.get('firma') or 'assente (versione vecchia)'}"
                           + ("" if aggiornato else " → chiudi e riapri Labellula"), aggiornato))
    except Exception:
        righe.append(_riga("Server della pagina", "non aperto"))
    if cartella:
        righe.append(_riga("Cartella controllata", str(cartella), cartella.is_dir()))
        if cartella.is_dir():
            for k, n in sorted(conta_formati(cartella).items()):
                righe.append(_riga(f"  {k}", str(n)))
    return "\n".join(righe)
