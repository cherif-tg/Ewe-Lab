#!/usr/bin/env python3
"""Construit dictionnaire.db à partir du lexique numérisé.

Colonnes source : section ; entree ; nature ; sous_entree ; traduction_ewe

Principes (étude §4.2) :
  - la donnée brute n'est jamais écrasée : `ewe_brut` conserve la graphie d'origine ;
  - la base est reconstruite depuis zéro à chaque exécution ;
  - toute correction est tracée dans data/corrections.csv ;
  - chaque enregistrement garde son numéro de ligne source.

Deux pièges du fichier, mesurés lors de l'audit (docs/etat_des_lieux.md §3) :
  - il contient des guillemets et apostrophes parasites (`"gaze'"`, `d'anyi`) :
    la lecture se fait donc en csv.QUOTE_NONE, sinon 13 % des lignes sont avalées ;
  - les lettres éwés sont déguisées par des diacritiques (`î` pour ƒ, `ô` pour ɔ,
    `â` pour ã…) et par des majuscules (L pour i, V pour ʋ). Le détail et le
    niveau de confiance de chaque règle vivent dans data/orthographe.csv.

Usage :
    python pipeline/build_dictionary.py
    python pipeline/build_dictionary.py data/riebstein-lexique-v2.tsv --db essai.db
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = ROOT / "data" / "riebstein-lexique-v2.tsv"
DEFAULT_DB = ROOT / "dictionnaire.db"
DEFAULT_CORRECTIONS = ROOT / "data" / "corrections.csv"
DEFAULT_ORTHO = ROOT / "data" / "orthographe.csv"
DEFAULT_QUALITE = ROOT / "data" / "qualite.csv"
DEFAULT_THEMES = ROOT / "content" / "themes.csv"
DEFAULT_VERIFICATIONS = ROOT / "data" / "verifications.csv"

EXPECTED = ["section", "entree", "nature", "sous_entree", "traduction_ewe"]

# Lettres éwés ramenées à l'ASCII pour les clés de recherche (étude §4.1, étape 7).
EWE_FOLD = str.maketrans(
    {"ɖ": "d", "ɛ": "e", "ɔ": "o", "ƒ": "f", "ŋ": "n", "ʋ": "v", "ɣ": "g"}
)

SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE entrees (
  id           INTEGER PRIMARY KEY,
  section      TEXT NOT NULL,
  mot_fr       TEXT NOT NULL,
  mot_fr_cle   TEXT NOT NULL,
  nature       TEXT,
  ligne_source INTEGER NOT NULL
);
CREATE INDEX idx_entrees_cle ON entrees(mot_fr_cle);

CREATE TABLE sens (
  id           INTEGER PRIMARY KEY,
  entree_id    INTEGER NOT NULL REFERENCES entrees(id),
  ordre        INTEGER NOT NULL,
  type         TEXT NOT NULL CHECK (type IN ('principal','collocation','glose')),
  libelle_fr   TEXT,
  phrase_fr    TEXT NOT NULL,
  ligne_source INTEGER NOT NULL
);
CREATE INDEX idx_sens_entree ON sens(entree_id, ordre);

CREATE TABLE traductions (
  id        INTEGER PRIMARY KEY,
  sens_id   INTEGER NOT NULL REFERENCES sens(id),
  rang      INTEGER NOT NULL,
  ewe_brut  TEXT NOT NULL,
  ewe       TEXT NOT NULL,
  ewe_cle   TEXT NOT NULL,
  verifie   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_trad_sens ON traductions(sens_id, rang);

CREATE VIRTUAL TABLE fts_fr USING fts5(
  texte, sens_id UNINDEXED, tokenize = "unicode61 remove_diacritics 2");
CREATE VIRTUAL TABLE fts_ewe USING fts5(
  texte, sens_id UNINDEXED, tokenize = "unicode61 remove_diacritics 2");

CREATE TABLE anomalies (
  id           INTEGER PRIMARY KEY,
  ligne_source INTEGER,
  type         TEXT NOT NULL,
  detail       TEXT
);
CREATE INDEX idx_anomalies_type ON anomalies(type);

-- Compteurs et paramètres de la construction (sert /v1/stats, étude §6.1)
CREATE TABLE meta (
  cle    TEXT PRIMARY KEY,
  valeur TEXT NOT NULL
);

-- Module « Apprendre l'éwé » (étude §16)
CREATE TABLE themes (
  id   INTEGER PRIMARY KEY,
  nom  TEXT NOT NULL UNIQUE
);
CREATE TABLE entree_theme (
  entree_id INTEGER NOT NULL REFERENCES entrees(id),
  theme_id  INTEGER NOT NULL REFERENCES themes(id),
  PRIMARY KEY (entree_id, theme_id)
);
"""


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------
def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "").strip()


def fold(s: str) -> str:
    """Clé de recherche : minuscules, sans accents, lettres éwés ramenées à l'ASCII."""
    s = nfc(s).lower().replace("’", "'").translate(EWE_FOLD)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s']|_", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def lemma_key(fr: str) -> str:
    """Clé d'entrée : ignore « s' », « se », les articles initiaux."""
    return re.sub(r"^(s'|se |l'|la |le |les |un |une )", "", fold(fr))


def kind_of(sous: str) -> str:
    if not sous:
        return "principal"
    return "glose" if re.fullmatch(r"\(.*\)", sous) else "collocation"


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
    return [p for p in (nfc(x) for x in parts) if p]


# --------------------------------------------------------------------------
# Tables de règles
# --------------------------------------------------------------------------
def load_corrections(path: Path) -> dict[str, dict[str, str]]:
    """Charge corrections.csv → {"ewe"|"fr": {brut: corrige}}.

    Colonnes : brut ; corrige ; motif ; colonne (facultative, défaut « ewe »).
    """
    out: dict[str, dict[str, str]] = {"ewe": {}, "fr": {}}
    if not path.exists():
        return out
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";", quoting=csv.QUOTE_NONE):
            brut, corrige = (r.get("brut") or "").strip(), r.get("corrige") or ""
            if not brut:
                continue
            colonne = (r.get("colonne") or "ewe").strip() or "ewe"
            out.setdefault(colonne, {})[brut] = corrige
    return out


def apply_corrections(s: str, corr: dict[str, str]) -> str:
    """Correction sur la chaîne entière, sinon mot par mot."""
    if not corr or not s:
        return s
    if s in corr:
        return corr[s]
    return " ".join(corr.get(tok, tok) for tok in s.split(" "))


def load_ortho(path: Path) -> tuple[dict[int, str], list[tuple[str, str]], list[tuple[str, str]]]:
    """Charge orthographe.csv.

    Colonnes : brut ; standard ; statut ; motif ; colonne (les deux dernières
    facultatives). Seules les règles au statut « valide » sont appliquées.
    Retourne (table str.translate, règles actives, règles en attente).
    """
    if not path.exists():
        return {}, [], []
    table: dict[int, str] = {}
    actives: list[tuple[str, str]] = []
    attente: list[tuple[str, str]] = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";", quoting=csv.QUOTE_NONE):
            brut, standard = r.get("brut") or "", r.get("standard") or ""
            statut = (r.get("statut") or "").strip()
            colonne = (r.get("colonne") or "ewe").strip() or "ewe"
            if colonne != "ewe" or not brut:
                continue
            if statut == "valide" and len(brut) == 1 and len(standard) == 1:
                table[ord(brut)] = standard
                actives.append((brut, standard))
            else:
                attente.append((brut, standard))
    return table, actives, attente


def to_standard(s: str, table: dict[int, str]) -> str:
    """Convertit vers les caractères éwé standard (NFC d'abord : « o + ^ » → « ô »)."""
    return nfc(s).translate(table) if table else nfc(s)


def load_taux_erreur(path: Path) -> float | None:
    """Dernier taux d'erreur mesuré, écrit par pipeline/echantillon.py (étude §8.1)."""
    if not Path(path).exists():
        return None
    with open(path, encoding="utf-8-sig", newline="") as f:
        lignes = list(csv.DictReader(f, delimiter=";"))
    if not lignes:
        return None
    try:
        return float(lignes[-1]["taux"])
    except (KeyError, ValueError):
        return None


def load_themes(path: Path) -> list[tuple[str, str]]:
    """Couples (thème, mot français) de content/themes.csv."""
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [
            ((r.get("theme") or "").strip(), (r.get("mot_fr") or "").strip())
            for r in csv.DictReader(f, delimiter=";", quoting=csv.QUOTE_NONE)
            if (r.get("theme") or "").strip() and (r.get("mot_fr") or "").strip()
        ]


def load_verifications(path: Path) -> dict[str, str]:
    """Mots relus : {mot français : relevé par qui}. Une ligne sans `relu_par` compte pour zéro."""
    if not Path(path).exists():
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {
            (r.get("mot_fr") or "").strip(): (r.get("relu_par") or "").strip()
            for r in csv.DictReader(f, delimiter=";", quoting=csv.QUOTE_NONE)
            if (r.get("mot_fr") or "").strip() and (r.get("relu_par") or "").strip()
        }


# --------------------------------------------------------------------------
# Lecture de la source
# --------------------------------------------------------------------------
def read_rows(path: Path):
    """Itère (numéro_de_ligne, dict, colonnes_en_trop) ; détecte le séparateur."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        head = f.read(4096)
        f.seek(0)
        delim = ";" if head.count(";") >= head.count("\t") else "\t"
        # QUOTE_NONE : indispensable, voir l'en-tête du module.
        reader = csv.DictReader(f, delimiter=delim, quoting=csv.QUOTE_NONE)
        if reader.fieldnames:
            reader.fieldnames = [nfc(x) for x in reader.fieldnames]
        for row in reader:
            clean, extra = {}, False
            for k, v in row.items():
                if k is None:          # colonnes en trop
                    extra = True
                    continue
                clean[k] = v if isinstance(v, str) else ""
            yield reader.line_num, clean, extra


# --------------------------------------------------------------------------
# Construction
# --------------------------------------------------------------------------
def build(
    src: Path = DEFAULT_SRC,
    db_path: Path = DEFAULT_DB,
    corrections_path: Path = DEFAULT_CORRECTIONS,
    ortho_path: Path = DEFAULT_ORTHO,
    qualite_path: Path = DEFAULT_QUALITE,
    themes_path: Path = DEFAULT_THEMES,
    verifications_path: Path = DEFAULT_VERIFICATIONS,
    log=print,
) -> dict:
    corr = load_corrections(corrections_path)
    ortho, actives, attente = load_ortho(ortho_path)
    taux_erreur = load_taux_erreur(qualite_path)

    for suffix in ("", "-wal", "-shm"):
        Path(str(db_path) + suffix).unlink(missing_ok=True)

    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    cur = con.cursor()

    entry_id, mot, ordre = None, "", 0
    nb_entrees = nb_sens = nb_trad = 0
    chars: Counter = Counter()
    natures: Counter = Counter()
    anomalies: Counter = Counter()
    regles_hits: Counter = Counter()

    def anomalie(line: int, kind: str, detail: str) -> None:
        anomalies[kind] += 1
        cur.execute(
            "INSERT INTO anomalies(ligne_source, type, detail) VALUES (?,?,?)",
            (line, kind, detail),
        )

    for line, r, extra in read_rows(src):
        if extra:
            anomalie(line, "colonnes_en_trop", str(r))

        entree = nfc(r.get("entree", ""))
        sous = nfc(r.get("sous_entree", ""))
        if corr.get("fr"):
            entree = apply_corrections(entree, corr["fr"])
            sous = apply_corrections(sous, corr["fr"])

        if entree:
            nature = nfc(r.get("nature", ""))
            natures[nature] += 1
            cle = lemma_key(entree)
            if not cle:
                anomalie(line, "cle_vide", entree)
            cur.execute(
                "INSERT INTO entrees(section, mot_fr, mot_fr_cle, nature, ligne_source)"
                " VALUES (?,?,?,?,?)",
                (nfc(r.get("section", "")), entree, cle, nature, line),
            )
            entry_id, mot, ordre = cur.lastrowid, entree, 0
            nb_entrees += 1
        elif entry_id is None:
            anomalie(line, "ligne_orpheline", str(r))
            continue

        typ = kind_of(sous)
        if typ == "principal":
            libelle, phrase = None, mot
        elif typ == "glose":
            libelle, phrase = sous[1:-1].strip(), f"{mot} ({sous[1:-1].strip()})"
        else:
            libelle, phrase = sous, f"{mot} {sous}"

        ordre += 1
        cur.execute(
            "INSERT INTO sens(entree_id, ordre, type, libelle_fr, phrase_fr, ligne_source)"
            " VALUES (?,?,?,?,?,?)",
            (entry_id, ordre, typ, libelle, phrase, line),
        )
        sens_id = cur.lastrowid
        nb_sens += 1
        cur.execute("INSERT INTO fts_fr(texte, sens_id) VALUES (?,?)", (fold(phrase), sens_id))

        brut_avant = nfc(r.get("traduction_ewe", ""))
        if '"' in brut_avant:
            anomalie(line, "guillemet_parasite", brut_avant)

        traductions = split_translations(brut_avant)
        if not traductions:
            anomalie(line, "traduction_vide", phrase)

        for rang, brut in enumerate(traductions, 1):
            corrige = apply_corrections(brut, corr.get("ewe", {}))
            for src_ch, dst_ch in actives:
                n = corrige.count(src_ch)
                if n:
                    regles_hits[f"{src_ch}→{dst_ch}"] += n
            ewe = to_standard(corrige, ortho)
            ewe_cle = fold(ewe)
            chars.update(ewe)
            if not ewe_cle:
                # Traces d'OCR sans aucune lettre (« bouilloire » → « \\ ») : on conserve
                # la ligne pour la traçabilité, on la signale, on ne la met pas en index.
                anomalie(line, "traduction_sans_lettre", ewe)
            if re.search(r"[a-zà-ÿɖɛɔƒŋʋɣ][A-Z]", ewe):
                anomalie(line, "majuscule_interne", ewe)
            if re.search(r"[0-9|\\/_@#]", ewe):
                anomalie(line, "symbole_suspect", ewe)
            cur.execute(
                "INSERT INTO traductions(sens_id, rang, ewe_brut, ewe, ewe_cle)"
                " VALUES (?,?,?,?,?)",
                (sens_id, rang, brut, ewe, ewe_cle),
            )
            if ewe_cle:
                cur.execute("INSERT INTO fts_ewe(texte, sens_id) VALUES (?,?)", (ewe_cle, sens_id))
            nb_trad += 1

    cur.execute("INSERT INTO fts_fr(fts_fr) VALUES ('optimize')")
    cur.execute("INSERT INTO fts_ewe(fts_ewe) VALUES ('optimize')")

    nb_themes, nb_liens = _charger_themes(cur, themes_path)
    nb_relues = _charger_verifications(cur, verifications_path)

    stats = {
        "source": src.name,
        "lignes_source": nb_sens,
        "entrees": nb_entrees,
        "sens": nb_sens,
        "traductions": nb_trad,
        "anomalies": dict(anomalies),
        "regles_actives": len(actives),
        "regles_en_attente": len(attente),
        "regles_hits": dict(regles_hits),
        "natures": dict(natures),
        "themes": nb_themes,
        "mots_themes": nb_liens,
        "traductions_relues": nb_relues,
        "taux_erreur_estime": "" if taux_erreur is None else taux_erreur,
        "importe_le": dt.datetime.now().isoformat(timespec="seconds"),
    }
    cur.executemany(
        "INSERT INTO meta(cle, valeur) VALUES (?,?)",
        [(k, (str(v) if not isinstance(v, (dict, list)) else _json(v))) for k, v in stats.items()],
    )
    con.commit()

    # Contrôles d'intégrité (étude §8.2) : on échoue plutôt que de publier une base trouée.
    controles = {
        "entrees_sans_sens": cur.execute(
            "SELECT COUNT(*) FROM entrees e WHERE NOT EXISTS (SELECT 1 FROM sens s WHERE s.entree_id = e.id)"
        ).fetchone()[0],
        "sens_sans_traduction": cur.execute(
            "SELECT COUNT(*) FROM sens s WHERE NOT EXISTS (SELECT 1 FROM traductions t WHERE t.sens_id = s.id)"
        ).fetchone()[0],
        "entrees_sans_cle": cur.execute(
            "SELECT COUNT(*) FROM entrees WHERE mot_fr_cle = ''"
        ).fetchone()[0],
        # Non bloquant : signalées en anomalie, conservées sans indexation.
        "traductions_sans_cle": cur.execute(
            "SELECT COUNT(*) FROM traductions WHERE ewe_cle = ''"
        ).fetchone()[0],
    }
    con.close()

    _report(stats, controles, actives, attente, chars, log)
    echecs = {k: v for k, v in controles.items() if v and k != "traductions_sans_cle"}
    if echecs:
        raise SystemExit(f"Intégrité non respectée : {echecs}")
    return {**stats, "controles": controles}


def _json(value) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _charger_themes(cur, chemin: Path) -> tuple[int, int]:
    """Insère les thèmes et leurs mots. Retourne (nombre de thèmes, nombre de liens)."""
    identifiants: dict[str, int] = {}
    liens = 0
    for theme, mot in load_themes(chemin):
        if theme not in identifiants:
            cur.execute("INSERT OR IGNORE INTO themes(nom) VALUES (?)", (theme,))
            identifiants[theme] = cur.execute(
                "SELECT id FROM themes WHERE nom = ?", (theme,)
            ).fetchone()[0]
        ligne = cur.execute(
            "SELECT id FROM entrees WHERE mot_fr_cle = ?", (lemma_key(mot),)
        ).fetchone()
        if ligne is None:
            continue
        cur.execute(
            "INSERT OR IGNORE INTO entree_theme(entree_id, theme_id) VALUES (?,?)",
            (ligne[0], identifiants[theme]),
        )
        liens += 1
    return len(identifiants), liens


def _charger_verifications(cur, chemin: Path) -> int:
    """Marque `verifie = 1` pour les mots relus. Retourne le nombre de traductions marquées."""
    marquees = 0
    for mot in load_verifications(chemin):
        cur.execute(
            "UPDATE traductions SET verifie = 1 WHERE sens_id IN ("
            "  SELECT id FROM sens WHERE entree_id IN ("
            "    SELECT id FROM entrees WHERE mot_fr_cle = ?))",
            (lemma_key(mot),),
        )
        marquees += cur.rowcount
    return marquees


def _report(stats, controles, actives, attente, chars, log) -> None:
    log(f"Source            : {stats['source']}")
    log(f"Lignes lues       : {stats['lignes_source']}")
    log(f"Entrées           : {stats['entrees']}")
    log(f"Sens              : {stats['sens']}")
    log(f"Traductions       : {stats['traductions']}")
    log(f"Règles actives    : {stats['regles_actives']} {actives if actives else ''}")
    log(f"Règles en attente : {stats['regles_en_attente']} {[b for b, _ in attente]}")
    if stats["regles_hits"]:
        log("Occurrences converties :")
        for regle, n in sorted(stats["regles_hits"].items(), key=lambda x: -x[1]):
            log(f"  {regle} : {n}")
    log(f"Anomalies         : {stats['anomalies'] or 'aucune'}")
    log(f"Taux d'erreur     : {stats['taux_erreur_estime'] or 'non mesuré (voir pipeline/echantillon.py)'}")
    log(f"Contrôles         : {controles}")
    non_ascii = {c: n for c, n in chars.items() if ord(c) > 127}
    log("Caractères non ASCII restants dans la colonne éwé :")
    for c, n in sorted(non_ascii.items(), key=lambda x: -x[1]):
        log(f"  {c!r} U+{ord(c):04X} : {n}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Construit dictionnaire.db.")
    ap.add_argument("source", nargs="?", default=DEFAULT_SRC, type=Path)
    ap.add_argument("--db", default=DEFAULT_DB, type=Path)
    ap.add_argument("--corrections", default=DEFAULT_CORRECTIONS, type=Path)
    ap.add_argument("--orthographe", default=DEFAULT_ORTHO, type=Path)
    args = ap.parse_args(argv)
    if not args.source.exists():
        raise SystemExit(f"Fichier source introuvable : {args.source}")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    build(args.source, args.db, args.corrections, args.orthographe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
