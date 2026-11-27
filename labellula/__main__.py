"""Comandi di Labellula.

  python -m labellula descrivi  [--config config.yaml] [--cartella X] [--limite N] [--rifai]
  python -m labellula indicizza [--config config.yaml]
  python -m labellula vettori   [--config config.yaml]
  python -m labellula server    [--config config.yaml] [--porta 8765] [--non-aprire]
  python -m labellula verifica  [--json] [--configura]     questo computer può descrivere le foto in locale?
  python -m labellula modelli   [--solo-ricerca] [--forza]  scarica solo i modelli adatti a questo computer
  python -m labellula prova     [--modello X]               descrive una foto di esempio e misura il tempo
  python -m labellula usa-ollama URL [--modello X]          usa l'Ollama di un altro computer (es. http://192.168.1.20:11434)
  python -m labellula usa-ollama locale                     torna all'Ollama di questo computer
  python -m labellula diagnosi  [--cartella X]              cosa c'è e cosa manca (da fotografare e mandare)
  python -m labellula rete attiva|disattiva|stato           accesso da telefono e tablet, con password
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import carica_config
from .registro import NOME_FILE as REGISTRO


def _percorsi(cfg):
    dati = cfg.cartella_dati
    return dati / "indice.sqlite3", dati / "miniature"


def cmd_descrivi(cfg, args) -> int:
    from .descrizione import Opzioni, esegui
    from .motori import ErroreMotore, crea_motore
    radice = Path(args.cartella) if args.cartella else cfg.radice_archivio
    if not radice.is_dir():
        print(f"Cartella non trovata: {radice}")
        return 2
    try:
        if args.modello:
            cfg["modello"]["nome"] = args.modello
        motore = crea_motore(cfg)
        opzioni = Opzioni.da_config(cfg)
        opzioni.radice = cfg.radice_archivio            # le cartelle sotto la radice sono indizi
        if args.cartella:
            try:
                radice.resolve().relative_to(cfg.radice_archivio.resolve())
            except (ValueError, OSError):
                opzioni.radice = None                   # cartella fuori dall'archivio: è lei la radice
        if args.prompt:
            opzioni.versione = args.prompt
        r = esegui(radice, motore, opzioni, cfg["archivio"]["estensioni"],
                   cfg["archivio"]["salta_cartelle"], cfg.cartella_dati,
                   limite=args.limite, rifai=args.rifai, aggiorna=args.aggiorna)
    except ErroreMotore as ex:
        print(ex)
        return 2
    return 1 if r["errori"] else 0


def cmd_indicizza(cfg) -> int:
    from .indice import costruisci
    file_indice, _ = _percorsi(cfg)
    registro = cfg.radice_archivio / REGISTRO if cfg["volti"]["attivo"] else None
    print(f"Archivio: {cfg.radice_archivio}")
    print(f"Indice  : {file_indice}")
    print(f"Volti   : {'attivo (' + str(registro) + ')' if registro else 'non attivo'}")
    r = costruisci(
        cfg.radice_archivio, file_indice,
        cartella_txt=cfg["schede"]["cartella_txt"],
        estensioni=cfg["archivio"]["estensioni"],
        salta_cartelle=cfg["archivio"]["salta_cartelle"],
        registro_file=registro,
    )
    print(f"Fatto: {r['schede_indicizzate']} schede indicizzate su {r['foto_trovate']} foto trovate"
          f" ({r['foto_con_persone']} foto con persone riconosciute) in {r['secondi']} s.")
    return 0


def _client(cfg):
    from .semantico import ClientEmbedding
    return ClientEmbedding(cfg["modello"]["ollama_url"], cfg["modello"]["embedding"])


def cmd_vettori(cfg) -> int:
    from .semantico import costruisci
    file_indice, _ = _percorsi(cfg)
    r = costruisci(file_indice, cfg.cartella_dati, _client(cfg))
    print(f"Fatto: {r['calcolate']} vettori calcolati ({r['schede']} schede in totale) in {r['secondi']} s.")
    return 0


def cmd_verifica(cfg, args) -> int:
    import json
    from .config import imposta_valore
    from .hardware import testo, verifica
    r = verifica(cfg["modello"]["ollama_url"])
    cfg.cartella_dati.mkdir(parents=True, exist_ok=True)
    (cfg.cartella_dati / "hardware.json").write_text(r.json(), encoding="utf-8")
    if args.configura and cfg.file:
        motore = "remoto" if r.verdetto == "insufficiente" else "ollama"
        cambiato = imposta_valore(cfg.file, "modello", "motore", motore)
        if r.modello_consigliato:
            cambiato |= imposta_valore(cfg.file, "modello", "nome", r.modello_consigliato)
        if cambiato and not args.json:
            print(f"config.yaml aggiornato: motore {motore}"
                  + (f", modello {r.modello_consigliato}" if r.modello_consigliato else "") + " (copia .bak salvata).")
    print(r.json() if args.json else testo(r))
    return {"ok": 0, "limite": 0, "da_provare": 0}.get(r.verdetto, 3)


def cmd_modelli(cfg, args) -> int:
    """Scarica con Ollama solo i modelli che servono, e solo se il computer è adatto (salvo --forza)."""
    import shutil
    import subprocess
    from .hardware import EMBEDDING, avvia_ollama, verifica
    avvia_ollama(cfg["modello"]["ollama_url"])
    r = verifica(cfg["modello"]["ollama_url"])
    if not r.ollama_installato or not shutil.which("ollama"):
        print("Ollama non è installato: lancia l'installatore (tools/installa.*) o scaricalo da https://ollama.com/download")
        return 2
    voluti = [EMBEDDING["nome"]]
    if not args.solo_ricerca:
        if r.verdetto == "insufficiente" and not args.forza:
            print("Questo computer non è adatto a descrivere le foto: scarico solo il modello per la ricerca "
                  f"({EMBEDDING['nome']}, {EMBEDDING['disco_gb']} GB). Usa --forza per scaricare comunque.")
        else:
            voluti.insert(0, r.modello_consigliato or cfg["modello"]["nome"])
    presenti = {x.removesuffix(":latest") for x in r.modelli_presenti}
    for m in voluti:
        if m in presenti:
            print(f"{m}: già presente")
            continue
        print(f"Scarico {m}…")
        if subprocess.run(["ollama", "pull", m]).returncode != 0:
            print(f"Download di {m} non riuscito.")
            return 1
    return 0


def cmd_prova(cfg, args) -> int:
    """Descrive una foto di esempio in una cartella temporanea e misura il tempo vero su questo computer."""
    import json
    import shutil
    import tempfile
    import time
    from .descrizione import Opzioni, descrivi_foto
    from .motori import ErroreMotore, MotoreOllama
    esempio = Path(__file__).resolve().parent.parent / "examples" / "foto" / "03_hardware-vintage.jpg"
    if not esempio.exists():
        print(f"Foto di esempio non trovata: {esempio}")
        return 2
    modello = args.modello or cfg["modello"]["nome"]
    from .hardware import avvia_ollama
    avvia_ollama(cfg["modello"]["ollama_url"])
    motore = MotoreOllama(cfg["modello"]["ollama_url"], modello)
    try:
        motore.controlla()
    except ErroreMotore as ex:
        print(ex)
        return 2
    with tempfile.TemporaryDirectory() as d:
        cartella = Path(d) / "2022-05-12 ctrlalt.museum Pavia"
        cartella.mkdir()
        foto = cartella / esempio.name
        shutil.copy(esempio, foto)
        opzioni = Opzioni.da_config(cfg)
        opzioni.radice = Path(d)
        print(f"Prova con {modello}.")
        print("1/2 Carico il modello nella scheda video e descrivo la foto una prima volta "
              "(può volerci un minuto o due, la finestra resta ferma: è normale)…", flush=True)
        t_carico = time.time()
        descrivi_foto(foto, motore, opzioni)                 # 1ª volta: carica il modello in memoria
        print(f"    fatto in {time.time() - t_carico:.0f} s.", flush=True)
        print("2/2 Misuro la velocità sulla stessa foto…", flush=True)
        t0 = time.time()
        _, dubbio, titolo = descrivi_foto(foto, motore, opzioni)
        secondi = round(time.time() - t0, 1)
    giudizio = ("ottimo" if secondi <= 12 else "buono" if secondi <= 25 else "lento" if secondi <= 60
                else "troppo lento per un archivio")
    print(f"Fatto: {secondi} s a foto ({giudizio}). Titolo: «{titolo}».")
    print(f"Per 1.000 foto servono circa {secondi * 1000 / 3600:.1f} ore; per 10.000 circa {secondi * 10000 / 3600:.0f} ore.")
    f = cfg.cartella_dati / "hardware.json"
    try:
        dati = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except ValueError:
        dati = {}
    dati["prova"] = {"modello": modello, "secondi_a_foto": secondi, "giudizio": giudizio,
                     "quando": time.strftime("%Y-%m-%d %H:%M")}
    cfg.cartella_dati.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(dati, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if secondi <= 60 else 3


def cmd_usa_ollama(cfg, args) -> int:
    """Collega Labellula all'Ollama di un altro computer della rete (per esempio il PC con la GPU),
    oppure torna a quello locale. Prima prova la connessione, poi scrive config.yaml (con copia .bak)."""
    from .ollama_rete import applica
    r = applica(cfg, args.indirizzo or "locale", args.modello or "")
    if not r["ok"]:
        print(r["errore"])
        return 2
    nomi = ", ".join(m["nome"] for m in r["modelli_visione"]) or "nessuno"
    print(f"Ollama {r['versione']} raggiungibile su {r['url']} (rete {r['rete']}). Modelli che vedono le immagini: {nomi}")
    if r["modello"]:
        print(f"Fatto: Labellula userà {r['modello']} su {r['url']}. Riavvia Labellula se è aperto.")
    if r.get("avviso"):
        print("Nota: " + r["avviso"])
    return 0


def cmd_diagnosi(cfg, args) -> int:
    from .diagnosi import esegui
    print(esegui(cfg, Path(args.cartella) if args.cartella else None))
    return 0


def cmd_rete(cfg, args) -> int:
    import getpass
    from .accesso import impronta, indirizzi_locali, password_valida
    from .config import imposta_valore
    azione = (args.indirizzo or "stato").lower()
    s = cfg["server"]
    if azione == "attiva":
        if not s.get("password_hash") or input("Vuoi cambiare la password? [s/N] ").strip().lower().startswith("s"):
            while True:
                p1 = getpass.getpass("Nuova password (almeno 8 caratteri): ")
                motivo = password_valida(p1)
                if motivo:
                    print(motivo)
                    continue
                if getpass.getpass("Ripetila: ") != p1:
                    print("Non coincidono, riprova.")
                    continue
                imposta_valore(cfg.file, "server", "password_hash", impronta(p1))
                break
        imposta_valore(cfg.file, "server", "indirizzo", "0.0.0.0")
        print("Accesso dalla rete ATTIVO. Chiudi e riapri Labellula, poi dal telefono (stessa Wi-Fi) apri:")
        for ip in indirizzi_locali():
            print(f"   http://{ip}:{s['porta']}")
        print("La prima volta il firewall del computer può chiedere il permesso: consentilo sulle reti private.")
    elif azione == "disattiva":
        imposta_valore(cfg.file, "server", "indirizzo", "127.0.0.1")
        print("Accesso dalla rete disattivato. Chiudi e riapri Labellula.")
    else:
        attivo = s.get("indirizzo", "127.0.0.1") not in ("127.0.0.1", "localhost")
        print(f"Accesso dalla rete: {'attivo' if attivo else 'disattivato'}; password "
              f"{'impostata' if s.get('password_hash') else 'non impostata'}.")
    return 0


def cmd_server(cfg, args) -> int:
    from .indice import Indice
    from .server import Applicazione, avvia
    file_indice, cache = _percorsi(cfg)
    if not file_indice.exists():                 # primo avvio: indice (anche vuoto) creato da solo
        print("Primo avvio: creo l'indice di ricerca…")
        cmd_indicizza(cfg)
    semantico = None
    try:
        from .semantico import IndiceSemantico
        semantico = IndiceSemantico(cfg.cartella_dati, _client(cfg))
        print(f"Ricerca per significato: attiva ({len(semantico.ids)} schede, modello {semantico.client.modello})")
    except FileNotFoundError:
        print("Ricerca per significato: non disponibile (lancia 'python -m labellula vettori')")
    except Exception as ex:
        print(f"Ricerca per significato: non disponibile ({ex})")
    app = Applicazione(cfg.radice_archivio, Indice(file_indice), cache, cfg["archivio"]["estensioni"], semantico, cfg)
    avvia(app, cfg["server"]["indirizzo"], int(args.porta or cfg["server"]["porta"]),
          apri_browser=not args.non_aprire)
    return 0


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass
    ap = argparse.ArgumentParser(prog="labellula", description="Catalogazione locale di archivi fotografici")
    ap.add_argument("comando", choices=["descrivi", "indicizza", "vettori", "server", "verifica", "modelli", "prova", "usa-ollama", "diagnosi", "rete"])
    ap.add_argument("indirizzo", nargs="?", help="usa-ollama: indirizzo dell'Ollama da usare (es. 192.168.1.20) o «locale»")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--porta", type=int)
    ap.add_argument("--non-aprire", action="store_true", help="non apre il browser")
    ap.add_argument("--cartella", help="descrivi: elabora questa cartella invece di archivio.radice")
    ap.add_argument("--limite", type=int, default=0, help="descrivi: al massimo N foto (per le prove)")
    ap.add_argument("--rifai", action="store_true", help="descrivi: riscrive anche le schede già presenti")
    ap.add_argument("--aggiorna", action="store_true",
                    help="descrivi: riscrive solo le schede fatte con un prompt diverso da quello attuale (riprende da dove era)")
    ap.add_argument("--modello", help="descrivi, prova, usa-ollama: modello Ollama da usare al posto di quello in config")
    ap.add_argument("--json", action="store_true", help="verifica: risultato in JSON (per gli installatori)")
    ap.add_argument("--configura", action="store_true", help="verifica: scrive motore e modello consigliato in config.yaml")
    ap.add_argument("--solo-ricerca", action="store_true", help="modelli: scarica solo il modello per la ricerca per significato")
    ap.add_argument("--forza", action="store_true", help="modelli: scarica il modello di descrizione anche se il PC non è adatto")
    ap.add_argument("--prompt", choices=["v4", "v5"], help="descrivi: versione del prompt: v5 (scrive nelle schede «v5.2», è la predefinita) oppure v4")
    args = ap.parse_args(argv)
    percorso = Path(args.config)
    if not percorso.exists() and percorso.name == "config.yaml":
        import shutil                            # primo avvio: config.yaml nasce dall'esempio
        esempio = percorso.with_name("config.example.yaml")
        if not esempio.exists():
            esempio = Path(__file__).resolve().parent.parent / "config.example.yaml"
        if esempio.exists():
            shutil.copyfile(esempio, percorso)
            if not getattr(args, "json", False):
                print(f"Creato {percorso.resolve()} dall'esempio: modifica archivio.radice o usa «Imposta come archivio».")
    cfg = carica_config(percorso)
    if args.comando == "descrivi":
        return cmd_descrivi(cfg, args)
    if args.comando == "indicizza":
        return cmd_indicizza(cfg)
    if args.comando == "vettori":
        return cmd_vettori(cfg)
    if args.comando == "verifica":
        return cmd_verifica(cfg, args)
    if args.comando == "modelli":
        return cmd_modelli(cfg, args)
    if args.comando == "prova":
        return cmd_prova(cfg, args)
    if args.comando == "usa-ollama":
        return cmd_usa_ollama(cfg, args)
    if args.comando == "diagnosi":
        return cmd_diagnosi(cfg, args)
    if args.comando == "rete":
        return cmd_rete(cfg, args)
    return cmd_server(cfg, args)


if __name__ == "__main__":
    raise SystemExit(main())
