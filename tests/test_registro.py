import tempfile
import unittest
from pathlib import Path

from labellula.migrazione_legacy import indice_da_id_legacy, migra
from labellula.registro import Registro, carica, salva

RADICE = r"H:\Archivio"
DB = {
    # stesso nome file in due cartelle: il DB legacy conosce solo la prima
    "DSCF0001_face1": r"H:\Archivio\2022\gita\DSCF0001.JPG",
    "DSCF0001_face2": r"H:\Archivio\2022\gita\DSCF0001.JPG",
    "IMG_5_face1": r"H:\Archivio\2023\mare\IMG_5.jpg",
}


class TestMigrazione(unittest.TestCase):
    def test_indice(self):
        self.assertEqual(indice_da_id_legacy("DSCF0001_face12"), 12)
        self.assertEqual(indice_da_id_legacy("foto_face_x_face3"), 3)
        with self.assertRaises(ValueError):
            indice_da_id_legacy("DSCF0001")

    def test_migra(self):
        pm = {
            "vector_map": {"DSCF0001_face1": "Anna", "IMG_5_face1": "Bruno", "NONESISTE_face1": "Carla"},
            "ignored_map": {"DSCF0001_face2": True, "IMG_5_face1": True, "VECCHIO_face9": True},
        }
        reg, res = migra(pm, DB, RADICE)
        self.assertEqual(reg.assegnati, {
            "2022/gita/DSCF0001.JPG#face1": "Anna",
            "2023/mare/IMG_5.jpg#face1": "Bruno",
        })
        # IMG_5_face1 era sia assegnato sia ignorato: vince l'assegnazione
        self.assertEqual(reg.ignorati, {"2022/gita/DSCF0001.JPG#face2"})
        self.assertEqual(res["assegnati_non_migrati"], [("NONESISTE_face1", "Carla")])
        self.assertEqual(res["ignorati_non_migrati"], ["VECCHIO_face9"])


class TestRegistro(unittest.TestCase):
    def test_salva_carica_e_backup(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "reg.json"
            r = Registro()
            r.assegna("a/b.jpg#face1", "Anna")
            r.ignora("a/b.jpg#face2")
            self.assertIsNone(salva(r, f))
            r2 = carica(f)
            self.assertEqual(r2.assegnati, {"a/b.jpg#face1": "Anna"})
            self.assertEqual(r2.ignorati, {"a/b.jpg#face2"})
            r2.assegna("a/b.jpg#face2", "Bruno")  # toglie dagli ignorati
            bak = salva(r2, f)
            self.assertTrue(bak and bak.exists())
            self.assertEqual(carica(f).ignorati, set())

    def test_id_non_valido(self):
        with self.assertRaises(ValueError):
            Registro().assegna("DSCF0001_face1", "Anna")


if __name__ == "__main__":
    unittest.main()
