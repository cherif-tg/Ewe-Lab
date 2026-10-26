#!/usr/bin/env python3
"""Échantillon de contrôle qualité (étude §8.1).

Deux temps, deux commandes :

    python pipeline/echantillon.py
        Tire 200 sens au hasard (graine fixée) et écrit audit_out/echantillon_200.csv,
        avec des colonnes vides à remplir à la main en comparant à la source.

    python pipeline/echantillon.py --depouiller audit_out/echantillon_200.csv
        Compte les verdicts, calcule le taux d'erreur et résume le résultat dans
        data/qualite.csv (versionné). Le prochain build de la base reprend ce taux
        et l'API le publie sur /v1/stats.

Colonnes du fichier d'échantillon :
    sens_id ; ligne_source ; entree ; nature ; phrase_fr ; ewe ; ewe_brut ;
    verdict ; type_erreur ; commentaire

Valeurs attendues :
    verdict     : correct | erreur | (vide = non relu)
    type_erreur : caractere | espacement | mot_manquant | mauvaise_ligne | autre
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import random
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_DEFAUT = ROOT / "dictionnaire.db"
SORTIE_DEFAUT = ROOT / "audit_out" / "echantillon_200.csv"
QUALITE = ROOT / "data" / "qualite.csv"

TAILLE = 200
GRAINE = 42
VERDICTS = ("correct", "erreur")
TYPES_ERREUR = ("caractere", "espacement", "mot_manquant", "mauvaise_ligne", "autre")

REQUETE = """
SELECT s.id AS sens_id, s.ligne_source, s.phrase_fr,
       e.mot_fr AS entree, e.nature,
       t.ewe, t.ewe_brut
FROM sens s
JOIN entrees e ON e.id = s.entree_id
LEFT JOIN traductions t ON t.sens_id = s.id AND t.rang = 1
ORDER BY s.id
"""


def tirer(db_path: Path = DB_DEFAUT, sortie: Path = SORTIE_DEFAUT, taille: int = TAILLE,
          graine: int = GRAINE) -> list[dict]:
    """Écrit l'échantillon et renvoie les lignes tirées."""
    con = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        lignes = [dict(r) for r in con.execute(REQUETE)]
    finally:
        con.close()

    if not lignes:
        raise SystemExit("Base vide : lancer d'abord python pipeline/build_dictionary.py")

    echantillon = random.Random(graine).sample(lignes, min(taille, len(lignes)))
    echantillon.sort(key=lambda r: r["sens_id"])

    sortie = Path(sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    with open(sortie, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["sens_id", "ligne_source", "entree", "nature", "phrase_fr", "ewe", "ewe_brut",
                    "verdict", "type_erreur", "commentaire"])
        for r in echantillon:
            w.writerow([r["sens_id"], r["ligne_source"], r["entree"], r["nature"] or "",
                        r["phrase_fr"], r["ewe"] or "", r["ewe_brut"] or "", "", "", ""])
    return echantillon


def depouiller(fichier: Path, qualite: Path = QUALITE) -> dict:
    """Compte les verdicts, écrit data/qualite.csv et renvoie le bilan."""
    with open(fichier, encoding="utf-8-sig", newline="") as f:
        lignes = list(csv.DictReader(f, delimiter=";"))

    relus = [r for r in lignes if (r.get("verdict") or "").strip()]
    erreurs = [r for r in relus if (r.get("verdict") or "").strip() == "erreur"]
    inconnus = {r["verdict"].strip() for r in relus} - set(VERDICTS)
    if inconnus:
        raise SystemExit(f"Verdicts inconnus : {sorted(inconnus)} (attendu : {VERDICTS})")
    if not relus:
        raise SystemExit("Aucune ligne relue : remplir la colonne « verdict » avant de dépouiller.")

    taux = round(len(erreurs) / len(relus) * 100, 1)
    par_type: dict[str, int] = {}
    for r in erreurs:
        cle = (r.get("type_erreur") or "non précisé").strip() or "non précisé"
        par_type[cle] = par_type.get(cle, 0) + 1

    qualite = Path(qualite)
    qualite.parent.mkdir(parents=True, exist_ok=True)
    nouveau = not qualite.exists()
    with open(qualite, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        if nouveau:
            w.writerow(["date", "fichier", "lignes", "relues", "erreurs", "taux", "details"])
        w.writerow([
            dt.date.today().isoformat(), Path(fichier).name, len(lignes), len(relus), len(erreurs), taux,
            ", ".join(f"{k}:{v}" for k, v in sorted(par_type.items(), key=lambda x: -x[1])),
        ])

    return {"lignes": len(lignes), "relues": len(relus), "erreurs": len(erreurs),
            "taux": taux, "par_type": par_type}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Échantillon de contrôle qualité du lexique.")
    ap.add_argument("--db", default=DB_DEFAUT, type=Path)
    ap.add_argument("--sortie", default=SORTIE_DEFAUT, type=Path)
    ap.add_argument("--taille", default=TAILLE, type=int)
    ap.add_argument("--graine", default=GRAINE, type=int)
    ap.add_argument("--depouiller", metavar="FICHIER", type=Path)
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.depouiller:
        bilan = depouiller(args.depouiller)
        print(f"Lignes          : {bilan['lignes']}")
        print(f"Relues          : {bilan['relues']}")
        print(f"Erreurs         : {bilan['erreurs']}")
        print(f"Taux d'erreur   : {bilan['taux']} %")
        if bilan["par_type"]:
            print(f"Par type        : {bilan['par_type']}")
        print(f"Résumé ajouté   : {QUALITE}")
        return 0

    lignes = tirer(args.db, args.sortie, args.taille, args.graine)
    print(f"Échantillon     : {len(lignes)} sens (graine {args.graine})")
    print(f"Fichier         : {args.sortie}")
    print("Colonnes à remplir : verdict (correct | erreur), type_erreur, commentaire.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
