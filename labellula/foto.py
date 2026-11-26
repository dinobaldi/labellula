"""Lettura di una foto senza AI: EXIF, data, luogo, metriche, copia ridotta da mandare al modello.

Tutto avviene sul PC dell'utente. La copia ridotta (`copia_ridotta`) è ri-codificata da PIL e quindi
non contiene EXIF né GPS: è l'unica cosa che un motore remoto vedrebbe.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None  # niente blocco sulle foto molto grandi

FORMATI_HEIC = (".heic", ".heif")
try:                      # foto HEIC/HEIF di iPhone e di molti telefoni Android (pacchetto pillow-heif)
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC = True
except ImportError:
    HEIC = False

try:
    import imagehash
except ImportError:  # facoltativo
    imagehash = None
try:
    from scipy.ndimage import laplace
except ImportError:  # facoltativo
    laplace = None

TAG_EXIF = [
    "-Make", "-Model", "-LensModel", "-DateTimeOriginal", "-CreateDate",
    "-GPSLatitude", "-GPSLongitude", "-FNumber", "-ExposureTime", "-ISO",
    "-FocalLength", "-Software", "-ProcessingSoftware",
]
_RE_DATA_NOME = re.compile(r"(?<!\d)((?:19|20)\d\d)[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?!\d)")


@dataclass
class InfoFoto:
    """Quello che si sa di una foto prima di chiedere al modello."""
    exif: dict = field(default_factory=dict)
    quando: str = "sconosciuta (prova a dedurla dalla cartella)"
    luogo: str | None = None
    gps: dict | None = None          # risultato di reverse_geocoder, per confrontarlo con le cartelle
    metriche: dict = field(default_factory=dict)
    indizi: "Indizi | None" = None


# ------------------------------------------------------------------ EXIF
def leggi_exif(foto: Path) -> dict:
    """EXIF con exiftool se c'è (più completo), altrimenti con PIL."""
    if shutil.which("exiftool"):
        try:
            r = subprocess.run(["exiftool", "-j", "-n", *TAG_EXIF, str(foto)],
                               capture_output=True, timeout=60)
            dati = json.loads(r.stdout.decode("utf-8", "replace") or "[]")
            if dati:
                return dati[0]
        except Exception:
            pass
    return _exif_pil(foto)


def _exif_pil(foto: Path) -> dict:
    try:
        with Image.open(foto) as im:
            ex = im.getexif()
            base = {k: ex.get(v) for k, v in (("Make", 271), ("Model", 272), ("Software", 305))}
            sub = ex.get_ifd(0x8769)
            base["DateTimeOriginal"] = sub.get(36867)
            gps = ex.get_ifd(0x8825)
    except Exception:
        return {}

    def gradi(v, rif):
        try:
            g = float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
            return -g if rif in ("S", "W") else g
        except Exception:
            return None
    if gps.get(2) and gps.get(4):
        base["GPSLatitude"] = gradi(gps[2], gps.get(1))
        base["GPSLongitude"] = gradi(gps[4], gps.get(3))
    return {k: v for k, v in base.items() if v is not None}


def data_exif(e: dict) -> datetime | None:
    for k in ("DateTimeOriginal", "CreateDate"):
        v = e.get(k)
        if isinstance(v, str):
            try:
                return datetime.strptime(v[:19], "%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue
    return None


def data_da_nome(nome: str) -> datetime | None:
    m = _RE_DATA_NOME.search(nome)
    if not m:
        return None
    try:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def quando(foto: Path, e: dict) -> str:
    d = data_exif(e)
    if d:
        return d.strftime("%d/%m/%Y %H:%M") + " (da EXIF)"
    d = data_da_nome(foto.name)
    if d:
        return d.strftime("%d/%m/%Y") + " (dal nome del file, meno affidabile)"
    return "sconosciuta (prova a dedurla dalla cartella)"


def _coordinate(e: dict):
    lat, lon = e.get("GPSLatitude"), e.get("GPSLongitude")
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)) or (lat == 0 and lon == 0):
        return None
    return lat, lon


def gps_luogo(e: dict) -> dict | None:
    """Località più vicina alle coordinate, calcolata in locale (reverse_geocoder, senza internet)."""
    c = _coordinate(e)
    if not c:
        return None
    try:
        import reverse_geocoder as rg
        return dict(rg.search(c, mode=1, verbose=False)[0])
    except Exception:
        return None


def luogo_da_gps(e: dict, r: dict | None = None) -> str | None:
    c = _coordinate(e)
    if not c:
        return None
    coordinate = f"lat {c[0]:.5f}, lon {c[1]:.5f}"
    r = r if r is not None else gps_luogo(e)
    return f"{r['name']}, {r['admin1']}, {r['cc']} ({coordinate})" if r else coordinate


def stagione_momento(d: datetime | None, lat: float | None = None) -> str:
    """'inverno, pomeriggio' dalla data e ora EXIF (emisfero sud se la latitudine è negativa; ai tropici niente stagione)."""
    if d is None:
        return ""
    parti = []
    if lat is None or abs(lat) > 23.5:
        stagioni = ["inverno", "inverno", "primavera", "primavera", "primavera", "estate",
                    "estate", "estate", "autunno", "autunno", "autunno", "inverno"]
        s = stagioni[d.month - 1]
        if lat is not None and lat < 0:
            s = {"inverno": "estate", "estate": "inverno", "primavera": "autunno", "autunno": "primavera"}[s]
        parti.append(s)
    h = d.hour + d.minute / 60
    if d.hour or d.minute or d.second:          # 00:00:00 di solito vuol dire "ora sconosciuta"
        parti.append("alba o primo mattino" if 5 <= h < 7.5 else "mattina" if h < 12 and h >= 7.5
                     else "mezzogiorno" if 12 <= h < 14 else "pomeriggio" if 14 <= h < 18
                     else "sera" if 18 <= h < 21.5 else "notte")
    return ", ".join(parti)


def scatto(e: dict) -> str | None:
    parti = []
    try:
        if e.get("FNumber"):
            parti.append(f"f/{float(e['FNumber']):g}")
        t = e.get("ExposureTime")
        if t:
            t = float(t)
            parti.append(f"1/{round(1 / t)} s" if t < 1 else f"{t:g} s")
        if e.get("ISO"):
            parti.append(f"ISO {e['ISO']}")
        if e.get("FocalLength"):
            parti.append(f"{float(e['FocalLength']):g} mm")
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return " · ".join(parti) or None


# -------------------------------------------------------------- immagine
def apri(foto: Path) -> Image.Image:
    with Image.open(foto) as im:
        return ImageOps.exif_transpose(im).convert("RGB")


def metriche(foto: Path, im: Image.Image) -> dict:
    """Metriche veloci senza AI, utili come filtri (duplicati, foto mosse o buie)."""
    out = {"larghezza": im.width, "altezza": im.height}
    try:
        out["peso_mb"] = foto.stat().st_size / (1024 * 1024)
    except OSError:
        out["peso_mb"] = 0.0
    r = im.width / im.height if im.height else 1
    out["formato"] = ("Panoramica" if r > 2.0 else "Orizzontale" if r > 1.2
                      else "Verticale" if r < 0.8 else "Quadrata")
    piccola = im.copy()
    piccola.thumbnail((512, 512))
    grigi = np.asarray(piccola.convert("L"), dtype=np.float64)
    out["luminosita"] = float(grigi.mean())
    if laplace is not None:
        out["nitidezza"] = float(laplace(grigi).var())
    if imagehash is not None:
        out["phash"] = str(imagehash.phash(im))
    return out


def copia_ridotta(im: Image.Image, lato_massimo: int, qualita: int = 90) -> bytes:
    """JPEG ridotto e senza metadati: è ciò che viene mandato al modello."""
    piccola = im.copy()
    piccola.thumbnail((lato_massimo, lato_massimo))
    buf = io.BytesIO()
    piccola.save(buf, "JPEG", quality=qualita)  # PIL non copia EXIF/GPS se non glieli si passa
    return buf.getvalue()


def analizza(foto: Path, radice: Path | None = None) -> tuple[InfoFoto, Image.Image]:
    from .indizi import raccogli
    e = leggi_exif(foto)
    im = apri(foto)
    g = gps_luogo(e)
    info = InfoFoto(exif=e, quando=quando(foto, e), luogo=luogo_da_gps(e, g), gps=g, metriche=metriche(foto, im))
    info.indizi = raccogli(foto, radice, data_exif(e), g)
    return info, im
