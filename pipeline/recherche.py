"""Moteur de recherche en cascade sur dictionnaire.db (étude §5).

Cinq niveaux, du plus sûr au plus permissif :

  1. entrée exacte      `abaisser`              → entrees.mot_fr_cle
  2. expression exacte  `abaisser les prix`     → FTS5, phrase entière (≥ 2 mots)
  3. préfixe            `abais`                 → entrees.mot_fr_cle LIKE 'abais%'
  4. plein texte        `prix abaisser`         → FTS5, chaque jeton en préfixe (≥ 2 mots)
  5. approximative      `abaissment`            → similarité ≥ 80

Les niveaux 2 et 4 exigent au moins deux mots : pour une requête d'un seul mot, une
« expression contenant ce mot » désigne une autre entrée (« maison » → « démolir la
maison ») et noierait les résultats légitimes.

Le niveau 5 utilise `fuzz.ratio` et écarte les candidats dont la longueur s'écarte trop
de la requête. `WRatio` (proposé par l'étude) donne 80 et plus à des mots très courts
(« an », « ban », « don » pour « abandonner ») : inutilisable ici.

L'étude décrit quatre niveaux (§5.1) et range l'expression exacte au deuxième rang
du classement (§5.3) : les deux lectures sont réconciliées ici en cinq niveaux, ce
qui permet de classer un mot trouvé avant une expression trouvée.

Chaque résultat porte son `niveau` et son `score` : la couche HTTP peut ainsi
expliquer pourquoi un mot sort, sans que le moteur connaisse quoi que ce soit de HTTP.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    from pipeline.build_dictionary import fold, lemma_key
except ModuleNotFoundError:  # python isolé (-I / -P) : la racine du dépôt n'est pas dans sys.path
    sys.path.insert(0, str(ROOT))
    from pipeline.build_dictionary import fold, lemma_key  # noqa: E402

DEFAULT_DB = ROOT / "dictionnaire.db"

SEUIL_APPROCHANT = 80
NIVEAUX = {
    1: "entree_exacte",
    2: "expression_exacte",
    3: "prefixe",
    4: "plein_texte",
    5: "approchant",
}

try:  # rapidfuzz est la référence de l'étude ; difflib sert de repli sans dépendance.
    from rapidfuzz import fuzz as _rf_fuzz
    from rapidfuzz import process as _rf_process

    SCORER = "rapidfuzz"
except ImportError:  # pragma: no cover - dépend de l'environnement
    _rf_fuzz = _rf_process = None
    SCORER = "difflib"


def _approchants(requete: str, cles: list[tuple[int, str]], limite: int) -> list[tuple[int, float]]:
    """Candidats similaires à `requete`, triés par score décroissant.

    Deux garde-fous contre le bruit : un seuil de similarité, et un écart de longueur
    borné — sans lui, un mot de deux lettres obtient un score élevé par simple
    correspondance partielle.
    """
    tolerance = max(2, round(0.34 * len(requete)))
    candidats = [(i, c) for i, c in cles if abs(len(c) - len(requete)) <= tolerance]
    if not candidats:
        return []
    choix = [c for _, c in candidats]

    if _rf_process is not None:
        resultats = _rf_process.extract(
            requete, choix, scorer=_rf_fuzz.ratio, limit=limite, score_cutoff=SEUIL_APPROCHANT
        )
        out = []
        for item in resultats:
            # rapidfuzz 3 renvoie (choix, score, index) ; les versions 2 (choix, score)
            score, idx = float(item[1]), (item[2] if len(item) > 2 else choix.index(item[0]))
            out.append((candidats[idx][0], score))
        return out

    scores = []
    for idx, (_, c) in enumerate(choix):
        score = SequenceMatcher(None, requete, c).ratio() * 100
        if score >= SEUIL_APPROCHANT:
            scores.append((candidats[idx][0], score))
    scores.sort(key=lambda x: -x[1])
    return scores[:limite]


class Moteur:
    """Recherche et lecture de fiches. Connexion ouverte en lecture seule."""

    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.db_path = Path(db_path)
        self.con = sqlite3.connect(
            f"file:{self.db_path.as_posix()}?mode=ro", uri=True, check_same_thread=False
        )
        self.con.row_factory = sqlite3.Row
        self._cles: list[tuple[int, str]] | None = None

    # ------------------------------------------------------------------
    # Index en mémoire (uniquement pour le niveau approximatif)
    # ------------------------------------------------------------------
    @property
    def cles(self) -> list[tuple[int, str]]:
        if self._cles is None:
            self._cles = [
                (r["id"], r["mot_fr_cle"])
                for r in self.con.execute("SELECT id, mot_fr_cle FROM entrees ORDER BY id")
            ]
        return self._cles

    # ------------------------------------------------------------------
    # Recherche
    # ------------------------------------------------------------------
    def recherche(self, requete: str, limite: int = 20) -> list[dict]:
        """Entrées classées pour `requete`, chacune avec son niveau et son score."""
        cle = lemma_key(requete)
        cle_pleine = fold(requete)
        if not cle or limite <= 0 or not re.search(r"\w", cle):
            return []

        trouves: dict[int, dict] = {}

        def ajouter(entree_id: int | None, niveau: int, score: float = 0.0) -> None:
            if entree_id is not None and entree_id not in trouves and len(trouves) < limite:
                trouves[entree_id] = {"id": entree_id, "niveau": niveau, "score": score}

        # 1. entrée exacte
        for r in self.con.execute(
            "SELECT id FROM entrees WHERE mot_fr_cle = ? ORDER BY mot_fr", (cle,)
        ):
            ajouter(r["id"], 1, 100.0)

        # 2. expression exacte (phrase entière dans l'index des sens)
        if len(trouves) < limite and len(cle_pleine.split()) >= 2:
            for entree_id in self._fts(f'"{cle_pleine}"', limite * 5):
                ajouter(entree_id, 2, 100.0)

        # 3. préfixe
        if len(trouves) < limite:
            for r in self.con.execute(
                "SELECT id FROM entrees WHERE mot_fr_cle LIKE ?"
                " ORDER BY length(mot_fr_cle), mot_fr LIMIT ?",
                (cle + "%", limite * 2),
            ):
                ajouter(r["id"], 3)

        # 4. plein texte, chaque jeton en préfixe
        jetons = [t for t in cle_pleine.split() if re.search(r"\w", t)]
        if len(trouves) < limite and len(jetons) >= 2:
            match = " ".join(f'"{t}"*' for t in jetons)
            for entree_id in self._fts(match, limite * 5):
                ajouter(entree_id, 4)

        # 5. approximative
        if len(trouves) < limite:
            for entree_id, score in _approchants(cle, self.cles, limite):
                ajouter(entree_id, 5, score)

        return self._resumes(list(trouves.values()))

    def _fts(self, match: str, limite: int) -> list[int]:
        """Entrées dont un sens correspond au `match` FTS5.

        `match` est toujours construit ici (jetons entre guillemets, `*` en suffixe),
        donc syntaxiquement valide : aucune exception n'est masquée. Le nom de table
        doit rester `fts_fr` — SQLite refuse un alias à gauche de `MATCH`.
        """
        rows = self.con.execute(
            "SELECT DISTINCT s.entree_id FROM fts_fr JOIN sens s ON s.id = fts_fr.sens_id"
            " WHERE fts_fr MATCH ? LIMIT ?",
            (match, limite),
        ).fetchall()
        return [r["entree_id"] for r in rows]

    def _resumes(self, classement: list[dict]) -> list[dict]:
        """Ajoute mot, nature et première traduction au classement, en une requête."""
        if not classement:
            return []
        ids = [c["id"] for c in classement]
        marques = ",".join("?" * len(ids))
        lignes = {
            r["id"]: r
            for r in self.con.execute(
                "SELECT e.id, e.mot_fr, e.nature,"
                " (SELECT t.ewe FROM traductions t JOIN sens s2 ON s2.id = t.sens_id"
                "  WHERE s2.entree_id = e.id ORDER BY s2.ordre, t.rang LIMIT 1) AS premiere"
                f" FROM entrees e WHERE e.id IN ({marques})",
                ids,
            )
        }
        out = []
        for c in classement:
            ligne = lignes.get(c["id"])
            if ligne is None:
                continue
            out.append(
                {
                    "id": ligne["id"],
                    "mot": ligne["mot_fr"],
                    "nature": ligne["nature"],
                    "premiere_traduction": ligne["premiere"],
                    "niveau": c["niveau"],
                    "niveau_nom": NIVEAUX[c["niveau"]],
                    "score": round(c["score"], 1),
                }
            )
        return out

    # ------------------------------------------------------------------
    # Fiche d'un mot
    # ------------------------------------------------------------------
    def fiche(self, entree_id: int, avec_brut: bool = False) -> dict | None:
        """Fiche complète, dans la forme de l'étude §6.2."""
        e = self.con.execute("SELECT * FROM entrees WHERE id = ?", (entree_id,)).fetchone()
        if e is None:
            return None
        sens = []
        for s in self.con.execute(
            "SELECT * FROM sens WHERE entree_id = ? ORDER BY ordre", (entree_id,)
        ):
            trads = self.con.execute(
                "SELECT ewe, ewe_brut, verifie FROM traductions WHERE sens_id = ? ORDER BY rang",
                (s["id"],),
            ).fetchall()
            item = {
                "type": s["type"],
                "libelle": s["libelle_fr"],
                "traductions": [t["ewe"] for t in trads],
                "verifie": any(t["verifie"] for t in trads),
            }
            if avec_brut:
                item["bruts"] = [t["ewe_brut"] for t in trads]
            sens.append(item)
        return {
            "id": e["id"],
            "mot": e["mot_fr"],
            "nature": e["nature"],
            "section": e["section"],
            "sens": sens,
        }

    def mot_du_jour(self, jour: str | None = None) -> dict | None:
        """Mot du jour, déterministe par date (étude §6.1)."""
        import datetime as dt
        import hashlib

        jour = jour or dt.date.today().isoformat()
        total = self.con.execute("SELECT COUNT(*) FROM entrees").fetchone()[0]
        if not total:
            return None
        index = int(hashlib.sha256(jour.encode()).hexdigest(), 16) % total
        row = self.con.execute(
            "SELECT id FROM entrees ORDER BY id LIMIT 1 OFFSET ?", (index,)
        ).fetchone()
        return self.fiche(row["id"])

    def fermer(self) -> None:
        self.con.close()


def recherche(requete: str, limite: int = 20, db_path: Path | str = DEFAULT_DB) -> list[dict]:
    """Raccourci sans état, pour les scripts et les tests."""
    moteur = Moteur(db_path)
    try:
        return moteur.recherche(requete, limite)
    finally:
        moteur.fermer()


def _cli(argv: list[str]) -> int:
    """Inspection en ligne de commande : python -m pipeline.recherche abaisser"""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    requete = " ".join(argv[1:]) or "abaisser"
    moteur = Moteur()
    try:
        resultats = moteur.recherche(requete, 10)
    finally:
        moteur.fermer()
    print(f"{requete!r} : {len(resultats)} résultat(s), moteur {SCORER}")
    for r in resultats:
        print(f"  [{r['niveau']}] {r['mot']} ({r['nature']}) = {r['premiere_traduction']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv))
