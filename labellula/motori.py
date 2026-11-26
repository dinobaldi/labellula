"""Motori di descrizione: chi guarda la foto e scrive il testo.

Un motore riceve la copia ridotta (JPEG senza metadati) e il prompt, e restituisce il testo.
Oggi c'è il motore Ollama locale; il motore remoto (servizio di labellizzazione) avrà la stessa forma.

    class Motore:
        nome: str            # es. "qwen3-vl:8b-instruct"
        locale: bool         # True = la foto non lascia il PC
        def controlla(self) -> None: ...                       # solleva ErroreMotore se non è pronto
        def descrivi(self, jpeg: bytes, prompt: str, ripetizioni: float = 1.1, lunghezza: int = 900) -> Risposta: ...
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass

import requests


class ErroreMotore(RuntimeError):
    pass


@dataclass
class Risposta:
    testo: str
    troncata: bool = False      # il modello ha esaurito i token


class MotoreOllama:
    locale = True

    def __init__(self, url: str, modello: str, timeout: int = 600):
        self.url = url.rstrip("/")
        self.nome = modello
        self.timeout = timeout

    def controlla(self) -> None:
        try:
            tags = requests.get(f"{self.url}/api/tags", timeout=5).json()
        except Exception:
            raise ErroreMotore("Ollama non risponde: avvialo (icona vicino all'orologio) e riprova.")
        nomi = [m["name"] for m in tags.get("models", [])]
        if self.nome not in nomi:
            raise ErroreMotore(f"Modello '{self.nome}' non trovato in Ollama (ollama pull {self.nome}). "
                               f"Presenti: {', '.join(nomi) or 'nessuno'}")

    def descrivi(self, jpeg: bytes, prompt: str, ripetizioni: float = 1.1, lunghezza: int = 900) -> Risposta:
        r = requests.post(
            f"{self.url}/api/chat",
            json={
                "model": self.nome, "stream": False, "keep_alive": "30m",
                "options": {"temperature": 0.2, "num_ctx": 8192, "num_predict": lunghezza,
                            "repeat_penalty": ripetizioni, "repeat_last_n": 256},
                "messages": [{"role": "user", "content": prompt,
                              "images": [base64.b64encode(jpeg).decode()]}],
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        j = r.json()
        testo = re.sub(r"<think>.*?</think>", "", j["message"]["content"], flags=re.S).strip()
        return Risposta(testo, j.get("done_reason") == "length")


def crea_motore(cfg) -> MotoreOllama:
    m = cfg["modello"]
    tipo = m.get("motore", "ollama")
    if tipo == "ollama":
        return MotoreOllama(m["ollama_url"], m["nome"])
    if tipo == "remoto":
        raise ErroreMotore("Questo computer è impostato per l'elaborazione remota a crediti, che è in preparazione. "
                           "Intanto la ricerca funziona; per descrivere in locale serve una scheda video adatta "
                           "(python -m labellula verifica).")
    raise ErroreMotore(f"Motore '{tipo}' non disponibile (per ora solo 'ollama').")
