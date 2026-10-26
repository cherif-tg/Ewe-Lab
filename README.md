# Agbalẽ — dictionnaire français–éwé

Cherche un mot français, obtiens l'éwé — avec ses sens, ses expressions et sa graphie d'origine.
API HTTP, base SQLite en lecture seule, interface mobile d'abord.

**État (26 octobre 2026)** : données, recherche, API et interface livrées. Reste la mesure du
taux d'erreur, la vérification des droits et le test sur appareils réels. Le module
« Apprendre l'éwé » viendra après.

## Ce que fait l'application

- **Recherche en cascade** : entrée exacte, expression, préfixe, plein texte, puis rattrapage
  des fautes de frappe (« abaissment » → « abaissement »).
- **Fiche d'un mot** : sens principal, expressions complètes, précisions de sens.
- **Texte d'origine** : la graphie numérisée reste consultable, sans correction, sous chaque fiche.
- **Mot du jour**, **signalements** (erreur, proposition, usage) et **chiffres publics**.

## Démarrage rapide

Prérequis : Python 3.13+ et [uv](https://docs.astral.sh/uv/).

```bash
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt   # Linux/macOS : .venv/bin/python
```

Puis, dans le terminal où l'environnement est activé (ou en préfixant par `.venv/Scripts/python.exe`) :

```bash
python pipeline/build_dictionary.py         # construit dictionnaire.db (~2,6 Mo)
python -m uvicorn api.main:app --reload     # API      → http://127.0.0.1:8000/docs
python -m http.server 5173 --directory web  # interface → http://127.0.0.1:5173
```

L'interface interroge l'API déclarée dans `<meta name="api-base">` (`web/index.html`).
En local, laisser cette valeur vide : la page retombe sur `http://127.0.0.1:8000`.
Pour un déploiement où l'API est servie sur la même origine, laisser aussi vide.

## Déploiement

Front sur **Cloudflare Pages**, API sur **Render** (offre gratuite). La base du dictionnaire n'est
pas dans le dépôt : elle est téléchargée à la construction depuis un asset de release privé, pour
ne jamais publier la donnée.

```bash
python scripts/base_de_donnees.py     # récupère la base si BASE_URL est défini
```

Marche à suivre complète : [`DEPLOIEMENT.md`](DEPLOIEMENT.md). Configuration Render :
[`render.yaml`](render.yaml).

## Organisation

```
api/          service HTTP FastAPI (main.py) + tests
content/      leçons (Markdown) et thèmes de vocabulaire
data/         tables de règles et de qualité, versionnées ; le lexique brut ne l'est pas
docs/         étude de cadrage, charte graphique, état des lieux
pipeline/     import en base, moteur de recherche, module Apprendre, tests
web/          interface statique : HTML, CSS, JS et Andika auto-hébergée
```

## Données

Le lexique source (`data/riebstein-lexique-v2.tsv`, non versionné) contient 8 574 lignes et
5 colonnes. Après import : **6 937 entrées, 8 574 sens, 15 267 traductions**, 1 560 expressions,
77 gloses. Toutes les lignes ont cinq champs ; les enregistrements gardent leur numéro de ligne
d'origine.

### Ce que la numérisation a laissé

| Constat | Traitement |
|---|---|
| Le module `csv` avalait 13 % du fichier (guillemets parasites) | lecture en `QUOTE_NONE` |
| Lettres éwés remplacées par des accents : `î` = `ƒ`, `ô` = `ɔ`, `â` = `ã` | règles `orthographe.csv`, 4 120 occurrences converties |
| `ɖ` et `ʋ` absents, probablement écrits `d` et `v` | aucune restauration mécanique possible, signalé |
| Majuscules internes (43), symboles suspects (77), guillemets (4) | conservés en base, listés dans la table `anomalies` |
| Restes de notes de bas de page dans quelques traductions | connus, non corrigés (voir « non fait ») |

### Règles d'orthographe

`data/orthographe.csv` sépare les règles sûres, appliquées, des règles en attente, jamais
appliquées :

- **valides** — `î → ƒ`, `ô → ɔ`, `ç → ɔ`, `â → ã` ;
- **en attente** — `ê/ë → ẽ`, `ï → ƒ`, `û → ũ`, `L → i`, `V → ʋ`, `W → w`.

Chaque règle porte son motif et sa preuve. Une règle ne passe en `valide` qu'après relecture :
`agbalẽ` (« livre ») ne s'écrit pas `agbalê`.

```bash
python pipeline/build_dictionary.py    # la base est reconstruite à chaque exécution
```

## Recherche

`pipeline/recherche.py`, cinq niveaux classés, connexion en lecture seule.

| Niveau | Requête type | Mécanisme |
|---|---|---|
| 1 | `abaisser` | entrée exacte (index) |
| 2 | `abaisser les prix` | expression exacte (FTS5, ≥ 2 mots) |
| 3 | `abais` | préfixe, trié par longueur |
| 4 | `prix abaisser` | plein texte, jetons en préfixe (≥ 2 mots) |
| 5 | `abaissment` | similarité ≥ 80 et écart de longueur borné |

Médiane mesurée sur le jeu de référence : **1,9 ms** (objectif : 300 ms).
Inspection en ligne de commande : `python pipeline/recherche.py maison`.

## API

| Route | Rôle |
|---|---|
| `GET /health` | disponibilité et version |
| `GET /v1/search?q=&limit=` | résultats (niveaux 1-4) et `suggestions` (niveau 5) |
| `GET /v1/entry/{id}?brut=` | fiche ; `brut=true` ajoute la graphie numérisée |
| `GET /v1/word-of-the-day?jour=` | mot du jour, déterministe par date |
| `GET /v1/stats` | compteurs, version des données, taux d'erreur mesuré |
| `POST /v1/report` | signalement, 201, 5 envois / 10 min par IP |
| `GET /v1/learn/lessons` | leçons et leur statut de relecture |
| `GET /v1/learn/lessons/{slug}` | contenu d'une leçon, rendu en HTML |
| `GET /v1/learn/themes` | thèmes de vocabulaire, effectif et mots relus |
| `GET /v1/learn/quiz?theme=&n=&sens=` | exercice à quatre propositions, sur mots relus uniquement |

La base du dictionnaire est ouverte en lecture seule ; les signalements vivent dans
`contributions.db`, un fichier distinct créé au démarrage.

## Apprendre l'éwé

Cinq leçons dans `content/lecons/` (Markdown avec un en-tête `statut` / `relu_par` / `sources`),
chargées par `pipeline/apprendre.py` et servies par `/v1/learn/lessons`. Tant qu'une leçon est
`brouillon`, l'interface affiche « Contenu en cours de relecture ».

Le vocabulaire vient de `content/themes.csv` : quatre thèmes (salutations, famille, marché, temps),
32 mots. **Les nombres manquent** : le lexique numérisé n'en contient aucun.

### La porte qualité

Seuls les mots **relus** entrent dans les exercices. Un mot ne compte comme relu que si
`data/verifications.csv` porte un nom dans la colonne `relu_par` :

```csv
mot_fr;relu_par;date
merci;TCA;2026-10-26
salut;;
```

Ici, `merci` est relu, `salut` ne l'est pas. Après avoir rempli le fichier :

```bash
python pipeline/build_dictionary.py
```

Le quiz s'ouvre alors pour ce mot (`/v1/learn/quiz` renvoie `items: []` et une `raison` tant qu'il
y a moins de quatre mots relus). La progression de l'apprenant — trois boîtes, une bonne réponse
fait monter, une erreur ramène à la première — vit dans le navigateur, jamais sur le serveur.

## Tests

98 tests, sans framework externe (`unittest`, compatible pytest) :

```bash
python -m unittest discover -s pipeline/tests -v   # 68 tests : import, recherche, échantillon, leçons, quiz
python -m unittest discover -s api/tests -v        # 30 tests : routes, validation, débit, CORS, taux, apprendre
```

## Qualité

L'échantillon de contrôle suit l'étude de cadrage (§8.1) : 200 sens tirés au hasard, graine
fixée, verdict saisi à la main, puis dépouillement qui calcule le taux et l'écrit dans
`data/qualite.csv`. Le build suivant reprend ce taux, et `/v1/stats` le publie.

```bash
python pipeline/echantillon.py                                      # audit_out/echantillon_200.csv
python pipeline/echantillon.py --depouiller audit_out/echantillon_200.csv
```

Tant que le dépouillement n'est pas fait, le taux vaut `null` et l'interface affiche
« en cours de mesure ».

## Licence et attribution

Voir [`LICENCE.md`](LICENCE.md) : licence du code non choisie, droits du lexique source non
vérifiés (consultation ouverte, pas d'export), police Andika sous SIL OFL 1.1
(`web/fonts/OFL.txt`).

## À propos du nom

**Agbalẽ** est le mot éwé pour « livre » (entrée `livre` du lexique). Il s'écrit avec un tilde,
`ẽ` (U+1EBD), et non avec un accent aigu : `Agbalé` serait un autre mot, qui n'existe pas.

Conséquence technique : Andika ne contient pas le glyphe précomposé U+1EBD. Le rendu repose
sur la décomposition en `e` + tilde combinant (U+0303), d'où la fusion des sous-ensembles de
police (`web/styles/polices.css`) : deux fichiers séparés ne composent pas un accent sur une
lettre.

## Ce qui n'est pas fait

- **URL lisibles** (`/mot/abaisser`) : le routage est par ancre (`#/mot/12`). Le référencement
  demandera un rendu par page.
- **Restes de bas de page OCR** dans quelques traductions (« donner » → « na. Vocabulaire don… »).
- **Test visuel sur appareils réels** (Android d'entrée de gamme, iPhone, ordinateur) avec la
  chaîne de contrôle de la charte.
- **Monogramme** encore provisoire (`ɛ` sur ivoire), décision 3 de la charte.
- **Leçons non relues** : les cinq sont en `brouillon`, aucune n'est validée par un locuteur natif.
- **Aucun mot relu** : le quiz est vide tant que `data/verifications.csv` n'est pas rempli.
