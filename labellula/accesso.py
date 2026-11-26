"""Accesso dalla rete di casa (telefono, tablet, altri computer) protetto da password.

- Da questo computer (127.0.0.1) la pagina si usa senza password, come sempre.
- Dagli altri dispositivi serve la password: viene salvata in config.yaml solo come impronta PBKDF2-SHA256
  (mai in chiaro). Dopo l'accesso il browser riceve un cookie di sessione (HttpOnly, SameSite=Strict).
- Senza password impostata, l'accesso dalla rete resta chiuso anche se il server ascolta sulla rete.
- Troppi tentativi sbagliati dallo stesso indirizzo: attesa crescente.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import secrets
import socket
import threading
import time

ITERAZIONI = 310_000
DURATA_SESSIONE = 30 * 24 * 3600          # 30 giorni
NOME_COOKIE = "labellula_sessione"


def impronta(password: str, iterazioni: int = ITERAZIONI) -> str:
    sale = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(sale), iterazioni)
    return f"pbkdf2_sha256${iterazioni}${sale}${h.hex()}"


def verifica_password(password: str, memorizzata: str) -> bool:
    try:
        schema, it, sale, h = memorizzata.split("$")
        if schema != "pbkdf2_sha256":
            return False
        calcolata = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(sale), int(it))
        return hmac.compare_digest(calcolata.hex(), h)
    except (ValueError, AttributeError):
        return False


def password_valida(password: str) -> str:
    """'' se va bene, altrimenti il motivo."""
    if len(password) < 8:
        return "La password deve avere almeno 8 caratteri."
    if password.lower() in ("password", "12345678", "labellula", "qwertyui"):
        return "Questa password è troppo facile da indovinare."
    return ""


def e_locale(ip: str) -> bool:
    """Richiesta che arriva da questo stesso computer."""
    try:
        return ipaddress.ip_address(ip.split("%")[0]).is_loopback
    except ValueError:
        return False


def indirizzi_locali() -> list[str]:
    """Indirizzi IPv4 di questo computer nella rete di casa (per aprirlo dal telefono)."""
    trovati: list[str] = []
    try:                                       # l'interfaccia usata per uscire (non invia niente)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 9))
        trovati.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            trovati.append(info[4][0])
    except OSError:
        pass
    utili = []
    for ip in trovati:
        a = ipaddress.ip_address(ip)
        if not (a.is_loopback or a.is_link_local) and ip not in utili:
            utili.append(ip)
    return utili


class Sessioni:
    def __init__(self):
        self._lock = threading.Lock()
        self._sessioni: dict[str, float] = {}
        self._errori: dict[str, list[float]] = {}

    def crea(self) -> str:
        t = secrets.token_urlsafe(32)
        with self._lock:
            self._sessioni[t] = time.time() + DURATA_SESSIONE
        return t

    def valida(self, token: str | None) -> bool:
        if not token:
            return False
        with self._lock:
            scade = self._sessioni.get(token)
            if scade and scade > time.time():
                return True
            self._sessioni.pop(token, None)
            return False

    def chiudi_tutte(self) -> None:
        with self._lock:
            self._sessioni.clear()

    def attesa(self, ip: str) -> int:
        """Secondi da aspettare prima di un nuovo tentativo da questo indirizzo (0 = si può)."""
        with self._lock:
            recenti = [t for t in self._errori.get(ip, []) if t > time.time() - 900]
            self._errori[ip] = recenti
            if len(recenti) < 5:
                return 0
            pausa = min(300, 30 * 2 ** (len(recenti) - 5))
            return max(0, int(recenti[-1] + pausa - time.time()))

    def errore(self, ip: str) -> None:
        with self._lock:
            self._errori.setdefault(ip, []).append(time.time())

    def riuscito(self, ip: str) -> None:
        with self._lock:
            self._errori.pop(ip, None)


def leggi_cookie(intestazione: str | None) -> str | None:
    for parte in (intestazione or "").split(";"):
        nome, _, valore = parte.strip().partition("=")
        if nome == NOME_COOKIE:
            return valore
    return None


PAGINA_ACCESSO = """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Labellula – accesso</title>
<link rel="icon" type="image/svg+xml" href="marchio.svg">
<style>
:root {{ --s:#f6f5f1; --c:#fff; --t:#1f2328; --a:#0b7a75; --b:#dcd9d0; }}
@media (prefers-color-scheme: dark) {{ :root {{ --s:#15181c; --c:#1e2227; --t:#e6e6e6; --a:#3cbfb8; --b:#333a42; }} }}
body {{ margin:0; min-height:100vh; display:grid; place-items:center; background:var(--s); color:var(--t);
        font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
form {{ background:var(--c); border:1px solid var(--b); border-radius:12px; padding:28px 24px; width:min(360px, calc(100% - 32px)); }}
h1 {{ font-family:Georgia,serif; font-weight:400; color:var(--a); margin:0 0 4px; display:flex; align-items:center; gap:8px; }}
input, button {{ font:inherit; width:100%; padding:10px 12px; border-radius:8px; border:1px solid var(--b);
                 background:var(--c); color:var(--t); box-sizing:border-box; margin-top:10px; }}
button {{ background:var(--a); border-color:var(--a); color:#fff; cursor:pointer; }}
.err {{ color:#b3261e; min-height:1.5em; margin:8px 0 0; }} .nota {{ font-size:13px; opacity:.75; }}
</style></head><body>
<form method="post" action="/accesso">
  <h1><img src="marchio.svg" width="34" height="34" alt="">Labellula</h1>
  <p class="nota">Archivio fotografico su questo computer di casa. Inserisci la password.</p>
  <input type="password" name="password" autocomplete="current-password" autofocus required aria-label="Password">
  <button>Entra</button>
  <p class="err">{errore}</p>
</form></body></html>"""

PAGINA_CHIUSA = """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Labellula</title></head>
<body style="font:16px/1.5 system-ui,sans-serif;max-width:520px;margin:40px auto;padding:0 16px">
<h1 style="font-family:Georgia,serif;font-weight:400;color:#0b7a75">Labellula</h1>
<p>L'accesso dalla rete non è ancora attivo: sul computer con Labellula apri la pagina, poi
<b>? › Telefono e tablet</b>, e scegli una password.</p></body></html>"""
