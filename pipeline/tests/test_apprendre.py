"""Tests du module « Apprendre l'éwé » (lot 6)."""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline import apprendre as ap  # noqa: E402
from pipeline import build_dictionary as bd  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mini.tsv"
ORTHO = "brut;standard;statut;motif;colonne\nî;ƒ;valide;test;ewe\n"
CORR = "brut;corrige;motif;colonne\n"
THEMES = "theme;mot_fr\ntest;abaisser\ntest;abandon\n"
VERIF = (
    "mot_fr;relu_par;date\n"
    "abaissement;TCA;2026-10-26\n"
    "abaisser;TCA;2026-10-26\n"
    "s'abaisser;TCA;2026-10-26\n"
    "bouilloire;TCA;2026-10-26\n"
    "abandon;TCA;2026-10-26\n"
)


class MarkdownTest(unittest.TestCase):
    def test_titres_listes_citations(self):
        html = ap.rendre_markdown("## Titre\n\nUn paragraphe.\n\n- un\n- deux\n\n> à retenir")
        self.assertIn("<h2>Titre</h2>", html)
        self.assertIn("<p>Un paragraphe.</p>", html)
        self.assertIn("<ul><li>un</li><li>deux</li></ul>", html)
        self.assertIn('<blockquote class="retenir">à retenir</blockquote>', html)

    def test_style_en_ligne(self):
        html = ap.rendre_markdown("**gras** et *italique* et `code`")
        self.assertIn("<strong>gras</strong>", html)
        self.assertIn("<em>italique</em>", html)
        self.assertIn("<code>code</code>", html)

    def test_html_source_echappe(self):
        html = ap.rendre_markdown('<script>alert("x")</script>')
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_lien_dangereux_ignore(self):
        html = ap.rendre_markdown("[clic](javascript:alert(1))")
        self.assertNotIn("javascript", html)
        self.assertIn("clic", html)
        html = ap.rendre_markdown("[fiche](#/mot/2)")
        self.assertIn('href="#/mot/2"', html)


class LeconsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lecons = ap.lister_lecons()

    def test_cinq_lecons_ordonnees(self):
        self.assertEqual(len(self.lecons), 5)
        self.assertEqual([lecon["ordre"] for lecon in self.lecons], [1, 2, 3, 4, 5])
        self.assertEqual(
            [lecon["slug"] for lecon in self.lecons],
            ["alphabet", "ecrire", "lire", "tons", "vocabulaire"],
        )

    def test_toutes_en_brouillon(self):
        for lecon in self.lecons:
            self.assertEqual(lecon["statut"], "brouillon")
            self.assertEqual(lecon["relu_par"], "")
            self.assertTrue(lecon["sources"], f"{lecon['slug']} sans source")
            self.assertTrue(lecon["resume"])

    def test_lire_une_lecon(self):
        lecon = ap.lire_lecon("alphabet")
        self.assertIsNotNone(lecon)
        self.assertEqual(lecon["titre"], "L'alphabet éwé")
        self.assertIn("<h2>", lecon["html"])
        self.assertIn("ɖ", lecon["html"])

    def test_lecon_inconnue(self):
        self.assertIsNone(ap.lire_lecon("inexistante"))


class QuizTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        (d / "ortho.csv").write_text(ORTHO, encoding="utf-8")
        (d / "corr.csv").write_text(CORR, encoding="utf-8")
        (d / "themes.csv").write_text(THEMES, encoding="utf-8")
        (d / "verif.csv").write_text(VERIF, encoding="utf-8")
        cls.db = d / "test.db"
        bd.build(FIXTURE, cls.db, d / "corr.csv", d / "ortho.csv",
                 qualite_path=d / "absente.csv", themes_path=d / "themes.csv",
                 verifications_path=d / "verif.csv", log=lambda *a: None)
        cls.con = sqlite3.connect(f"file:{cls.db.as_posix()}?mode=ro", uri=True)
        cls.con.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def test_mots_relus_comptes(self):
        # vérifier une entrée marque toutes ses traductions : on compte les entrées
        n = self.con.execute(
            "SELECT COUNT(DISTINCT s.entree_id) FROM traductions t"
            " JOIN sens s ON s.id = t.sens_id WHERE t.verifie = 1"
        ).fetchone()[0]
        self.assertEqual(n, 5)

    def test_themes(self):
        themes = {theme["theme"]: theme for theme in ap.themes(self.con)}
        self.assertEqual(themes["test"]["mots"], 2)
        self.assertEqual(themes["test"]["relus"], 2)

    def test_quiz_francais_vers_ewe(self):
        resultat = ap.quiz(self.con, n=3, graine=1)
        self.assertEqual(resultat["disponibles"], 5)
        self.assertTrue(resultat["items"])
        self.assertLessEqual(len(resultat["items"]), 3)
        for item in resultat["items"]:
            self.assertEqual(len(item["propositions"]), 4)
            self.assertIn(item["reponse"], item["propositions"])
            self.assertEqual(len(set(item["propositions"])), 4, "propositions dupliquées")
            self.assertTrue(item["question"])
        self.assertNotIn("raison", resultat)

    def test_quiz_ewe_vers_francais(self):
        resultat = ap.quiz(self.con, n=2, sens="ewe_fr", graine=2)
        for item in resultat["items"]:
            self.assertIn(item["question"], [c["ewe"] for c in ap._candidats(self.con, None)])
            self.assertEqual(item["reponse"], item["reponse"].strip())
        self.assertEqual(resultat["sens"], "ewe_fr")

    def test_graine_donne_la_meme_selection(self):
        a = ap.quiz(self.con, n=3, graine=42)
        b = ap.quiz(self.con, n=3, graine=42)
        self.assertEqual([i["id"] for i in a["items"]], [i["id"] for i in b["items"]])

    def test_theme_filtre(self):
        resultat = ap.quiz(self.con, n=5, theme="test", graine=3)
        self.assertEqual(resultat["disponibles"], 2)
        self.assertTrue(all(item["question"] in ("abaisser", "abandon") for item in resultat["items"]))

    def test_theme_inconnu(self):
        resultat = ap.quiz(self.con, n=5, theme="inexistant")
        self.assertEqual(resultat["items"], [])
        self.assertIn("relu", resultat["raison"])

    def test_sens_inconnu(self):
        with self.assertRaises(ValueError):
            ap.quiz(self.con, sens="n_importe_quoi")


class SansRelectureTest(unittest.TestCase):
    """La porte qualité : sans mot relu, aucun exercice."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        (d / "ortho.csv").write_text(ORTHO, encoding="utf-8")
        (d / "corr.csv").write_text(CORR, encoding="utf-8")
        (d / "verif.csv").write_text("mot_fr;relu_par;date\nabaisser;;\n", encoding="utf-8")
        cls.db = d / "vide.db"
        bd.build(FIXTURE, cls.db, d / "corr.csv", d / "ortho.csv",
                 qualite_path=d / "absente.csv", themes_path=d / "absente.csv",
                 verifications_path=d / "verif.csv", log=lambda *a: None)
        cls.con = sqlite3.connect(f"file:{cls.db.as_posix()}?mode=ro", uri=True)
        cls.con.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def test_aucun_mot_verifie(self):
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM traductions WHERE verifie = 1").fetchone()[0], 0)
        resultat = ap.quiz(self.con)
        self.assertEqual(resultat["items"], [])
        self.assertIn("relu", resultat["raison"])


if __name__ == "__main__":
    unittest.main()
