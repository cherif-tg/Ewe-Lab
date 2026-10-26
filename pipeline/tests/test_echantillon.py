"""Tests de l'échantillon de contrôle qualité (lot 5)."""
from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline import build_dictionary as bd  # noqa: E402
from pipeline import echantillon as ech  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mini.tsv"
ORTHO = "brut;standard;statut;motif;colonne\nî;ƒ;valide;test;ewe\n"
CORR = "brut;corrige;motif;colonne\n"

ENTETE = ["sens_id", "ligne_source", "entree", "nature", "phrase_fr", "ewe", "ewe_brut",
          "verdict", "type_erreur", "commentaire"]


def lire(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


class EchantillonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        (d / "ortho.csv").write_text(ORTHO, encoding="utf-8")
        (d / "corr.csv").write_text(CORR, encoding="utf-8")
        cls.d = d
        cls.db = d / "test.db"
        bd.build(FIXTURE, cls.db, d / "corr.csv", d / "ortho.csv",
                 qualite_path=d / "absente.csv", log=lambda *a: None)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_tirage_deterministe(self):
        a = ech.tirer(self.db, self.d / "a.csv", taille=5, graine=42)
        b = ech.tirer(self.db, self.d / "b.csv", taille=5, graine=42)
        self.assertEqual([r["sens_id"] for r in a], [r["sens_id"] for r in b])
        self.assertEqual(len(a), 5)
        autre = ech.tirer(self.db, self.d / "c.csv", taille=5, graine=7)
        self.assertNotEqual([r["sens_id"] for r in a], [r["sens_id"] for r in autre])

    def test_fichier_a_remplir(self):
        ech.tirer(self.db, self.d / "ech.csv", taille=200, graine=42)
        lignes = lire(self.d / "ech.csv")
        self.assertEqual(list(lignes[0].keys()), ENTETE)
        self.assertEqual(len(lignes), 10)          # la fixture ne contient que 10 sens
        self.assertTrue(all(ligne["verdict"] == "" for ligne in lignes))
        self.assertTrue(all(ligne["phrase_fr"] for ligne in lignes))

    def test_depouillement(self):
        fichier = self.d / "ech_dep.csv"
        with open(fichier, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(ENTETE)
            w.writerow([1, 2, "a", "m", "a", "x", "x", "correct", "", ""])
            w.writerow([2, 3, "b", "m", "b", "y", "y", "erreur", "caractere", "î au lieu de ƒ"])
            w.writerow([3, 4, "c", "f", "c", "z", "z", "correct", "", ""])
            w.writerow([4, 5, "d", "f", "d", "w", "w", "", "", ""])
        qualite = self.d / "qualite.csv"
        bilan = ech.depouiller(fichier, qualite)
        self.assertEqual(bilan["relues"], 3)
        self.assertEqual(bilan["erreurs"], 1)
        self.assertEqual(bilan["taux"], 33.3)
        self.assertEqual(bilan["par_type"], {"caractere": 1})
        lignes = lire(qualite)
        self.assertEqual(list(lignes[0].keys())[:6], ["date", "fichier", "lignes", "relues", "erreurs", "taux"])
        self.assertEqual(lignes[-1]["taux"], "33.3")

    def test_depouillement_refuse_si_vide(self):
        fichier = self.d / "vide.csv"
        with open(fichier, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(ENTETE)
            w.writerow([1, 2, "a", "m", "a", "x", "x", "", "", ""])
        with self.assertRaises(SystemExit):
            ech.depouiller(fichier, self.d / "qualite2.csv")

    def test_le_taux_entre_dans_la_base(self):
        qualite = self.d / "qualite_mesuree.csv"
        qualite.write_text(
            "date;fichier;lignes;relues;erreurs;taux;details\n2026-10-26;ech.csv;10;10;2;20.0;caractere:2\n",
            encoding="utf-8",
        )
        stats = bd.build(FIXTURE, self.d / "avec_taux.db", self.d / "corr.csv", self.d / "ortho.csv",
                         qualite_path=qualite, log=lambda *a: None)
        self.assertEqual(stats["taux_erreur_estime"], 20.0)

    def test_sans_fichier_qualite_le_taux_est_vide(self):
        self.assertEqual(bd.load_taux_erreur(self.d / "inexistant.csv"), None)


if __name__ == "__main__":
    unittest.main()
