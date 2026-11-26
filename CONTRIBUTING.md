# Come contribuire

Grazie per l'interesse! Labellula è nato per gli archivi di [ctrlalt.museum](https://ctrlalt.museum/) ed è aperto a tutti.

## Modi per aiutare, anche senza programmare

- **Provalo** sul tuo archivio e raccontaci com'è andata: computer, scheda video, velocità, qualità delle schede.
- **Segnala un errore** con una *issue*: cosa hai fatto, cosa ti aspettavi, cosa è successo. Allega il risultato di `python -m labellula diagnosi` (togli prima i percorsi che non vuoi mostrare).
- **Segnala una scheda sbagliata**: incolla il testo della scheda e descrivi la foto. **Non allegare foto con persone** senza il loro consenso.
- **Proponi un'idea** con una *issue* che inizi con "Idea:".
- **Traduci** la pagina o la guida in un'altra lingua.

## Se vuoi scrivere codice

1. Fai un *fork* del repository e crea un ramo con un nome chiaro, per esempio `correzione-heic-mac`.
2. Installa come da [guida](docs/GUIDA.md) e lancia i test:
   ```sh
   python -m unittest discover -s tests -t .
   ```
3. Fai modifiche piccole e mirate, con i test per ciò che cambi. I test devono passare su Windows, macOS e Linux: GitHub li esegue da solo a ogni *pull request*.
4. Scrivi in italiano commenti, messaggi e testi dell'interfaccia; per le altre lingue usa i file delle traduzioni.
5. Aggiorna [CHANGELOG.md](CHANGELOG.md) e, se cambia l'uso, la [guida](docs/GUIDA.md).
6. Apri una *pull request* spiegando cosa cambia e perché.

## Principi da rispettare

- **Le foto restano dell'utente**: niente invio di dati a servizi esterni senza una scelta esplicita.
- **Formati aperti**: le schede restano file di testo leggibili da chiunque.
- **Facile**: chi non è un tecnico deve poterlo installare e usare.

## Licenza dei contributi

Contribuendo accetti che il tuo codice sia distribuito con la stessa licenza del progetto, [GNU AGPL-3.0](LICENSE).

## Comportamento

Rispetto, gentilezza e pazienza con tutti, soprattutto con chi è alle prime armi.
