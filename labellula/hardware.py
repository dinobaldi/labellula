"""Verifica dell'hardware: questo computer può descrivere le foto in locale con Ollama?

    python -m labellula verifica            # rapporto leggibile
    python -m labellula verifica --json     # per gli installatori

Funziona su Windows, macOS e Linux senza librerie in più: legge le informazioni con i comandi del sistema
(nvidia-smi, rocm-smi, system_profiler, sysctl, /proc, PowerShell). Non installa e non scarica niente.

Il verdetto è prudente: in caso di dubbio dice "da provare" e suggerisce `python -m labellula prova`,
che descrive davvero una foto di esempio e misura il tempo.
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

GB = 1024 ** 3

# Modelli consigliati per fascia di memoria video (GB), dal più grande al più piccolo.
MODELLI = [
    {"nome": "qwen3-vl:8b-instruct", "disco_gb": 6.2, "vram_gb": 11, "nota": "qualità piena (provato: RTX 3080 Ti 12 GB, ~8 s a foto)"},
    {"nome": "qwen3-vl:4b-instruct", "disco_gb": 3.3, "vram_gb": 6, "nota": "più piccolo: schede meno ricche di dettagli"},
]
EMBEDDING = {"nome": "bge-m3", "disco_gb": 1.2, "nota": "ricerca per significato; va bene anche senza GPU"}
OLLAMA_GB = 2.0          # spazio occupato dal programma Ollama (circa)
RAM_MINIMA_GB = 8


@dataclass
class Scheda:
    nome: str
    marca: str                 # nvidia, amd, apple, intel, altro
    vram_gb: float | None      # memoria video (per Apple Silicon: memoria unificata)
    usabile_da_ollama: bool | None = None   # None = da provare


@dataclass
class Rapporto:
    sistema: str = ""
    versione: str = ""
    architettura: str = ""
    cpu: str = ""
    ram_gb: float = 0.0
    disco_libero_gb: float = 0.0
    cartella_modelli: str = ""
    schede: list[Scheda] = field(default_factory=list)
    ollama_installato: bool = False
    ollama_attivo: bool = False
    modelli_presenti: list[str] = field(default_factory=list)
    verdetto: str = ""         # "ok", "limite", "da_provare", "insufficiente"
    modello_consigliato: str = ""
    da_scaricare_gb: float = 0.0
    motivi: list[str] = field(default_factory=list)
    consiglio: str = ""

    def json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


# ------------------------------------------------------------------ esecuzione dei comandi
def _esegui(cmd: list[str], timeout: int = 20) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


# ------------------------------------------------------------------ memoria e disco
def ram_gb(esegui=_esegui) -> float:
    s = platform.system()
    try:
        if s == "Windows":
            import ctypes

            class MEM(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MEM(); m.dwLength = ctypes.sizeof(MEM)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return round(m.ullTotalPhys / GB, 1)
        if s == "Darwin":
            return round(int(esegui(["sysctl", "-n", "hw.memsize"]).strip() or 0) / GB, 1)
        with open("/proc/meminfo", encoding="utf-8") as f:
            for riga in f:
                if riga.startswith("MemTotal:"):
                    return round(int(riga.split()[1]) * 1024 / GB, 1)
    except Exception:
        pass
    return 0.0


def cartella_modelli() -> Path:
    if os.environ.get("OLLAMA_MODELS"):
        return Path(os.environ["OLLAMA_MODELS"])
    if platform.system() == "Linux" and Path("/usr/share/ollama/.ollama").exists():
        return Path("/usr/share/ollama/.ollama/models")      # installazione di sistema su Linux
    return Path.home() / ".ollama" / "models"


def disco_libero_gb(cartella: Path) -> float:
    p = cartella
    while not p.exists() and p.parent != p:
        p = p.parent
    try:
        return round(shutil.disk_usage(p).free / GB, 1)
    except OSError:
        return 0.0


# ------------------------------------------------------------------ schede video
def schede_nvidia(esegui=_esegui) -> list[Scheda]:
    out = esegui(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
    schede = []
    for riga in out.strip().splitlines():
        parti = [x.strip() for x in riga.split(",")]
        if len(parti) == 2 and parti[1].replace(".", "").isdigit():
            schede.append(Scheda(parti[0], "nvidia", round(float(parti[1]) / 1024, 1), True))
    return schede


def schede_mac(esegui=_esegui) -> list[Scheda]:
    cpu = esegui(["sysctl", "-n", "machdep.cpu.brand_string"]).strip()
    if platform.machine() == "arm64" or cpu.startswith("Apple"):
        # Apple Silicon: la GPU usa la memoria unificata e Ollama la sfrutta (Metal)
        return [Scheda(cpu or "Apple Silicon", "apple", ram_gb(esegui), True)]
    schede = []
    try:
        dati = json.loads(esegui(["system_profiler", "SPDisplaysDataType", "-json"], timeout=40) or "{}")
    except ValueError:
        dati = {}
    for g in dati.get("SPDisplaysDataType", []):
        nome = g.get("sppci_model", "scheda video")
        vram = g.get("spdisplays_vram") or g.get("spdisplays_vram_shared") or ""
        m = re.search(r"([\d.]+)\s*(GB|MB)", vram)
        gb = (float(m.group(1)) / (1024 if m.group(2) == "MB" else 1)) if m else None
        marca = "amd" if re.search(r"AMD|Radeon", nome, re.I) else "intel" if "Intel" in nome else "altro"
        # Sui Mac con processore Intel Ollama non usa la GPU: lavora solo con la CPU
        schede.append(Scheda(nome, marca, round(gb, 1) if gb else None, False))
    return schede


def schede_amd_linux(esegui=_esegui) -> list[Scheda]:
    schede = []
    for f in sorted(Path("/sys/class/drm").glob("card*/device/mem_info_vram_total")):
        try:
            gb = int(f.read_text().strip()) / GB
        except (OSError, ValueError):
            continue
        nome = "AMD Radeon"
        try:
            nome = (f.parent / "product_name").read_text().strip() or nome
        except OSError:
            pass
        rocm = bool(shutil.which("rocm-smi")) or Path("/opt/rocm").exists()
        schede.append(Scheda(nome, "amd", round(gb, 1), True if rocm and gb >= 7.5 else None))
    return schede


def schede_windows_altre(esegui=_esegui) -> list[Scheda]:
    """Schede non NVIDIA su Windows (AMD, Intel). La memoria si legge dal registro (qwMemorySize),
    perché AdapterRAM di WMI si ferma a 4 GB."""
    ps = ("Get-ItemProperty 'HKLM:\\SYSTEM\\ControlSet001\\Control\\Class\\{4d36e968-e325-11ce-bfc1-08002be10318}\\0*' "
          "-ErrorAction SilentlyContinue | ForEach-Object { \"$($_.DriverDesc)|$($_.'HardwareInformation.qwMemorySize')\" }")
    out = esegui(["powershell", "-NoProfile", "-Command", ps])
    schede = []
    for riga in out.strip().splitlines():
        nome, _, mem = riga.partition("|")
        if not nome or re.search(r"NVIDIA|Microsoft Basic|Remote|Virtual", nome, re.I):
            continue
        gb = round(int(mem) / GB, 1) if mem.strip().isdigit() else None
        marca = "amd" if re.search(r"AMD|Radeon", nome, re.I) else "intel" if "Intel" in nome else "altro"
        # Ollama su Windows usa solo alcune Radeon recenti (ROCm): va provato
        schede.append(Scheda(nome.strip(), marca, gb, None if marca == "amd" and (gb or 0) >= 7.5 else False))
    return schede


def trova_schede(esegui=_esegui) -> list[Scheda]:
    s = platform.system()
    if s == "Darwin":
        return schede_mac(esegui)
    schede = schede_nvidia(esegui) if shutil.which("nvidia-smi") or s == "Windows" else []
    if s == "Windows":
        schede += schede_windows_altre(esegui)
    elif s == "Linux":
        schede += schede_amd_linux(esegui)
    return schede


# ------------------------------------------------------------------ Ollama
def stato_ollama(url: str = "http://localhost:11434") -> tuple[bool, bool, list[str]]:
    installato = bool(shutil.which("ollama")) or any(Path(p).exists() for p in (
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"), "/Applications/Ollama.app",
        "/usr/local/bin/ollama", "/usr/bin/ollama"))
    try:
        import requests
        modelli = [m["name"] for m in requests.get(f"{url}/api/tags", timeout=3).json().get("models", [])]
        return True, True, modelli
    except Exception:
        return installato, False, []


def _risponde(url: str) -> bool:
    try:
        import requests
        return requests.get(f"{url}/api/version", timeout=2).ok
    except Exception:
        return False


def avvia_ollama(url: str = "http://localhost:11434", attesa: float = 45, popen=subprocess.Popen,
                 risponde=_risponde, dormi=None) -> bool:
    """Se l'Ollama di questo computer è installato ma spento, lo avvia e aspetta che risponda.

    Serve subito dopo l'installazione (winget installa Ollama ma non sempre lo avvia) e dopo un riavvio
    se l'avvio automatico è disattivato. Non tocca un Ollama remoto.
    """
    import time
    dormi = dormi or time.sleep
    if risponde(url):
        return True
    if not re.match(r"https?://(localhost|127\.0\.0\.1|\[::1\])(:|/|$)", url):
        return False
    app_win = Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"))
    if platform.system() == "Windows" and app_win.exists():
        comando = [str(app_win)]                      # l'app con il lama vicino all'orologio
    elif platform.system() == "Darwin" and Path("/Applications/Ollama.app").exists():
        comando = ["open", "-a", "Ollama"]
    elif shutil.which("ollama"):
        comando = [shutil.which("ollama"), "serve"]
    else:
        return False
    print("Ollama è installato ma spento: lo avvio…", flush=True)
    opzioni = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "stdin": subprocess.DEVNULL}
    if platform.system() == "Windows":
        opzioni["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        opzioni["start_new_session"] = True
    try:
        popen(comando, **opzioni)
    except OSError:
        return False
    passi = int(attesa)
    for _ in range(passi):
        if risponde(url):
            print("Ollama è pronto.", flush=True)
            return True
        dormi(1)
    print("Ollama non risponde: aprilo dal menu Start (o da Applicazioni sul Mac) e riprova.", flush=True)
    return False


# ------------------------------------------------------------------ verdetto
def valuta(r: Rapporto) -> Rapporto:
    """Decide cosa fare con questo computer. Le soglie sono prudenti e vanno confermate con `prova`."""
    migliore = max((s for s in r.schede if s.usabile_da_ollama is not False and s.vram_gb),
                   key=lambda s: s.vram_gb, default=None)
    r.motivi = []
    if r.ram_gb and r.ram_gb < RAM_MINIMA_GB:
        r.motivi.append(f"memoria RAM di {r.ram_gb} GB: ne servono almeno {RAM_MINIMA_GB}")
    if migliore is None:
        if any(s.marca in ("amd", "intel") and s.usabile_da_ollama is False for s in r.schede) and r.sistema == "Darwin":
            r.motivi.append("Mac con processore Intel: Ollama non usa la scheda video, solo il processore")
        elif r.schede:
            r.motivi.append("nessuna scheda video che Ollama possa usare (servono NVIDIA, Apple Silicon "
                            "o alcune AMD recenti)")
        else:
            r.motivi.append("nessuna scheda video adatta trovata")
    scelto = None
    if migliore is not None:
        for m in MODELLI:
            if migliore.vram_gb >= m["vram_gb"]:
                scelto = m
                break
        if scelto is None:
            r.motivi.append(f"{migliore.nome}: {migliore.vram_gb} GB di memoria video, ne servono almeno "
                            f"{MODELLI[-1]['vram_gb']}")
    if scelto:
        presenti = {x.removesuffix(":latest") for x in r.modelli_presenti}
        mancano = [m for m in (scelto, EMBEDDING) if m["nome"] not in presenti]
        r.da_scaricare_gb = round(sum(m["disco_gb"] for m in mancano) + (0 if r.ollama_installato else OLLAMA_GB), 1)
        if r.disco_libero_gb and r.disco_libero_gb < r.da_scaricare_gb + 2:
            r.motivi.append(f"spazio libero su disco {r.disco_libero_gb} GB: ne servono circa {r.da_scaricare_gb + 2}")
    if r.motivi and (scelto is None or any("RAM" in x or "disco" in x for x in r.motivi)):
        r.verdetto, r.modello_consigliato = "insufficiente", ""
        r.da_scaricare_gb = 0.0
        r.consiglio = ("Su questo computer la descrizione delle foto sarebbe troppo lenta: non scarichiamo i modelli. "
                       "Usa l'elaborazione remota a crediti (sostiene ctrlalt.museum). La ricerca funziona comunque in locale.")
        return r
    r.modello_consigliato = scelto["nome"]
    if migliore.usabile_da_ollama is None:
        r.verdetto = "da_provare"
        r.consiglio = (f"{migliore.nome} potrebbe funzionare con Ollama, ma non è garantito: installa e lancia "
                       "`python -m labellula prova` prima di descrivere tutto l'archivio.")
    elif scelto is MODELLI[0]:
        r.verdetto = "ok"
        r.consiglio = f"Questo computer può descrivere le foto in locale con {scelto['nome']}: {scelto['nota']}."
    else:
        r.verdetto = "limite"
        r.consiglio = (f"Si può lavorare in locale con il modello più piccolo {scelto['nome']} ({scelto['nota'].split(':')[0]}), "
                       "oppure usare l'elaborazione remota per la qualità piena.")
    return r


def verifica(url_ollama: str = "http://localhost:11434", esegui=_esegui) -> Rapporto:
    r = Rapporto(sistema=platform.system(), versione=platform.release(), architettura=platform.machine())
    if r.sistema == "Darwin":
        r.cpu = esegui(["sysctl", "-n", "machdep.cpu.brand_string"]).strip()
        r.versione = platform.mac_ver()[0] or r.versione
    elif r.sistema == "Linux":
        try:
            r.cpu = next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo", encoding="utf-8")
                          if l.startswith("model name")), "")
        except OSError:
            pass
    else:
        r.cpu = esegui(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor | Select-Object -First 1).Name"]).strip() or platform.processor()
        build = platform.version().split(".")[-1]
        if r.versione == "10" and build.isdigit() and int(build) >= 22000:
            r.versione = "11"                       # Windows 11 si presenta come "10" con build >= 22000
    r.ram_gb = ram_gb(esegui)
    cart = cartella_modelli()
    r.cartella_modelli, r.disco_libero_gb = str(cart), disco_libero_gb(cart)
    r.schede = trova_schede(esegui)
    r.ollama_installato, r.ollama_attivo, r.modelli_presenti = stato_ollama(url_ollama)
    return valuta(r)


ETICHETTE = {"ok": "ADATTO", "limite": "AL LIMITE", "da_provare": "DA PROVARE", "insufficiente": "NON ADATTO"}


def testo(r: Rapporto) -> str:
    nomi = {"Windows": "Windows", "Darwin": "macOS", "Linux": "Linux"}
    righe = [f"Sistema     : {nomi.get(r.sistema, r.sistema)} {r.versione} ({r.architettura})",
             f"Processore  : {r.cpu or 'non rilevato'}",
             f"Memoria RAM : {r.ram_gb} GB",
             f"Disco libero: {r.disco_libero_gb} GB (in {r.cartella_modelli})"]
    if r.schede:
        for s in r.schede:
            uso = {True: "usabile da Ollama", False: "non usabile da Ollama", None: "da provare"}[s.usabile_da_ollama]
            righe.append(f"Scheda video: {s.nome} – {s.vram_gb if s.vram_gb is not None else '?'} GB – {uso}")
    else:
        righe.append("Scheda video: nessuna rilevata")
    righe.append(f"Ollama      : {'attivo' if r.ollama_attivo else 'installato, non attivo' if r.ollama_installato else 'non installato'}"
                 + (f" (modelli: {', '.join(r.modelli_presenti)})" if r.modelli_presenti else ""))
    righe += ["", f"VERDETTO: {ETICHETTE.get(r.verdetto, r.verdetto)}"]
    righe += [f"  - {m}" for m in r.motivi]
    righe.append(r.consiglio)
    if r.modello_consigliato:
        righe.append(f"Modello consigliato: {r.modello_consigliato}; da scaricare circa {r.da_scaricare_gb} GB.")
    return "\n".join(righe)
