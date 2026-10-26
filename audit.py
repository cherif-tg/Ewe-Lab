#!/usr/bin/env python3
"""Audit du lexique numérisé (section;entree;nature;sous_entree;traduction_ewe).

Usage : python audit.py riebstein-lexique-v2.tsv

Produit dans le dossier audit_out/ :
  - rapport.md                       : synthèse lisible (aussi affichée à l'écran)
  - inventaire_caracteres.csv        : caractères non ASCII (français / éwé), effectifs, exemples
  - echantillon_o_e_circonflexe.csv  : occurrences de ô/ê dans la colonne éwé, à relire à la main
  - anomalies.csv                    : lignes suspectes (traduction vide, majuscule interne, symboles...)
"""
import csv
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "riebstein-lexique-v2.tsv")
OUT = Path("audit_out")
OUT.mkdir(exist_ok=True)

EXPECTED = ["section", "entree", "nature", "sous_entree", "traduction_ewe"]
EWE_SPECIAL = "ɖɛƒɣŋɔʋ"          # lettres éwés spécifiques (minuscules)
SUSPECT = "êôÊÔ"                  # candidates à la conversion vers ɛ / ɔ
PROPOSITION = str.maketrans({"ô": "ɔ", "Ô": "Ɔ", "ê": "ɛ", "Ê": "Ɛ"})
SAMPLE_SIZE = 50


def nfc(s) -> str:
    return unicodedata.normalize("NFC", s or "").strip()


def load(path: Path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        head = f.read(4096)
        f.seek(0)
        delim = ";" if head.count(";") >= head.count("\t") else "\t"
        # QUOTE_NONE : le lexique contient des apostrophes et des guillemets parasites
        # (« gaze' », « d'anyi »). Avec la gestion des guillemets par défaut, csv
        # fusionne les lignes suivantes dans un même champ et perd ~13 % du fichier.
        reader = csv.DictReader(f, delimiter=delim, quoting=csv.QUOTE_NONE)
        rows, extra = [], 0
        for row in reader:
            if None in row:
                extra += 1
            clean = {k: nfc(v) if isinstance(v, str) else "" for k, v in row.items() if k is not None}
            rows.append((reader.line_num, clean))
        return rows, delim, reader.fieldnames or [], extra


def split_translations(raw: str) -> list[str]:
    """Sépare sur la virgule, en ignorant celles entre parenthèses."""
    parts, buf, depth = [], [], 0
    for ch in raw:
        depth = max(depth + (ch == "(") - (ch == ")"), 0)
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def kind_of(sous: str) -> str:
    if not sous:
        return "principal"
    return "glose" if re.fullmatch(r"\(.*\)", sous) else "collocation"


def main() -> None:
    rows, delim, fields, extra = load(SRC)
    manquantes = [c for c in EXPECTED if c not in fields]

    courant, orphelines = None, 0
    nb_entrees = nb_trad = 0
    natures: Counter = Counter()
    types: Counter = Counter()
    sections: Counter = Counter()
    entrees_vues = defaultdict(list)
    chars_fr: Counter = Counter()
    chars_ewe: Counter = Counter()
    exemples: dict[str, list[str]] = defaultdict(list)
    occurrences: list[tuple[int, str, str]] = []
    anomalies: list[tuple[int, str, str]] = []

    for line, r in rows:
        entree = r.get("entree", "")
        sous = r.get("sous_entree", "")
        sections[r.get("section", "")] += 1

        if entree:
            courant = entree
            nb_entrees += 1
            natures[r.get("nature", "")] += 1
            entrees_vues[entree.lower()].append(line)
        elif courant is None:
            orphelines += 1
            anomalies.append((line, "ligne_orpheline", str(r)))
        types[kind_of(sous)] += 1

        for c in entree + sous:
            if ord(c) > 127:
                chars_fr[c] += 1

        trads = split_translations(r.get("traduction_ewe", ""))
        if not trads:
            anomalies.append((line, "traduction_vide", f"{courant} | {sous}"))
        for t in trads:
            nb_trad += 1
            for c in t:
                if ord(c) > 127:
                    chars_ewe[c] += 1
                    if len(exemples[c]) < 3 and t not in exemples[c]:
                        exemples[c].append(t)
            if any(c in SUSPECT for c in t):
                occurrences.append((line, courant or "", t))
            if re.search(r"[a-zà-ÿɖɛɔƒŋʋɣ][A-Z]", t):
                anomalies.append((line, "majuscule_interne", t))
            if re.search(r"[0-9|\\/_@#]", t):
                anomalies.append((line, "symbole_suspect", t))

    doublons = {k: v for k, v in entrees_vues.items() if len(v) > 1}

    # --- Fichiers de sortie ---
    with open(OUT / "inventaire_caracteres.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["colonne", "caractere", "code", "effectif", "exemples"])
        for colonne, cnt in (("francais", chars_fr), ("ewe", chars_ewe)):
            for c, n in sorted(cnt.items(), key=lambda x: -x[1]):
                w.writerow([colonne, c, f"U+{ord(c):04X}", n,
                            " | ".join(exemples[c]) if colonne == "ewe" else ""])

    random.seed(42)
    echantillon = random.sample(occurrences, min(SAMPLE_SIZE, len(occurrences)))
    with open(OUT / "echantillon_o_e_circonflexe.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ligne", "entree", "ewe_brut", "ewe_propose", "valide (oui/non)", "commentaire"])
        for line, entree, t in sorted(echantillon):
            w.writerow([line, entree, t, t.translate(PROPOSITION), "", ""])

    with open(OUT / "anomalies.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ligne", "type", "detail"])
        w.writerows(anomalies)

    # --- Rapport ---
    absentes = [c for c in "ɖƒʋ" if chars_ewe.get(c, 0) == 0]
    presentes = {c: chars_ewe[c] for c in EWE_SPECIAL if chars_ewe.get(c, 0) > 0}
    n_suspects = {c: chars_ewe.get(c, 0) for c in SUSPECT}
    anom = Counter(a[1] for a in anomalies)

    L = []
    L.append("# Rapport d'audit du lexique\n")
    L.append(f"- Fichier : `{SRC}` (séparateur : `{delim}`)")
    L.append(f"- Colonnes trouvées : {fields}")
    if manquantes:
        L.append(f"- ATTENTION, colonnes attendues manquantes : {manquantes}")
    if extra:
        L.append(f"- ATTENTION, {extra} ligne(s) avec des colonnes en trop")
    L.append(f"- Lignes de données : {len(rows)}")
    L.append(f"- Entrées principales : {nb_entrees}")
    L.append(f"- Lignes par type : {dict(types)}")
    L.append(f"- Traductions (après séparation sur la virgule) : {nb_trad}")
    L.append(f"- Lignes orphelines (sans entrée précédente) : {orphelines}")
    L.append(f"- Entrées dupliquées (même mot, casse ignorée) : {len(doublons)}")
    L.append(f"- Sections (lettres) : {len(sections)}")
    L.append("\n## Valeurs de `nature` (à confirmer avec la liste d'abréviations du lexique)\n")
    for k, v in natures.most_common():
        L.append(f"- `{k or '(vide)'}` : {v}")
    L.append("\n## Lettres éwés spécifiques dans la colonne éwé\n")
    L.append(f"- Présentes : {presentes if presentes else 'aucune'}")
    if absentes:
        L.append(f"- **Absentes : {''.join(absentes)}** : la numérisation a probablement utilisé d / f / v simples. "
                 "Une étape de restauration assistée sera nécessaire (aucune règle automatique ne suffit).")
    else:
        L.append("- ɖ, ƒ et ʋ sont présents : pas de restauration de consonnes à prévoir (à vérifier par sondage).")
    L.append("\n## Candidats à la conversion (ô, ê, Ô, Ê) dans la colonne éwé\n")
    L.append(f"- Effectifs : {n_suspects}")
    L.append(f"- Occurrences distinctes : {len(occurrences)} ; échantillon de {len(echantillon)} écrit dans "
             "`echantillon_o_e_circonflexe.csv` (colonne « valide » à remplir)")
    L.append("\n## Anomalies\n")
    L.append(f"- {dict(anom) if anom else 'aucune'} (détail dans `anomalies.csv`)")
    L.append("\n## Autres caractères non ASCII (colonne éwé)\n")
    autres = {c: n for c, n in chars_ewe.items() if c not in EWE_SPECIAL and c not in SUSPECT}
    L.append(f"- {autres if autres else 'aucun'}")
    L.append("\nVoir `inventaire_caracteres.csv` pour la liste complète avec exemples.")

    rapport = "\n".join(L) + "\n"
    (OUT / "rapport.md").write_text(rapport, encoding="utf-8")
    print(rapport)


if __name__ == "__main__":
    main()
