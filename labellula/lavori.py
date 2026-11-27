"""Lavori in background avviati dall'interfaccia web: descrivere una cartella e poi aggiornare la ricerca.

Un solo lavoro alla volta (la GPU è una). Lo stato si legge con `stato()`; `ferma()` chiede di fermarsi
alla foto successiva: le schede già scritte restano, e rilanciando si riprende da dove si era.
"""
from __future__ import annotations

import os
import string
import threading
import time
from pathlib import Path


def elenca_cartelle(percorso: str, estensioni, cartella_txt: str = "_txt") -> dict:
    """Sottocartelle di `percorso` (o le unità disco se vuoto), con quante foto e schede ci sono direttamente dentro."""
    est = {e.lower() for e in estensioni}
    if not percorso:
        if os.name == "nt":
            unita = [f"{l}:\\" for l in string.ascii_uppercase if Path(f"{l}:\\").exists()]
            return {"percorso": "", "padre": None, "cartelle": [{"nome": u, "percorso": u} for u in unita],
                    "foto": 0, "schede": 0}
        percorso = "/"
    p = Path(percorso).expanduser()
    if not p.is_dir():
        raise FileNotFoundError(f"Cartella non trovata: {percorso}")
    cartelle, foto, schede, heic = [], 0, 0, 0
    try:
        voci = sorted(p.iterdir(), key=lambda x: x.name.lower())
    except PermissionError:
        voci = []
    for x in voci:
        try:
            if x.is_dir():
                if not x.name.startswith(("_", ".", "$")) and x.name.lower() != "system volume information":
                    cartelle.append({"nome": x.name, "percorso": str(x)})
            elif x.suffix.lower() in est and not x.name.startswith("._"):
                foto += 1
                heic += x.suffix.lower() in (".heic", ".heif")
                schede += (x.parent / cartella_txt / (x.stem + ".txt")).exists()
        except OSError:
            continue
    padre = str(p.parent) if p.parent != p else ("" if os.name == "nt" else None)
    return {"percorso": str(p), "padre": padre, "cartelle": cartelle, "foto": foto, "schede": schede, "heic": heic}


def _non_dormire(attivo: bool) -> None:
    """Su Windows chiede di non andare in sospensione finché il lavoro è in corso (non cambia le impostazioni:
    vale solo per questo processo e solo per il thread del lavoro). Sugli altri sistemi non fa niente."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if attivo else 0))
    except Exception:
        pass


class GestoreLavori:
    def __init__(self, cfg, al_termine=None):
        """`al_termine(cartella)` viene chiamata a lavoro finito (es. per aggiornare l'indice)."""
        self.cfg = cfg
        self.al_termine = al_termine
        self._lock = threading.Lock()
        self._filo: threading.Thread | None = None
        self._stop = threading.Event()
        self._stato: dict = {"attivo": False}

    def stato(self) -> dict:
        with self._lock:
            return dict(self._stato)

    def _aggiorna(self, **kv):
        with self._lock:
            self._stato.update(kv)

    def conta(self, cartella: Path, rifai: bool = False, aggiorna: bool = False) -> dict:
        from .descrizione import Opzioni, da_fare, etichetta
        a = self.cfg["archivio"]
        versione = etichetta(Opzioni.da_config(self.cfg).versione, Opzioni.da_config(self.cfg).lingua)
        totale, lista, doppi = da_fare(cartella, a["estensioni"], a["salta_cartelle"],
                                       self.cfg["schede"]["cartella_txt"], rifai,
                                       aggiorna_a=versione if aggiorna else None)
        return {"totale": totale, "da_fare": len(lista), "doppi": len(doppi),
                "minuti_stimati": round(len(lista) * 6 / 60)}

    def avvia(self, cartella: str, rifai: bool = False, limite: int = 0, aggiorna: bool = False,
              modello: str = "", a_lotti: bool = False) -> dict:
        """`a_lotti`: descrive una sottocartella alla volta e aggiorna la ricerca dopo ognuna
        (per i lavori lunghi: se si ferma, quello che è fatto è già cercabile)."""
        from .descrizione import Opzioni, esegui
        from .indice import trova_foto
        from .motori import MotoreOllama, crea_motore
        c = Path(cartella)
        if not c.is_dir():
            raise FileNotFoundError(f"Cartella non trovata: {cartella}")
        a = self.cfg["archivio"]
        salta = {s.lower() for s in a["salta_cartelle"]}
        lotti = [(c, True)]                       # (cartella, con le sottocartelle?)
        if a_lotti:
            sotto = sorted(x for x in c.iterdir() if x.is_dir() and not x.name.startswith(("_", "."))
                           and x.name.lower() not in salta)
            if sotto:
                # le foto che stanno direttamente nella cartella scelta sono un lotto a sé
                sciolte = next(trova_foto(c, a["estensioni"], a["salta_cartelle"], ricorsiva=False), None)
                lotti = ([(c, False)] if sciolte else []) + [(x, True) for x in sotto]
        # Motore e opzioni prima di segnare il lavoro come attivo: se qui c'è un errore
        # (es. motore "remoto" non ancora disponibile) non resta un lavoro "in corso" fantasma.
        motore = MotoreOllama(self.cfg["modello"]["ollama_url"], modello) if modello else crea_motore(self.cfg)
        opzioni = Opzioni.da_config(self.cfg)
        try:
            c.resolve().relative_to(self.cfg.radice_archivio.resolve())
            opzioni.radice = self.cfg.radice_archivio     # dentro l'archivio: le cartelle superiori sono indizi
        except (ValueError, OSError):
            opzioni.radice = c                            # fuori: gli indizi partono dalla cartella scelta
        with self._lock:
            if self._stato.get("attivo"):
                raise RuntimeError("C'è già un lavoro in corso: aspetta che finisca o fermalo.")
            self._stop.clear()
            self._stato = {"attivo": True, "fase": "preparazione", "cartella": str(c), "fatte": 0,
                           "totale": None, "foto": "", "esito": "", "secondi_mancanti": None,
                           "iniziato": time.strftime("%H:%M:%S"), "messaggi": [],
                           "lotti": len(lotti), "lotto": 0, "fatte_totali": 0}

        def messaggio(s: str):
            with self._lock:
                self._stato.setdefault("messaggi", []).append(s)
                self._stato["messaggi"] = self._stato["messaggi"][-8:]

        def lavora():
            _non_dormire(True)
            try:
                somma = {"totale": 0, "fatte": 0, "errori": 0, "da_verificare": 0, "secondi": 0.0}
                for k, (lotto, ricorsiva) in enumerate(lotti, 1):
                    if self._stop.is_set():
                        break
                    resto = limite - somma["fatte"] - somma["errori"] if limite else 0
                    if limite and resto <= 0:          # il limite vale per tutto il lavoro, non per ogni lotto
                        break
                    self._aggiorna(fase="descrizione", lotto=k, nome_lotto=lotto.name)
                    r = esegui(lotto, motore, opzioni, a["estensioni"], a["salta_cartelle"], self.cfg.cartella_dati,
                               limite=resto, rifai=rifai, aggiorna=aggiorna, stampa=messaggio,
                               avanzamento=lambda d: self._aggiorna(**d), fermati=self._stop.is_set,
                               ricorsiva=ricorsiva)
                    for x in somma:
                        somma[x] += r.get(x, 0)
                    self._aggiorna(risultato=dict(somma), fatte_totali=somma["fatte"])
                    if self.al_termine and r.get("fatte"):
                        self._aggiorna(fase="aggiornamento della ricerca", foto="", secondi_mancanti=None, in_corso="")
                        self.al_termine(lotto, messaggio)
                self._aggiorna(fase="fermato" if self._stop.is_set() else "finito")
            except Exception as ex:
                self._aggiorna(fase="errore", errore=str(ex))
            finally:
                _non_dormire(False)
                self._aggiorna(attivo=False, finito_alle=time.strftime("%H:%M:%S"))

        self._filo = threading.Thread(target=lavora, name="labellula-descrizione", daemon=True)
        self._filo.start()
        return self.stato()

    def ferma(self) -> dict:
        self._stop.set()
        self._aggiorna(fase="in arresto (finisce la foto in corso)")
        return self.stato()


def modelli_visione(url: str) -> list[dict]:
    """Modelli installati in Ollama che sanno guardare le immagini (capability "vision")."""
    import requests
    out = []
    try:
        for m in requests.get(f"{url.rstrip('/')}/api/tags", timeout=5).json().get("models", []):
            try:
                info = requests.post(f"{url.rstrip('/')}/api/show", json={"model": m["name"]}, timeout=10).json()
            except Exception:
                continue
            if "vision" in (info.get("capabilities") or []):
                out.append({"nome": m["name"], "dimensione_gb": round(m.get("size", 0) / 1e9, 1),
                            "parametri": (m.get("details") or {}).get("parameter_size", "")})
    except Exception:
        pass
    return out
