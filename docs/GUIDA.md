# Guida di Labellula

Questa guida spiega come installare e usare Labellula da zero, passo per passo.
Va tenuta aggiornata a ogni modifica che cambia l'installazione o l'uso (vedi anche [CHANGELOG](../CHANGELOG.md)).

- [1. Cosa serve](#1-cosa-serve)
- [2. Installazione passo passo (anche se non hai mai usato GitHub)](#2-installazione-passo-passo-anche-se-non-hai-mai-usato-github): [Windows](#22-windows-10-e-11), [macOS](#23-macos), [Linux](#24-linux-ubuntu-debian-mint-e-simili)
- [3. Installazione a mano](#3-installazione-a-mano)
- [3bis. Usare la GPU di un altro computer](#3bis-usare-la-gpu-di-un-altro-computer-di-casa-o-dellufficio)
- [4. Configurazione](#4-configurazione)
- [5. Primo uso dalla pagina web](#5-primo-uso-dalla-pagina-web)
- [6. Uso dalla riga di comando](#6-uso-dalla-riga-di-comando)
- [7. Le schede](#7-le-schede)
- [8. Dare buoni nomi alle cartelle](#8-dare-buoni-nomi-alle-cartelle)
- [9. Aggiornare Labellula](#9-aggiornare-labellula)
- [10. Problemi frequenti](#10-problemi-frequenti)
- [11. Privacy e sicurezza](#11-privacy-e-sicurezza)
- [12. Modulo volti (facoltativo)](#12-modulo-volti-facoltativo)

---

## 1. Cosa serve

| | Minimo | Consigliato | Provato |
|---|---|---|---|
| Sistema | Windows 10/11, macOS 13+, Linux | | Windows 11 (macOS e Linux: installatore pronto, da provare) |
| Scheda video | NVIDIA con 8 GB, o Mac Apple Silicon con 16 GB di memoria | NVIDIA con 12 GB o più | RTX 3080 Ti 12 GB |
| Spazio su disco | ~10 GB per i modelli, più ~1 KB per scheda | SSD | |
| Software | Python 3.10+, Ollama | Git, exiftool | Python 3.11, Ollama 0.40 |

Tempi misurati su RTX 3080 Ti: **~4 s a foto con il prompt v4, ~6,5 s con il v5**, cioè circa 550 foto all'ora.
Senza scheda video Ollama funziona lo stesso, ma è molto più lento: adatto solo per provare poche foto.
**Se non hai una GPU adatta**, la descrizione delle foto è troppo lenta per un archivio vero: usa la GPU di un altro computer della rete (§3bis) oppure l'elaborazione remota a crediti (in preparazione), che sostiene ctrlalt.museum. La ricerca invece funziona su qualsiasi PC.

## 2. Installazione passo passo (anche se non hai mai usato GitHub)

Non serve un account GitHub e non serve saper programmare: bastano un browser e, per una volta, il terminale.

### 2.1 Scaricare Labellula (uguale per tutti)
1. Apri <https://github.com/dinobaldi/labellula>.
2. Clicca il pulsante verde **Code** e poi **Download ZIP**.
3. Apri la cartella **Download** ed estrai lo ZIP: compare la cartella **`labellula-main`**.
   - Windows: clic destro sullo ZIP › **Estrai tutto…** › **Estrai**.
   - macOS: doppio clic sullo ZIP.
   - Linux: clic destro › **Estrai qui** (oppure `unzip labellula-main.zip`).

Puoi spostare la cartella dove vuoi (per esempio in Documenti): basta farlo **prima** di installare.

### 2.2 Windows 10 e 11
1. Apri la cartella `labellula-main`. Se dentro ne trovi un'altra con lo stesso nome (succede con «Estrai tutto»), apri anche quella: sei nel posto giusto quando vedi il file **`Installa-Windows.cmd`** e la cartella `tools`.
2. **Doppio clic su `Installa-Windows.cmd`.** Si apre una finestra nera con le domande dell'installatore.
   - Se Windows mostra «Windows ha protetto il PC», clicca **Ulteriori informazioni** › **Esegui comunque**. Se chiede «Impossibile verificare l'autore», clicca **Esegui**. Succede con tutti i programmi scaricati da internet senza firma digitale.
   - Perché non lanciare direttamente `tools\installa.ps1`? Windows blocca gli script PowerShell scaricati da internet («l'esecuzione di script è disabilitata»). `Installa-Windows.cmd` dà il permesso solo a questa installazione, senza cambiare le impostazioni di sicurezza del PC.
3. Rispondi alle domande con **S** (sì) o **N** (no) e Invio. Se manca Python, l'installatore propone di installarlo.
4. Alla fine trovi **Labellula** sul desktop e si apre la pagina di ricerca.

### 2.3 macOS
1. Premi **⌘ + Spazio**, scrivi **Terminale** e premi Invio.
2. Scrivi (o incolla) e premi Invio:
   ```sh
   cd ~/Downloads/labellula-main
   ```
3. Poi:
   ```sh
   sh tools/installa.sh
   ```
4. Rispondi alle domande con **s** o **n** e Invio.
   - Se macOS propone di installare gli **Strumenti da riga di comando**, accetta e poi rilancia il comando del punto 3.
   - Se manca Python 3.10 o più recente, scaricalo da <https://www.python.org/downloads/macos/>, installalo e rilancia il punto 3.
5. Alla fine trovi **Labellula.command** sul desktop: doppio clic per aprire Labellula.

### 2.4 Linux (Ubuntu, Debian, Mint e simili)
1. Apri il **Terminale** (Ctrl + Alt + T).
2. Se non li hai già, installa Python e il modulo venv:
   ```sh
   sudo apt install python3 python3-venv python3-pip
   ```
3. Entra nella cartella e lancia l'installatore:
   ```sh
   cd ~/Downloads/labellula-main
   sh tools/installa.sh
   ```
4. Rispondi alle domande. L'installazione di Ollama chiede la password di amministratore.
5. Alla fine trovi **Labellula** nel menu delle applicazioni (e sul desktop, se c'è).

### 2.5 Cosa fa l'installatore, in breve
L'installatore chiede conferma prima di ogni cosa che scarica o installa:
   1. **Python**: se manca lo propone (Windows: winget; macOS: Homebrew) o spiega dove scaricarlo. Su macOS e Linux le librerie vanno in un ambiente separato `.venv`, senza toccare il Python di sistema.
   2. **Verifica dell'hardware** (`python -m labellula verifica --configura`): scheda video e memoria video, RAM, spazio libero nella cartella dei modelli di Ollama, Ollama già presente. Scrive in `config.yaml` il motore (`ollama` o `remoto`) e il modello adatto.
   3. **Solo se il computer è adatto**: installa Ollama (Windows: winget o l'installatore ufficiale; macOS: Homebrew o l'app da ollama.com; Linux: lo script ufficiale), scarica **solo** i modelli che servono (`python -m labellula modelli`) e fa una prova di velocità su una foto di esempio (`python -m labellula prova`).
   4. **Se il computer non è adatto**: niente download, motore impostato su "remoto". Se vuoi, puoi installare solo la ricerca per significato (Ollama più 1,2 GB, va bene anche senza GPU).
   5. Crea l'avvio con doppio clic (Windows: collegamento sul desktop; macOS: `Labellula.command` sul desktop; Linux: voce nel menu delle applicazioni) e apre Labellula.

### 2.6 Come decide la verifica

| Hardware | Verdetto | Modello |
|---|---|---|
| NVIDIA con 11 GB o più (RTX 3060 12 GB, 3080 Ti, 4070…) | adatto | `qwen3-vl:8b-instruct` (6,2 GB) |
| NVIDIA con 6–11 GB (RTX 3060 Ti 8 GB, 4060…) | al limite | `qwen3-vl:4b-instruct` (3,3 GB), schede meno ricche |
| Mac Apple Silicon (M1–M4) con 16 GB o più | adatto | `qwen3-vl:8b-instruct` |
| Mac Apple Silicon con 8 GB | al limite | `qwen3-vl:4b-instruct` |
| AMD Radeon recente con 8 GB o più (Windows o Linux con ROCm) | da provare | dipende dalla prova |
| Mac con processore Intel (anche con Radeon), schede con meno di 6 GB, nessuna GPU | non adatto | nessun download: elaborazione remota |

Inoltre servono almeno 8 GB di RAM e lo spazio per i modelli più 2 GB di margine. Le soglie sono prudenti: decide la **prova di velocità** (`python -m labellula prova`), che descrive davvero una foto e dice quante ore servono per 1.000 e per 10.000 foto. Riferimento: RTX 3080 Ti, 5,2 s a foto.

Il risultato resta in `dati/hardware.json` e si vede anche nella pagina, nella finestra **＋ Descrivi foto**.

## 3. Installazione a mano

<details><summary>Windows</summary>

```powershell
# Python 3.10+ da https://www.python.org/downloads/ (spunta "Add python.exe to PATH")
# Ollama da https://ollama.com/download
cd labellula
python -m pip install -r requirements.txt
python -m labellula verifica --configura      # dice se il PC è adatto e quale modello usare
python -m labellula modelli                   # scarica solo i modelli adatti
python -m labellula prova                     # velocità vera su una foto di esempio
python -m labellula server
```
exiftool (facoltativo) da <https://exiftool.org/>, rinominato `exiftool.exe` e messo nel PATH.
</details>

<details><summary>macOS e Linux</summary>

```sh
# Ollama: https://ollama.com/download  (Linux: curl -fsSL https://ollama.com/install.sh | sh)
cd labellula
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -r requirements.txt
python -m labellula verifica --configura
python -m labellula modelli
python -m labellula prova
sh tools/avvia_labellula.sh
```
exiftool: `brew install exiftool` (macOS) oppure `sudo apt install libimage-exiftool-perl` (Debian/Ubuntu).
</details>

## 3bis. Usare la GPU di un altro computer di casa o dell'ufficio

Hai un computer con una buona scheda video (per esempio un PC fisso con una RTX) e un altro senza (per esempio un portatile o un Mac con processore Intel)? Labellula sul secondo può far descrivere le foto all'Ollama del primo, nella stessa rete. Le schede, l'indice e la ricerca restano sul computer da cui lavori; al PC con la GPU arriva solo la copia ridotta delle foto, senza EXIF e GPS.

**Sul computer con la GPU** (una volta sola):
1. Installa Labellula o almeno Ollama e il modello: `ollama pull qwen3-vl:8b-instruct` e `ollama pull bge-m3`.
2. Fai ascoltare Ollama sulla rete:
   - Windows: imposta la variabile d'ambiente utente `OLLAMA_HOST` = `0.0.0.0` (in PowerShell: `setx OLLAMA_HOST 0.0.0.0`), poi esci e riapri Ollama dall'icona vicino all'orologio;
   - macOS: `launchctl setenv OLLAMA_HOST 0.0.0.0` e riapri Ollama;
   - Linux (servizio systemd): `sudo systemctl edit ollama` e aggiungi `[Service]` più `Environment="OLLAMA_HOST=0.0.0.0"`, poi `sudo systemctl restart ollama`.
3. Lascia passare la porta **11434** nel firewall, **solo** dal computer che la userà (Windows, PowerShell da amministratore):
   `New-NetFirewallRule -DisplayName "Ollama da Labellula" -Direction Inbound -Protocol TCP -LocalPort 11434 -RemoteAddress 192.168.1.30 -Action Allow`
   (al posto di 192.168.1.30 l'indirizzo dell'altro computer).
4. Annota l'indirizzo IP di questo computer: Windows `ipconfig` (riga "Indirizzo IPv4"), macOS e Linux `ip a` o Impostazioni › Rete.

**Sul computer senza GPU**, il modo più semplice è dalla pagina: **＋ Descrivi foto** › campo **Ollama su:** › scrivi l'indirizzo del computer con la GPU (per esempio `192.168.1.20`) › **Prova**. Compare la conferma, con la versione di Ollama e i modelli disponibili, oppure il motivo per cui non risponde. Se va bene, **Usa**: l'indirizzo viene salvato in `config.yaml` (con copia `.bak`) e vale anche per la ricerca per significato. Per tornare all'Ollama del tuo computer, svuota il campo e premi **Usa**.

Gli indirizzi su internet (pubblici) vengono segnalati: Ollama non ha password, quindi non va esposto su internet. Se il computer con la GPU è lontano, usa una VPN (Tailscale, WireGuard) e il suo indirizzo privato.

In alternativa, dal terminale, nella cartella di Labellula:
```sh
python -m labellula usa-ollama 192.168.1.20          # l'indirizzo del computer con la GPU
```
(su macOS e Linux: `.venv/bin/python -m labellula usa-ollama 192.168.1.20`). Il comando prova la connessione, elenca i modelli che vedono le immagini e aggiorna `config.yaml`. Poi riapri Labellula: nella finestra **＋ Descrivi foto** compare l'indirizzo dell'Ollama usato. Per tornare all'Ollama locale: `usa-ollama locale`.

**Attenzione.** Ollama non ha password: chiunque raggiunga la porta 11434 può usare la scheda video (e gestire i modelli). Per questo la regola del firewall va limitata al solo computer che serve, e mai su reti pubbliche. Le foto ridotte viaggiano in chiaro nella rete locale.

## 4. Configurazione

Al primo avvio `config.yaml` viene creato copiando `config.example.yaml` (Git non lo carica mai su GitHub: resta tuo).
La cartella delle foto si può scegliere dalla pagina (**＋ Descrivi foto › Imposta come archivio**) oppure a mano:

```yaml
archivio:
  radice: "D:/Foto"          # la cartella che contiene tutte le tue foto
```

Le voci più utili:

| Voce | A cosa serve |
|---|---|
| `archivio.estensioni` | formati delle foto: JPG, PNG e **HEIC/HEIF** (iPhone e molti Android; serve il pacchetto `pillow-heif`, installato dall'installatore). Le HEIC si vedono in tutti i browser: la pagina le converte al volo in JPEG |
| `archivio.salta_cartelle` | cartelle da non elaborare (nomi, senza maiuscole) |
| `descrizione.lingua` | lingua delle schede: `it`, `en`, `fr`, `de`, `es`; si cambia anche dal menu della lingua in alto nella pagina (vale per la pagina e per le nuove schede). Per riscrivere le schede esistenti nella nuova lingua: «＋ Descrivi foto» › «Aggiorna» |
| `descrizione.prompt` | `v5` (predefinito) o `v4` |
| `descrizione.contesto` | chi scatta e cosa fotografa di solito, in una frase. Aiuta il modello, ma lo condiziona: lascialo vuoto se l'archivio è vario |
| `descrizione.categorie` | l'elenco fisso di categorie tra cui il modello sceglie |
| `descrizione.luoghi_noti` | nomi delle tue cartelle che solo tu sai spiegare, es. `"Casa": "abitazione a Pavia"` |
| `server.indirizzo` | `127.0.0.1` = solo questo PC (consigliato) |
| `servizio.url_acquisto`, `servizio.url_donazioni` | link dei pulsanti dell'elaborazione remota e delle donazioni |
| `volti.attivo` | modulo volti, spento di default |

Anche la pagina web può cambiare `archivio.radice` (pulsante **Imposta come archivio**): prima salva una copia `config.yaml.bak-AAAAMMGG-hhmmss`.

## 5. Primo uso dalla pagina web

1. Avvia con il collegamento sul desktop, oppure `python -m labellula server`. Si apre <http://localhost:8765>.
   Al primo avvio Labellula crea da solo `config.yaml` (copiando l'esempio) e l'indice di ricerca, anche vuoto.
2. Clic su **＋ Descrivi foto**:
   - scegli la cartella (⬆ per salire, clic per entrare, oppure scrivi il percorso e **Vai**);
   - **Conta le foto** dice quante foto mancano e quanto tempo serve;
   - spunta **Prova: solo le prime 20 foto** e premi **Avvia la descrizione**.
3. La barra gialla mostra l'avanzamento: foto in corso, modello e versione del prompt, ultima scheda scritta, tempo che manca. **Ferma** si ferma alla foto successiva: rilanciando, si riparte da dove eri.
   - **Modello**: si sceglie tra i modelli di Ollama installati che sanno guardare le immagini; ogni scheda riporta il modello che l'ha scritta (lo vedi anche nel piè di pagina della ricerca).
   - **Aggiorna**: riscrive solo le schede fatte con un prompt più vecchio. **A lotti**: una sottocartella alla volta, con la ricerca aggiornata dopo ognuna; consigliato per gli archivi grandi.
   - Durante un lavoro Windows non va in sospensione (senza cambiare le impostazioni del risparmio energetico).
4. Alla fine la ricerca si aggiorna da sola. Se la cartella è fuori dall'archivio, **Imposta come archivio**.
5. Cerca. Clic su una foto: scheda completa, **Foto simili**, **Stessa cartella**, **Copia scheda**; frecce ← → per scorrere.
6. Altri strumenti: **Solo da verificare** (schede con dubbi del modello), **☆ Salva ricerca**, **Esporta CSV**, **?** per l'aiuto.

## 6. Uso dalla riga di comando

```powershell
python -m labellula descrivi --limite 20      # prova su 20 foto dell'archivio
python -m labellula descrivi                  # tutto l'archivio (si interrompe con Ctrl+C e si riprende)
python -m labellula descrivi --cartella "D:/Foto/2024"   # solo una cartella
python -m labellula descrivi --aggiorna       # riscrive solo le schede fatte con un prompt più vecchio (riprende da dove era)
python -m labellula descrivi --rifai          # riscrive tutte le schede
python -m labellula descrivi --modello gemma3:12b --limite 20   # prova un altro modello Ollama con la visione
python -m labellula indicizza                 # indice per parole (secondi)
python -m labellula vettori                   # ricerca per significato (GPU; poi solo le schede nuove)
python -m labellula server [--porta 8765] [--non-aprire]
```
Tutti i comandi accettano `--config altro.yaml`. Gli errori finiscono in `dati/descrizione_errori.log`,
le schede in cui il modello si è ripetuto in `dati/descrizione_da_verificare.txt`.

## 7. Le schede

Per `D:/Foto/2024/2024-02-04 gara karate Torino/DSCF4846.JPG` la scheda è
`D:/Foto/2024/2024-02-04 gara karate Torino/_txt/DSCF4846.txt`:

```
TITOLO: Gara di karate a Torino con bambini e allenatori
DESCRIZIONE: ...
TESTI VISIBILI: ...
LUOGO E PERIODO: Torino, Provincia di Torino, Piemonte (dalla cartella); 4 febbraio 2024, pomeriggio (da EXIF)
OCCASIONE: gara di karate (dalla cartella)
CATEGORIA: famiglia-e-amici
PERSONE: ...
ASPETTI FOTOGRAFICI: ...
PAROLE CHIAVE: ...
DUBBI: nessuno

---
File: DSCF4846.JPG
Data: 04/02/2024 15:12 (da EXIF)
Fotocamera: FUJIFILM X-T4
Indizi dalle cartelle: data 04/02/2024 (confermata dall'EXIF); luogo Torino, ... (presunto)
Generato con: qwen3-vl:8b-instruct (prompt v5)
```

- Le schede sono testo semplice UTF-8: si possono leggere, correggere a mano e copiare con le foto.
- Ogni informazione su luogo e data riporta la fonte: EXIF, GPS, cartella, nome del file, immagine.
- Due foto con lo stesso nome ed estensione diversa nella stessa cartella (`IMG_1.jpg`, `IMG_1.png`) condividono il nome della scheda: oggi la seconda viene saltata e segnalata.

## 8. Dare buoni nomi alle cartelle

Il modello legge i nomi delle cartelle e Labellula li **verifica** prima di passarglieli:
- **data**: `2024-02-04`, `20240204`, `2024-02` o `2024` all'inizio del nome; confrontata con la data EXIF
  (stesso giorno = confermata; fino a 45 giorni dopo o 15 prima = coerente; altrimenti in contrasto);
- **luogo**: nomi di località con l'iniziale maiuscola (`Torino`, `Castel San Giovanni`, `Ginevra`), cercati in un elenco
  offline di circa 145.000 località e confrontati con il GPS (entro 30 km = confermato);
- **evento e persone**: il resto del nome (`gara karate`, `compleanno Anna`) arriva al modello come informazione presunta.

Esempi efficaci: `2024/2024-08-11 vacanza Olanda Belgio Francia/2024-08-23 Ginevra/`, `2022-03-19 gara ciclistica Milano Sanremo`.
I nomi che nessun elenco conosce (`Casa`, il nome di un'azienda) si spiegano in `luoghi_noti`.

## 9. Aggiornare Labellula

```powershell
cd labellula
git pull
python -m pip install -r requirements.txt
python -m labellula indicizza
```
Le schede già scritte restano valide: le versioni nuove del prompt si applicano solo con `--rifai`.

## 10. Problemi frequenti

| Problema | Soluzione |
|---|---|
| "Ollama non risponde" | avvia Ollama (menu Start) e riprova; verifica con `ollama list` |
| "Modello non trovato" | `ollama pull qwen3-vl:8b-instruct` |
| La pagina non si apre | guarda `dati\server_errori.log`; la porta 8765 potrebbe essere occupata: `--porta 8766` |
| "Indice non trovato" | `python -m labellula indicizza` |
| Ricerca per significato non disponibile | `ollama pull bge-m3` e `python -m labellula vettori` |
| Molto lento | il modello sta girando sulla CPU: controlla la GPU con `ollama ps` (colonna PROCESSOR) |
| Le date sono sbagliate | l'orologio della fotocamera era sbagliato: la scheda lo segnala ("in contrasto") |
| Dopo un aggiornamento qualcosa «non è disponibile» o «non trovato» | è ancora aperta la versione precedente: chiudi e riapri Labellula con l'icona (lo fa da sola); in alternativa riavvia il computer |
| Qualcosa non va e non sai cosa | `python -m labellula diagnosi --cartella "percorso"` (su Mac e Linux `.venv/bin/python …`): elenca Python, Pillow, supporto HEIC, estensioni, archivio, Ollama, server aperto e quante foto di ogni formato ci sono nella cartella. Fotografa il risultato e mandalo |
| Le foto `.heic` non compaiono | rilancia l'installatore (aggiunge `pillow-heif`) e riapri Labellula. Sul Mac la libreria di Foto (`Libreria Foto.photoslibrary`) ha cartelle senza nomi utili: meglio esportare le foto in cartelle (Foto › File › Esporta) |
| Il modello vede sempre le stesse cose | togli o riduci `descrizione.contesto` |
| Voglio provare un altro modello | `ollama pull <nome>` di un modello con la visione (es. `gemma3:12b`, `qwen2.5vl:7b`), poi sceglilo in **Descrivi foto** o usa `--modello`; prova su 20 foto e confronta |

## 11. Privacy e sicurezza

- In locale le foto non lasciano mai il PC. Al modello arriva solo una copia ridotta (1344 px) **senza EXIF e GPS**.
- La pagina risponde solo a `localhost`. Le richieste che avviano lavori o cambiano la configurazione richiedono
  un'intestazione speciale e un Host locale, così un sito esterno aperto nel browser non può usarle.
- **Telefono e tablet**: dalla pagina, **? › Telefono e tablet**, scegli una password e premi *Attiva*; poi chiudi e riapri Labellula. Dal telefono, sulla stessa Wi-Fi, apri l'indirizzo che compare (per esempio `http://192.168.1.20:8765`) e inserisci la password. In alternativa: `python -m labellula rete attiva`.
  - Da questo computer la password non serve; dagli altri dispositivi sì, e senza password l'accesso resta chiuso.
  - La password è salvata solo come impronta (PBKDF2); dopo 5 tentativi sbagliati si aspetta sempre di più.
  - Le impostazioni di rete si cambiano solo dal computer con Labellula, non dal telefono.
  - Il collegamento nella rete di casa non è cifrato (http): non usarlo su reti pubbliche e non aprire la porta 8765 verso internet.
  - La prima volta il firewall di Windows o macOS chiede il permesso: consentilo sulle reti **private**.
- `config.yaml`, gli indici (`dati/`), le schede e i registri dei volti sono esclusi da Git.

## 12. Modulo volti (facoltativo)

Il riconoscimento dei volti è un modulo separato, spento di default, **non ancora incluso in questa versione**.
Quando c'è, la ricerca legge il registro `labellula_identita.json` nella radice dell'archivio se `volti.attivo: true`.
Attenzione alle licenze: alcuni pesi pre-addestrati per i volti sono solo per uso non commerciale (vedi [licenze](LICENZE.md)).
I dati biometrici sono dati particolari secondo il GDPR (art. 9): restano sempre sul tuo PC.
