# Installatore di Labellula per Windows 10/11.
# Uso: doppio clic su "Installa-Windows.cmd" nella cartella di Labellula (avvia questo script).
#
# Cosa fa, chiedendo conferma prima di ogni cosa che scarica o installa:
#   1. controlla Python (3.10 o più recente) e installa le librerie di Labellula
#   2. controlla l'hardware: scheda video, memoria, spazio su disco (python -m labellula verifica)
#   3. solo se il PC è adatto: installa Ollama, scarica il modello giusto e fa una prova di velocità
#      se non è adatto: niente download inutili, si imposta l'elaborazione remota
#   4. crea il collegamento sul desktop e apre Labellula

$ErrorActionPreference = "Stop"
$radice = Split-Path -Parent $PSScriptRoot
Set-Location $radice
# I file estratti da uno ZIP scaricato portano il segno "scaricato da internet": lo tolgo ai soli file di
# Labellula, cosi collegamento e avvio non vengono bloccati (le impostazioni di Windows non cambiano).
Get-ChildItem -LiteralPath $radice -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue

function Scrivi-Titolo($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Chiedi-Si($domanda, $predefinito = $true) {
    $s = if ($predefinito) { "[S/n]" } else { "[s/N]" }
    $r = Read-Host "$domanda $s"
    if ([string]::IsNullOrWhiteSpace($r)) { return $predefinito }
    return $r.Trim().ToLower().StartsWith("s")
}
function Trova-Python {
    foreach ($c in @("python", "py")) {
        $cmd = Get-Command $c -ErrorAction SilentlyContinue
        if (-not $cmd -or $cmd.Source -like "*WindowsApps*") { continue }   # il finto python dello Store
        $v = & $c -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($v -and [version]$v -ge [version]"3.10") { return $cmd.Source }
    }
    return $null
}

Write-Host "Labellula – installazione per Windows" -ForegroundColor Green
Write-Host "Cartella: $radice"

# ------------------------------------------------------------------ 1. Python
Scrivi-Titolo "1. Python"
$python = Trova-Python
if (-not $python) {
    Write-Host "Python 3.10 o più recente non è installato."
    if ((Get-Command winget -ErrorAction SilentlyContinue) -and (Chiedi-Si "Lo installo con winget (Python 3.12, circa 30 MB)?")) {
        winget install --id Python.Python.3.12 -e
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
        $python = Trova-Python
    }
    if (-not $python) {
        Write-Host "Installa Python da https://www.python.org/downloads/ spuntando 'Add python.exe to PATH', poi rilancia questo script." -ForegroundColor Yellow
        exit 1
    }
}
Write-Host "Python: $python"
& $python -m pip install --disable-pip-version-check -q -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "Installazione delle librerie non riuscita." -ForegroundColor Red; exit 1 }
Write-Host "Librerie installate."
& $python -m pip install --disable-pip-version-check -q pillow-heif
if ($LASTEXITCODE -eq 0) { Write-Host "Supporto per le foto HEIC (iPhone) installato." }
else { Write-Host "ATTENZIONE: il supporto per le foto HEIC non si è installato; le JPG funzionano lo stesso." -ForegroundColor Yellow }

# ------------------------------------------------------------------ 2. Hardware
Scrivi-Titolo "Diagnosi"
& $python -m labellula diagnosi

Scrivi-Titolo "2. Verifica dell'hardware"
& $python -m labellula verifica --configura
$r = & $python -m labellula verifica --json | ConvertFrom-Json

# ------------------------------------------------------------------ 3. Ollama e modelli
Scrivi-Titolo "3. Modelli di intelligenza artificiale"
$adatto = $r.verdetto -in @("ok", "limite", "da_provare")
$ollamaPronto = $r.ollama_installato
if ($adatto) {
    if (-not $ollamaPronto) {
        if (Chiedi-Si "Installo Ollama, il programma gratuito che fa girare i modelli (circa 2 GB)?") {
            if (Get-Command winget -ErrorAction SilentlyContinue) {
                winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
            } else {
                $setup = Join-Path $env:TEMP "OllamaSetup.exe"
                Invoke-WebRequest -UseBasicParsing "https://ollama.com/download/OllamaSetup.exe" -OutFile $setup
                Start-Process $setup -Wait
            }
            $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
            Start-Sleep 5
            $ollamaPronto = [bool](Get-Command ollama -ErrorAction SilentlyContinue)
        }
    }
    if ($ollamaPronto) {
        if (Chiedi-Si "Scarico $($r.modello_consigliato) e il modello per la ricerca (circa $($r.da_scaricare_gb) GB)?") {
            & $python -m labellula modelli
            if ($LASTEXITCODE -eq 0 -and (Chiedi-Si "Faccio una prova di velocità su una foto di esempio (1-2 minuti)?")) {
                & $python -m labellula prova
            }
        }
    } else {
        Write-Host "Senza Ollama Labellula può solo cercare tra schede già fatte. Puoi installarlo più tardi rilanciando questo script."
    }
} else {
    Write-Host "Questo PC non è adatto a descrivere le foto in locale: non scarico i modelli (risparmi circa 8 GB)."
    Write-Host "Labellula è impostato per l'elaborazione remota a crediti (in preparazione), che sostiene ctrlalt.museum."
    if (Chiedi-Si "Vuoi comunque la ricerca per significato? Serve Ollama (2 GB) e un modello da 1,2 GB, va bene anche senza GPU." $false) {
        if (-not $ollamaPronto -and (Get-Command winget -ErrorAction SilentlyContinue)) { winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements }
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
        & $python -m labellula modelli --solo-ricerca
    }
}

# ------------------------------------------------------------------ 4. Collegamento e avvio
Scrivi-Titolo "4. Collegamento sul desktop"
if (Chiedi-Si "Creo il collegamento 'Labellula' sul desktop?") {
    $ws = New-Object -ComObject WScript.Shell
    $l = $ws.CreateShortcut("$([Environment]::GetFolderPath('Desktop'))\Labellula.lnk")
    $l.TargetPath = "powershell.exe"
    $l.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$radice\tools\avvia_labellula.ps1`""
    $l.WorkingDirectory = $radice
    $l.IconLocation = "$radice\docs\logo\labellula.ico,0"
    $l.Save()
    Write-Host "Collegamento creato."
}
Write-Host ""
Write-Host "Fatto. Apro Labellula: scegli la cartella con '+ Descrivi foto' e 'Imposta come archivio'." -ForegroundColor Green
& powershell -NoProfile -ExecutionPolicy Bypass -File "$radice\tools\avvia_labellula.ps1"
