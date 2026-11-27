import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from labellula import hardware as H
from labellula.config import imposta_valore


def finto(risposte: dict):
    """esegui() finto: restituisce l'uscita registrata per il primo elemento del comando."""
    return lambda cmd, timeout=20: risposte.get(cmd[0] if cmd[0] != "sysctl" else " ".join(cmd[:3]), "")


MAC_INTEL = {
    "sysctl -n machdep.cpu.brand_string": "Intel(R) Core(TM) i9-9880H CPU @ 2.30GHz\n",
    "sysctl -n hw.memsize": str(16 * 1024 ** 3),
    "system_profiler": json.dumps({"SPDisplaysDataType": [
        {"sppci_model": "Intel UHD Graphics 630", "spdisplays_vram_shared": "1536 MB"},
        {"sppci_model": "AMD Radeon Pro 5300M", "spdisplays_vram": "4 GB"}]}),
}


def rapporto(schede, ram=32.0, disco=200.0, sistema="Windows", modelli=()):
    return H.Rapporto(sistema=sistema, ram_gb=ram, disco_libero_gb=disco, schede=schede,
                      ollama_installato=True, modelli_presenti=list(modelli))


class TestAvviaOllama(unittest.TestCase):
    def test_gia_acceso(self):
        lanciati = []
        self.assertTrue(H.avvia_ollama(popen=lambda c, **k: lanciati.append(c), risponde=lambda u: True))
        self.assertEqual(lanciati, [])

    def test_spento_viene_avviato(self):
        risposte = iter([False, False, False, True])
        lanciati = []
        with mock.patch.object(H.shutil, "which", return_value="/usr/bin/ollama"), \
                mock.patch.object(H.platform, "system", return_value="Linux"):
            ok = H.avvia_ollama(popen=lambda c, **k: lanciati.append(c), risponde=lambda u: next(risposte),
                                dormi=lambda s: None)
        self.assertTrue(ok)
        self.assertEqual(lanciati, [["/usr/bin/ollama", "serve"]])

    def test_remoto_non_si_avvia(self):
        lanciati = []
        ok = H.avvia_ollama("http://192.168.7.180:11434", popen=lambda c, **k: lanciati.append(c),
                            risponde=lambda u: False)
        self.assertFalse(ok)
        self.assertEqual(lanciati, [])


class TestHardware(unittest.TestCase):
    def test_mac_intel_con_radeon_non_adatto(self):
        """Un MacBook Pro 2019: i9 + Radeon Pro 5300M 4 GB -> elaborazione remota, niente download."""
        # il test può girare su un Mac con chip Apple (GitHub Actions): si simula un Mac Intel
        with mock.patch.object(H.platform, "machine", return_value="x86_64"):
            schede = H.schede_mac(finto(MAC_INTEL))
        self.assertEqual([s.marca for s in schede], ["intel", "amd"])
        self.assertTrue(all(s.usabile_da_ollama is False for s in schede))
        self.assertEqual(schede[1].vram_gb, 4.0)
        r = H.valuta(rapporto(schede, ram=16, sistema="Darwin"))
        self.assertEqual(r.verdetto, "insufficiente")
        self.assertEqual(r.da_scaricare_gb, 0)
        self.assertIn("processore Intel", " ".join(r.motivi))

    def test_apple_silicon(self):
        r = H.valuta(rapporto([H.Scheda("Apple M2 Pro", "apple", 16.0, True)], sistema="Darwin"))
        self.assertEqual((r.verdetto, r.modello_consigliato), ("ok", "qwen3-vl:8b-instruct"))
        r = H.valuta(rapporto([H.Scheda("Apple M1", "apple", 8.0, True)], ram=8, sistema="Darwin"))
        self.assertEqual((r.verdetto, r.modello_consigliato), ("limite", "qwen3-vl:4b-instruct"))

    def test_nvidia(self):
        r = H.valuta(rapporto([H.Scheda("RTX 3080 Ti", "nvidia", 12.0, True)], modelli=["bge-m3:latest"]))
        self.assertEqual(r.verdetto, "ok")
        self.assertEqual(r.da_scaricare_gb, 6.2)                     # bge-m3 c'è già
        r = H.valuta(rapporto([H.Scheda("RTX 3060 Ti", "nvidia", 8.0, True)]))
        self.assertEqual((r.verdetto, r.modello_consigliato), ("limite", "qwen3-vl:4b-instruct"))
        r = H.valuta(rapporto([H.Scheda("GTX 1650", "nvidia", 4.0, True)]))
        self.assertEqual(r.verdetto, "insufficiente")

    def test_amd_da_provare_e_senza_gpu(self):
        r = H.valuta(rapporto([H.Scheda("Radeon RX 7900 XT", "amd", 20.0, None)]))
        self.assertEqual(r.verdetto, "da_provare")
        r = H.valuta(rapporto([]))
        self.assertEqual(r.verdetto, "insufficiente")

    def test_disco_e_ram_insufficienti(self):
        r = H.valuta(rapporto([H.Scheda("RTX 4090", "nvidia", 24.0, True)], disco=5))
        self.assertEqual(r.verdetto, "insufficiente")
        self.assertIn("disco", " ".join(r.motivi))
        r = H.valuta(rapporto([H.Scheda("RTX 4090", "nvidia", 24.0, True)], ram=4))
        self.assertEqual(r.verdetto, "insufficiente")

    def test_nvidia_smi(self):
        s = H.schede_nvidia(lambda cmd, timeout=20: "NVIDIA GeForce RTX 3080 Ti, 12288\n")
        self.assertEqual((s[0].nome, s[0].vram_gb), ("NVIDIA GeForce RTX 3080 Ti", 12.0))

    def test_imposta_valore_config(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "config.yaml"
            f.write_text('# commento\nmodello:\n  # motore\n  motore: "ollama"\n  nome: "x"\nserver:\n  porta: 8765\n', encoding="utf-8")
            self.assertTrue(imposta_valore(f, "modello", "motore", "remoto"))
            self.assertFalse(imposta_valore(f, "modello", "motore", "remoto"))
            imposta_valore(f, "modello", "embedding", "bge-m3")
            t = f.read_text(encoding="utf-8")
            self.assertIn('  motore: "remoto"', t)
            self.assertIn('  embedding: "bge-m3"', t)
            self.assertIn("# commento", t)
            self.assertIn("porta: 8765", t)
            self.assertGreaterEqual(len(list(Path(d).glob("config.yaml.bak-*"))), 1)


if __name__ == "__main__":
    unittest.main()


class TestOllamaRete(unittest.TestCase):
    def test_normalizza(self):
        from labellula.ollama_rete import normalizza
        self.assertEqual(normalizza("192.168.1.20"), "http://192.168.1.20:11434")
        self.assertEqual(normalizza("http://pc-studio:11500/"), "http://pc-studio:11500")
        self.assertEqual(normalizza("locale"), "http://localhost:11434")
        self.assertEqual(normalizza(""), "http://localhost:11434")
        with self.assertRaises(ValueError):
            normalizza("ftp://x")

    def test_tipo_rete(self):
        from labellula.ollama_rete import tipo_rete
        self.assertEqual(tipo_rete("http://localhost:11434"), "locale")
        self.assertEqual(tipo_rete("http://192.168.7.180:11434"), "privata")
        self.assertEqual(tipo_rete("http://100.101.102.103:11434"), "privata")   # Tailscale
        self.assertEqual(tipo_rete("http://212.73.153.205:11434"), "pubblica")

    def test_prova_indirizzo_sbagliato(self):
        from labellula.ollama_rete import prova
        r = prova("127.0.0.1:9", timeout=1)
        self.assertFalse(r["ok"])
        self.assertIn("non risponde", r["errore"])


class TestRadicePredefinita(unittest.TestCase):
    def test_percorso_windows_su_altri_sistemi(self):
        import os
        from labellula.config import Config, PREDEFINITI, _unisci
        cfg = Config(dati=_unisci(PREDEFINITI, {"archivio": {"radice": "C:/Users/tuonome/Pictures"}}), cartella_base=Path("/x"))
        if os.name == "nt":
            self.assertEqual(cfg.radice_archivio, Path("C:/Users/tuonome/Pictures"))
        else:
            self.assertIn(cfg.radice_archivio, (Path.home() / "Pictures", Path.home()))
        vuota = Config(dati=_unisci(PREDEFINITI, {"archivio": {"radice": ""}}), cartella_base=Path("/x"))
        self.assertIn(vuota.radice_archivio, (Path.home() / "Pictures", Path.home()))

    def test_firma_codice(self):
        from labellula.server import FIRMA_AVVIO, firma_codice
        self.assertEqual(firma_codice(), FIRMA_AVVIO)
        self.assertEqual(len(FIRMA_AVVIO), 12)


class TestAccesso(unittest.TestCase):
    def test_impronta_e_verifica(self):
        from labellula.accesso import impronta, verifica_password
        h = impronta("una-password-lunga", iterazioni=1000)
        self.assertTrue(h.startswith("pbkdf2_sha256$1000$"))
        self.assertNotIn("una-password-lunga", h)
        self.assertTrue(verifica_password("una-password-lunga", h))
        self.assertFalse(verifica_password("sbagliata", h))
        self.assertFalse(verifica_password("x", "rotta"))

    def test_regole_password_e_attesa(self):
        from labellula.accesso import Sessioni, password_valida
        self.assertTrue(password_valida("corta"))
        self.assertTrue(password_valida("password"))
        self.assertEqual(password_valida("libellula-2026"), "")
        s = Sessioni()
        t = s.crea()
        self.assertTrue(s.valida(t))
        self.assertFalse(s.valida("inventato"))
        for _ in range(5):
            s.errore("10.0.0.9")
        self.assertGreater(s.attesa("10.0.0.9"), 0)
        self.assertEqual(s.attesa("10.0.0.8"), 0)
        s.chiudi_tutte()
        self.assertFalse(s.valida(t))
