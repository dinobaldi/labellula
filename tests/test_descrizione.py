import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from labellula import foto as F
from labellula.descrizione import Opzioni, componi_prompt, degenerata, esegui, file_scheda
from labellula.motori import Risposta
from labellula.schede import leggi_file

RISPOSTA = """DESCRIZIONE: Un computer Commodore PET su un tavolo.
TESTI VISIBILI: commodore
LUOGO E PERIODO: non determinabile
CATEGORIA: hardware-vintage
PERSONE: nessuna
PAROLE CHIAVE: Commodore, PET, computer vintage"""


class MotoreFinto:
    nome = "finto:1"
    locale = True

    def __init__(self, risposte=None):
        self.risposte = list(risposte or [])
        self.chiamate = []

    def controlla(self):
        pass

    def descrivi(self, jpeg, prompt, ripetizioni=1.1, lunghezza=900):
        self.chiamate.append((jpeg, prompt, ripetizioni))
        return self.risposte.pop(0) if self.risposte else Risposta(RISPOSTA)


def foto_con_gps(percorso: Path):
    im = Image.new("RGB", (3000, 2000), (200, 30, 30))
    ex = Image.Exif()
    ex[271] = "FUJIFILM"
    ex[272] = "X-T4"
    gps = ex.get_ifd(0x8825)
    gps.update({1: "N", 2: (45.0, 11.0, 0.0), 3: "E", 4: (9.0, 9.0, 0.0)})
    im.save(percorso, "JPEG", exif=ex)


class TestDescrizione(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.radice = Path(self.tmp.name) / "archivio"
        (self.radice / "2022 museo").mkdir(parents=True)
        self.foto = self.radice / "2022 museo" / "PET_2022-05-12.jpg"
        foto_con_gps(self.foto)

    def tearDown(self):
        self.tmp.cleanup()

    def _esegui(self, motore, **kw):
        return esegui(self.radice, motore, Opzioni(), [".jpg"], [], Path(self.tmp.name) / "dati",
                      stampa=lambda s: None, **kw)

    def test_copia_ridotta_senza_metadati(self):
        im = F.apri(self.foto)
        dati = F.copia_ridotta(im, 1344)
        with Image.open(io.BytesIO(dati)) as r:
            self.assertEqual(max(r.size), 1344)
            self.assertEqual(len(r.getexif()), 0)   # niente EXIF né GPS nella copia mandata al modello

    def test_scheda_scritta_e_leggibile(self):
        r = self._esegui(MotoreFinto())
        self.assertEqual(r["fatte"], 1)
        s = leggi_file(file_scheda(self.foto, "_txt"))
        self.assertEqual(s.categoria, "hardware-vintage")
        self.assertEqual(s.data_iso, "2022-05-12")          # dal nome del file
        self.assertIn("finto:1 (prompt v5.2)", s.modello)
        self.assertIn("data 2022", s.piede.get("Indizi dalle cartelle", ""))
        self.assertIn("lat 45.18", s.piede.get("Luogo GPS", ""))

    def test_riprende_e_rifai(self):
        m = MotoreFinto()
        self._esegui(m)
        self._esegui(m)
        self.assertEqual(len(m.chiamate), 1)                 # la seconda volta non c'è niente da fare
        self._esegui(m, rifai=True)
        self.assertEqual(len(m.chiamate), 2)

    def test_ripetizioni_riprova_e_segnala(self):
        incantata = Risposta("DESCRIZIONE: " + "Una tastiera beige con tasti. " * 10, troncata=True)
        m = MotoreFinto([incantata, incantata])
        r = self._esegui(m)
        self.assertEqual(r["da_verificare"], 1)
        self.assertEqual(m.chiamate[1][2], 1.5)
        self.assertTrue(leggi_file(file_scheda(self.foto, "_txt")).avviso)

    def test_prompt_senza_percorso(self):
        info, _ = F.analizza(self.foto)
        con = componi_prompt(self.foto, info, "colleziona computer", ["altro"])
        senza = componi_prompt(self.foto, info, "colleziona computer", ["altro"], con_percorso=False)
        self.assertIn("PET_2022-05-12.jpg", con)
        self.assertNotIn("PET_2022-05-12.jpg", senza)
        self.assertNotIn("museo", senza)
        self.assertNotIn("lat 45", senza)
        self.assertIn("colleziona computer", senza)

    def test_avanzamento_e_arresto(self):
        (self.radice / "2022 museo" / "altra.jpg").write_bytes(self.foto.read_bytes())
        passi = []
        r = self._esegui(MotoreFinto(), avanzamento=passi.append, fermati=lambda: len(passi) >= 2)
        self.assertEqual(r["fatte"], 1)                     # si ferma dopo la prima foto
        self.assertEqual(passi[0]["totale"], 2)

    def test_elenco_cartelle(self):
        from labellula.lavori import elenca_cartelle
        r = elenca_cartelle(str(self.radice / "2022 museo"), [".jpg"])
        self.assertEqual((r["foto"], r["schede"]), (1, 0))
        r = elenca_cartelle(str(self.radice), [".jpg"])
        self.assertEqual([c["nome"] for c in r["cartelle"]], ["2022 museo"])

    def test_aggiorna_solo_schede_vecchie(self):
        m = MotoreFinto()
        self._esegui(m)                                      # scheda v5.x
        self.assertEqual(self._esegui(m, aggiorna=True)["fatte"], 0)
        dest = file_scheda(self.foto, "_txt")
        dest.write_text(dest.read_text(encoding="utf-8").replace("(prompt v5.2)", "(prompt v4)"), encoding="utf-8")
        self.assertEqual(self._esegui(m, aggiorna=True)["fatte"], 1)   # scheda v4: va rifatta

    def test_stagione_momento(self):
        from datetime import datetime
        self.assertEqual(F.stagione_momento(datetime(2024, 2, 18, 17, 4)), "inverno, pomeriggio")
        self.assertEqual(F.stagione_momento(datetime(2024, 2, 18, 17, 4), lat=-33.9), "estate, pomeriggio")
        self.assertEqual(F.stagione_momento(datetime(2006, 11, 1, 12, 30), lat=4.2), "mezzogiorno")  # tropici
        self.assertEqual(F.stagione_momento(datetime(2006, 8, 6)), "estate")       # ora 00:00 = sconosciuta
        self.assertEqual(F.stagione_momento(None), "")

    def test_foto_heic(self):
        if not F.HEIC:
            self.skipTest("pillow-heif non installato")
        heic = self.radice / "2022 museo" / "IMG_0001.HEIC"
        im = Image.new("RGB", (800, 600), (10, 120, 200))
        ex = Image.Exif()
        ex[271], ex[272] = "Apple", "iPhone 13 Pro"
        ex.get_ifd(0x8769)[36867] = "2022:07:30 15:42:10"
        im.save(heic, format="HEIF", exif=ex.tobytes())
        info, img = F.analizza(heic)
        self.assertEqual(img.size, (800, 600))
        self.assertIn("30/07/2022 15:42", info.quando)
        r = esegui(self.radice, MotoreFinto(), Opzioni(), [".jpg", ".heic"], [], Path(self.tmp.name) / "dati",
                   stampa=lambda s: None)
        self.assertEqual(r["fatte"], 2)                      # la JPG e la HEIC
        self.assertTrue(file_scheda(heic, "_txt").exists())

    def test_degenerata(self):
        self.assertTrue(degenerata("Una tastiera beige con tasti. " * 5))
        self.assertFalse(degenerata(RISPOSTA))


if __name__ == "__main__":
    unittest.main()
