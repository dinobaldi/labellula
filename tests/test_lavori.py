"""Lavori in background (GestoreLavori): errori all'avvio, lotti, limite."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from labellula.config import PREDEFINITI, Config, _unisci
from labellula.descrizione import Opzioni, cartella_relativa, esegui
from labellula.lavori import GestoreLavori
from labellula.motori import ErroreMotore

from .test_descrizione import MotoreFinto


def foto(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 48), (10, 120, 200)).save(p, "JPEG")


def aspetta(g: GestoreLavori, secondi=20):
    fine = time.time() + secondi
    while g.stato().get("attivo") and time.time() < fine:
        time.sleep(0.05)
    return g.stato()


class TestLavori(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.arch = self.base / "arch"
        foto(self.arch / "a.jpg")
        foto(self.arch / "sub" / "b.jpg")
        foto(self.arch / "sub2" / "c.jpg")
        self.cfg = Config(dati=_unisci(PREDEFINITI, {"archivio": {"radice": str(self.arch)}}),
                          cartella_base=self.base)

    def tearDown(self):
        self.tmp.cleanup()

    def test_errore_del_motore_non_blocca_i_lavori_successivi(self):
        """B1: se il motore non si può creare (es. "remoto"), il lavoro non resta «in corso» per sempre."""
        g = GestoreLavori(self.cfg)
        with mock.patch("labellula.motori.crea_motore", side_effect=ErroreMotore("remoto non disponibile")):
            with self.assertRaises(ErroreMotore):
                g.avvia(str(self.arch))
        self.assertFalse(g.stato().get("attivo"))
        with mock.patch("labellula.motori.crea_motore", return_value=MotoreFinto()):
            g.avvia(str(self.arch))          # prima: «C'è già un lavoro in corso»
            self.assertEqual(aspetta(g).get("fase"), "finito")

    def test_a_lotti_descrive_anche_le_foto_della_cartella_scelta(self):
        """B2: con «a lotti» le foto che stanno direttamente nella cartella non vanno perse."""
        g = GestoreLavori(self.cfg)
        with mock.patch("labellula.motori.crea_motore", return_value=MotoreFinto()):
            g.avvia(str(self.arch), a_lotti=True)
            st = aspetta(g)
        self.assertEqual(st.get("fase"), "finito")
        self.assertEqual(st.get("lotti"), 3)
        for scheda in ("_txt/a.txt", "sub/_txt/b.txt", "sub2/_txt/c.txt"):
            self.assertTrue((self.arch / scheda).exists(), scheda)

    def test_limite_vale_per_tutto_il_lavoro(self):
        g = GestoreLavori(self.cfg)
        with mock.patch("labellula.motori.crea_motore", return_value=MotoreFinto()):
            g.avvia(str(self.arch), a_lotti=True, limite=2)
            st = aspetta(g)
        self.assertEqual(st["risultato"]["fatte"], 2)
        self.assertEqual(len(list(self.arch.rglob("_txt/*.txt"))), 2)

    def test_lotti_fuori_archivio_usano_la_cartella_scelta_come_radice(self):
        """Gli indizi di ogni lotto partono dalla cartella scelta, non dal primo lotto."""
        fuori = self.base / "fuori"
        foto(fuori / "2023 gita Torino" / "x.jpg")
        foto(fuori / "2024 mare Albisola" / "y.jpg")
        radici = []
        import labellula.descrizione as D
        vero = D.descrivi_foto

        def spia(f, motore, opzioni):
            radici.append(opzioni.radice)
            return vero(f, motore, opzioni)
        g = GestoreLavori(self.cfg)
        with mock.patch("labellula.motori.crea_motore", return_value=MotoreFinto()), \
                mock.patch.object(D, "descrivi_foto", spia):
            g.avvia(str(fuori), a_lotti=True)
            aspetta(g)
        self.assertEqual(radici, [fuori, fuori])


class TestEsegui(unittest.TestCase):
    def test_non_modifica_le_opzioni_di_chi_chiama(self):
        with tempfile.TemporaryDirectory() as t:
            foto(Path(t) / "a.jpg")
            op = Opzioni()
            esegui(Path(t), MotoreFinto(), op, [".jpg"], [], Path(t) / "dati", stampa=lambda s: None)
            self.assertIsNone(op.radice)

    def test_non_ricorsiva(self):
        with tempfile.TemporaryDirectory() as t:
            foto(Path(t) / "a.jpg")
            foto(Path(t) / "sub" / "b.jpg")
            r = esegui(Path(t), MotoreFinto(), Opzioni(), [".jpg"], [], Path(t) / "dati",
                       stampa=lambda s: None, ricorsiva=False)
            self.assertEqual((r["totale"], r["fatte"]), (1, 1))

    def test_cartelle_nascoste_saltate(self):
        with tempfile.TemporaryDirectory() as t:
            foto(Path(t) / "a.jpg")
            foto(Path(t) / ".thumbnails" / "b.jpg")
            r = esegui(Path(t), MotoreFinto(), Opzioni(), [".jpg"], [], Path(t) / "dati", stampa=lambda s: None)
            self.assertEqual(r["totale"], 1)


class TestPiede(unittest.TestCase):
    def test_cartella_relativa_alla_radice(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            self.assertEqual(cartella_relativa(r / "2022" / "museo" / "x.jpg", r), "2022/museo")
            self.assertEqual(cartella_relativa(r / "x.jpg", r), ".")
            self.assertEqual(cartella_relativa(Path("/altrove/gita/x.jpg"), r), "gita")
            self.assertEqual(cartella_relativa(r / "gita" / "x.jpg", None), "gita")


if __name__ == "__main__":
    unittest.main()
