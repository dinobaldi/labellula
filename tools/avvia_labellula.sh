#!/usr/bin/env sh
# Avvia la ricerca di Labellula su macOS e Linux e apre il browser.
# Se il server risponde già sulla porta 8765 apre solo il browser; altrimenti lo avvia in background
# (log in dati/server.log). Per fermarlo:  kill $(cat dati/server.pid)
cd "$(dirname "$0")/.." || exit 1
PORTA=8765
CONFIG=config.yaml
# se config.yaml manca, il server lo crea copiando config.example.yaml
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=$(command -v python3 || command -v python); fi   # .venv creato da tools/installa.sh

risponde() { "$PY" -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:$PORTA/api/info', timeout=2)" 2>/dev/null; }

# Se il server aperto è di una versione precedente (programma aggiornato nel frattempo), lo chiudo e lo riapro
vecchio() { "$PY" -c "import json,sys,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:$PORTA/api/info', timeout=2)); import os; c=d.get('codice'); altra=bool(c) and os.path.realpath(c)!=os.path.realpath('.'); sys.exit(0 if d.get('riavvio_necessario') or not d.get('firma') or altra else 1)" 2>/dev/null; }
if risponde && vecchio; then
  echo "Chiudo la versione precedente di Labellula ancora aperta…"
  [ -f dati/server.pid ] && kill "$(cat dati/server.pid)" 2>/dev/null
  if command -v lsof >/dev/null 2>&1; then lsof -ti "tcp:$PORTA" -sTCP:LISTEN | xargs kill 2>/dev/null; fi
  sleep 1
fi

if ! risponde; then
  mkdir -p dati
  nohup "$PY" -m labellula server --config "$CONFIG" --non-aprire > dati/server.log 2>&1 &
  echo $! > dati/server.pid
  i=0
  while [ $i -lt 60 ] && ! risponde; do sleep 0.5; i=$((i + 1)); done
  risponde || { echo "Labellula non si è avviata: guarda dati/server.log"; exit 1; }
fi
URL="http://localhost:$PORTA/"
if command -v open >/dev/null 2>&1; then open "$URL"; else xdg-open "$URL" >/dev/null 2>&1 || echo "Apri $URL"; fi
