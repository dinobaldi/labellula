import os
import unittest
from pathlib import Path, PureWindowsPath

from labellula.ids import (
    id_foto, id_legacy, id_volto, rinomina_prefisso, scomponi_id_volto,
)

# percorsi nel formato del sistema su cui girano i test (Windows, macOS, Linux)
BASE = Path("D:/") if os.name == "nt" else Path("/mnt")
RADICE = str(BASE / "Archivio")
A = str(BASE / "Archivio" / "2022" / "2022-03-19 gara ciclistica" / "DSCF1727.JPG")
B = str(BASE / "Archivio" / "2023" / "2023-08 Polonia" / "Cracovia" / "DSCF1727.JPG")


class TestIds(unittest.TestCase):
    def test_id_foto_relativo_con_barre(self):
        self.assertEqual(id_foto(RADICE, A), "2022/2022-03-19 gara ciclistica/DSCF1727.JPG")

    def test_stesso_nome_cartelle_diverse_id_diversi(self):
        # il bug del codice legacy: stesso ID per foto diverse
        self.assertEqual(id_legacy(A, 1), id_legacy(B, 1))
        self.assertNotEqual(id_volto(RADICE, A, 1), id_volto(RADICE, B, 1))

    @unittest.skipUnless(os.name == "nt", "su Windows maiuscole e minuscole nei percorsi sono uguali")
    def test_radice_maiuscole_minuscole(self):
        self.assertEqual(id_foto("d:/archivio", A), "2022/2022-03-19 gara ciclistica/DSCF1727.JPG")

    def test_foto_fuori_radice(self):
        with self.assertRaises(ValueError):
            id_foto(RADICE, str(BASE / "altro" / "foto.jpg"))

    def test_radice_che_e_prefisso_di_un_altra_cartella(self):
        """«Archivio» non contiene «Archivio2»: dopo la radice ci vuole un separatore."""
        with self.assertRaises(ValueError):
            id_foto(RADICE, str(BASE / "Archivio2" / "foto.jpg"))
        with self.assertRaises(ValueError):            # percorsi Windows letti su Linux/macOS
            id_foto("H:\\Foto", "H:\\Fotografie\\2022\\x.jpg")
        self.assertEqual(id_foto("H:\\Foto", "H:\\Foto\\2022\\x.jpg"), "2022/x.jpg")

    def test_scomponi(self):
        vid = id_volto(RADICE, A, 3)
        self.assertEqual(scomponi_id_volto(vid), ("2022/2022-03-19 gara ciclistica/DSCF1727.JPG", 3))
        with self.assertRaises(ValueError):
            scomponi_id_volto("DSCF1727_face1")

    def test_id_legacy(self):
        self.assertEqual(id_legacy(PureWindowsPath("D:/Archivio/2022/DSCF1727.JPG"), 2), "DSCF1727_face2")

    def test_rinomina_prefisso(self):
        vid = id_volto(RADICE, A, 1)
        self.assertEqual(
            rinomina_prefisso(vid, "2022/2022-03-19 gara ciclistica", "2022/2022-03-19 Milano-Sanremo"),
            "2022/2022-03-19 Milano-Sanremo/DSCF1727.JPG#face1",
        )
        # non tocca cartelle con nome che inizia uguale
        self.assertEqual(rinomina_prefisso("2022x/a.jpg#face1", "2022", "2099"), "2022x/a.jpg#face1")


if __name__ == "__main__":
    unittest.main()
