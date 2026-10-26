"""Tests du pipeline d'import (stdlib unittest, compatible pytest).

Lancement depuis la racine :
    python -m unittest discover -s pipeline/tests -v
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

import build_dictionary as bd  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mini.tsv"

ORTHO = """\
brut;standard;statut;motif;colonne
î;ƒ;valide;test;ewe
ô;ɔ;valide;test;ewe
â;ã;valide;test;ewe
ê;ẽ;a_valider;test;
"""

CORR = """\
brut;corrige;motif;colonne
anyL;anyi;test;ewe
de Peau;de l'eau;test;fr
"""


class NormalisationTest(unittest.TestCase):
    def test_split_translations_ignore_les_virgules_entre_parentheses(self):
        self.assertEqual(
            bd.split_translations("de nu dzi, de (un, deux) autres"),
            ["de nu dzi", "de (un, deux) autres"],
        )
        self.assertEqual(bd.split_translations("a,, b "), ["a", "b"])
        self.assertEqual(bd.split_translations("   "), [])

    def test_kind_of(self):
        self.assertEqual(bd.kind_of(""), "principal")
        self.assertEqual(bd.kind_of("(diminution)"), "glose")
        self.assertEqual(bd.kind_of("des prix"), "collocation")

    def test_fold_tolere_les_lettres_ewes(self):
        # ɖ/ɛ/ɔ/ƒ/ŋ/ʋ/ɣ ramenés à l'ASCII, accents supprimés
        self.assertEqual(bd.fold("Ɖe ƒe ʋu"), "de fe vu")
        self.assertEqual(bd.fold("gbegblẽdi"), "gbegbledi")
        self.assertEqual(bd.fold("s’abaisser"), "s'abaisser")

    def test_lemma_key_ignore_les_prefixes(self):
        self.assertEqual(bd.lemma_key("s'abaisser"), "abaisser")
        self.assertEqual(bd.lemma_key("se laver"), "laver")
        self.assertEqual(bd.lemma_key("les prix"), "prix")


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        (d / "ortho.csv").write_text(ORTHO, encoding="utf-8")
        (d / "corr.csv").write_text(CORR, encoding="utf-8")
        cls.db_path = d / "test.db"
        cls.stats = bd.build(FIXTURE, cls.db_path, d / "corr.csv", d / "ortho.csv", log=lambda *a: None)
        cls.con = sqlite3.connect(cls.db_path)
        cls.con.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def one(self, sql, args=()):
        return self.con.execute(sql, args).fetchone()

    def test_comptages(self):
        self.assertEqual(self.stats["entrees"], 5)
        self.assertEqual(self.stats["sens"], 10)
        self.assertEqual(self.stats["traductions"], 16)

    def test_la_ligne_a_guillemet_ne_mange_pas_la_suivante(self):
        # Régression : avec la lecture csv par défaut, « abandon » disparaissait.
        self.assertIsNotNone(self.one("SELECT id FROM entrees WHERE mot_fr = 'abandon'"))
        self.assertEqual(self.one("SELECT COUNT(*) FROM anomalies WHERE type = 'guillemet_parasite'")[0], 1)

    def test_hierarchie_et_phrases(self):
        sens = self.con.execute(
            "SELECT s.type, s.libelle_fr, s.phrase_fr FROM sens s"
            " JOIN entrees e ON e.id = s.entree_id WHERE e.mot_fr = 'abaissement' ORDER BY s.ordre"
        ).fetchall()
        self.assertEqual([s["type"] for s in sens], ["principal", "collocation", "collocation", "glose"])
        self.assertEqual(sens[1]["phrase_fr"], "abaissement des prix")
        self.assertEqual(sens[3]["libelle_fr"], "diminution")
        self.assertEqual(sens[3]["phrase_fr"], "abaissement (diminution)")

    def test_regles_validees_appliquees_regles_en_attente_ignorees(self):
        self.assertEqual(self.one("SELECT ewe FROM traductions WHERE ewe_brut = 'île nu'")["ewe"], "ƒle nu")
        # ê est en attente : la graphie d'origine doit rester intacte
        self.assertEqual(
            self.one("SELECT ewe FROM traductions WHERE ewe_brut = 'gbegblêdi'")["ewe"], "gbegblêdi"
        )

    def test_donnee_brute_conservee(self):
        row = self.one("SELECT ewe_brut, ewe, ewe_cle FROM traductions WHERE ewe_brut = 'île nu'")
        self.assertEqual(row["ewe_brut"], "île nu")
        self.assertEqual(row["ewe_cle"], "fle nu")

    def test_corrections_fr_et_ewe(self):
        # colonne=fr : « de Peau » devient « de l'eau » dans la phrase reconstruite
        self.assertEqual(
            self.one("SELECT phrase_fr FROM sens WHERE phrase_fr LIKE 'abaissement de%' AND libelle_fr = 'de l''eau'")["phrase_fr"],
            "abaissement de l'eau",
        )
        # mécanisme isolé, dans les deux colonnes
        self.assertEqual(bd.apply_corrections("dze ko anyL", {"anyL": "anyi"}), "dze ko anyi")
        self.assertEqual(bd.apply_corrections("de Peau", {"de Peau": "de l'eau"}), "de l'eau")

    def test_cles_de_recherche(self):
        self.assertEqual(
            self.one("SELECT mot_fr_cle FROM entrees WHERE mot_fr = \"s'abaisser\"")["mot_fr_cle"], "abaisser"
        )

    def test_fts_fr_retrouve_une_expression(self):
        rows = self.con.execute("SELECT sens_id FROM fts_fr WHERE fts_fr MATCH 'abaissement AND prix'").fetchall()
        self.assertEqual(len(rows), 1)
        phrase = self.one("SELECT phrase_fr FROM sens WHERE id = ?", (rows[0]["sens_id"],))["phrase_fr"]
        self.assertEqual(phrase, "abaissement des prix")

    def test_fts_ewe_est_tolerant(self):
        # requête saisie sans les caractères éwés : « fle » doit retrouver « ƒle nu »
        rows = self.con.execute("SELECT sens_id FROM fts_ewe WHERE fts_ewe MATCH 'fle'").fetchall()
        self.assertTrue(rows)

    def test_integrite(self):
        self.assertEqual(self.stats["controles"]["entrees_sans_sens"], 0)
        self.assertEqual(self.stats["controles"]["sens_sans_traduction"], 0)
        self.assertEqual(self.stats["controles"]["entrees_sans_cle"], 0)

    def test_traduction_sans_lettre_conservee_mais_non_indexee(self):
        # « cruchon » → « \\ » : ligne conservée pour la traçabilité, signalée, hors index
        row = self.one("SELECT ewe, ewe_cle FROM traductions WHERE ewe = '\\\\'")
        self.assertIsNotNone(row)
        self.assertEqual(row["ewe_cle"], "")
        self.assertEqual(self.stats["controles"]["traductions_sans_cle"], 1)
        self.assertEqual(self.one("SELECT COUNT(*) FROM anomalies WHERE type = 'traduction_sans_lettre'")[0], 1)

    def test_meta_renseignee(self):
        cle = self.one("SELECT valeur FROM meta WHERE cle = 'entrees'")["valeur"]
        self.assertEqual(cle, "5")


class TablesReellesTest(unittest.TestCase):
    """Vérifie les décisions prises dans les tables versionnées du dépôt."""

    def setUp(self):
        ortho = ROOT / "data" / "orthographe.csv"
        if not ortho.exists():
            self.skipTest("data/orthographe.csv absent")
        self.table, self.actives, self.attente = bd.load_ortho(ortho)
        self.corr = bd.load_corrections(ROOT / "data" / "corrections.csv")

    def test_regles_fortes_actives(self):
        for brut, standard in (("î", "ƒ"), ("ô", "ɔ"), ("â", "ã"), ("ç", "ɔ")):
            self.assertEqual(self.table.get(ord(brut)), standard, f"règle {brut} absente")

    def test_regles_douteuses_non_appliquees(self):
        # ê → ɛ de l'étude est écarté : ẽ est probable (agbalẽ, gblẽ, nusẽ)
        self.assertNotIn(ord("ê"), self.table)
        self.assertIn("ê", [brut for brut, _ in self.attente])

    def test_orthographe_sur_un_mot_reel(self):
        self.assertEqual(bd.to_standard("gbegblêdi", self.table), "gbegblêdi")
        self.assertEqual(bd.to_standard("île nu", self.table), "ƒle nu")


if __name__ == "__main__":
    unittest.main()
