# Sicurezza

Grazie se ci aiuti a rendere Labellula più sicuro.

## Come segnalare un problema di sicurezza

**Non aprire una issue pubblica** per un problema di sicurezza: chiunque potrebbe leggerla prima che sia risolto.

Usa invece la segnalazione privata di GitHub: nella pagina del repository, scheda **Security › Report a vulnerability**. Scrivi:
- cosa hai trovato e su quale versione (si legge in `CHANGELOG.md` o nel commit);
- come riprodurlo, passo per passo;
- cosa potrebbe fare chi lo sfruttasse.

Rispondiamo di solito entro una settimana. Labellula è un progetto volontario: correggiamo prima i problemi più gravi e ti diciamo quando la correzione è pubblicata. Se vuoi, ti citiamo nelle note della versione.

## Versioni supportate

Correggiamo i problemi di sicurezza solo nell'**ultima versione** pubblicata.

## Cosa è già previsto

- La pagina di ricerca risponde di default **solo al computer su cui gira** (`127.0.0.1`).
- L'accesso dalla rete di casa si attiva solo su richiesta e **richiede una password**, salvata solo come impronta (PBKDF2).
- Le richieste che modificano qualcosa sono protette contro siti esterni aperti nel browser (controllo dell'Host e intestazione dedicata).
- Al modello arriva solo una copia ridotta delle foto, **senza dati EXIF e GPS**.

## Cosa non è nel nostro perimetro

- **Ollama** non ha password: se lo rendi raggiungibile dalla rete, limita la porta 11434 nel firewall al solo computer che lo usa, e non esporlo mai su internet. I problemi di Ollama vanno segnalati al suo progetto.
- I modelli di intelligenza artificiale possono sbagliare o inventare dettagli: è un limite noto, non un problema di sicurezza.
