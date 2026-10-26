"""Module « Apprendre l'éwé » (étude §16).

Contenu : leçons en Markdown (`content/lecons/`), thèmes (`content/themes.csv`), et
génération d'exercices à partir des seuls mots **relus** (`data/verifications.csv`).

La porte qualité est stricte : un mot non relu reste consultable dans le dictionnaire,
mais n'entre jamais dans un exercice — un apprenant ne doit pas mémoriser une erreur de
numérisation (étude §16.3).
"""
from __future__ import annotations

import html
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LECONS = ROOT / "content" / "lecons"

SENS = ("fr_ewe", "ewe_fr")
MINIMUM_POUR_JOUER = 4  # une bonne réponse + trois propositions fausses


# --------------------------------------------------------------------------
# Leçons
# --------------------------------------------------------------------------
def _valeur(brut: str):
    brut = brut.strip()
    if brut.startswith("[") and brut.endswith("]"):
        contenu = brut[1:-1].strip()
        return [v.strip().strip('"') for v in contenu.split(",") if v.strip()]
    return brut.strip('"')


def lire_entete(texte: str) -> tuple[dict, str]:
    """Sépare l'en-tête `---` du corps Markdown."""
    if not texte.startswith("---"):
        return {}, texte
    fin = texte.find("\n---", 3)
    if fin == -1:
        return {}, texte
    entete: dict = {}
    for ligne in texte[3:fin].strip().splitlines():
        if ":" not in ligne:
            continue
        cle, _, valeur = ligne.partition(":")
        entete[cle.strip()] = _valeur(valeur)
    return entete, texte[fin + 4:].lstrip("\n")


def _resume(corps: str) -> str:
    for bloc in corps.split("\n\n"):
        bloc = bloc.strip()
        if bloc and not bloc.startswith(("#", ">", "-")):
            return re.sub(r"[*`]", "", bloc)[:160]
    return ""


def _fiche_lecon(chemin: Path) -> dict:
    entete, corps = lire_entete(chemin.read_text(encoding="utf-8"))
    return {
        "slug": entete.get("slug") or chemin.stem,
        "titre": entete.get("titre") or chemin.stem,
        "statut": entete.get("statut") or "brouillon",
        "relu_par": entete.get("relu_par") or "",
        "sources": entete.get("sources") or [],
        "ordre": int(entete.get("ordre") or 99),
        "resume": _resume(corps),
    }


def lister_lecons(dossier: Path = LECONS) -> list[dict]:
    lecons = [_fiche_lecon(chemin) for chemin in sorted(Path(dossier).glob("*.md"))]
    lecons.sort(key=lambda lecon: lecon["ordre"])
    return lecons


def lire_lecon(slug: str, dossier: Path = LECONS) -> dict | None:
    """Leçon complète, contenu rendu en HTML, ou None si le slug est inconnu."""
    for chemin in sorted(Path(dossier).glob("*.md")):
        lecon = _fiche_lecon(chemin)
        if lecon["slug"] == slug:
            _, corps = lire_entete(chemin.read_text(encoding="utf-8"))
            lecon["html"] = rendre_markdown(corps)
            return lecon
    return None


# --------------------------------------------------------------------------
# Rendu Markdown (sous-ensemble volontairement limité)
# --------------------------------------------------------------------------
def _en_ligne(texte: str) -> str:
    texte = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texte)
    texte = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", texte)
    texte = re.sub(r"`([^`]+)`", r"<code>\1</code>", texte)

    def lien(correspondance: re.Match) -> str:
        libelle, url = correspondance.group(1), correspondance.group(2)
        if url.startswith(("http://", "https://", "#/")):
            return f'<a href="{url}">{libelle}</a>'
        return libelle

    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lien, texte)


def rendre_markdown(texte: str) -> str:
    """Rend un sous-ensemble : titres, listes, citations, gras, italique, code, liens.

    Tout est échappé avant transformation : aucune balise de la source ne passe.
    """
    blocs = re.split(r"\n\s*\n", texte.strip())
    sortie = []
    for bloc in blocs:
        lignes = [ligne.rstrip() for ligne in bloc.splitlines() if ligne.strip()]
        if not lignes:
            continue
        if lignes[0].startswith("### "):
            sortie.append(f"<h3>{_en_ligne(html.escape(lignes[0][4:]))}</h3>")
            lignes = lignes[1:]
        elif lignes[0].startswith("## "):
            sortie.append(f"<h2>{_en_ligne(html.escape(lignes[0][3:]))}</h2>")
            lignes = lignes[1:]
        elif lignes[0].startswith("# "):
            sortie.append(f"<h2>{_en_ligne(html.escape(lignes[0][2:]))}</h2>")
            lignes = lignes[1:]
        if not lignes:
            continue
        if all(ligne.startswith("- ") for ligne in lignes):
            items = "".join(f"<li>{_en_ligne(html.escape(l[2:]))}</li>" for l in lignes)
            sortie.append(f"<ul>{items}</ul>")
        elif all(ligne.startswith("> ") for ligne in lignes):
            contenu = " ".join(_en_ligne(html.escape(l[2:])) for l in lignes)
            sortie.append(f'<blockquote class="retenir">{contenu}</blockquote>')
        else:
            texte_bloc = " ".join(_en_ligne(html.escape(ligne)) for ligne in lignes)
            sortie.append(f"<p>{texte_bloc}</p>")
    return "\n".join(sortie)


# --------------------------------------------------------------------------
# Thèmes et exercices
# --------------------------------------------------------------------------
def themes(con) -> list[dict]:
    """Thèmes, effectif et nombre de mots déjà relus."""
    lignes = con.execute(
        """
        SELECT th.nom AS theme, e.id AS entree_id,
               EXISTS(SELECT 1 FROM traductions t JOIN sens s ON s.id = t.sens_id
                      WHERE s.entree_id = e.id AND t.verifie = 1) AS relu
        FROM themes th
        JOIN entree_theme et ON et.theme_id = th.id
        JOIN entrees e ON e.id = et.entree_id
        ORDER BY th.nom, e.mot_fr
        """
    ).fetchall()
    aggregation: dict[str, dict] = {}
    for ligne in lignes:
        theme = aggregation.setdefault(ligne["theme"], {"theme": ligne["theme"], "mots": 0, "relus": 0})
        theme["mots"] += 1
        theme["relus"] += 1 if ligne["relu"] else 0
    return list(aggregation.values())


def _candidats(con, theme: str | None) -> list[dict]:
    """Un candidat par entrée relue : mot français, nature, première traduction vérifiée."""
    sql = """
        SELECT e.id, e.mot_fr, e.nature, t.ewe, t.rang, s.ordre
        FROM traductions t
        JOIN sens s ON s.id = t.sens_id
        JOIN entrees e ON e.id = s.entree_id
        WHERE t.verifie = 1 AND TRIM(t.ewe) <> ''
    """
    args: list = []
    if theme:
        sql += " AND e.id IN (SELECT et.entree_id FROM entree_theme et JOIN themes th ON th.id = et.theme_id WHERE th.nom = ?)"
        args.append(theme)
    sql += " ORDER BY e.id, s.ordre, t.rang"

    vus: dict[int, dict] = {}
    for ligne in con.execute(sql, args):
        if ligne["id"] not in vus:
            vus[ligne["id"]] = {
                "id": ligne["id"],
                "mot_fr": ligne["mot_fr"],
                "nature": ligne["nature"] or "",
                "ewe": ligne["ewe"],
            }
    return list(vus.values())


def quiz(con, n: int = 10, theme: str | None = None, sens: str = "fr_ewe",
         graine: int | None = None) -> dict:
    """QCM à quatre propositions, construit uniquement sur des mots relus."""
    if sens not in SENS:
        raise ValueError(f"sens inconnu : {sens}")
    vivier = _candidats(con, theme)
    reponse = {"sens": sens, "theme": theme, "disponibles": len(vivier), "items": []}

    if len(vivier) < MINIMUM_POUR_JOUER:
        reponse["raison"] = (
            "Aucun mot relu pour l'instant." if not vivier
            else f"Seulement {len(vivier)} mot(s) relu(s) : il en faut {MINIMUM_POUR_JOUER} pour proposer des choix."
        )
        return reponse

    aleatoire = random.Random(graine)
    selection = aleatoire.sample(vivier, min(n, len(vivier)))
    for candidat in selection:
        if sens == "fr_ewe":
            question, bonne = candidat["mot_fr"], candidat["ewe"]
            univers = [c["ewe"] for c in vivier if c["id"] != candidat["id"]]
            memes = [c["ewe"] for c in vivier if c["id"] != candidat["id"] and c["nature"] == candidat["nature"]]
        else:
            question, bonne = candidat["ewe"], candidat["mot_fr"]
            univers = [c["mot_fr"] for c in vivier if c["id"] != candidat["id"]]
            memes = [c["mot_fr"] for c in vivier if c["id"] != candidat["id"] and c["nature"] == candidat["nature"]]

        leurres = [v for v in dict.fromkeys(memes) if v != bonne]
        if len(leurres) < 3:
            leurres += [v for v in dict.fromkeys(univers) if v != bonne and v not in leurres]
        aleatoire.shuffle(leurres)
        propositions = [bonne] + leurres[:3]
        if len(propositions) < 4:   # vivier trop homogène : item écarté
            continue
        aleatoire.shuffle(propositions)
        reponse["items"].append(
            {
                "id": candidat["id"],
                "question": question,
                "reponse": bonne,
                "propositions": propositions,
                "nature": candidat["nature"],
            }
        )
    return reponse
