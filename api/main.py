"""API HTTP du dictionnaire français–éwé (étude §6).

Lancement (depuis la racine du dépôt) :
    python -m uvicorn api.main:app --reload

Documentation interactive : http://127.0.0.1:8000/docs

Configuration par variables d'environnement :
    DICTIONNAIRE_DB    chemin de la base (défaut : dictionnaire.db à la racine)
    CONTRIBUTIONS_DB   base des signalements (défaut : contributions.db)
    CORS_ORIGINS       origines autorisées, séparées par des virgules

Principes :
  - la base du dictionnaire est ouverte en lecture seule ;
  - les signalements vivent dans un fichier séparé (étude §3.3) ;
  - /v1/report est limité en débit par adresse IP (étude §6.3) ;
  - toutes les routes sont versionnées sous /v1 dès le départ (étude §6.3).
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # python isolé ou lancé depuis un autre dossier
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Query, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from pipeline import apprendre  # noqa: E402
from pipeline.recherche import Moteur  # noqa: E402

VERSION = "1.0.0"
DB_DEFAUT = ROOT / "dictionnaire.db"
CONTRIBUTIONS_DEFAUT = ROOT / "contributions.db"
ORIGINES_DEFAUT = (
    "http://localhost:8000,http://127.0.0.1:8000,"
    "http://localhost:5173,http://127.0.0.1:5173"
)
MAX_SIGNALEMENTS = 5
FENETRE_SIGNALEMENTS = 600  # secondes

SCHEMA_CONTRIBUTIONS = """
CREATE TABLE IF NOT EXISTS signalements (
  id          INTEGER PRIMARY KEY,
  entree_id   INTEGER,
  type        TEXT NOT NULL,
  texte       TEXT NOT NULL,
  contact     TEXT,
  cree_le     TEXT NOT NULL DEFAULT (datetime('now')),
  statut      TEXT NOT NULL DEFAULT 'nouveau'
);
CREATE INDEX IF NOT EXISTS idx_signalements_statut ON signalements(statut);
"""


# --------------------------------------------------------------------------
# Schémas exposés (et documentation OpenAPI)
# --------------------------------------------------------------------------
class Resultat(BaseModel):
    id: int
    mot: str
    nature: str | None = None
    premiere_traduction: str | None = None
    niveau: int = Field(description="1 entrée exacte, 2 expression, 3 préfixe, 4 plein texte")
    score: float


class ReponseRecherche(BaseModel):
    query: str
    count: int
    results: list[Resultat]
    suggestions: list[str] = Field(
        default_factory=list,
        description="Mots approchants (niveau 5), à afficher comme « Vouliez-vous dire ? »",
    )


class Sens(BaseModel):
    type: Literal["principal", "collocation", "glose"]
    libelle: str | None = None
    phrase: str | None = Field(default=None, description="Expression complète, ex. « abaisser les prix »")
    traductions: list[str]
    verifie: bool = False
    bruts: list[str] | None = Field(default=None, description="Graphie d'origine, si brut=true")


class Fiche(BaseModel):
    id: int
    mot: str
    nature: str | None = None
    section: str | None = None
    sens: list[Sens]


class Stats(BaseModel):
    entrees: int
    sens: int
    traductions: int
    regles_actives: int
    regles_en_attente: int
    themes: int = 0
    traductions_relues: int = 0
    importe_le: str | None = None
    version_donnees: str | None = None
    version_api: str = VERSION
    taux_erreur_estime: float | None = Field(
        default=None,
        description="Mesuré sur 200 sens (étude §8.1) ; null tant que l'échantillonnage n'est pas fait",
    )


class Signalement(BaseModel):
    entree_id: int | None = Field(default=None, ge=1)
    type: Literal["erreur", "proposition", "usage"]
    texte: str = Field(min_length=2, max_length=500)
    contact: str | None = Field(default=None, max_length=100)


class Lecon(BaseModel):
    slug: str
    titre: str
    statut: str
    relu_par: str = ""
    sources: list[str] = Field(default_factory=list)
    ordre: int
    resume: str = ""


class LeconComplete(Lecon):
    html: str


class Theme(BaseModel):
    theme: str
    mots: int
    relus: int


class Exercice(BaseModel):
    id: int
    question: str
    reponse: str
    propositions: list[str]
    nature: str = ""


class Quiz(BaseModel):
    sens: Literal["fr_ewe", "ewe_fr"]
    theme: str | None = None
    disponibles: int = 0
    items: list[Exercice] = Field(default_factory=list)
    raison: str | None = Field(default=None, description="Pourquoi le quiz est vide, le cas échéant")


# --------------------------------------------------------------------------
# Limitation de débit (fenêtre glissante en mémoire)
# --------------------------------------------------------------------------
class Limiteur:
    def __init__(self, max_appels: int, fenetre: float):
        self.max_appels = max_appels
        self.fenetre = fenetre
        self._appels: dict[str, deque[float]] = defaultdict(deque)

    def autorise(self, cle: str) -> bool:
        maintenant = time.monotonic()
        appels = self._appels[cle]
        while appels and maintenant - appels[0] > self.fenetre:
            appels.popleft()
        if len(appels) >= self.max_appels:
            return False
        appels.append(maintenant)
        return True


# --------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------
def _moteur(request: Request) -> Moteur:
    return request.app.state.moteur


def preparer_contributions(chemin: Path) -> None:
    """Crée la base des signalements si besoin (étude §3.3)."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(chemin)
    try:
        con.executescript(SCHEMA_CONTRIBUTIONS)
        con.commit()
    finally:
        con.close()


def _entier(meta: dict[str, str], cle: str) -> int:
    try:
        return int(meta.get(cle, "0"))
    except ValueError:
        return 0


def _taux(meta: dict[str, str]) -> float | None:
    """Taux d'erreur mesuré, absent tant que l'échantillon n'est pas dépouillé."""
    try:
        valeur = meta.get("taux_erreur_estime", "")
        return float(valeur) if valeur else None
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------
def creer_app(
    db_path: Path | str | None = None,
    contributions_path: Path | str | None = None,
    origines: list[str] | None = None,
) -> FastAPI:
    base = Path(db_path or os.environ.get("DICTIONNAIRE_DB", DB_DEFAUT))
    contributions = Path(contributions_path or os.environ.get("CONTRIBUTIONS_DB", CONTRIBUTIONS_DEFAUT))
    autorisees = [
        o.strip()
        for o in (origines if origines is not None else os.environ.get("CORS_ORIGINS", ORIGINES_DEFAUT).split(","))
        if o.strip()
    ]
    # Visible dans les journaux du serveur : la cause n°1 d'un front muet est une liste vide.
    print(f"CORS : origines autorisées = {autorisees or 'aucune (vérifier CORS_ORIGINS)'}")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not base.exists():
            raise RuntimeError(
                f"Base introuvable : {base}\nConstruire la base : python pipeline/build_dictionary.py"
            )
        app.state.moteur = Moteur(base)
        app.state.limiteur = Limiteur(MAX_SIGNALEMENTS, FENETRE_SIGNALEMENTS)
        preparer_contributions(contributions)
        try:
            yield
        finally:
            app.state.moteur.fermer()

    app = FastAPI(
        title="API Agbalẽ — dictionnaire français–éwé",
        version=VERSION,
        description=(
            "Agbalẽ : recherche français → éwé, fiches de mots, mot du jour et signalements. "
            "Données issues d'un lexique numérisé ; les graphies d'origine restent accessibles."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=autorisees,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health", summary="Disponibilité du service")
    def health() -> dict:
        return {"status": "ok", "version": VERSION}

    @app.get("/v1/search", response_model=ReponseRecherche, summary="Recherche en cascade")
    def recherche(
        request: Request,
        q: str = Query(..., min_length=1, max_length=80, description="Mot ou expression française"),
        limit: int = Query(20, ge=1, le=50),
    ) -> ReponseRecherche:
        trouves = _moteur(request).recherche(q, limit)
        fiables = [r for r in trouves if r["niveau"] <= 4]
        suggestions = [r["mot"] for r in trouves if r["niveau"] == 5][:3]
        return ReponseRecherche(
            query=q,
            count=len(fiables),
            results=[
                Resultat(
                    id=r["id"],
                    mot=r["mot"],
                    nature=r["nature"],
                    premiere_traduction=r["premiere_traduction"],
                    niveau=r["niveau"],
                    score=r["score"],
                )
                for r in fiables
            ],
            suggestions=suggestions,
        )

    @app.get("/v1/entry/{entree_id}", response_model=Fiche, summary="Fiche d'un mot")
    def entree(
        request: Request,
        entree_id: int,
        brut: bool = Query(False, description="Inclure la graphie numérisée (ewe_brut)"),
    ) -> Fiche:
        fiche = _moteur(request).fiche(entree_id, avec_brut=brut)
        if fiche is None:
            raise HTTPException(status_code=404, detail=f"Entrée {entree_id} introuvable")
        return Fiche(**fiche)

    @app.get("/v1/word-of-the-day", response_model=Fiche, summary="Mot du jour")
    def mot_du_jour(
        request: Request,
        jour: str | None = Query(
            None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date ISO, pour prévisualiser un autre jour"
        ),
    ) -> Fiche:
        fiche = _moteur(request).mot_du_jour(jour)
        if fiche is None:
            raise HTTPException(status_code=503, detail="Base vide")
        return Fiche(**fiche)

    @app.get("/v1/stats", response_model=Stats, summary="Chiffres publics")
    def stats(request: Request) -> Stats:
        moteur = _moteur(request)
        meta = {r["cle"]: r["valeur"] for r in moteur.con.execute("SELECT cle, valeur FROM meta")}
        importe_le = meta.get("importe_le")
        return Stats(
            entrees=_entier(meta, "entrees"),
            sens=_entier(meta, "sens"),
            traductions=_entier(meta, "traductions"),
            regles_actives=_entier(meta, "regles_actives"),
            regles_en_attente=_entier(meta, "regles_en_attente"),
            themes=_entier(meta, "themes"),
            traductions_relues=_entier(meta, "traductions_relues"),
            importe_le=importe_le,
            version_donnees=importe_le[:10] if importe_le else None,
            taux_erreur_estime=_taux(meta),
        )

    @app.get("/v1/learn/lessons", response_model=list[Lecon], summary="Leçons disponibles")
    def lecons() -> list[Lecon]:
        return [Lecon(**lecon) for lecon in apprendre.lister_lecons()]

    @app.get("/v1/learn/lessons/{slug}", response_model=LeconComplete, summary="Contenu d'une leçon")
    def lecon(slug: str) -> LeconComplete:
        trouvee = apprendre.lire_lecon(slug)
        if trouvee is None:
            raise HTTPException(status_code=404, detail=f"Leçon « {slug} » introuvable")
        return LeconComplete(**trouvee)

    @app.get("/v1/learn/themes", response_model=list[Theme], summary="Thèmes de vocabulaire")
    def themes_vocabulaire(request: Request) -> list[Theme]:
        return [Theme(**theme) for theme in apprendre.themes(_moteur(request).con)]

    @app.get("/v1/learn/quiz", response_model=Quiz, summary="Exercice de vocabulaire")
    def quiz_vocabulaire(
        request: Request,
        theme: str | None = Query(None, max_length=40, description="Thème de vocabulaire ; vide = tous"),
        n: int = Query(10, ge=1, le=30),
        sens: Literal["fr_ewe", "ewe_fr"] = Query("fr_ewe"),
    ) -> Quiz:
        return Quiz(**apprendre.quiz(_moteur(request).con, n=n, theme=theme, sens=sens))

    @app.post("/v1/report", status_code=201, summary="Signaler une erreur ou proposer une traduction")
    def signalement(s: Signalement, request: Request) -> dict:
        ip = request.client.host if request.client else "inconnu"
        if not request.app.state.limiteur.autorise(ip):
            raise HTTPException(
                status_code=429,
                detail="Trop de signalements envoyés depuis cette adresse. Réessayez dans quelques minutes.",
                headers={"Retry-After": str(FENETRE_SIGNALEMENTS)},
            )
        texte = s.texte.strip()
        if len(texte) < 2:
            raise HTTPException(status_code=422, detail="Le texte du signalement est vide")
        if s.entree_id is not None and _moteur(request).fiche(s.entree_id) is None:
            raise HTTPException(status_code=422, detail=f"Entrée {s.entree_id} introuvable")

        contact = (s.contact or "").strip() or None
        con = sqlite3.connect(contributions)
        try:
            cur = con.execute(
                "INSERT INTO signalements(entree_id, type, texte, contact) VALUES (?,?,?,?)",
                (s.entree_id, s.type, texte, contact),
            )
            con.commit()
            identifiant = cur.lastrowid
        finally:
            con.close()
        return {"status": "recu", "id": identifiant}

    return app


app = creer_app()
