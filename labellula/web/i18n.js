// Labellula: traduzioni dell'interfaccia.
// La lingua di partenza è l'italiano: nel codice i testi sono in italiano e T("testo") li traduce.
// Se una traduzione manca resta l'italiano, quindi niente si rompe. Per aggiungere una lingua:
// copia il blocco "en" con un nuovo codice, traduci i valori, aggiungi la lingua a LINGUE.
"use strict";

const LINGUE = { it: "Italiano", en: "English", fr: "Français", de: "Deutsch", es: "Español" };
const LOCALI = { it: "it-IT", en: "en-GB", fr: "fr-FR", de: "de-DE", es: "es-ES" };

const LINGUA = (() => {
  try { const s = localStorage.getItem("labellula.lingua"); if (s && LINGUE[s]) return s; } catch { /* niente */ }
  const b = (navigator.language || "it").slice(0, 2).toLowerCase();
  return LINGUE[b] ? b : "it";
})();
const LOCALE = LOCALI[LINGUA];

// ------------------------------------------------------------------ testi brevi (interfaccia)
const TRADUZIONI = {
  en: {
    "Labellula è un progetto open source italiano, nato per sostenere ctrlalt.museum": "Labellula is an Italian open source project, born to support ctrlalt.museum",
    "Cerca": "Search", "Cerca: commodore, gara di karate a Torino, volpe, cattedrale…": "Search: commodore, karate competition in Turin, fox, cathedral…",
    "Testo da cercare": "Text to search", "Tipo di ricerca": "Search type", "Come confrontare il testo cercato con le schede": "How to compare the text with the records",
    "Parole + significato": "Words + meaning", "Solo significato": "Meaning only", "Solo parole": "Words only",
    "＋ Descrivi foto": "＋ Describe photos", "Scegli una cartella del PC e fai descrivere le foto": "Choose a folder on your computer and have its photos described",
    "Elaborazione remota": "Remote processing", "Non hai una GPU? Le foto vengono descritte dalla GPU di Labellula, a crediti": "No GPU? Your photos are described by Labellula's GPU, with credits",
    "Aiuto: come funziona Labellula (?)": "Help: how Labellula works (?)", "Aiuto": "Help", "Filtri": "Filters", "Azioni": "Actions",
    "Tutte le categorie": "All categories", "Categoria": "Category", "Dal": "From", "Al": "To", "Dall'anno": "From year", "All'anno": "To year",
    "Tutte le persone": "All people", "Persona": "Person", "Solo da verificare": "Only to be checked",
    "Labellula è un progetto open source nato per gli archivi di ctrlalt.museum": "Labellula is an open source project born for the archives of ctrlalt.museum",
    "ctrlalt.museum: il museo dei computer dell'associazione comPVter": "ctrlalt.museum: the computer museum of the comPVter association",
    "Associazione culturale comPVter": "comPVter cultural association",
    "Ferma": "Stop", "Nascondi": "Hide", "Ultime ricerche": "Recent searches", "☆ Salva ricerca": "☆ Save search", "★ Salvata": "★ Saved",
    "Salva questa ricerca tra le preferite": "Save this search to favourites", "Esporta CSV": "Export CSV",
    "Scarica i risultati in un file CSV (Excel, LibreOffice)": "Download the results as a CSV file (Excel, LibreOffice)",
    "Caricamento…": "Loading…", "Risultati": "Results", "Mostra altri risultati": "Show more results",
    "Scheda della foto": "Photo record", "Precedente (←)": "Previous (←)", "Successiva (→)": "Next (→)", "Chiudi (Esc)": "Close (Esc)", "Chiudi": "Close",
    "Apri la foto originale": "Open the original photo", "Foto simili": "Similar photos", "Foto con una descrizione simile": "Photos with a similar description",
    "Stessa cartella": "Same folder", "Tutte le foto di questa cartella": "All photos in this folder", "Copia scheda": "Copy record",
    "Copia la scheda negli appunti": "Copy the record to the clipboard", "Copiata ✓": "Copied ✓", "Copia non riuscita": "Copy failed",
    "Descrivi le foto di una cartella": "Describe the photos in a folder", "Cartella superiore": "Parent folder", "Percorso della cartella": "Folder path", "Vai": "Go",
    "Chi descrive le foto": "Who describes the photos", "Questo PC, con Ollama: gratis, serve una GPU (~4–7 s a foto)": "This computer, with Ollama: free, needs a GPU (~4–7 s per photo)",
    "Ollama su:": "Ollama on:", "questo computer, oppure 192.168.1.20": "this computer, or 192.168.1.20", "Indirizzo di Ollama": "Ollama address",
    "Prova": "Test", "Usa": "Use", "Controlla che Ollama risponda, senza cambiare niente": "Check that Ollama answers, without changing anything",
    "Usa questo Ollama per descrivere le foto (salvato in config.yaml)": "Use this Ollama to describe the photos (saved in config.yaml)",
    "Modello:": "Model:", "Modello che descrive le foto": "Model that describes the photos",
    "Servizio Labellula a crediti, senza GPU: in arrivo": "Labellula service with credits, no GPU needed: coming soon",
    "Riscrivi tutte le schede, anche quelle già aggiornate": "Rewrite all records, including up-to-date ones",
    "A lotti: una sottocartella alla volta, con la ricerca aggiornata dopo ognuna (per archivi grandi)": "In batches: one subfolder at a time, updating the search after each (for large archives)",
    "Prova: solo le prime 20 foto": "Trial: only the first 20 photos", "Imposta come archivio": "Set as archive",
    "Cerca in questa cartella invece che nell'archivio attuale": "Search in this folder instead of the current archive",
    "Conta le foto": "Count photos", "Avvia la descrizione": "Start describing", "Archivio della ricerca:": "Search archive:",
    "Codice": "Code", "Acquista crediti": "Buy credits", "Sostieni il museo": "Support the museum", "Sostieni ctrlalt.museum": "Support ctrlalt.museum",
    "Come funziona Labellula": "How Labellula works", "Telefono e tablet": "Phone and tablet", "Scorciatoie": "Shortcuts", "Privacy": "Privacy",
    "Tre modi di usare Labellula": "Three ways to use Labellula", "Primi passi": "First steps", "Consigli": "Tips",
    "password (almeno 8 caratteri)": "password (at least 8 characters)", "ripeti la password": "repeat the password",
    "Password per l'accesso dalla rete": "Password for network access", "Ripeti la password": "Repeat the password",
    "Attiva l'accesso dalla rete": "Enable network access", "Disattiva": "Disable", "Cambia la password": "Change password", "Esci": "Log out",
    "Tutto gira su questo computer: nessuna foto lascia la macchina.": "Everything runs on this computer: no photo leaves the machine.",
    "Cartella": "Folder", "Togli il filtro": "Remove filter", "Ultime:": "Recent:", "(nessuna)": "(none)",
    "Indice: {n} schede, aggiornato il {data}.": "Index: {n} records, updated on {data}.", "Ricerca per significato attiva.": "Search by meaning active.",
    "Schede scritte da:": "Records written by:", "sconosciuto": "unknown", "Ricerca…": "Searching…",
    "Foto simili a <b>{nome}</b> ({n}).": "Photos similar to <b>{nome}</b> ({n}).", "Torna alla ricerca": "Back to search",
    "L'archivio è ancora vuoto.": "The archive is still empty.", "Guarda l'archivio dimostrativo di ctrlalt.museum": "View the ctrlalt.museum demo archive",
    "oppure": "or", "＋ Descrivi le tue foto": "＋ Describe your photos",
    "Nessuna foto trovata. Prova con meno parole o togli un filtro.": "No photos found. Try fewer words or remove a filter.",
    "{n} foto": "{n} photos", ", ne vedi {m}": ", showing {m}",
    "Descrizione": "Description", "Testi visibili": "Visible text", "Luogo e periodo": "Place and date", "Occasione": "Occasion", "Data": "Date",
    "Persone (dalla descrizione)": "People (from the description)", "Persone riconosciute": "Recognised people", "Aspetti fotografici": "Photographic aspects",
    "Parole chiave": "Keywords", "Dubbi del modello": "Model's doubts", "Generato con:": "Generated with:",
    "Il modello si era ripetuto: descrizione da controllare.": "The model repeated itself: description to be checked.",
    "Nessuna sottocartella.": "No subfolders.", "In questa cartella (senza le sottocartelle): {n} foto": "In this folder (without subfolders): {n} photos",
    " (di cui {h} HEIC)": " ({h} HEIC)", ", {s} già descritte.": ", {s} already described.",
    "Le foto HEIC non si possono leggere: manca il pacchetto pillow-heif (rilancia l'installatore).": "HEIC photos cannot be read: the pillow-heif package is missing (run the installer again).",
    "Scegli un'unità disco.": "Choose a drive.", "Conto le foto, anche nelle sottocartelle…": "Counting photos, subfolders included…",
    "{n} foto in tutto, da descrivere: {d}": "{n} photos in total, to describe: {d}", "(circa {t} su questa GPU)": "(about {t} on this GPU)",
    "{m} minuti": "{m} minutes", "{o} ore": "{o} hours", "Preparo l'archivio dimostrativo…": "Preparing the demo archive…",
    "Usare \"{p}\" come archivio della ricerca?\nconfig.yaml viene aggiornato (con una copia di sicurezza) e l'indice ricostruito.": "Use \"{p}\" as the search archive?\nconfig.yaml will be updated (with a backup copy) and the index rebuilt.",
    "Ricostruisco l'indice…": "Rebuilding the index…", "Fatto: la ricerca ora usa questa cartella.": "Done: search now uses this folder.",
    "lotto {k}/{n} «{l}»": "batch {k}/{n} «{l}»", "Descrivo «{nome}»": "Describing «{nome}»", "Errore": "Error", "Errore:": "Error:",
    "con {m}, prompt {p}": "with {m}, prompt {p}", "{f}/{t} foto": "{f}/{t} photos", ", mancano circa {d}": ", about {d} left",
    "ora:": "now:", "ultima:": "last:", "in {s} s": "in {s} s", "{f} schede scritte, {e} errori, {v} da verificare.": "{f} records written, {e} errors, {v} to be checked.",
    "descrizione": "describing", "preparazione": "preparing", "aggiornamento della ricerca": "updating the search", "finito": "finished", "fermato": "stopped",
    "errore": "error", "in arresto (finisce la foto in corso)": "stopping (finishing the current photo)",
    "non installato?": "not installed?", "Le schede riportano sempre il modello che le ha scritte.": "Each record always states the model that wrote it.",
    "Altri modelli: «ollama pull <nome>» (es. gemma3:12b).": "Other models: «ollama pull <name>» (e.g. gemma3:12b).", "Ollama non risponde.": "Ollama does not answer.",
    "nessun modello che vede le immagini": "no model that can see images", "Ollama {v} risponde su {u} (rete {r}). Modelli: {m}.": "Ollama {v} answers at {u} ({r} network). Models: {m}.",
    "locale": "local", "privata": "private", "pubblica": "public", "sconosciuta": "unknown",
    "Manca bge-m3 per la ricerca per significato.": "bge-m3 is missing for search by meaning.", "In uso con {m}.": "In use with {m}.",
    "Premi «Usa» per descrivere le foto con questo Ollama.": "Press «Use» to describe the photos with this Ollama.", "Provo a raggiungere Ollama…": "Trying to reach Ollama…",
    "Il server di Labellula aperto è una versione precedente: chiudi e riapri Labellula (doppio clic sull'icona), poi riprova.": "The running Labellula server is an older version: close and reopen Labellula (double-click the icon), then try again.",
    "Questo computer{s}: {v} per descrivere in locale.": "This computer{s}: {v} for describing locally.", "adatto": "suitable", "al limite": "borderline", "da provare": "to be tested", "non adatto": "not suitable",
    "Prova: {s} s a foto con {m}.": "Test: {s} s per photo with {m}.",
    "Le foto vengono descritte dall'Ollama di un altro computer della rete ({u}).": "Photos are described by the Ollama of another computer on the network ({u}).",
    "<b>Attivo.</b> Dal telefono, sulla stessa Wi-Fi, apri: <b>{i}</b>": "<b>Active.</b> From your phone, on the same Wi-Fi, open: <b>{i}</b>",
    "Impostato: chiudi e riapri Labellula (icona sul desktop) per attivarlo.": "Set: close and reopen Labellula (desktop icon) to activate it.",
    "Disattivato: chiudi e riapri Labellula per chiudere l'accesso dalla rete.": "Disabled: close and reopen Labellula to close network access.",
    "Non attivo: la ricerca si apre solo da questo computer.": "Not active: search opens only on this computer.",
    "La password deve avere almeno 8 caratteri.": "The password must be at least 8 characters long.", "Le due password non coincidono.": "The two passwords do not match.",
    "Salvato. Chiudi e riapri Labellula (doppio clic sull'icona) per applicare. La prima volta il firewall può chiedere il permesso: consentilo sulle reti private.": "Saved. Close and reopen Labellula (double-click the icon) to apply. The first time the firewall may ask for permission: allow it on private networks.",
    "Salvato.": "Saved.", "Il servizio è in preparazione: l'acquisto dei codici sarà disponibile sullo shop di ctrlalt.museum.": "The service is being prepared: codes will be available in the ctrlalt.museum shop.",
    "Stai guardando l'<b>archivio dimostrativo</b>: foto di ctrlalt.museum. Per le tue foto: <b>＋ Descrivi foto</b> › scegli la cartella › <b>Imposta come archivio</b>.": "You are viewing the <b>demo archive</b>: photos of ctrlalt.museum. For your own photos: <b>＋ Describe photos</b> › choose the folder › <b>Set as archive</b>.",
    "<b>Labellula è stato aggiornato:</b> chiudi e riapri Labellula (doppio clic sull'icona) per usare la versione nuova.": "<b>Labellula has been updated:</b> close and reopen Labellula (double-click the icon) to use the new version.",
    "Aggiorna le schede fatte con un prompt più vecchio (": "Update records made with an older prompt (",
    "); si riprende da dove ci si era fermati": "); it resumes where it stopped", "ultimo": "latest",
    "Ora la ricerca mostra l'archivio dimostrativo. Uso \"{p}\" come tuo archivio, così le schede nuove si possono cercare?": "The search is showing the demo archive. Use \"{p}\" as your archive, so the new records can be searched?",
    "\"{p}\" non fa parte dell'archivio della ricerca ({a}): le schede verrebbero scritte ma non le troveresti cercando.\nLa uso come archivio? (Annulla = descrivi soltanto)": "\"{p}\" is not part of the search archive ({a}): the records would be written but you would not find them when searching.\nUse it as the archive? (Cancel = just describe)",
    "Lingua": "Language", "Lingua dell'interfaccia e delle nuove schede": "Language of the interface and of new records",
    "Le nuove schede saranno scritte in {l}. Per riscrivere quelle esistenti: «＋ Descrivi foto» › «Aggiorna».": "New records will be written in {l}. To rewrite existing ones: «＋ Describe photos» › «Update».",
  },
};
// Francese, tedesco e spagnolo: interfaccia tradotta; dove manca una voce si usa l'inglese, poi l'italiano.
const _base = (o) => Object.assign({}, o);
TRADUZIONI.fr = _base({
  "Labellula è un progetto open source italiano, nato per sostenere ctrlalt.museum": "Labellula est un projet open source italien, né pour soutenir ctrlalt.museum",
  "Stai guardando l'<b>archivio dimostrativo</b>: foto di ctrlalt.museum. Per le tue foto: <b>＋ Descrivi foto</b> › scegli la cartella › <b>Imposta come archivio</b>.": "Vous consultez l'<b>archive de démonstration</b> : photos de ctrlalt.museum. Pour vos photos : <b>＋ Décrire des photos</b> › choisissez le dossier › <b>Définir comme archive</b>.",
  "Cerca": "Rechercher", "Cerca: commodore, gara di karate a Torino, volpe, cattedrale…": "Rechercher : commodore, compétition de karaté à Turin, renard, cathédrale…",
  "Parole + significato": "Mots + sens", "Solo significato": "Sens seulement", "Solo parole": "Mots seulement",
  "＋ Descrivi foto": "＋ Décrire des photos", "Elaborazione remota": "Traitement à distance", "Tutte le categorie": "Toutes les catégories",
  "Dal": "Du", "Al": "Au", "Tutte le persone": "Toutes les personnes", "Solo da verificare": "Seulement à vérifier",
  "Labellula è un progetto open source nato per gli archivi di ctrlalt.museum": "Labellula est un projet open source né pour les archives de ctrlalt.museum",
  "Ferma": "Arrêter", "☆ Salva ricerca": "☆ Enregistrer", "★ Salvata": "★ Enregistrée", "Esporta CSV": "Exporter CSV", "Caricamento…": "Chargement…",
  "Mostra altri risultati": "Afficher plus de résultats", "Foto simili": "Photos similaires", "Stessa cartella": "Même dossier", "Copia scheda": "Copier la fiche",
  "Copiata ✓": "Copiée ✓", "Descrivi le foto di una cartella": "Décrire les photos d'un dossier", "Vai": "Aller",
  "Chi descrive le foto": "Qui décrit les photos", "Questo PC, con Ollama: gratis, serve una GPU (~4–7 s a foto)": "Cet ordinateur, avec Ollama : gratuit, carte graphique requise (~4–7 s par photo)",
  "Ollama su:": "Ollama sur :", "Prova": "Tester", "Usa": "Utiliser", "Modello:": "Modèle :", "Imposta come archivio": "Définir comme archive",
  "Conta le foto": "Compter les photos", "Avvia la descrizione": "Lancer la description", "Archivio della ricerca:": "Archive de recherche :",
  "Acquista crediti": "Acheter des crédits", "Sostieni il museo": "Soutenir le musée", "Sostieni ctrlalt.museum": "Soutenir ctrlalt.museum",
  "Come funziona Labellula": "Comment fonctionne Labellula", "Telefono e tablet": "Téléphone et tablette", "Scorciatoie": "Raccourcis", "Privacy": "Confidentialité",
  "Tre modi di usare Labellula": "Trois façons d'utiliser Labellula", "Primi passi": "Premiers pas", "Consigli": "Conseils",
  "Attiva l'accesso dalla rete": "Activer l'accès réseau", "Disattiva": "Désactiver", "Cambia la password": "Changer le mot de passe", "Esci": "Se déconnecter",
  "Tutto gira su questo computer: nessuna foto lascia la macchina.": "Tout fonctionne sur cet ordinateur : aucune photo ne quitte la machine.",
  "Cartella": "Dossier", "Ultime:": "Récentes :", "Indice: {n} schede, aggiornato il {data}.": "Index : {n} fiches, mis à jour le {data}.",
  "Ricerca per significato attiva.": "Recherche par le sens active.", "Schede scritte da:": "Fiches écrites par :", "Ricerca…": "Recherche…",
  "Foto simili a <b>{nome}</b> ({n}).": "Photos similaires à <b>{nome}</b> ({n}).", "Torna alla ricerca": "Retour à la recherche",
  "L'archivio è ancora vuoto.": "L'archive est encore vide.", "Guarda l'archivio dimostrativo di ctrlalt.museum": "Voir l'archive de démonstration de ctrlalt.museum",
  "oppure": "ou", "＋ Descrivi le tue foto": "＋ Décrire vos photos", "Nessuna foto trovata. Prova con meno parole o togli un filtro.": "Aucune photo trouvée. Essayez avec moins de mots ou retirez un filtre.",
  "{n} foto": "{n} photos", ", ne vedi {m}": ", {m} affichées", "Descrizione": "Description", "Testi visibili": "Textes visibles", "Luogo e periodo": "Lieu et date",
  "Occasione": "Occasion", "Data": "Date", "Persone (dalla descrizione)": "Personnes (d'après la description)", "Aspetti fotografici": "Aspects photographiques",
  "Parole chiave": "Mots-clés", "Dubbi del modello": "Doutes du modèle", "Generato con:": "Généré avec :", "Categoria": "Catégorie",
  "{n} foto in tutto, da descrivere: {d}": "{n} photos au total, à décrire : {d}", "{f}/{t} foto": "{f}/{t} photos", "Descrivo «{nome}»": "Description de «{nome}»",
  "Errore": "Erreur", "Errore:": "Erreur :", "Lingua": "Langue", "Lingua dell'interfaccia e delle nuove schede": "Langue de l'interface et des nouvelles fiches",
  "Le nuove schede saranno scritte in {l}. Per riscrivere quelle esistenti: «＋ Descrivi foto» › «Aggiorna».": "Les nouvelles fiches seront écrites en {l}. Pour réécrire les existantes : «＋ Décrire des photos» › «Mettre à jour».",
});
TRADUZIONI.de = _base({
  "Labellula è un progetto open source italiano, nato per sostenere ctrlalt.museum": "Labellula ist ein italienisches Open-Source-Projekt zur Unterstützung von ctrlalt.museum",
  "Stai guardando l'<b>archivio dimostrativo</b>: foto di ctrlalt.museum. Per le tue foto: <b>＋ Descrivi foto</b> › scegli la cartella › <b>Imposta come archivio</b>.": "Sie sehen das <b>Demo-Archiv</b>: Fotos aus ctrlalt.museum. Für Ihre Fotos: <b>＋ Fotos beschreiben</b> › Ordner wählen › <b>Als Archiv festlegen</b>.",
  "Cerca": "Suchen", "Cerca: commodore, gara di karate a Torino, volpe, cattedrale…": "Suchen: commodore, Karatewettkampf in Turin, Fuchs, Kathedrale…",
  "Parole + significato": "Wörter + Bedeutung", "Solo significato": "Nur Bedeutung", "Solo parole": "Nur Wörter",
  "＋ Descrivi foto": "＋ Fotos beschreiben", "Elaborazione remota": "Fernverarbeitung", "Tutte le categorie": "Alle Kategorien",
  "Dal": "Von", "Al": "Bis", "Tutte le persone": "Alle Personen", "Solo da verificare": "Nur zu prüfen",
  "Labellula è un progetto open source nato per gli archivi di ctrlalt.museum": "Labellula ist ein Open-Source-Projekt, entstanden für die Archive von ctrlalt.museum",
  "Ferma": "Anhalten", "☆ Salva ricerca": "☆ Suche speichern", "★ Salvata": "★ Gespeichert", "Esporta CSV": "CSV exportieren", "Caricamento…": "Wird geladen…",
  "Mostra altri risultati": "Weitere Ergebnisse", "Foto simili": "Ähnliche Fotos", "Stessa cartella": "Gleicher Ordner", "Copia scheda": "Datensatz kopieren",
  "Copiata ✓": "Kopiert ✓", "Descrivi le foto di una cartella": "Fotos eines Ordners beschreiben", "Vai": "Los",
  "Chi descrive le foto": "Wer beschreibt die Fotos", "Questo PC, con Ollama: gratis, serve una GPU (~4–7 s a foto)": "Dieser Computer, mit Ollama: kostenlos, Grafikkarte nötig (~4–7 s pro Foto)",
  "Ollama su:": "Ollama auf:", "Prova": "Testen", "Usa": "Verwenden", "Modello:": "Modell:", "Imposta come archivio": "Als Archiv festlegen",
  "Conta le foto": "Fotos zählen", "Avvia la descrizione": "Beschreibung starten", "Archivio della ricerca:": "Sucharchiv:",
  "Acquista crediti": "Guthaben kaufen", "Sostieni il museo": "Das Museum unterstützen", "Sostieni ctrlalt.museum": "ctrlalt.museum unterstützen",
  "Come funziona Labellula": "So funktioniert Labellula", "Telefono e tablet": "Telefon und Tablet", "Scorciatoie": "Tastenkürzel", "Privacy": "Datenschutz",
  "Tre modi di usare Labellula": "Drei Arten, Labellula zu nutzen", "Primi passi": "Erste Schritte", "Consigli": "Tipps",
  "Attiva l'accesso dalla rete": "Netzwerkzugriff aktivieren", "Disattiva": "Deaktivieren", "Cambia la password": "Passwort ändern", "Esci": "Abmelden",
  "Tutto gira su questo computer: nessuna foto lascia la macchina.": "Alles läuft auf diesem Computer: kein Foto verlässt das Gerät.",
  "Cartella": "Ordner", "Ultime:": "Zuletzt:", "Indice: {n} schede, aggiornato il {data}.": "Index: {n} Datensätze, aktualisiert am {data}.",
  "Ricerca per significato attiva.": "Bedeutungssuche aktiv.", "Schede scritte da:": "Datensätze erstellt von:", "Ricerca…": "Suche…",
  "Foto simili a <b>{nome}</b> ({n}).": "Fotos ähnlich wie <b>{nome}</b> ({n}).", "Torna alla ricerca": "Zurück zur Suche",
  "L'archivio è ancora vuoto.": "Das Archiv ist noch leer.", "Guarda l'archivio dimostrativo di ctrlalt.museum": "Demo-Archiv von ctrlalt.museum ansehen",
  "oppure": "oder", "＋ Descrivi le tue foto": "＋ Eigene Fotos beschreiben", "Nessuna foto trovata. Prova con meno parole o togli un filtro.": "Keine Fotos gefunden. Weniger Wörter versuchen oder einen Filter entfernen.",
  "{n} foto": "{n} Fotos", ", ne vedi {m}": ", {m} angezeigt", "Descrizione": "Beschreibung", "Testi visibili": "Sichtbarer Text", "Luogo e periodo": "Ort und Zeit",
  "Occasione": "Anlass", "Data": "Datum", "Persone (dalla descrizione)": "Personen (laut Beschreibung)", "Aspetti fotografici": "Fotografische Aspekte",
  "Parole chiave": "Schlagwörter", "Dubbi del modello": "Zweifel des Modells", "Generato con:": "Erstellt mit:", "Categoria": "Kategorie",
  "{n} foto in tutto, da descrivere: {d}": "{n} Fotos insgesamt, zu beschreiben: {d}", "{f}/{t} foto": "{f}/{t} Fotos", "Descrivo «{nome}»": "Beschreibe «{nome}»",
  "Errore": "Fehler", "Errore:": "Fehler:", "Lingua": "Sprache", "Lingua dell'interfaccia e delle nuove schede": "Sprache der Oberfläche und der neuen Datensätze",
  "Le nuove schede saranno scritte in {l}. Per riscrivere quelle esistenti: «＋ Descrivi foto» › «Aggiorna».": "Neue Datensätze werden auf {l} geschrieben. Bestehende neu schreiben: «＋ Fotos beschreiben» › «Aktualisieren».",
});
TRADUZIONI.es = _base({
  "Labellula è un progetto open source italiano, nato per sostenere ctrlalt.museum": "Labellula es un proyecto italiano de código abierto, nacido para apoyar a ctrlalt.museum",
  "Stai guardando l'<b>archivio dimostrativo</b>: foto di ctrlalt.museum. Per le tue foto: <b>＋ Descrivi foto</b> › scegli la cartella › <b>Imposta come archivio</b>.": "Estás viendo el <b>archivo de demostración</b>: fotos de ctrlalt.museum. Para tus fotos: <b>＋ Describir fotos</b> › elige la carpeta › <b>Definir como archivo</b>.",
  "Cerca": "Buscar", "Cerca: commodore, gara di karate a Torino, volpe, cattedrale…": "Buscar: commodore, competición de kárate en Turín, zorro, catedral…",
  "Parole + significato": "Palabras + significado", "Solo significato": "Solo significado", "Solo parole": "Solo palabras",
  "＋ Descrivi foto": "＋ Describir fotos", "Elaborazione remota": "Procesamiento remoto", "Tutte le categorie": "Todas las categorías",
  "Dal": "Desde", "Al": "Hasta", "Tutte le persone": "Todas las personas", "Solo da verificare": "Solo por revisar",
  "Labellula è un progetto open source nato per gli archivi di ctrlalt.museum": "Labellula es un proyecto de código abierto nacido para los archivos de ctrlalt.museum",
  "Ferma": "Detener", "☆ Salva ricerca": "☆ Guardar búsqueda", "★ Salvata": "★ Guardada", "Esporta CSV": "Exportar CSV", "Caricamento…": "Cargando…",
  "Mostra altri risultati": "Mostrar más resultados", "Foto simili": "Fotos similares", "Stessa cartella": "Misma carpeta", "Copia scheda": "Copiar ficha",
  "Copiata ✓": "Copiada ✓", "Descrivi le foto di una cartella": "Describir las fotos de una carpeta", "Vai": "Ir",
  "Chi descrive le foto": "Quién describe las fotos", "Questo PC, con Ollama: gratis, serve una GPU (~4–7 s a foto)": "Este ordenador, con Ollama: gratis, requiere tarjeta gráfica (~4–7 s por foto)",
  "Ollama su:": "Ollama en:", "Prova": "Probar", "Usa": "Usar", "Modello:": "Modelo:", "Imposta come archivio": "Definir como archivo",
  "Conta le foto": "Contar fotos", "Avvia la descrizione": "Iniciar la descripción", "Archivio della ricerca:": "Archivo de búsqueda:",
  "Acquista crediti": "Comprar créditos", "Sostieni il museo": "Apoyar al museo", "Sostieni ctrlalt.museum": "Apoyar a ctrlalt.museum",
  "Come funziona Labellula": "Cómo funciona Labellula", "Telefono e tablet": "Teléfono y tableta", "Scorciatoie": "Atajos", "Privacy": "Privacidad",
  "Tre modi di usare Labellula": "Tres formas de usar Labellula", "Primi passi": "Primeros pasos", "Consigli": "Consejos",
  "Attiva l'accesso dalla rete": "Activar el acceso desde la red", "Disattiva": "Desactivar", "Cambia la password": "Cambiar la contraseña", "Esci": "Salir",
  "Tutto gira su questo computer: nessuna foto lascia la macchina.": "Todo funciona en este ordenador: ninguna foto sale de la máquina.",
  "Cartella": "Carpeta", "Ultime:": "Recientes:", "Indice: {n} schede, aggiornato il {data}.": "Índice: {n} fichas, actualizado el {data}.",
  "Ricerca per significato attiva.": "Búsqueda por significado activa.", "Schede scritte da:": "Fichas escritas por:", "Ricerca…": "Buscando…",
  "Foto simili a <b>{nome}</b> ({n}).": "Fotos similares a <b>{nome}</b> ({n}).", "Torna alla ricerca": "Volver a la búsqueda",
  "L'archivio è ancora vuoto.": "El archivo todavía está vacío.", "Guarda l'archivio dimostrativo di ctrlalt.museum": "Ver el archivo de demostración de ctrlalt.museum",
  "oppure": "o", "＋ Descrivi le tue foto": "＋ Describir tus fotos", "Nessuna foto trovata. Prova con meno parole o togli un filtro.": "No se encontraron fotos. Prueba con menos palabras o quita un filtro.",
  "{n} foto": "{n} fotos", ", ne vedi {m}": ", ves {m}", "Descrizione": "Descripción", "Testi visibili": "Textos visibles", "Luogo e periodo": "Lugar y fecha",
  "Occasione": "Ocasión", "Data": "Fecha", "Persone (dalla descrizione)": "Personas (según la descripción)", "Aspetti fotografici": "Aspectos fotográficos",
  "Parole chiave": "Palabras clave", "Dubbi del modello": "Dudas del modelo", "Generato con:": "Generado con:", "Categoria": "Categoría",
  "{n} foto in tutto, da descrivere: {d}": "{n} fotos en total, por describir: {d}", "{f}/{t} foto": "{f}/{t} fotos", "Descrivo «{nome}»": "Describiendo «{nome}»",
  "Errore": "Error", "Errore:": "Error:", "Lingua": "Idioma", "Lingua dell'interfaccia e delle nuove schede": "Idioma de la interfaz y de las nuevas fichas",
  "Le nuove schede saranno scritte in {l}. Per riscrivere quelle esistenti: «＋ Descrivi foto» › «Aggiorna».": "Las nuevas fichas se escribirán en {l}. Para reescribir las existentes: «＋ Describir fotos» › «Actualizar».",
});

function T(testo, valori) {
  let s = testo;
  if (LINGUA !== "it") {
    const d = TRADUZIONI[LINGUA] || {};
    s = d[testo] ?? (TRADUZIONI.en[testo] ?? testo);
  }
  if (valori) for (const [k, v] of Object.entries(valori)) s = s.split("{" + k + "}").join(String(v));
  return s;
}

// ------------------------------------------------------------------ blocchi lunghi (Aiuto, Elaborazione remota)
// Per francese, tedesco e spagnolo si usa l'inglese.
const BLOCCHI_EN = {
  "aiuto-intro": "Labellula looks at each photo with an artificial intelligence model and writes a <b>record</b>: title, description, legible writings, place and date (with the source), occasion, people, keywords. Records are text files in a <code>_txt</code> folder next to the photos: they stay yours and can be read with any program. Then you can search the whole archive by words or by meaning.",
  "aiuto-gpu": "To describe photos on this computer you need a <b>graphics card with about 12 GB</b> of memory, or another computer on your network that has one (field «Ollama on:»). Without it, search still works but describing is too slow: use <b>remote processing</b>, which supports ctrlalt.museum.",
  "aiuto-modo1": "<b>Everything on your computer, free.</b> Download Labellula from GitHub and run the installer: it checks your computer and installs Ollama and the right model. You need a graphics card with about 12 GB, yours or on another computer of your network. Photos never leave your home. <a id=\"a-guida\" target=\"_blank\" rel=\"noopener\">Installation guide</a>. A donation to the museum is welcome.",
  "aiuto-modo2": "<b>Remote processing, with credits, supporting the museum.</b> No GPU: buy a code and your photos are described by Labellula's GPU. Only a reduced copy without metadata reaches the server, and it is not stored; the record comes straight back to your computer. <i>Coming soon.</i>",
  "aiuto-modo3": "<b>Turnkey, for museums and archives.</b> For large collections or photo archives: installation, description, review and archive formats. On request.",
  "aiuto-passo1": "Click <b>＋ Describe photos</b>, choose the folder and press <b>Count photos</b> to know how long it takes.",
  "aiuto-passo2": "Try with <b>only the first 20 photos</b>, look at the records, then run the whole folder. You can stop and resume whenever you like.",
  "aiuto-passo3": "If the folder is not inside the search archive, use <b>Set as archive</b>.",
  "aiuto-passo4": "Search: «karate competition», «fox», «Commodore», «red car». Click a photo for the full record. Search by meaning also works across languages.",
  "aiuto-cons1": "Give folders clear names, for example <code>2024-02-04 karate competition Turin</code>: date, place and event are checked against the photo data and end up in the record.",
  "aiuto-cons2": "In <code>config.yaml</code>, under <code>luoghi_noti</code>, you can explain names only you know, for example «Home».",
  "aiuto-cons3": "<b>Only to be checked</b> shows the records where the model has doubts.",
  "aiuto-cons4": "<b>Export CSV</b> saves the results for Excel or LibreOffice.",
  "aiuto-rete": "You can open the search from a phone, tablet or other computers on the same Wi-Fi network, with a password. On this computer no password is needed.",
  "aiuto-scorciatoie": "<kbd>/</kbd> search · <kbd>?</kbd> help · <kbd>←</kbd> <kbd>→</kbd> previous and next photo · <kbd>Esc</kbd> close",
  "aiuto-privacy": "Locally no photo leaves your computer, and the page answers only this computer (or, if you enable it, your network with a password). Face recognition, if enabled, always stays local. Recent searches are stored only in this browser.",
  "descrivi-intro": "Choose the folder: Labellula describes all the photos it contains, subfolders included, and writes the records in <code>_txt</code> next to the photos. Photos already described are skipped. Folder names (dates, places, events) help the model a lot.",
  "crediti-1": "No suitable graphics card, or a very large archive? With a <b>credit code</b> your photos are described by Labellula's GPU, outside your computer: each described photo uses one credit. Search, records and photos stay on your computer.",
  "crediti-2": "If you have a GPU with at least 12 GB you can do everything for free on your computer: see <button type=\"button\" class=\"link apri-aiuto\">Help › Three ways to use Labellula</button>.",
  "crediti-li1": "Only a <b>reduced copy without metadata</b> reaches the server (no GPS, no folder names unless you choose so).",
  "crediti-li2": "Photo and record are <b>not stored</b> on the server: the record comes straight back to your computer.",
  "crediti-li3": "Face recognition always stays on your computer only.",
  "crediti-li4": "The first photos are free to try.",
  "crediti-4": "The proceeds support <a href=\"https://ctrlalt.museum/\" target=\"_blank\" rel=\"noopener\">ctrlalt.museum</a>, the computer museum of the comPVter cultural association in Pavia.",
};

// ------------------------------------------------------------------ applicazione alla pagina
function traduciPagina() {
  document.documentElement.lang = LINGUA;
  if (LINGUA === "it") return;
  document.querySelectorAll("[data-t]").forEach((el) => {
    const h = BLOCCHI_EN[el.dataset.t];
    if (h) el.innerHTML = h;
  });
  const cammina = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodi = [];
  while (cammina.nextNode()) nodi.push(cammina.currentNode);
  for (const n of nodi) {
    const s = n.nodeValue.trim();
    if (s && !n.parentElement.closest("[data-t], script, code")) {
      const tr = T(s);
      if (tr !== s) n.nodeValue = n.nodeValue.replace(s, tr);
    }
  }
  for (const attr of ["placeholder", "title", "aria-label"]) {
    document.querySelectorAll(`[${attr}]`).forEach((el) => {
      const s = el.getAttribute(attr);
      const tr = T(s);
      if (tr !== s) el.setAttribute(attr, tr);
    });
  }
}
