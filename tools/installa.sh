#!/usr/bin/env sh
# Installatore di Labellula per macOS e Linux.
# Uso, dalla cartella di Labellula:   sh tools/installa.sh
#
# Cosa fa, chiedendo conferma prima di ogni cosa che scarica o installa:
#   1. controlla Python (3.10 o più recente), crea un ambiente .venv e installa le librerie
#   2. controlla l'hardware: scheda video, memoria, spazio su disco (python -m labellula verifica)
#   3. solo se il computer è adatto: installa Ollama, scarica il modello giusto e fa una prova di velocità
#      se non è adatto (per esempio un Mac con processore Intel): niente download inutili,
#      si imposta l'elaborazione remota
#   4. crea l'avvio con doppio clic e apre Labellula

set -e
cd "$(dirname "$0")/.."
RADICE=$(pwd)
SISTEMA=$(uname -s)

titolo() { printf '\n== %s ==\n' "$1"; }
chiedi() {   # chiedi "domanda" s|n  -> 0 = sì
  if [ "$2" = "n" ]; then suff="[s/N]"; else suff="[S/n]"; fi
  printf '%s %s ' "$1" "$suff"; read -r risposta || risposta=""
  [ -z "$risposta" ] && { [ "$2" != "n" ]; return; }
  case "$risposta" in [sSyY]*) return 0 ;; *) return 1 ;; esac
}

echo "Labellula – installazione per $SISTEMA"
echo "Cartella: $RADICE"

# ------------------------------------------------------------------ 1. Python
titolo "1. Python"
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PY=$(command -v "$c"); break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.10 o più recente non è installato."
  if [ "$SISTEMA" = "Darwin" ] && command -v brew >/dev/null 2>&1 && chiedi "Lo installo con Homebrew (brew install python)?"; then
    brew install python && PY=$(command -v python3)
  fi
  if [ -z "$PY" ]; then
    if [ "$SISTEMA" = "Darwin" ]; then echo "Installalo da https://www.python.org/downloads/macos/ e rilancia questo script."
    else echo "Installalo con il gestore pacchetti, per esempio: sudo apt install python3 python3-venv python3-pip"; fi
    exit 1
  fi
fi
echo "Python: $PY"
if [ ! -x .venv/bin/python ]; then                           # ambiente separato: non tocca il Python di sistema
  if ! "$PY" -m venv .venv; then
    rm -rf .venv
    echo ""
    echo "Non riesco a creare l'ambiente Python: manca il modulo venv."
    VER=$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
    if command -v apt >/dev/null 2>&1; then
      echo "Su Ubuntu, Debian e Mint installalo con:   sudo apt install python3-venv python3-pip   (oppure python$VER-venv)"
    elif command -v dnf >/dev/null 2>&1; then
      echo "Su Fedora installalo con:   sudo dnf install python3-pip"
    else
      echo "Installa il pacchetto venv di Python con il gestore pacchetti del sistema."
    fi
    echo "Poi rilancia:   sh tools/installa.sh"
    exit 1
  fi
fi
VPY="$RADICE/.venv/bin/python"
"$VPY" -m pip install --disable-pip-version-check -q -r requirements.txt
echo "Librerie installate in .venv"
if "$VPY" -m pip install --disable-pip-version-check -q pillow-heif; then
  echo "Supporto per le foto HEIC (iPhone) installato."
else
  echo "ATTENZIONE: il supporto per le foto HEIC non si è installato; le JPG funzionano lo stesso."
fi

# ------------------------------------------------------------------ 2. Hardware
titolo "Diagnosi"
"$VPY" -m labellula diagnosi || true

titolo "2. Verifica dell'hardware"
"$VPY" -m labellula verifica --configura || true
JSON=$("$VPY" -m labellula verifica --json || true)
campo() { printf '%s' "$JSON" | "$VPY" -c "import json,sys; print(json.load(sys.stdin).get('$1', ''))"; }
VERDETTO=$(campo verdetto)
MODELLO=$(campo modello_consigliato)
DA_SCARICARE=$(campo da_scaricare_gb)
OLLAMA=$(campo ollama_installato)

installa_ollama() {
  if [ "$SISTEMA" = "Darwin" ]; then
    if command -v brew >/dev/null 2>&1; then
      brew install ollama && (brew services start ollama || true)
    else
      echo "Scarica Ollama per Mac da https://ollama.com/download, aprilo una volta, poi rilancia questo script."
      open "https://ollama.com/download" 2>/dev/null || true
      return 1
    fi
  else
    if ! command -v curl >/dev/null 2>&1; then
      echo "Per installare Ollama serve curl: installalo (su Ubuntu e Debian: sudo apt install curl) e rilancia lo script."
      return 1
    fi
    echo "Uso l'installatore ufficiale di Ollama (https://ollama.com/install.sh): chiederà la password di amministratore."
    curl -fsSL https://ollama.com/install.sh | sh
  fi
  sleep 5
  command -v ollama >/dev/null 2>&1
}

# ------------------------------------------------------------------ 3. Ollama e modelli
titolo "3. Modelli di intelligenza artificiale"
case "$VERDETTO" in
  ok|limite|da_provare)
    if [ "$OLLAMA" != "True" ]; then
      if chiedi "Installo Ollama, il programma gratuito che fa girare i modelli (circa 2 GB)?"; then
        installa_ollama && OLLAMA=True || true
      fi
    fi
    if [ "$OLLAMA" = "True" ] && chiedi "Scarico $MODELLO e il modello per la ricerca (circa $DA_SCARICARE GB)?"; then
      if "$VPY" -m labellula modelli && chiedi "Faccio una prova di velocità su una foto di esempio (1-2 minuti)?"; then
        "$VPY" -m labellula prova || true
      fi
    fi
    ;;
  *)
    echo "Questo computer non è adatto a descrivere le foto in locale: non scarico i modelli (risparmi circa 8 GB)."
    echo "Labellula è impostato per l'elaborazione remota a crediti (in preparazione), che sostiene ctrlalt.museum."
    if chiedi "Vuoi comunque la ricerca per significato? Serve Ollama (2 GB) e un modello da 1,2 GB, va bene anche senza GPU." n; then
      { [ "$OLLAMA" = "True" ] || installa_ollama; } && "$VPY" -m labellula modelli --solo-ricerca || true
    fi
    ;;
esac

# ------------------------------------------------------------------ 4. Avvio con doppio clic
titolo "4. Avvio con doppio clic"
if chiedi "Creo l'avvio di Labellula sul desktop?"; then
  if [ "$SISTEMA" = "Darwin" ]; then
    F="$HOME/Desktop/Labellula.command"
    printf '#!/bin/sh\nsh "%s/tools/avvia_labellula.sh"\n' "$RADICE" > "$F"
    chmod +x "$F"
  else
    mkdir -p "$HOME/.local/share/applications"
    F="$HOME/.local/share/applications/labellula.desktop"
    cat > "$F" <<EOF
[Desktop Entry]
Type=Application
Name=Labellula
Comment=Catalogazione di archivi fotografici con l'AI
Exec=sh "$RADICE/tools/avvia_labellula.sh"
Icon=$RADICE/docs/logo/labellula-marchio-512.png
Terminal=false
Categories=Graphics;Photography;
EOF
    chmod +x "$F"
    [ -d "$HOME/Desktop" ] && cp "$F" "$HOME/Desktop/" 2>/dev/null || true
  fi
  echo "Creato: $F"
fi
echo ""
echo "Fatto. Apro Labellula: scegli la cartella con '+ Descrivi foto' e 'Imposta come archivio'."
sh "$RADICE/tools/avvia_labellula.sh"
