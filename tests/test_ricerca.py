import tempfile
import unittest
from pathlib import Path

from PIL import Image

from labellula.indice import Filtri, Indice, costruisci
from labellula.schede import leggi_testo

SCHEDA = """DESCRIZIONE: Un computer Commodore CBM 2001 su un tavolo,
con schermo monocromatico.

TESTI VISIBILI: commodore, CBM, Città di Pavia

LUOGO E PERIODO: non determinabile

CATEGORIA: hardware-vintage

PERSONE: nessuna

PAROLE CHIAVE: Commodore, computer vintage, anni '80

---
File: DSCF0001.JPG
Cartella: H:\\Archivio\\2022\\museo
Data: 12/05/2022 14:33 (da EXIF)
Generato con: qwen3-vl:8b-instruct (prompt v4)

NUMERO PERSONE RILEVATE:
- Volti riconosciuti: 1
"""


class TestSchede(unittest.TestCase):
    def test_lettura(self):
        s = leggi_testo(SCHEDA)
        self.assertTrue(s.descrizione.startswith("Un computer Commodore"))
        self.assertIn("schermo monocromatico", s.descrizione)  # sezione su più righe
        self.assertEqual(s.categoria, "hardware-vintage")
        self.assertEqual(s.data_iso, "2022-05-12")
        self.assertEqual(s.anno(), 2022)
        self.assertEqual(s.modello, "qwen3-vl:8b-instruct (prompt v4)")
        self.assertNotIn("Volti riconosciuti", s.piede)  # blocco legacy ignorato

    def test_anno_dalla_cartella(self):
        s = leggi_testo("DESCRIZIONE: x\n\n---\nData: sconosciuta (prova a dedurla dalla cartella)\n")
        self.assertEqual(s.anno("2004/2004-08-26 Auronzo"), 2004)


class TestIndice(unittest.TestCase):
    def test_costruisci_e_cerca(self):
        with tempfile.TemporaryDirectory() as d:
            radice = Path(d) / "archivio"
            for cart, testo in [("2022/museo", SCHEDA), ("2023/mare", SCHEDA.replace("Commodore", "Spiaggia").replace("commodore", "spiaggia")
                                                                 .replace("hardware-vintage", "viaggi-e-vacanze")
                                                                 .replace("2022", "2023"))]:
                c = radice / cart
                (c / "_txt").mkdir(parents=True)
                Image.new("RGB", (8, 8)).save(c / "DSCF0001.JPG")
                (c / "_txt" / "DSCF0001.txt").write_text(testo, encoding="utf-8")
            f = Path(d) / "dati" / "indice.sqlite3"
            r = costruisci(radice, f, avanzamento=lambda *_: None)
            self.assertEqual(r["schede_indicizzate"], 2)
            ix = Indice(f)
            self.addCleanup(ix.chiudi)  # su Windows un file SQLite aperto non si può cancellare
            self.assertEqual(ix.cerca(Filtri(testo="commod"))["totale"], 1)      # inizio parola
            self.assertEqual(ix.cerca(Filtri(testo="CITTA"))["totale"], 2)       # senza accenti
            self.assertEqual(ix.cerca(Filtri(categoria="viaggi-e-vacanze"))["totale"], 1)
            self.assertEqual(ix.cerca(Filtri(anno_da=2023))["totale"], 1)
            self.assertEqual(ix.cerca(Filtri(testo="'\"*) OR"))["totale"], 0)  # input strano: nessun errore
            self.assertEqual(ix.cerca(Filtri(testo="computer rosso"))["totale"], 0)
            self.assertEqual(ix.cerca(Filtri(testo="calcolatore"))["totale"], 2)    # sinonimo di computer
            self.assertEqual(ix.cerca(Filtri(testo="un tavolo"))["totale"], 2)      # "un" ignorato
            self.assertIsNotNone(ix.scheda("2022/museo/DSCF0001.JPG"))
            self.assertEqual(ix.cerca(Filtri(cartella="2022"))["totale"], 1)         # sottocartelle comprese
            self.assertEqual(ix.cerca(Filtri(cartella="202"))["totale"], 0)          # non un prefisso qualsiasi
            self.assertEqual(ix.statistiche()["schede"], 2)
            self.assertEqual(len(ix.tutte(Filtri(testo="tavolo"))), 2)
            ix.chiudi()

    def test_significato_con_modello_finto(self):
        import numpy as np
        from labellula import semantico as sem

        class Finto:  # "modello" che riconosce solo due concetti: computer e mare
            modello = "finto"
            def vettori(self, testi):
                m = np.array([[("ommodore" in t or "computer" in t) * 1.0, ("piaggia" in t or "mare" in t) * 1.0, 0.1]
                              for t in testi], dtype=np.float32)
                return m / np.linalg.norm(m, axis=1, keepdims=True)

        with tempfile.TemporaryDirectory() as d:
            radice = Path(d) / "archivio"
            for cart, testo in [("2022/museo", SCHEDA),
                                ("2023/mare", SCHEDA.replace("Commodore", "Spiaggia").replace("commodore", "spiaggia")
                                 .replace("computer", "ombrellone"))]:
                c = radice / cart
                (c / "_txt").mkdir(parents=True)
                Image.new("RGB", (8, 8)).save(c / "DSCF0001.JPG")
                (c / "_txt" / "DSCF0001.txt").write_text(testo, encoding="utf-8")
            dati = Path(d) / "dati"
            costruisci(radice, dati / "indice.sqlite3", avanzamento=lambda *_: None)
            r = sem.costruisci(dati / "indice.sqlite3", dati, Finto(), avanzamento=lambda *_: None)
            self.assertEqual(r["calcolate"], 2)
            self.assertEqual(sem.costruisci(dati / "indice.sqlite3", dati, Finto(),
                                            avanzamento=lambda *_: None)["calcolate"], 0)  # incrementale
            ix, s = Indice(dati / "indice.sqlite3"), sem.IndiceSemantico(dati, Finto())
            self.addCleanup(ix.chiudi)
            # "mare" non compare nel testo della scheda di spiaggia come parola cercata, ma il senso sì
            r = ix.cerca(Filtri(testo="al mare"), semantico=s, modo="significato")
            self.assertEqual(r["risultati"][0]["id_foto"], "2023/mare/DSCF0001.JPG")
            r = ix.cerca(Filtri(testo="computer", categoria="viaggi-e-vacanze"), semantico=s, modo="misto")
            self.assertTrue(all(x["categoria"] == "viaggi-e-vacanze" for x in r["risultati"]))
            self.assertEqual([x["id_foto"] for x in ix.simili("2022/museo/DSCF0001.JPG", s)], ["2023/mare/DSCF0001.JPG"])
            ix.chiudi()

    def test_radice_e_sinonimi(self):
        from labellula.indice import _query_fts, _radice
        self.assertEqual(_radice("rossa"), "ross")
        self.assertEqual(_radice("barche"), "barc")
        self.assertEqual(_radice("mare"), "mare")  # parole brevi invariate
        self.assertIn('"vettur"*', _query_fts("automobile rossa"))
        self.assertEqual(_query_fts("barca a vela").count(" AND "), 1)


if __name__ == "__main__":
    unittest.main()
