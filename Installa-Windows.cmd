@echo off
rem Installatore di Labellula per Windows 10 e 11: doppio clic su questo file.
rem Avvia tools\installa.ps1. Windows blocca gli script PowerShell scaricati da internet:
rem il permesso dato qui vale solo per questa installazione e non cambia le impostazioni del PC.
title Installazione di Labellula
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\installa.ps1"
if errorlevel 1 (
  echo.
  echo L'installazione si e' fermata: leggi il messaggio qui sopra.
  echo Se non e' chiaro, copialo in una segnalazione su GitHub, scheda Issues.
  pause
)
