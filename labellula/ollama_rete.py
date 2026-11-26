"""Collegarsi all'Ollama di un altro computer: normalizzare l'indirizzo, provarlo, salvarlo in config.yaml.

Usato dal comando `python -m labellula usa-ollama` e dalla pagina web (finestra «Descrivi foto»).
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

PORTA = 11434


def normalizza(indirizzo: str) -> str:
    """'192.168.1.20' -> 'http://192.168.1.20:11434'; 'locale' -> 'http://localhost:11434'."""
    s = (indirizzo or "").strip().rstrip("/")
    if s.lower() in ("", "locale", "localhost", "questo computer"):
        return f"http://localhost:{PORTA}"
    if "://" not in s:
        s = "http://" + s
    u = urlparse(s)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError(f"Indirizzo non valido: {indirizzo}")
    host = f"[{u.hostname}]" if ":" in u.hostname else u.hostname
    return f"{u.scheme}://{host}:{u.port or PORTA}"


def tipo_rete(url: str) -> str:
    """'locale' (questo computer), 'privata' (casa, ufficio, VPN) o 'pubblica' (internet)."""
    host = urlparse(url).hostname or ""
    if host in ("localhost",):
        return "locale"
    try:
        ips = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            ips = {ipaddress.ip_address(x[4][0]) for x in socket.getaddrinfo(host, None)}
        except OSError:
            return "sconosciuta"
    if all(ip.is_loopback for ip in ips):
        return "locale"
    if all(ip.is_private or ip.is_link_local or not ip.is_global for ip in ips):   # 10.x, 172.16-31.x, 192.168.x, 100.64.x (VPN tipo Tailscale)
        return "privata"
    return "pubblica"


AVVISI = {
    "privata": "Ollama non ha password: chi è nella stessa rete può usarlo. Limita la porta 11434 nel firewall "
               "al solo computer che lo usa. Le foto ridotte viaggiano in chiaro nella rete locale.",
    "pubblica": "Indirizzo su internet: Ollama non ha password e le foto viaggerebbero in chiaro. Sconsigliato: "
                "usa una VPN (per esempio Tailscale o WireGuard) e l'indirizzo privato che ti dà, "
                "oppure l'elaborazione remota di Labellula.",
    "sconosciuta": "Non riesco a capire se l'indirizzo è nella rete locale o su internet.",
    "locale": "",
}


def prova(indirizzo: str, timeout: float = 5) -> dict:
    """Prova l'indirizzo senza cambiare niente. Restituisce un dizionario leggibile dalla pagina."""
    import requests
    from .lavori import modelli_visione
    try:
        url = normalizza(indirizzo)
    except ValueError as ex:
        return {"ok": False, "errore": str(ex)}
    rete = tipo_rete(url)
    try:
        versione = requests.get(f"{url}/api/version", timeout=timeout).json().get("version", "?")
    except Exception as ex:
        return {"ok": False, "url": url, "rete": rete, "avviso": AVVISI.get(rete, ""),
                "errore": f"Ollama non risponde su {url} ({type(ex).__name__}). Controlla che l'altro computer sia acceso, "
                          "nella stessa rete, con Ollama aperto alla rete (OLLAMA_HOST=0.0.0.0) e la porta 11434 libera nel firewall."}
    try:
        tutti = [m["name"] for m in requests.get(f"{url}/api/tags", timeout=timeout).json().get("models", [])]
    except Exception:
        tutti = []
    visione = modelli_visione(url)
    return {"ok": True, "url": url, "rete": rete, "versione": versione, "avviso": AVVISI.get(rete, ""),
            "modelli_visione": visione,
            "ricerca_significato": any(x.removesuffix(":latest") == "bge-m3" for x in tutti)}


def applica(cfg, url: str, modello: str = "") -> dict:
    """Salva l'indirizzo (e il modello) in config.yaml, con copia .bak, e aggiorna la configurazione in memoria."""
    from .config import imposta_valore
    r = prova(url)
    if not r["ok"]:
        return r
    nomi = [m["nome"] for m in r["modelli_visione"]]
    modello = modello if modello in nomi else (cfg["modello"]["nome"] if cfg["modello"]["nome"] in nomi
                                               else (nomi[0] if nomi else ""))
    if cfg.file:
        imposta_valore(cfg.file, "modello", "ollama_url", r["url"])
        if modello:
            imposta_valore(cfg.file, "modello", "nome", modello)
            imposta_valore(cfg.file, "modello", "motore", "ollama")
    cfg.dati["modello"]["ollama_url"] = r["url"]
    if modello:
        cfg.dati["modello"]["nome"] = modello
        cfg.dati["modello"]["motore"] = "ollama"
    r["modello"] = modello
    r["salvato"] = bool(cfg.file)
    if not modello:
        r["avviso"] = ("Su quel computer non c'è ancora un modello che vede le immagini: lì lancia "
                       "«ollama pull qwen3-vl:8b-instruct». " + r.get("avviso", "")).strip()
    return r
