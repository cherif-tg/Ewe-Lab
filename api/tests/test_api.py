"""Tests de l'API (lot 3).

Lancement depuis la racine :
    python -m unittest discover -s api/tests -v
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from api.main import VERSION, creer_app  # noqa: E402
from pipeline import build_dictionary as bd  # noqa: E402

FIXTURE = ROOT / "pipeline" / "tests" / "fixtures" / "mini.tsv"
ORTHO = "brut;standard;statut;motif;colonne\nî;ƒ;valide;test;ewe\nô;ɔ;valide;test;ewe\n"
CORR = "brut;corrige;motif;colonne\n"
ORIGINE = "http://test.local"


class ApiTest(unittest.TestCase):
    """Une application neuve par test : le limiteur de débit repart de zéro."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        (d / "ortho.csv").write_text(ORTHO, encoding="utf-8")
        (d / "corr.csv").write_text(CORR, encoding="utf-8")
        cls.db = d / "api.db"
        cls.contrib = d / "contrib.db"
        bd.build(FIXTURE, cls.db, d / "corr.csv", d / "ortho.csv", log=lambda *a: None)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.app = creer_app(self.db, self.contrib, origines=[ORIGINE])
        self.client = TestClient(self.app)
        self.client.__enter__()  # déclenche le lifespan (ouverture de la base)
        self.addCleanup(self.client.__exit__, None, None, None)

    # -- service ---------------------------------------------------------
    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok", "version": VERSION})

    def test_openapi_disponible(self):
        r = self.client.get("/openapi.json")
        self.assertEqual(r.status_code, 200)
        chemins = r.json()["paths"]
        for chemin in ("/health", "/v1/search", "/v1/entry/{entree_id}", "/v1/word-of-the-day", "/v1/stats", "/v1/report"):
            self.assertIn(chemin, chemins)

    # -- recherche -------------------------------------------------------
    def test_recherche(self):
        r = self.client.get("/v1/search", params={"q": "abaisser"})
        self.assertEqual(r.status_code, 200)
        corps = r.json()
        self.assertEqual(corps["query"], "abaisser")
        self.assertEqual(corps["count"], len(corps["results"]))
        self.assertEqual(corps["results"][0]["mot"], "abaisser")
        self.assertEqual(corps["results"][0]["niveau"], 1)
        self.assertEqual(corps["results"][0]["premiere_traduction"], "didi nu de anyi")

    def test_recherche_expression(self):
        r = self.client.get("/v1/search", params={"q": "abaissement des prix"})
        corps = r.json()
        self.assertEqual(corps["results"][0]["mot"], "abaissement")
        self.assertLessEqual(corps["results"][0]["niveau"], 2)

    def test_suggestions_separees_des_resultats(self):
        r = self.client.get("/v1/search", params={"q": "abaissment"})
        corps = r.json()
        self.assertEqual(corps["count"], 0)
        self.assertEqual(corps["results"], [])
        self.assertEqual(corps["suggestions"][0], "abaissement")

    def test_limite(self):
        r = self.client.get("/v1/search", params={"q": "abais", "limit": 2})
        self.assertEqual(r.status_code, 200)
        self.assertLessEqual(len(r.json()["results"]), 2)

    def test_parametres_invalides(self):
        for params in ({"q": ""}, {"q": "a" * 81}, {"q": "abaisser", "limit": 0}, {"q": "abaisser", "limit": 51}, {}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get("/v1/search", params=params).status_code, 422)

    def test_recherche_sans_resultat(self):
        r = self.client.get("/v1/search", params={"q": "xyzzy"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["count"], 0)

    # -- fiche -----------------------------------------------------------
    def test_fiche(self):
        identifiant = self.client.get("/v1/search", params={"q": "abaissement"}).json()["results"][0]["id"]
        r = self.client.get(f"/v1/entry/{identifiant}")
        self.assertEqual(r.status_code, 200)
        fiche = r.json()
        self.assertEqual(fiche["mot"], "abaissement")
        self.assertEqual([s["type"] for s in fiche["sens"]], ["principal", "collocation", "collocation", "glose"])
        self.assertEqual(fiche["sens"][1]["phrase"], "abaissement des prix")
        self.assertIsNone(fiche["sens"][0]["bruts"])

    def test_fiche_avec_graphie_d_origine(self):
        identifiant = self.client.get("/v1/search", params={"q": "abaisser"}).json()["results"][0]["id"]
        fiche = self.client.get(f"/v1/entry/{identifiant}", params={"brut": True}).json()
        self.assertIn("île nu", fiche["sens"][0]["bruts"])
        self.assertIn("ƒle nu", fiche["sens"][0]["traductions"])

    def test_fiche_inconnue(self):
        r = self.client.get("/v1/entry/999999")
        self.assertEqual(r.status_code, 404)
        self.assertIn("introuvable", r.json()["detail"])

    # -- mot du jour ------------------------------------------------------
    def test_mot_du_jour(self):
        a = self.client.get("/v1/word-of-the-day").json()
        b = self.client.get("/v1/word-of-the-day", params={"jour": "2026-10-26"}).json()
        c = self.client.get("/v1/word-of-the-day", params={"jour": "2026-10-26"}).json()
        self.assertEqual(b, c)
        self.assertIn("mot", a)
        self.assertTrue(a["sens"])

    def test_mot_du_jour_date_invalide(self):
        r = self.client.get("/v1/word-of-the-day", params={"jour": "26/10/2026"})
        self.assertEqual(r.status_code, 422)

    # -- chiffres ---------------------------------------------------------
    def test_stats(self):
        corps = self.client.get("/v1/stats").json()
        self.assertEqual(corps["entrees"], 5)
        self.assertEqual(corps["traductions"], 16)
        self.assertEqual(corps["version_api"], VERSION)
        self.assertIsNone(corps["taux_erreur_estime"])
        self.assertRegex(corps["version_donnees"], r"^\d{4}-\d{2}-\d{2}$")

    # -- signalements -----------------------------------------------------
    def test_signalement(self):
        r = self.client.post("/v1/report", json={"type": "erreur", "texte": "Traduction à revoir"})
        self.assertEqual(r.status_code, 201)
        corps = r.json()
        self.assertEqual(corps["status"], "recu")
        avec = sqlite3.connect(self.contrib)
        try:
            ligne = avec.execute(
                "SELECT type, texte, statut FROM signalements WHERE id = ?", (corps["id"],)
            ).fetchone()
        finally:
            avec.close()
        self.assertEqual(ligne, ("erreur", "Traduction à revoir", "nouveau"))

    def test_signalement_avec_entree(self):
        identifiant = self.client.get("/v1/search", params={"q": "abandon"}).json()["results"][0]["id"]
        r = self.client.post(
            "/v1/report",
            json={"entree_id": identifiant, "type": "usage", "texte": "Mot encore utilisé", "contact": " "},
        )
        self.assertEqual(r.status_code, 201)
        avec = sqlite3.connect(self.contrib)
        try:
            contact = avec.execute(
                "SELECT contact FROM signalements WHERE id = ?", (r.json()["id"],)
            ).fetchone()[0]
        finally:
            avec.close()
        self.assertIsNone(contact)  # un contact vide n'est pas stocké

    def test_signalement_invalide(self):
        for corps in (
            {"type": "autre", "texte": "valide"},
            {"type": "erreur", "texte": "x"},
            {"type": "erreur", "texte": "   "},
            {"type": "erreur", "texte": "valide", "entree_id": 999999},
        ):
            with self.subTest(corps=corps):
                self.assertEqual(self.client.post("/v1/report", json=corps).status_code, 422)

    def test_signalement_limite_en_debit(self):
        corps = {"type": "erreur", "texte": "Signalement répété"}
        codes = [self.client.post("/v1/report", json=corps).status_code for _ in range(6)]
        self.assertEqual(codes[:5], [201] * 5)
        self.assertEqual(codes[5], 429)

    # -- CORS -------------------------------------------------------------
    def test_cors_origine_autorisee(self):
        r = self.client.get("/v1/stats", headers={"Origin": ORIGINE})
        self.assertEqual(r.headers.get("access-control-allow-origin"), ORIGINE)

    def test_cors_origine_refusee(self):
        r = self.client.get("/v1/stats", headers={"Origin": "http://ailleurs.example"})
        self.assertIsNone(r.headers.get("access-control-allow-origin"))


class DemarrageTest(unittest.TestCase):
    def test_base_absente(self):
        with tempfile.TemporaryDirectory() as d:
            app = creer_app(Path(d) / "absente.db", Path(d) / "contrib.db")
            with self.assertRaises(RuntimeError):
                with TestClient(app):
                    pass


if __name__ == "__main__":
    unittest.main()
