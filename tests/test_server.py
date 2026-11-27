"""Server HTTP: protezioni (Host, intestazione delle POST) e limiti per chi entra dalla rete di casa."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from PIL import Image

from labellula.accesso import NOME_COOKIE, impronta
from labellula.config import PREDEFINITI, Config, _unisci
from labellula.indice import Indice, costruisci
from labellula.server import Applicazione, crea_handler

SCHEDA = """DESCRIZIONE: Un computer Commodore PET.
CATEGORIA: hardware-vintage
PAROLE CHIAVE: commodore
"""


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.arch = base / "arch"
        (cls.arch / "museo" / "_txt").mkdir(parents=True)
        Image.new("RGB", (64, 48)).save(cls.arch / "museo" / "pet.jpg", "JPEG")
        (cls.arch / "museo" / "_txt" / "pet.txt").write_text(SCHEDA, encoding="utf-8")
        cls.fuori = base / "fuori"
        cls.fuori.mkdir()
        dati = base / "dati"
        dati.mkdir()
        costruisci(cls.arch, dati / "indice.sqlite3", estensioni=[".jpg"], avanzamento=lambda *a: None)
        cls.cfg = Config(dati=_unisci(PREDEFINITI, {"archivio": {"radice": str(cls.arch)},
                                                    "server": {"password_hash": impronta("password-di-prova", 1000)},
                                                    "dati": {"cartella": str(dati)}}),
                         cartella_base=base)
        cls.app = Applicazione(cls.arch, Indice(dati / "indice.sqlite3"), dati / "miniature", [".jpg"], cfg=cls.cfg)
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), crea_handler(cls.app))
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.token = cls.app.sessioni.crea()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.app.indice.chiudi()
        cls.tmp.cleanup()

    def chiama(self, percorso, corpo=None, host="localhost", intestazione=True, cookie=True):
        h = {"Host": host}
        if corpo is not None:
            h["Content-Type"] = "application/json"
            if intestazione:
                h["X-Labellula"] = "1"
        if cookie:
            h["Cookie"] = f"{NOME_COOKIE}={self.token}"
        req = urllib.request.Request(self.url + percorso, headers=h,
                                     data=None if corpo is None else json.dumps(corpo).encode())
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def dalla_rete(self):
        """Simula una richiesta che arriva da un altro dispositivo della rete di casa."""
        return mock.patch("labellula.accesso.e_locale", return_value=False)

    # ------------------------------------------------------------ da questo computer
    def test_ricerca(self):
        stato, r = self.chiama("/api/cerca?q=commodore")
        self.assertEqual(stato, 200)
        self.assertEqual(r["totale"], 1)

    def test_host_estraneo_rifiutato(self):
        self.assertEqual(self.chiama("/api/info", host="attacco.example")[0], 403)

    def test_post_senza_intestazione_rifiutata(self):
        self.assertEqual(self.chiama("/api/lavoro/ferma", {}, intestazione=False)[0], 403)

    def test_cartelle_da_questo_computer_anche_fuori_archivio(self):
        stato, r = self.chiama("/api/cartelle?percorso=" + urllib.request.quote(str(self.fuori)))
        self.assertEqual(stato, 200)

    # ------------------------------------------------------------ dalla rete di casa
    def test_rete_senza_sessione(self):
        with self.dalla_rete():
            self.assertEqual(self.chiama("/api/cerca?q=x", cookie=False)[0], 401)

    def test_rete_con_sessione_cerca(self):
        with self.dalla_rete():
            self.assertEqual(self.chiama("/api/cerca?q=commodore")[0], 200)

    def test_rete_non_cambia_impostazioni(self):
        with self.dalla_rete():
            for percorso, corpo in [("/api/ollama", {"indirizzo": "203.0.113.5"}),
                                    ("/api/ollama/prova", {"indirizzo": "192.168.1.1"}),
                                    ("/api/archivio", {"radice": str(self.fuori)}),
                                    ("/api/lingua", {"lingua": "en"}),
                                    ("/api/rete", {"attiva": False})]:
                self.assertEqual(self.chiama(percorso, corpo)[0], 403, percorso)
        self.assertEqual(self.cfg["modello"]["ollama_url"], PREDEFINITI["modello"]["ollama_url"])
        self.assertEqual(self.app.radice, self.arch.resolve())

    def test_rete_vede_solo_le_cartelle_dell_archivio(self):
        with self.dalla_rete():
            stato, r = self.chiama("/api/cartelle?percorso=")
            self.assertEqual(stato, 200)
            self.assertEqual(Path(r["percorso"]).resolve(), self.arch.resolve())
            self.assertIsNone(r["padre"])
            self.assertEqual(self.chiama("/api/cartelle?percorso=/")[0], 403)
            self.assertEqual(self.chiama("/api/cartelle?percorso=" + urllib.request.quote(str(self.fuori)))[0], 403)

    def test_rete_descrive_solo_nell_archivio(self):
        with self.dalla_rete():
            self.assertEqual(self.chiama("/api/lavoro", {"cartella": str(self.fuori)})[0], 403)
            self.assertEqual(self.chiama("/api/conta?percorso=" + urllib.request.quote(str(self.fuori)))[0], 403)


class TestAggiornamentoIndice(unittest.TestCase):
    def test_ricerche_durante_la_sostituzione_dell_indice(self):
        """Le ricerche in corso finiscono prima che l'indice venga chiuso e sostituito."""
        from labellula.server import LetturaScrittura
        lock = LetturaScrittura()
        ordine = []
        dentro = threading.Event()

        def lettore():
            with lock.leggi():
                dentro.set()
                ordine.append("lettura iniziata")
                threading.Event().wait(0.2)
                ordine.append("lettura finita")
        t = threading.Thread(target=lettore)
        t.start()
        dentro.wait(2)
        with lock.scrivi():
            ordine.append("sostituzione")
        t.join()
        self.assertEqual(ordine, ["lettura iniziata", "lettura finita", "sostituzione"])


if __name__ == "__main__":
    unittest.main()
