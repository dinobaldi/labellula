# Avvia la ricerca di Labellula su Windows e apre il browser.
# 1) se il server non risponde già sulla porta 8765, lo avvia in background (finestra nascosta);
#    il log va in dati\server.log
# 2) aspetta che risponda (al primo avvio carica indice e vettori: qualche secondo)
# 3) apre http://localhost:8765 nel browser predefinito
# Per fermare il server: Gestione attività > python.exe, oppure
#   Get-NetTCPConnection -LocalPort 8765 -State Listen | % { Stop-Process -Id $_.OwningProcess }
# Per Ollama (ricerca per significato) serve che Ollama sia in esecuzione; senza, funziona la ricerca per parole.

$porta = 8765
$indirizzo = "http://localhost:$porta/"
$radice = Split-Path -Parent $PSScriptRoot          # cartella del repository
$config = Join-Path $radice "config.yaml"
# se config.yaml manca, il server lo crea copiando config.example.yaml

function Test-Labellula {
    # 127.0.0.1 e non localhost: Windows PowerShell prova prima ::1 (IPv6) e va in timeout
    try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://127.0.0.1:$porta/api/info" | Out-Null; return $true }
    catch { return $false }
}

# Se il server aperto è di una versione precedente (programma aggiornato nel frattempo), lo chiudo e lo riapro
try {
    $info = Invoke-RestMethod -TimeoutSec 2 "http://127.0.0.1:$porta/api/info"
    # ...o se gira da un'altra cartella: per esempio Labellula riscaricata ed estratta in un posto nuovo
    $altraCartella = $info.codice -and ((Resolve-Path $radice).Path.TrimEnd('\') -ne ([string]$info.codice).TrimEnd('\'))
    if ($info.riavvio_necessario -or -not $info.firma -or $altraCartella) {
        Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
        Start-Sleep 1
    }
} catch { }

if (-not (Test-Labellula)) {
    $python = (Get-Command python -ErrorAction Stop).Source
    $dati = Join-Path $radice "dati"
    New-Item -ItemType Directory -Force $dati | Out-Null
    Start-Process -WindowStyle Hidden -WorkingDirectory $radice -FilePath $python `
        -ArgumentList @("-m", "labellula", "server", "--config", "`"$config`"", "--non-aprire") `
        -RedirectStandardOutput (Join-Path $dati "server.log") -RedirectStandardError (Join-Path $dati "server_errori.log")
    for ($i = 0; $i -lt 60 -and -not (Test-Labellula); $i++) { Start-Sleep -Milliseconds 500 }
    if (-not (Test-Labellula)) {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show("Labellula non si è avviata. Guarda $dati\server_errori.log", "Labellula") | Out-Null
        exit 1
    }
}
Start-Process $indirizzo
