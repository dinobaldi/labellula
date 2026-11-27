"""Server locale di Labellula: API di ricerca, miniature, foto originali, lavori e interfaccia web.

Usa solo la libreria standard di Python (http.server). Di default ascolta su 127.0.0.1,
quindi è raggiungibile solo da questo PC.

API GET (risposte JSON salvo immagini e CSV):
  /api/info                       stato dell'indice e configurazione pubblica (link, motore, archivio)
  /api/filtri                     categorie, anni, persone disponibili
  /api/statistiche                schede, foto per anno, modelli usati, schede da verificare
  /api/cerca?q=&categoria=&anno_da=&anno_a=&persona=&cartella=&verificare=1&pagina=&modo=misto|significato|parole
  /api/simili?id=<id_foto>        foto con la scheda più simile (serve l'indice per significato)
  /api/esporta.csv?<come cerca>   risultati con tutti i campi, per Excel/LibreOffice
  /api/scheda?id=<id_foto>        scheda completa di una foto
  /api/cartelle?percorso=         sottocartelle (vuoto = unità disco), con foto e schede presenti
  /api/conta?percorso=            foto da descrivere in una cartella (con le sottocartelle)
  /api/lavoro                     stato del lavoro di descrizione in corso
  /api/modelli                    modelli Ollama installati che sanno guardare le immagini
  /miniatura?id=<id_foto>[&lato=1600]  JPEG ridotto a 480 px (o 1600 px), in cache
  /foto?id=<id_foto>              foto originale

API POST (corpo JSON, intestazione obbligatoria `X-Labellula: 1`):
  /api/lavoro      {"cartella": "...", "rifai": false, "aggiorna": false, "limite": 0, "modello": "", "a_lotti": false}
  /api/lavoro/ferma                                                  si ferma alla foto successiva
  /api/archivio    {"radice": "..."}   cambia la cartella dell'archivio (config.yaml, con copia .bak)
  /api/ollama/prova {"indirizzo": "192.168.1.20"}   prova un Ollama senza cambiare niente
  /api/ollama      {"indirizzo": "...", "modello": ""}   usa quell'Ollama (config.yaml, con copia .bak)

Protezioni: si accettano solo richieste con Host localhost/127.0.0.1 (contro il DNS rebinding) e le POST
richiedono un'intestazione personalizzata, che un sito esterno non può inviare senza permesso CORS.
Dalla rete di casa (con password) si cerca e si guarda; le impostazioni (archivio, Ollama, lingua, rete)
si cambiano solo da questo computer, e cartelle e lavori sono limitati all'archivio.
"""
from __future__ import annotations

import csv
import io
import json
import mimetypes
import os
import re
import sys
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .indice import Filtri, Indice
from .miniature import miniatura

WEB = Path(__file__).with_name("web")


def firma_codice() -> str:
    """Impronta dei file .py del programma: se cambia mentre il server gira, il server è "vecchio"
    (per esempio dopo aver scaricato una versione nuova senza chiudere quella aperta)."""
    import hashlib
    h = hashlib.sha1()
    for f in sorted(Path(__file__).parent.glob("*.py")):
        try:
            h.update(f.name.encode() + f.read_bytes())
        except OSError:
            pass
    return h.hexdigest()[:12]


FIRMA_AVVIO = firma_codice()
HOST_AMMESSI = {"localhost", "127.0.0.1", "[::1]"}
# Dalla rete di casa queste POST non sono ammesse: cambiano dove vanno le foto (Ollama), cosa si legge
# dal disco (archivio) o chi può entrare (rete). Si usano solo dal computer su cui gira Labellula.
SOLO_DA_QUESTO_COMPUTER = {"/api/ollama", "/api/ollama/prova", "/api/archivio", "/api/lingua", "/api/rete"}
CAMPI_CSV = ["id_foto", "cartella", "nome", "data", "anno", "categoria", "titolo", "descrizione", "testi",
             "luogo", "occasione", "persone_testo", "persone_riconosciute", "fotografia", "parole_chiave",
             "dubbi", "modello"]


class LetturaScrittura:
    """Molte richieste possono leggere l'indice insieme; la sostituzione aspetta che abbiano finito
    (prima una ricerca poteva trovare il database già chiuso: «Cannot operate on a closed database»)."""

    def __init__(self):
        self._cond = threading.Condition()
        self._lettori = 0
        self._scrittore = False

    def leggi(self):
        lock = self

        class _L:
            def __enter__(self_):
                with lock._cond:
                    lock._cond.wait_for(lambda: not lock._scrittore)
                    lock._lettori += 1

            def __exit__(self_, *a):
                with lock._cond:
                    lock._lettori -= 1
                    lock._cond.notify_all()
        return _L()

    def scrivi(self):
        lock = self

        class _S:
            def __enter__(self_):
                with lock._cond:
                    lock._cond.wait_for(lambda: not lock._scrittore)
                    lock._scrittore = True          # dalle nuove letture in poi si aspetta
                    lock._cond.wait_for(lambda: lock._lettori == 0)

            def __exit__(self_, *a):
                with lock._cond:
                    lock._scrittore = False
                    lock._cond.notify_all()
        return _S()


class Applicazione:
    def __init__(self, radice: Path, indice: Indice, cache_miniature: Path, estensioni, semantico=None, cfg=None):
        self.radice = radice.resolve()
        self.semantico = semantico
        self.indice = indice
        self.cache = cache_miniature
        self.estensioni = {e.lower() for e in estensioni}
        self.cfg = cfg
        self.lavori = None
        self.host_extra: set[str] = set()
        from .accesso import Sessioni
        self.sessioni = Sessioni()
        self.ascolto = "127.0.0.1"          # indirizzo su cui il server è stato avviato (avvia())
        self.porta = 8765
        self._lock_indice = LetturaScrittura()
        if cfg is not None:
            from .lavori import GestoreLavori
            self.lavori = GestoreLavori(cfg, al_termine=self.aggiorna_ricerca)

    # ---------------------------------------------------------------- foto
    def percorso_foto(self, fid: str) -> Path | None:
        """Percorso sicuro della foto: deve stare sotto la radice ed essere nell'indice."""
        if not fid or self.indice.scheda(fid) is None:
            return None
        p = (self.radice / fid).resolve()
        try:
            p.relative_to(self.radice)
        except ValueError:
            return None
        if p.suffix.lower() not in self.estensioni or not p.is_file():
            return None
        return p

    def nell_archivio(self, percorso: str | Path) -> bool:
        try:
            Path(percorso).resolve().relative_to(self.radice)
            return True
        except (ValueError, OSError):
            return False

    def rete(self, da_questo_computer: bool) -> dict:
        from .accesso import indirizzi_locali
        s = self.cfg["server"] if self.cfg else {}
        configurata = s.get("indirizzo", "127.0.0.1") not in ("127.0.0.1", "localhost")
        attiva = self.ascolto not in ("127.0.0.1", "localhost")
        return {"attiva": attiva, "configurata": configurata, "password": bool(s.get("password_hash")),
                "porta": self.porta, "da_questo_computer": da_questo_computer,
                "indirizzi": indirizzi_locali() if da_questo_computer else []}

    def info_pubblica(self) -> dict:
        s = (self.cfg.dati.get("servizio") if self.cfg else None) or {}
        m = self.cfg["modello"] if self.cfg else {}
        from .descrizione import Opzioni, etichetta
        prompt = etichetta(Opzioni.da_config(self.cfg).versione, Opzioni.da_config(self.cfg).lingua) if self.cfg else ""
        demo = Path(__file__).resolve().parent.parent / "examples" / "demo"
        return {"archivio": str(self.radice), "demo": str(demo) if demo.is_dir() else "",
                "in_demo": demo.is_dir() and self.radice == demo.resolve(),
                "motore": m.get("motore", "ollama"), "modello": m.get("nome", ""),
                "prompt": prompt, "hardware": self.hardware(), "heic": self.heic(),
                "ollama_url": m.get("ollama_url", ""),
                "ollama_remoto": not any(h in m.get("ollama_url", "") for h in ("localhost", "127.0.0.1", "[::1]")),
                "url_acquisto": s.get("url_acquisto", ""), "url_donazioni": s.get("url_donazioni", ""),
                "lavori": self.lavori is not None}

    @staticmethod
    def heic() -> bool:
        from . import foto
        return foto.HEIC

    def hardware(self) -> dict:
        """Ultimo risultato di `python -m labellula verifica` e `prova` (dati/hardware.json), se c'è."""
        if not self.cfg:
            return {}
        f = self.cfg.cartella_dati / "hardware.json"
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        schede = ", ".join(f"{s['nome']} {s['vram_gb']} GB" for s in d.get("schede", []) if s.get("nome"))
        return {"verdetto": d.get("verdetto", ""), "consiglio": d.get("consiglio", ""), "schede": schede,
                "modello": d.get("modello_consigliato", ""), "prova": d.get("prova") or {}}

    # ----------------------------------------------------- aggiornare la ricerca
    def aggiorna_ricerca(self, cartella: Path | None = None, messaggio=print) -> None:
        """Ricostruisce l'indice per parole e aggiorna i vettori (solo quelli nuovi), poi li ricarica."""
        from .indice import costruisci
        from .registro import NOME_FILE as REGISTRO
        cfg = self.cfg
        if cartella is not None:
            try:
                cartella.resolve().relative_to(self.radice)
            except ValueError:
                messaggio("La cartella è fuori dall'archivio: le nuove schede non entrano nella ricerca. "
                          "Usa «Imposta come archivio» per cercarle.")
                return
        dati = cfg.cartella_dati
        nuovo = dati / "indice.nuovo.sqlite3"
        messaggio("Aggiorno l'indice per parole…")
        registro = self.radice / REGISTRO if cfg["volti"]["attivo"] else None
        costruisci(self.radice, nuovo, cartella_txt=cfg["schede"]["cartella_txt"],
                   estensioni=cfg["archivio"]["estensioni"], salta_cartelle=cfg["archivio"]["salta_cartelle"],
                   registro_file=registro, avanzamento=messaggio)
        with self._lock_indice.scrivi():
            vecchio = self.indice
            vecchio.chiudi()                     # su Windows un file aperto non si può sostituire
            os.replace(nuovo, dati / "indice.sqlite3")
            self.indice = Indice(dati / "indice.sqlite3")
        try:
            from .semantico import ClientEmbedding, IndiceSemantico, costruisci as vettori
            messaggio("Aggiorno la ricerca per significato…")
            client = ClientEmbedding(cfg["modello"]["ollama_url"], cfg["modello"]["embedding"])
            vettori(dati / "indice.sqlite3", dati, client, avanzamento=messaggio)
            self.semantico = IndiceSemantico(dati, client)
        except Exception as ex:
            messaggio(f"Ricerca per significato non aggiornata: {ex}")
        messaggio("Ricerca aggiornata.")

    def cambia_archivio(self, radice: str) -> dict:
        """Scrive la nuova radice in config.yaml (con copia .bak) e ricostruisce la ricerca."""
        p = Path(radice)
        if not radice or not p.is_dir():
            raise FileNotFoundError(f"Cartella non trovata: {radice}")
        f = getattr(self.cfg, "file", None)
        if f and f.exists():
            testo = f.read_text(encoding="utf-8")
            (f.with_name(f.name + time.strftime(".bak-%Y%m%d-%H%M%S"))).write_text(testo, encoding="utf-8")
            nuovo, n = re.subn(r'(?m)^(\s*radice:\s*).*$', lambda m: m.group(1) + json.dumps(p.as_posix()), testo, 1)
            if n:
                f.write_text(nuovo, encoding="utf-8")
        self.cfg.dati["archivio"]["radice"] = str(p)
        self.radice = p.resolve()
        self.aggiorna_ricerca(None)
        return {"archivio": str(self.radice)}


def _filtri(q: dict) -> Filtri:
    return Filtri(
        testo=q.get("q", ""), categoria=q.get("categoria", ""),
        anno_da=int(q["anno_da"]) if q.get("anno_da") else None,
        anno_a=int(q["anno_a"]) if q.get("anno_a") else None,
        persona=q.get("persona", ""), cartella=q.get("cartella", ""),
        da_verificare=q.get("verificare") == "1",
    )


def crea_handler(app: Applicazione):
    class Handler(BaseHTTPRequestHandler):
        server_version = "Labellula"

        def log_message(self, fmt, *args):  # meno rumore nel terminale
            if "/api/" in (args[0] if args else ""):
                sys.stderr.write("%s\n" % (fmt % args))

        def _json(self, dati, stato=HTTPStatus.OK):
            corpo = json.dumps(dati, ensure_ascii=False).encode("utf-8")
            self.send_response(stato)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def _file(self, percorso: Path, tipo: str | None = None, cache_sec: int = 0):
            dati = percorso.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", tipo or mimetypes.guess_type(percorso.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(dati)))
            # pagina, script e stili: il browser ricontrolla sempre (dopo un aggiornamento niente versioni vecchie)
            self.send_header("Cache-Control", f"max-age={cache_sec}" if cache_sec else "no-cache")
            self.end_headers()
            self.wfile.write(dati)

        def _remoto(self) -> bool:
            from .accesso import e_locale
            return not e_locale(self.client_address[0])

        def _autorizzato(self) -> bool:
            """Da questo computer sempre; dalla rete solo con password impostata e sessione valida."""
            if not self._remoto():
                return True
            from .accesso import NOME_COOKIE, leggi_cookie  # noqa: F401
            if not (app.cfg and app.cfg["server"].get("password_hash")):
                return False
            return app.sessioni.valida(leggi_cookie(self.headers.get("Cookie")))

        def _html(self, testo: str, stato=HTTPStatus.OK, cookie: str | None = None, vai: str | None = None):
            corpo = testo.encode("utf-8")
            self.send_response(HTTPStatus.SEE_OTHER if vai else stato)
            if vai:
                self.send_header("Location", vai)
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def _blocca_se_serve(self, percorso: str) -> bool:
            """Per le richieste dalla rete senza sessione: pagina di accesso, o pagina "chiusa". True = gestita."""
            if self._autorizzato():
                return False
            from .accesso import PAGINA_ACCESSO, PAGINA_CHIUSA
            if percorso in ("/marchio.svg",):
                return False
            if percorso.startswith("/api/") or percorso in ("/miniatura", "/foto"):
                self._json({"errore": "accesso richiesto"}, HTTPStatus.UNAUTHORIZED)
            elif not (app.cfg and app.cfg["server"].get("password_hash")):
                self._html(PAGINA_CHIUSA, HTTPStatus.FORBIDDEN)
            elif percorso == "/accesso":
                self._html(PAGINA_ACCESSO.format(errore=""))
            else:
                self._html("", vai="/accesso")
            return True

        def _host_ok(self) -> bool:
            import ipaddress
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].lower().strip("[]")
            if host in HOST_AMMESSI or host in app.host_extra or host == "::1":
                return True
            if self._remoto() and app.ascolto not in ("127.0.0.1", "localhost"):
                try:                       # dalla rete: indirizzo IP diretto, o nome .local del computer
                    ipaddress.ip_address(host)
                    return True
                except ValueError:
                    if host.endswith(".local") or host.endswith(".lan"):
                        return True
            self._json({"errore": "host non ammesso"}, HTTPStatus.FORBIDDEN)
            return False

        def do_GET(self):
            if not self._host_ok():
                return
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            if self._blocca_se_serve(u.path):
                return
            if u.path == "/esci":
                from .accesso import NOME_COOKIE
                return self._html("", cookie=f"{NOME_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict", vai="/")
            try:
                with app._lock_indice.leggi():
                    return self._get(u, q)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except FileNotFoundError as ex:
                self._json({"errore": str(ex)}, HTTPStatus.NOT_FOUND)
            except Exception as ex:  # errore leggibile invece di una pagina vuota
                try:
                    self._json({"errore": self._messaggio(ex)}, HTTPStatus.INTERNAL_SERVER_ERROR)
                except Exception:
                    pass

        def _messaggio(self, ex: Exception) -> str:
            """Dalla rete niente dettagli interni (percorsi, moduli): solo il tipo di errore."""
            return str(ex) if not self._remoto() else f"errore interno ({type(ex).__name__})"

        def _get(self, u, q):
            if u.path == "/api/info":
                info = app.indice.info()
                info["firma"] = FIRMA_AVVIO
                info["codice"] = str(Path(__file__).resolve().parent.parent)   # cartella di Labellula in uso
                rete = app.rete(not self._remoto())
                info["rete"] = rete
                info["riavvio_necessario"] = firma_codice() != FIRMA_AVVIO or rete["attiva"] != rete["configurata"]
                info["significato"] = app.semantico is not None
                info.update(app.info_pubblica())
                return self._json(info)
            if u.path == "/api/filtri":
                return self._json(app.indice.valori_filtri())
            if u.path == "/api/statistiche":
                return self._json(app.indice.statistiche())
            if u.path == "/api/cerca":
                return self._json(app.indice.cerca(_filtri(q), pagina=int(q.get("pagina", 1)),
                                                   semantico=app.semantico, modo=q.get("modo", "misto")))
            if u.path == "/api/simili":
                if app.semantico is None:
                    return self._json({"errore": "ricerca per significato non attiva"}, HTTPStatus.CONFLICT)
                r = app.indice.simili(q.get("id", ""), app.semantico)
                return self._json({"totale": len(r), "pagina": 1, "per_pagina": len(r), "modo": "simili",
                                   "risultati": r})
            if u.path == "/api/esporta.csv":
                righe = app.indice.tutte(_filtri(q), semantico=app.semantico, modo=q.get("modo", "misto"))
                buf = io.StringIO()
                w = csv.DictWriter(buf, fieldnames=CAMPI_CSV, extrasaction="ignore", delimiter=";")
                w.writeheader()
                w.writerows(righe)
                corpo = ("﻿" + buf.getvalue()).encode("utf-8")   # BOM: Excel riconosce l'UTF-8
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="labellula_risultati.csv"')
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)
                return
            if u.path == "/api/scheda":
                s = app.indice.scheda(q.get("id", ""))
                return self._json(s) if s else self._json({"errore": "non trovata"}, HTTPStatus.NOT_FOUND)
            if u.path == "/api/cartelle":
                from .lavori import elenca_cartelle
                percorso = q.get("percorso", "")
                if self._remoto():          # dalla rete si sfoglia solo l'archivio, non tutto il disco
                    percorso = percorso or str(app.radice)
                    if not app.nell_archivio(percorso):
                        return self._json({"errore": "dalla rete si vedono solo le cartelle dell'archivio"},
                                          HTTPStatus.FORBIDDEN)
                r = elenca_cartelle(percorso, app.estensioni,
                                    app.cfg["schede"]["cartella_txt"] if app.cfg else "_txt")
                if self._remoto() and Path(r["percorso"]).resolve() == app.radice:
                    r["padre"] = None
                return self._json(r)
            if u.path == "/api/conta":
                if not app.lavori:
                    return self._json({"errore": "lavori non disponibili"}, HTTPStatus.CONFLICT)
                if self._remoto() and not app.nell_archivio(q.get("percorso", "")):
                    return self._json({"errore": "dalla rete si lavora solo dentro l'archivio"},
                                      HTTPStatus.FORBIDDEN)
                percorso = Path(q.get("percorso", ""))
                risposta = app.lavori.conta(percorso, q.get("rifai") == "1", q.get("aggiorna") == "1")
                try:
                    percorso.resolve().relative_to(app.radice)
                    risposta["in_archivio"] = True
                except (ValueError, OSError):
                    risposta["in_archivio"] = False
                risposta["in_demo"] = app.info_pubblica().get("in_demo", False)
                return self._json(risposta)
            if u.path == "/api/modelli":
                from .lavori import modelli_visione
                return self._json({"attuale": app.cfg["modello"]["nome"] if app.cfg else "",
                                   "modelli": modelli_visione(app.cfg["modello"]["ollama_url"]) if app.cfg else []})
            if u.path == "/api/lavoro":
                return self._json(app.lavori.stato() if app.lavori else {"attivo": False})
            if u.path in ("/miniatura", "/foto"):
                p = app.percorso_foto(q.get("id", ""))
                if p is None:
                    return self._json({"errore": "foto non trovata"}, HTTPStatus.NOT_FOUND)
                if u.path == "/foto":
                    if p.suffix.lower() in (".heic", ".heif"):     # i browser (tranne Safari) non mostrano l'HEIC
                        return self._file(miniatura(p, app.cache, q["id"], 3000), "image/jpeg", cache_sec=86400)
                    return self._file(p)
                lato = 1600 if q.get("lato") == "1600" else 480  # (3000 solo per le HEIC "originali")
                return self._file(miniatura(p, app.cache, q["id"], lato), "image/jpeg", cache_sec=86400)
            # file statici dell'interfaccia
            nome = "index.html" if u.path in ("", "/") else u.path.lstrip("/")
            f = (WEB / nome).resolve()
            if f.parent == WEB.resolve() and f.is_file():
                return self._file(f)
            return self._json({"errore": "non trovato"}, HTTPStatus.NOT_FOUND)

        def do_POST(self):
            if not self._host_ok():
                return
            u0 = urlparse(self.path).path
            if u0 == "/accesso" and self._remoto():
                return self._accesso()
            if self._blocca_se_serve(u0):
                return
            if self.headers.get("X-Labellula") != "1":
                return self._json({"errore": "richiesta non ammessa"}, HTTPStatus.FORBIDDEN)
            if not app.lavori:
                return self._json({"errore": "lavori non disponibili"}, HTTPStatus.CONFLICT)
            try:
                n = int(self.headers.get("Content-Length") or 0)
                corpo = json.loads(self.rfile.read(n) or b"{}") if n else {}
                u = urlparse(self.path)
                if self._remoto() and u.path in SOLO_DA_QUESTO_COMPUTER:
                    return self._json({"errore": "si imposta solo dal computer con Labellula"}, HTTPStatus.FORBIDDEN)
                if u.path == "/api/lavoro":
                    if self._remoto() and not app.nell_archivio(str(corpo.get("cartella", ""))):
                        return self._json({"errore": "dalla rete si descrivono solo cartelle dell'archivio"},
                                          HTTPStatus.FORBIDDEN)
                    return self._json(app.lavori.avvia(str(corpo.get("cartella", "")), bool(corpo.get("rifai")),
                                                       int(corpo.get("limite") or 0), bool(corpo.get("aggiorna")),
                                                       str(corpo.get("modello") or ""), bool(corpo.get("a_lotti"))))
                if u.path == "/api/lavoro/ferma":
                    return self._json(app.lavori.ferma())
                if u.path == "/api/ollama/prova":
                    from .ollama_rete import prova
                    return self._json(prova(str(corpo.get("indirizzo", ""))))
                if u.path == "/api/ollama":
                    if app.lavori.stato().get("attivo"):
                        return self._json({"errore": "aspetta la fine del lavoro in corso"}, HTTPStatus.CONFLICT)
                    from .ollama_rete import applica
                    r = applica(app.cfg, str(corpo.get("indirizzo", "")), str(corpo.get("modello", "")))
                    if r.get("ok") and app.semantico is not None:   # anche la ricerca per significato usa quell'Ollama
                        from .semantico import ClientEmbedding
                        app.semantico.client = ClientEmbedding(r["url"], app.cfg["modello"]["embedding"])
                    return self._json(r)
                if u.path == "/api/lingua":
                    from .config import imposta_valore
                    from .descrizione import LINGUE
                    lingua = str(corpo.get("lingua", ""))
                    if lingua not in LINGUE:
                        return self._json({"errore": "lingua non disponibile"}, HTTPStatus.CONFLICT)
                    for sezione in ("descrizione", "interfaccia"):
                        app.cfg.dati.setdefault(sezione, {})["lingua"] = lingua
                        if app.cfg.file:
                            imposta_valore(app.cfg.file, sezione, "lingua", lingua)
                    return self._json({"ok": True, "lingua": lingua})
                if u.path == "/api/rete":
                    return self._json(self._imposta_rete(corpo))
                if u.path == "/api/archivio":
                    if app.lavori.stato().get("attivo"):
                        return self._json({"errore": "aspetta la fine del lavoro in corso"}, HTTPStatus.CONFLICT)
                    return self._json(app.cambia_archivio(str(corpo.get("radice", ""))))
                return self._json({"errore": "funzione non disponibile in questo server: chiudi e riapri Labellula"},
                                  HTTPStatus.NOT_FOUND)
            except (FileNotFoundError, RuntimeError, ValueError) as ex:
                return self._json({"errore": str(ex)}, HTTPStatus.CONFLICT)
            except Exception as ex:
                return self._json({"errore": self._messaggio(ex)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def _accesso(self):
            from urllib.parse import parse_qs as pq
            from .accesso import DURATA_SESSIONE, NOME_COOKIE, PAGINA_ACCESSO, verifica_password
            ip = self.client_address[0]
            n = min(int(self.headers.get("Content-Length") or 0), 4096)
            password = pq(self.rfile.read(n).decode("utf-8", "replace")).get("password", [""])[0]
            attesa = app.sessioni.attesa(ip)
            if attesa:
                return self._html(PAGINA_ACCESSO.format(errore=f"Troppi tentativi: riprova tra {attesa} secondi."),
                                  HTTPStatus.TOO_MANY_REQUESTS)
            memorizzata = (app.cfg["server"].get("password_hash") if app.cfg else "") or ""
            if memorizzata and verifica_password(password, memorizzata):
                app.sessioni.riuscito(ip)
                token = app.sessioni.crea()
                return self._html("", vai="/", cookie=f"{NOME_COOKIE}={token}; Path=/; Max-Age={DURATA_SESSIONE}; "
                                                    "HttpOnly; SameSite=Strict")
            app.sessioni.errore(ip)
            time.sleep(1)
            return self._html(PAGINA_ACCESSO.format(errore="Password sbagliata."), HTTPStatus.UNAUTHORIZED)

        def _imposta_rete(self, corpo: dict) -> dict:
            from .accesso import impronta, password_valida
            from .config import imposta_valore
            attiva = bool(corpo.get("attiva"))
            password = str(corpo.get("password") or "")
            s = app.cfg["server"]
            if attiva:
                if password:
                    motivo = password_valida(password)
                    if motivo:
                        return {"ok": False, "errore": motivo}
                    h = impronta(password)
                    s["password_hash"] = h
                    if app.cfg.file:
                        imposta_valore(app.cfg.file, "server", "password_hash", h)
                    app.sessioni.chiudi_tutte()
                elif not s.get("password_hash"):
                    return {"ok": False, "errore": "Scegli una password (almeno 8 caratteri)."}
            s["indirizzo"] = "0.0.0.0" if attiva else "127.0.0.1"
            if app.cfg.file:
                imposta_valore(app.cfg.file, "server", "indirizzo", s["indirizzo"])
            r = app.rete(True)
            r["ok"] = True
            r["riavvio"] = r["attiva"] != r["configurata"]
            return r

    return Handler


def avvia(app: Applicazione, indirizzo: str = "127.0.0.1", porta: int = 8765, apri_browser: bool = True):
    srv = ThreadingHTTPServer((indirizzo, porta), crea_handler(app))
    app.ascolto, app.porta = indirizzo, porta
    url = f"http://{'localhost' if indirizzo in ('127.0.0.1', '0.0.0.0') else indirizzo}:{porta}/"
    if indirizzo not in ("127.0.0.1", "localhost"):
        import socket
        app.host_extra |= {indirizzo, socket.gethostname().lower()}
        try:
            app.host_extra.add(socket.gethostbyname(socket.gethostname()))
        except OSError:
            pass
    print(f"Labellula è in ascolto su {url}  (Ctrl+C per fermare)", flush=True)
    if indirizzo != "127.0.0.1":
        from .accesso import indirizzi_locali
        con_password = bool(app.cfg and app.cfg["server"].get("password_hash"))
        print("Accesso dalla rete: " + ("attivo, con password. Dal telefono: "
              + ", ".join(f"http://{ip}:{porta}" for ip in indirizzi_locali()) if con_password
              else "il server ascolta sulla rete ma senza password nessuno può entrare."), flush=True)
    if apri_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nServer fermato.")
    finally:
        srv.server_close()
