"""Tests du moteur de recherche (lot 2).

Lancement depuis la racine :
    python -m unittest discover -s pipeline/tests -v
"""
from __future__ import annotations

import statistics
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline import build_dictionary as bd  # noqa: E402
from pipeline.recherche import NIVEAUX, Moteur, recherche  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mini.tsv"
DB_REELLE = ROOT / "dictionnaire.db"
ORTHO = "brut;standard;statut;motif;colonne\nî;ƒ;valide;test;ewe\nô;ɔ;valide;test;ewe\n"
CORR = "brut;corrige;motif;colonne\n"


class CascadeTest(unittest.TestCase):
    """Les cinq niveaux, sur la base de la fixture."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        (d / "ortho.csv").write_text(ORTHO, encoding="utf-8")
        (d / "corr.csv").write_text(CORR, encoding="utf-8")
        cls.db = d / "test.db"
        bd.build(FIXTURE, cls.db, d / "corr.csv", d / "ortho.csv", qualite_path=d / "qualite_absente.csv", log=lambda *a: None)
        cls.moteur = Moteur(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.moteur.fermer()
        cls.tmp.cleanup()

    def test_niveau_1_entree_exacte(self):
        res = self.moteur.recherche("abaisser")
        self.assertEqual(res[0]["mot"], "abaisser")
        self.assertEqual(res[0]["niveau"], 1)
        # la forme pronominale partage la même clé : elle doit sortir aussi
        self.assertIn("s'abaisser", [r["mot"] for r in res])

    def test_niveau_1_insensible_a_la_casse_et_aux_apostrophes(self):
        for requete in ("ABANDON", "Abandon", "abandon"):
            with self.subTest(requete=requete):
                self.assertEqual(self.moteur.recherche(requete)[0]["mot"], "abandon")
        self.assertEqual(self.moteur.recherche("s\u2019abaisser")[0]["mot"], "abaisser")

    def test_niveau_2_expression_exacte(self):
        res = self.moteur.recherche("abaissement des prix")
        self.assertTrue(res)
        self.assertEqual(res[0]["mot"], "abaissement")
        self.assertLessEqual(res[0]["niveau"], 2)

    def test_niveau_3_prefixe(self):
        res = self.moteur.recherche("abais")
        noms = [r["mot"] for r in res]
        self.assertIn("abaissement", noms)
        self.assertIn("abaisser", noms)
        self.assertTrue(all(r["niveau"] in (3, 4, 5) for r in res))

    def test_niveau_4_plein_texte(self):
        # jetons présents mais dans un autre ordre : seule l'étape plein texte les relie
        res = self.moteur.recherche("prix abaissement")
        self.assertTrue(res)
        self.assertEqual(res[0]["mot"], "abaissement")
        self.assertEqual(res[0]["niveau"], 4)

    def test_niveau_5_approchant(self):
        res = self.moteur.recherche("abaissment")
        self.assertTrue(res)
        self.assertEqual(res[0]["mot"], "abaissement")
        self.assertEqual(res[0]["niveau"], 5)
        self.assertGreaterEqual(res[0]["score"], 80)

    def test_requete_vide_ou_limite(self):
        self.assertEqual(self.moteur.recherche(""), [])
        self.assertEqual(self.moteur.recherche("   "), [])
        self.assertEqual(self.moteur.recherche("abais", limite=0), [])
        self.assertLessEqual(len(self.moteur.recherche("abais", limite=2)), 2)

    def test_ponctuation_seule_ne_casse_rien(self):
        for requete in ('"', "'", "***", "(", "-", "NEAR("):
            with self.subTest(requete=requete):
                self.assertIsInstance(self.moteur.recherche(requete), list)

    def test_resume_complet(self):
        res = self.moteur.recherche("abaisser")[0]
        self.assertEqual(
            set(res), {"id", "mot", "nature", "premiere_traduction", "niveau", "niveau_nom", "score"}
        )
        self.assertEqual(res["nature"], "vt")
        self.assertEqual(res["premiere_traduction"], "didi nu de anyi")
        self.assertEqual(res["niveau_nom"], NIVEAUX[1])

    def test_regle_de_classement(self):
        # un mot exact sort avant une expression, qui sort avant un préfixe
        res = self.moteur.recherche("abaisser")
        niveaux = [r["niveau"] for r in res]
        self.assertEqual(niveaux, sorted(niveaux))

    def test_fiche(self):
        entree = self.moteur.recherche("abaissement")[0]
        fiche = self.moteur.fiche(entree["id"])
        self.assertEqual(fiche["mot"], "abaissement")
        self.assertEqual([s["type"] for s in fiche["sens"]], ["principal", "collocation", "collocation", "glose"])
        self.assertEqual(fiche["sens"][1]["libelle"], "des prix")
        self.assertEqual(fiche["sens"][1]["traductions"], ["asidzidede", "nudzidede"])
        self.assertNotIn("bruts", fiche["sens"][0])

    def test_fiche_avec_texte_d_origine(self):
        entree = self.moteur.recherche("abaisser")[0]
        fiche = self.moteur.fiche(entree["id"], avec_brut=True)
        brut = fiche["sens"][0]["bruts"]
        self.assertIn("île nu", brut)            # graphie numérisée
        self.assertIn("ƒle nu", fiche["sens"][0]["traductions"])  # graphie standard

    def test_fiche_inexistante(self):
        self.assertIsNone(self.moteur.fiche(999999))

    def test_mot_du_jour_deterministe(self):
        a = self.moteur.mot_du_jour("2026-10-26")
        b = self.moteur.mot_du_jour("2026-10-26")
        self.assertEqual(a, b)
        self.assertIsNotNone(a)
        self.assertIn("sens", a)
        self.assertTrue(a["sens"])

    def test_connexion_en_lecture_seule(self):
        with self.assertRaises(Exception):
            self.moteur.con.execute("DELETE FROM entrees")


@unittest.skipUnless(DB_REELLE.exists(), "dictionnaire.db absent : lancer pipeline/build_dictionary.py")
class GoldenSetTest(unittest.TestCase):
    """Golden set de l'étude §5.4, sur la base réelle."""

    @classmethod
    def setUpClass(cls):
        cls.moteur = Moteur(DB_REELLE)

    @classmethod
    def tearDownClass(cls):
        cls.moteur.fermer()

    def fiche_du(self, mot, requete=None):
        res = self.moteur.recherche(requete or mot)
        entree = next(r for r in res if r["mot"] == mot)
        return self.moteur.fiche(entree["id"])

    def traductions(self, sens):
        out = []
        for s in sens["sens"]:
            out.extend(s["traductions"])
        return out

    def traductions_principales(self, fiche):
        return next(s for s in fiche["sens"] if s["type"] == "principal")["traductions"]

    def test_abaisser(self):
        res = self.moteur.recherche("abaisser")
        self.assertEqual(res[0]["mot"], "abaisser")
        self.assertEqual(res[0]["niveau"], 1)
        fiche = self.fiche_du("abaisser")
        expressions = [s["libelle"] for s in fiche["sens"] if s["type"] == "collocation"]
        self.assertIn("les prix", expressions)
        self.assertIn("quelqu'un", expressions)

    def test_abaisser_les_prix(self):
        fiche = self.fiche_du("abaisser", "Abaisser les prix")
        collocation = next(s for s in fiche["sens"] if s["libelle"] == "les prix")
        self.assertEqual(collocation["traductions"], ["de nu dzi", "de asi le nu dzi"])

    def test_s_abaisser_trouve_des_deux_cotes(self):
        self.assertIn("s'abaisser", [r["mot"] for r in self.moteur.recherche("s'abaisser")])
        self.assertIn("s'abaisser", [r["mot"] for r in self.moteur.recherche("abaisser")])

    def test_faute_de_frappe(self):
        res = self.moteur.recherche("abaissment")
        self.assertEqual(res[0]["mot"], "abaissement")
        self.assertEqual(res[0]["niveau"], 5)

    def test_abandon(self):
        fiche = self.fiche_du("abandon")
        self.assertEqual(
            self.traductions_principales(fiche),
            ["gbegblêdi", "yametsitsi", "beble"],
        )

    def test_mot_unique_n_active_pas_la_recherche_d_expression(self):
        # « maison » ne doit pas ramener « démolir la maison » : seule l'entrée compte
        res = self.moteur.recherche("maison")
        self.assertEqual(res[0]["mot"], "maison")
        self.assertEqual(res[0]["niveau"], 1)
        self.assertFalse([r for r in res if r["niveau"] == 2])

    def test_approchant_ecarte_les_mots_trop_courts(self):
        res = self.moteur.recherche("abandonner")
        self.assertEqual(res[0]["mot"], "abandonner")
        courts = [r["mot"] for r in res if len(r["mot"]) <= 3]
        self.assertEqual(courts, [], f"mots trop courts remontés : {courts}")

    def test_requete_sans_accent(self):
        res = self.moteur.recherche("lumiere")
        self.assertEqual(res[0]["mot"], "lumière")
        self.assertEqual(res[0]["niveau"], 1)

    def test_performance(self):
        requetes = ["abaisser", "Abaisser les prix", "s'abaisser", "abaissment", "abandon", "prix"]
        temps = []
        for q in requetes:
            debut = time.perf_counter()
            self.moteur.recherche(q)
            temps.append((time.perf_counter() - debut) * 1000)
        median = statistics.median(temps)
        self.assertLess(median, 300, f"médiane {median:.1f} ms pour {temps}")
        print(f"\n  performance : médiane {median:.1f} ms, max {max(temps):.1f} ms ({requetes})")

    def test_absence_de_doublon(self):
        ids = [r["id"] for r in self.moteur.recherche("a", 50)]
        self.assertEqual(len(ids), len(set(ids)))


class RechercheSansEtatTest(unittest.TestCase):
    @unittest.skipUnless(DB_REELLE.exists(), "dictionnaire.db absent")
    def test_raccourci(self):
        res = recherche("abandon")
        self.assertTrue(res)
        self.assertEqual(res[0]["mot"], "abandon")


if __name__ == "__main__":
    unittest.main()
