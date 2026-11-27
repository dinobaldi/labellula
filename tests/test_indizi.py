import importlib.util
import unittest
from datetime import date, datetime
from pathlib import Path

from labellula.indizi import descrizione_nome_file, raccogli, scomponi_cartella
from labellula.schede import leggi_testo

R = Path("H:/Archivio")
TORINO = {"name": "Turin", "admin1": "Piedmont", "admin2": "Provincia di Torino", "cc": "IT"}


class TestIndizi(unittest.TestCase):
    def test_scomponi_cartella(self):
        self.assertEqual(scomponi_cartella("2022-03-20 Castel San Giovanni - 18 compleanno Anna"),
                         (date(2022, 3, 20), "giorno", "Castel San Giovanni - 18 compleanno Anna"))
        self.assertEqual(scomponi_cartella("20060806 fuochi di vico soprano")[0], date(2006, 8, 6))
        self.assertEqual(scomponi_cartella("2024")[1:], ("anno", ""))
        self.assertEqual(scomponi_cartella("San-Martino-Campo")[2], "San Martino Campo")

    def test_nomi_file(self):
        for generico in ("DSCF1727.JPG", "DSCN0001.JPG", "IMG_20240204_101010.jpg", "DJI_0042.JPG",
                         "SANY0001.JPG", "PANO_20200101_1.jpg", "_1234.JPG", "1234.jpg", "PARA0001_LOWRES.JPG"):
            self.assertEqual(descrizione_nome_file(generico), "", generico)
        self.assertEqual(descrizione_nome_file("Tramonto sul Po 2.jpg"), "Tramonto sul Po")

    def test_data_confermata_viaggio_contrasto(self):
        f = R / "2024/2024-08-11 vacanza Olanda/2024-08-23 Ginevra/DSCF1.JPG"
        self.assertEqual(raccogli(f, R, datetime(2024, 8, 23), None).verifica_data, "confermata dall'EXIF")
        f = R / "2024/2024-08-11 vacanza Olanda/DSCF1.JPG"
        self.assertTrue(raccogli(f, R, datetime(2024, 8, 20), None).verifica_data.startswith("coerente"))
        self.assertTrue(raccogli(f, R, datetime(2019, 1, 1), None).verifica_data.startswith("in contrasto"))
        self.assertEqual(raccogli(f, R, None, None).verifica_data, "")

    def test_luogo(self):
        f = R / "2024/2024-02-04 gara karate Torino/DSCF1.JPG"
        self.assertTrue(raccogli(f, R, None, TORINO).verifica_luogo.startswith("confermati dal GPS"))
        f = R / "2024/2024-08-11 vacanza Olanda Belgio/DSCF1.JPG"
        g = {"name": "Bruges", "admin1": "Flanders", "admin2": "", "cc": "BE"}
        self.assertTrue(raccogli(f, R, None, g).verifica_luogo.startswith("paese confermato"))
        f = R / "2021/2021-06-17 Venezia/DSCF1.JPG"
        g = {"name": "Florence", "admin1": "Tuscany", "admin2": "Provincia di Firenze", "cc": "IT"}
        self.assertIn("Firenze", raccogli(f, R, None, g).verifica_luogo)

    def test_righe_prompt(self):
        f = R / "2022/2022-03-20 Castel San Giovanni - 18 compleanno Anna/DSCF2.JPG"
        righe = "\n".join(raccogli(f, R, None, None).righe_prompt())
        self.assertIn('"Castel San Giovanni - 18 compleanno Anna"', righe)
        self.assertIn("presunta valida", righe)
        self.assertNotIn("2022", raccogli(f, R, None, None).cartelle[0])

    def test_scheda_v5(self):
        s = leggi_testo("TITOLO: Gara di karate a Torino\nDESCRIZIONE: Due atleti.\nOCCASIONE: gara (dalla cartella)\n"
                        "CATEGORIA: famiglia-e-amici\nASPETTI FOTOGRAFICI: teleobiettivo\nDUBBI: nessuno\n")
        self.assertEqual(s.titolo, "Gara di karate a Torino")
        self.assertEqual(s.occasione, "gara (dalla cartella)")
        self.assertEqual(s.fotografia, "teleobiettivo")


    @unittest.skipUnless(importlib.util.find_spec("reverse_geocoder"), "reverse_geocoder (facoltativo) non installato")
    def test_luoghi_dalle_cartelle(self):
        from labellula.indizi import cerca_luoghi
        nomi = lambda s: [r["name"] for r in cerca_luoghi(s)]
        self.assertEqual(nomi("Castel San Giovanni - 18 compleanno Anna"), ["Castel San Giovanni"])
        self.assertEqual(nomi("Motorshow di Ginevra"), ["Geneve"])
        self.assertEqual(nomi("Casa rana bruchi insetti e prove"), [])
        self.assertEqual(nomi("gara karate Anna Torino"), ["Turin"])
        self.assertEqual(nomi("Anna a casa a San Martino"), [])      # ambiguo: 4 San Martino in Italia

    def test_ripulisci_e_luoghi_noti(self):
        from labellula.descrizione import luoghi_noti_citati, ripulisci
        self.assertEqual(ripulisci("PERSONE: nessuna. Le cartelle citano: nessuno.\nCATEGORIA: altro"),
                         "PERSONE: nessuna.\nCATEGORIA: altro")
        self.assertIn("Anna", ripulisci("PERSONE: una ragazza. Le cartelle citano: Anna."))
        ind = raccogli(R / "2021/2021-11-06 Casa Ravioli timelapse/DSCF1.JPG", R, None, None)
        self.assertEqual(luoghi_noti_citati(ind, {"Casa": "abitazione a Pavia", "Baldi srl": "azienda"}),
                         ['"Casa" = abitazione a Pavia'])


class TestEsonimi(unittest.TestCase):
    def test_munich_non_e_il_principato(self):
        from labellula.indizi import ESONIMI
        self.assertEqual(ESONIMI["munich"], "monaco di baviera")
        self.assertNotIn("monaco", ESONIMI.values())


if __name__ == "__main__":
    unittest.main()
