# Novità

Le modifiche che cambiano l'installazione o l'uso vanno annotate qui e nella [guida](docs/GUIDA.md).

## 0.2.1 (27/11/2026)

**Correzioni**
- Un lavoro che non riusciva a partire (per esempio con l'elaborazione remota, ancora in preparazione) restava «in corso» per sempre: «Descrivi foto», «Imposta come archivio» e il cambio di Ollama rispondevano «aspetta la fine del lavoro» fino al riavvio.
- «A lotti» saltava le foto che stanno direttamente nella cartella scelta, quando c'erano anche sottocartelle. Ora sono il primo lotto. Il limite («Prova: solo le prime 20 foto») vale per tutto il lavoro, non per ogni lotto, e con una cartella fuori dall'archivio gli indizi di ogni lotto partono dalla cartella scelta.
- Una ricerca durante l'aggiornamento dell'indice poteva rispondere «Cannot operate on a closed database»: ora l'indice viene sostituito solo quando le ricerche in corso hanno finito.
- L'evidenziazione delle parole cercate non si sposta più con testi che hanno accenti staccati (NFD), legature o emoji.
- Le cartelle nascoste (che iniziano con un punto, come `.thumbnails`) non vengono più esplorate cercando le foto.
- Luoghi: «Munich» diventa «Monaco di Baviera», per non confonderlo con il Principato di Monaco.

**Sicurezza**
- Dalla rete di casa (telefono, tablet) si cerca e si guarda; le impostazioni si cambiano solo dal computer con Labellula. In particolare non si possono più cambiare l'Ollama a cui vanno le foto (né provarne uno), l'archivio, la lingua e la rete.
- Dalla rete si sfogliano e si descrivono solo le cartelle dell'archivio, non tutto il disco.
- Gli errori inattesi mostrati ai dispositivi della rete non contengono più percorsi interni.

**Schede**
- Il piè della scheda riporta la cartella relativa all'archivio (`Cartella: 2024/2024-02-04 gara karate Torino`) invece del percorso completo del disco: niente nome utente o lettera dell'unità nelle schede condivise o esportate. Le schede già scritte restano valide.

## 0.2.0 (26/11/2026)

**Installazione**
- `LEGGIMI - COME INSTALLARE.txt` nella cartella principale: istruzioni in testo semplice per chi riceve lo ZIP senza passare da GitHub.
- Linux: se mancano il modulo `venv` di Python o `curl`, l'installatore dice il comando esatto per installarli.
- Windows: si installa con un doppio clic su `Installa-Windows.cmd`, senza dover sbloccare gli script PowerShell. L'installatore toglie ai file di Labellula il segno «scaricato da internet».
- Se Ollama è installato ma spento (succede subito dopo l'installazione con winget), `modelli` e `prova` lo avviano da soli; la prova di velocità dice cosa sta facendo invece di restare muta.
- «Descrivi foto» su una cartella fuori dall'archivio della ricerca (o mentre si guarda l'archivio dimostrativo): prima di partire Labellula chiede se usarla come archivio, altrimenti le schede nuove non si troverebbero cercando.
- Labellula riscaricata in un'altra cartella: l'icona sul desktop chiude il server della vecchia copia ancora aperto e avvia quello nuovo; pagina e script non restano più nella cache del browser.

**Descrizione**
- Comando `python -m labellula descrivi`, con motore sostituibile (oggi Ollama locale).
- Prompt v5: titolo, fonte di ogni informazione su luogo e data, occasione, aspetti fotografici, dubbi.
- Nomi di cartelle e file letti e verificati con EXIF, GPS ed elenco offline delle località; `luoghi_noti` in `config.yaml`.
- Al modello arriva solo una copia ridotta senza EXIF e GPS.

- Prompt v5.2: stagione e momento della giornata dalla data EXIF, data e ora esatte, tipo di luogo invece di "non determinabile", `luoghi_noti`. Le schede riportano la versione esatta del prompt.
- `--aggiorna` (solo schede con prompt più vecchio) e `--modello`.

**Pagina web**
- ＋ Descrivi foto: scelta della cartella, conteggio, avanzamento, Ferma, aggiornamento automatico della ricerca, Imposta come archivio.
- Elaborazione remota (in preparazione), Aiuto, loghi di ctrlalt.museum e comPVter.
- Ultime ricerche e ricerche salvate, Foto simili, Stessa cartella, Copia scheda, Solo da verificare, Esporta CSV.
- Versione per telefono e tablet.
- Scelta del modello (modelli Ollama con la visione), modalità Aggiorna e A lotti; stato dal vivo (foto in corso, modello, ultima scheda); modelli usati nel piè di pagina.
- Durante un lavoro il PC non va in sospensione.

**Installazione**
- Installatori `tools/installa.ps1` (Windows) e `tools/installa.sh` (macOS, Linux): controllano l'hardware e scaricano Ollama e i modelli **solo se il computer è adatto**, chiedendo conferma; altrimenti impostano l'elaborazione remota.
- `python -m labellula verifica` (scheda video, RAM, disco, Ollama; verdetto e modello consigliato), `modelli` (scarica solo quelli adatti), `prova` (velocità vera su una foto di esempio). Verdetto visibile nella finestra «Descrivi foto».
- `python -m labellula usa-ollama <indirizzo>`: usa l'Ollama (e la GPU) di un altro computer della rete; `usa-ollama locale` per tornare indietro. Provato sull indirizzo di rete del PC con la RTX 3080 Ti; prova dal Mac da fare.
- `python -m labellula diagnosi [--cartella X]`: un riepilogo da fotografare quando qualcosa non va; lanciato anche dagli installatori. `pillow-heif` installato a parte, così se non si installa non blocca il resto; la pagina avvisa se ci sono HEIC ma il supporto manca.
- **Multilingua**: menu della lingua (italiano, English, Français, Deutsch, Español) per la pagina e per le nuove schede, che vengono scritte nella lingua scelta (categorie comprese). La ricerca per significato funziona anche tra lingue diverse. Traduzioni in `labellula/web/i18n.js` (Aiuto completo in italiano e inglese).
- **Archivio dimostrativo** di ctrlalt.museum (Commodore PET, Commodore 64, ZX Spectrum, Apple IIc) con le schede già pronte: la pagina lo propone quando l'archivio è vuoto.
- **Telefono e tablet**: accesso dalla rete di casa con password (? › Telefono e tablet, oppure `python -m labellula rete attiva`): impronta PBKDF2, cookie di sessione protetto, attesa dopo i tentativi sbagliati, impostazioni modificabili solo dal computer con Labellula; senza password la rete resta chiusa.
- Foto **HEIC/HEIF** (iPhone, molti Android): descrizione, EXIF e GPS, miniature; nella pagina convertite al volo in JPEG. Nuova dipendenza `pillow-heif`; le estensioni HEIC vengono aggiunte anche ai `config.yaml` già esistenti.
- Dopo un aggiornamento il server ancora aperto (versione precedente) viene riconosciuto: la pagina lo dice e il doppio clic sull'icona lo chiude e riapre da solo. Archivio predefinito: la cartella Immagini dell'utente (prima un percorso Windows anche su Mac).
- Pagina: campo «Ollama su:» nella finestra «Descrivi foto», con **Prova** (conferma, versione, modelli; avviso per gli indirizzi su internet) e **Usa** (salva in `config.yaml`).
- Guida: installazione passo passo per chi non usa GitHub (Windows, macOS, Linux) e GPU condivisa in rete.
- Modello più piccolo `qwen3-vl:4b-instruct` per le schede da 6–11 GB e i Mac Apple Silicon da 8 GB.
- `requirements.txt`; avvio con doppio clic su Windows (`tools/avvia_labellula.ps1`) e su macOS/Linux (`tools/avvia_labellula.sh`).
- Primo avvio automatico: `config.yaml` e indice creati da soli.

## 0.1.0 (23/11/2026)
- Prima versione della descrizione (prompt v4) e del registro delle identità per il modulo volti.
- Nuovo ID dei volti e registro delle identità.
- Ricerca per parole (SQLite FTS5) e per significato (bge-m3), interfaccia web HTML5.
