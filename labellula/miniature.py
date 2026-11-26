"""Miniature delle foto, create al primo uso e conservate in una cache su disco."""
from __future__ import annotations

import hashlib
import threading
from pathlib import Path

from PIL import Image, ImageOps

from . import foto as _foto  # noqa: F401  (registra l'apertura delle foto HEIC, se pillow-heif c'è)

Image.MAX_IMAGE_PIXELS = None
_lock = threading.Lock()


def file_miniatura(cache: Path, fid: str, lato: int) -> Path:
    h = hashlib.sha1(f"{fid}|{lato}".encode("utf-8")).hexdigest()
    return cache / h[:2] / f"{h}.jpg"


def miniatura(foto: Path, cache: Path, fid: str, lato: int = 480) -> Path:
    dest = file_miniatura(cache, fid, lato)
    if dest.exists() and dest.stat().st_mtime >= foto.stat().st_mtime:
        return dest
    with Image.open(foto) as im:
        im.draft("RGB", (lato * 2, lato * 2))  # decodifica JPEG ridotta: molto più veloce
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((lato, lato))
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(f".{threading.get_ident()}.tmp")
        im.save(tmp, "JPEG", quality=82)  # senza EXIF
    with _lock:
        tmp.replace(dest)
    return dest
