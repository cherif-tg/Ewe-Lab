#!/usr/bin/env python3
"""Récupère dictionnaire.db au moment de la construction, sans la publier.

Le fichier est stocké en asset de release dans un dépôt **privé** : il n'apparaît
ni dans l'historique Git, ni dans le site, ni dans les logs.

Variables d'environnement :
    BASE_URL        URL de l'asset. Pour GitHub :
                    https://api.github.com/repos/<compte>/<dépôt>/releases/assets/<id>
    GH_TOKEN        jeton de lecture du dépôt privé (facultatif si l'URL est publique)
    DICTIONNAIRE_DB chemin de sortie (défaut : dictionnaire.db à la racine)

Usage :
    python scripts/base_de_donnees.py            # télécharge si la base est absente
    python scripts/base_de_donnees.py --forcer   # retélécharge

Code de sortie 1 si la base est absente et introuvable : la construction échoue
plutôt que de démarrer une API vide.
"""
from __future__ import annotations

import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAGIE_SQLITE = b"SQLite format 3\x00"


def _media(url: str) -> str:
    """Type de média attendu, selon la forme de l'URL.

    Un asset de release se demande en binaire (`application/octet-stream`), un fichier
    versionné via l'API des contenus en brut (`application/vnd.github.raw`). Se tromper
    renvoie du JSON au lieu de la base.
    """
    return "application/vnd.github.raw" if "/contents/" in url else "application/octet-stream"


def telecharger(url: str, jeton: str | None, destination: Path) -> None:
    entetes = {"User-Agent": "agbale-build", "Accept": _media(url)}
    if jeton:
        entetes["Authorization"] = f"Bearer {jeton}"
    requete = urllib.request.Request(url, headers=entetes)
    temporaire = destination.with_suffix(destination.suffix + ".partiel")
    try:
        with urllib.request.urlopen(requete, timeout=120) as reponse, open(temporaire, "wb") as sortie:
            shutil.copyfileobj(reponse, sortie)
    except urllib.error.HTTPError as erreur:
        temporaire.unlink(missing_ok=True)
        raise SystemExit(
            f"Téléchargement refusé ({erreur.code}) : vérifier BASE_URL et GH_TOKEN "
            "(un asset de dépôt privé exige un jeton avec accès au dépôt)."
        ) from erreur

    debut = temporaire.open("rb").read(len(MAGIE_SQLITE))
    if debut != MAGIE_SQLITE:
        temporaire.unlink(missing_ok=True)
        if debut.startswith(b"{"):
            raise SystemExit(
                "L'API a renvoyé du JSON au lieu du fichier : le type de média ne correspond pas "
                "à l'URL (asset de release ou fichier versionné)."
            )
        raise SystemExit("Le fichier téléchargé n'est pas une base SQLite valide.")
    temporaire.replace(destination)


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    destination = Path(os.environ.get("DICTIONNAIRE_DB") or ROOT / "dictionnaire.db")
    if not destination.is_absolute():
        destination = ROOT / destination
    forcer = "--forcer" in argv

    if destination.exists() and not forcer:
        taille = destination.stat().st_size / 1024
        print(f"Base déjà présente : {destination} ({taille:.0f} Ko) — rien à faire.")
        return 0

    url = (os.environ.get("BASE_URL") or "").strip()
    if not url:
        raise SystemExit(
            "Base absente et BASE_URL non défini.\n"
            "En local : python pipeline/build_dictionary.py\n"
            "En déploiement : renseigner BASE_URL (asset de release) et GH_TOKEN."
        )

    print(f"Téléchargement de la base depuis {url.split('?')[0]} …")
    telecharger(url, os.environ.get("GH_TOKEN") or None, destination)
    print(f"Base installée : {destination} ({destination.stat().st_size / 1024:.0f} Ko)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
