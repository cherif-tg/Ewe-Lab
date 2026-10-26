# État des lieux et plan de travail — Dictionnaire français–éwé

**Date :** 26 octobre 2026
**Objet :** photographie du dépôt avant implémentation, écarts mesurés avec l'étude de cadrage (v1.1), décisions à prendre, ordre des travaux.
**Portée :** complète `docs/etude_dictionnaire_francais_ewe.md` (produit, données, API, calendrier) et `docs/Charte graphique et couleurs …` (design). Aucune décision de produit n'est rouverte ici.

---

## 1. Ce que contient le dépôt

| Élément | État | Remarque |
|---|---|---|
| `docs/etude_dictionnaire_francais_ewe.md` | complet, v1.1 | cadrage + annexe A (script d'import) + annexe B (squelette FastAPI) |
| `docs/Charte graphique et couleurs …` | complet, v1.0 | palette mesurée WCAG, Andika, variables CSS prêtes |
| `data/riebstein-lexique-v2.tsv` | présent, **non versionné** (`.gitignore`) | 8 574 lignes de données, séparateur `;` |
| `audit.py` | présent à la racine | script du jour 1 ; l'étude le prévoit dans `pipeline/` |
| `api/`, `pipeline/`, `web/` | **vides** | dossiers créés, aucun fichier |
| `README.md` | **vide** | doit porter les chiffres d'audit, le schéma, la licence (étude §10) |
| `LICENCE.md` | **vide** | dépend de la vérification des droits (étude §9) |
| Git | 1 commit `Definition de l'architecture du projet`, branche `main` | arbre propre avant cette session |

Outillage local : Python 3.13.15, Node 24.20.0. `fastapi`, `uvicorn`, `rapidfuzz`, `pydantic`, `pytest`, `httpx` **ne sont pas installés** — il faudra un `requirements.txt` et un environnement virtuel avant le lot API.

---

## 2. Mesures de référence (audit du 26 octobre 2026)

Résultat de `python audit.py data/riebstein-lexique-v2.tsv` après correction du défaut de lecture décrit en 3.1.

| Indicateur | Valeur |
|---|---|
| Lignes de données | **8 574** |
| Entrées principales | **6 937** |
| Collocations (sous-entrées de type expression) | 1 560 |
| Gloses (sous-entrées entre parenthèses) | **77** |
| Traductions après séparation sur la virgule | **15 267** |
| Lignes orphelines | 0 |
| Entrées dupliquées (casse ignorée) | 65 |
| Sections | 24 (A à Z, sans J ni X) |
| Anomalies | 43 majuscules internes, 77 symboles suspects |

Valeurs de `nature` : `m` 3 102, `vt` 1 916, `f` 1 591, `adv` 170, `v` 121, `pr` 16, `prép` 16, `n` 2, `part` 2, `adj` 1.
→ Dix valeurs seulement, et **`adj` une seule fois** : soit les adjectifs sont codés `m`/`f`, soit la numérisation a perdu l'étiquette. À confirmer avec la liste d'abréviations du lexique (étude §2.7).

Les 509 « incohérences » entre section et initiale du mot ne sont **pas** des erreurs : le classement suit le lemme (`s'abaisser` en A, `ébahir` en E). Rien à corriger.

---

## 3. Écarts entre l'étude et le fichier réel

### 3.1 Le module `csv` perdait 13 % du fichier — corrigé

Le lexique contient des apostrophes et des guillemets parasites (`"gaze'"`, `d'anyi`). Avec la gestion des guillemets par défaut de Python, `csv` ouvre un champ et avale les lignes suivantes : l'audit ne voyait que **7 438 lignes sur 8 574**, et fabriquait de faux enregistrements (une « traduction » de 33 685 caractères, des lignes à 9 champs).

Correction appliquée dans `audit.py` : lecture en `quoting=csv.QUOTE_NONE`. Les 8 574 lignes ont exactement 5 champs, le fichier est donc structurellement sain. **Le même piège attend l'annexe A** (`build_dictionary.py`), il faudra y appliquer la même option.

### 3.2 Les lettres éwés ne sont pas absentes : elles sont déguisées

L'audit annonce « `ɖ ƒ ʋ` absentes ». C'est vrai à la lettre, faux en pratique : environ **4 000 occurrences** de lettres éwés ont été remplacées par des caractères accentués. Preuves relevées dans le fichier :

| Glyphe | Occurrences | Lecture proposée | Preuves | Confiance |
|---|---|---|---|---|
| `î` (et `ï`) | 1 384 + 107 | **`ƒ`** | `île nu` = `ƒle nu` (« acheter ») ; `îe (gleti 12)` = `ƒe` (« an ») ; `aïe` = `aƒe` (« maison ») ; le même mot est écrit `dzifo` (« ciel ») et `dziîoyiyi` (« ascension ») ; suivi d'une voyelle dans 93 % des cas, et `ƒl` existe (`ƒle`) alors que `ɖl` n'existe pas en éwé | **forte** |
| `ô` (et `ç`) | 705 + 19 | **`ɔ`** | `gbôdidi` = `gbɔdidi` (exemple de l'étude elle-même), `kpç nu dzi` = `kpɔ nu dzi` (« regarder »), `nyô` = `nyɔ` ; présent en fin de mot dans 44 % des cas | **forte** |
| `â` | 1 012 | **`ã`** | `lâ` = `lã` (« viande, animal »), `gbâ` = `gbã` (« casser »), `nyâ aîa na ame` = `nyã aƒa na ame` | **forte** |
| `ê` et `ë` | 633 + 73 | **`ẽ`** (et non `ɛ`) | `agbalê` = `agbalẽ` (« livre »), `gblê`/`gblë` = `gblẽ` (« abîmer »), `nusê` = `nusẽ` | moyenne |
| `û` | 101 | **`ũ`** | `avû` = `avũ`, `mû` = `mũ` | moyenne |
| `é è à ù` | 477 | **tons** (aigu = ton haut, grave = ton bas), avec des fuites de français | `lé`, `dzè`, `nù` ; mais aussi `à bras ouverts`, `goût`, `août` | à trier |
| `ɖ`, `ʋ` | 0 | écrits `d` et `v` ? | `de` là où l'éwé attend `ɖe` (« délivrer » → `de, ho ame`) | **aucune restauration mécanique possible** |

**Conséquences directes :**

1. La table `orthographe.csv` de l'étude (`ô→ɔ`, `ê→ɛ`) ne couvre que **1 338 des 4 034 occurrences** (33 %) et se trompe probablement sur `ê` : appliquée telle quelle, elle transformerait `agbalẽ` en `agbalɛ`, `gblẽ` en `gblɛ` — c'est-à-dire des mots faux.
2. Le point dur n'est pas une voyelle mais une **consonne** (`ƒ`, 1 491 occurrences), ce que l'étude ne prévoyait pas.
3. `ɖ` et `ʋ` restent hors de portée d'une règle. Le risque « lettres absentes » de l'étude (§14) est donc **à moitié levé** : `ƒ` est récupérable, `d`/`v` ne le sont pas.
4. La substitution n'est pas bijective : le même mot peut apparaître en `kpç`, `kpo` et `kpɔ` selon les pages. Aucune conversion ne peut être « mécanique » sans contrôle : le champ `verifie` et le statut `a_valider` de `orthographe.csv` sont indispensables.
5. `ɛ` semble n'avoir jamais été saisi (le lexique écrit `e`). `e`/`ɛ` sont donc fusionnés dans la source : c'est une **limite de la donnée à documenter**, pas une erreur à corriger.

### 3.3 Autres constats

- **Gloses marginales** : 77 lignes seulement (1 %). L'étude les traite comme une catégorie de premier plan ; en pratique ce sont les collocations (1 560) qui portent la valeur.
- **Provenance identifiée** : une ligne (`zouave`) contient le tampon de prêt d'une bibliothèque — « Date Due », « Boston College Library, Chestnut Hill 67, Mass. », auteur illisible. C'est une piste sérieuse pour la vérification des droits (étude §9), à exploiter avant toute publication du fichier complet.
- **Français dans la colonne éwé** : 12 lignes au moins mélangent exemples français et traduction (`j'ai dix ans fè ewo le asinye`, `à bras ouverts ho ame atu`). Il faudra un filtre, sinon ces phrases polluent la recherche éwé.
- **Bruit OCR ponctuel** : 93 tirets cadratins, `•` (7), `■` (1), `°` (2), `£` (1), `\` (29), `*` (26), `<`/`>` : listes à puces et notes de bas de page collées dans les traductions.
- **65 doublons** dont quelques cas légitimes (`baiser` `vt` et `m`, `boucher` `vt` et `m`) : à ne pas fusionner en aveugle.

---

## 4. Décisions qui t'appartiennent

| # | Décision | Ce qu'elle bloque | Recommandation |
|---|---|---|---|
| 1 | **Validation de la table d'orthographe** sur un échantillon (étude §2.5) | la qualité de tout ce qui s'affiche ; le taux d'erreur publié | faire relire 50 à 60 candidats par un locuteur natif, en une passe ; je peux produire la liste triée par fréquence avec la conversion proposée |
| 2 | **Droits du lexique** (piste Boston College) | publication du fichier complet, page « À propos », `LICENCE.md` | vérifier avant le lot 3 ; en attendant, recherche seule, pas de téléchargement (étude §9) |
| 3 | Nom du produit + monogramme (`ɛ` ou `ɖ`) | en-tête, favicon, partage | après test du `ɖ` en 16 px |
| 4 | Andika seule, ou Andika + Charis SIL pour les leçons | lot 3 | Andika seule (plus léger, une seule famille) |
| 5 | Mode sombre en v1 ou v1.1 | lot 3 | en v1 : les variables existent déjà |
| 6 | Nature `adj` (1 occurrence) | filtres et étiquettes | confirmer avec la liste d'abréviations du lexique |

Aucune de ces décisions ne bloque le lot 1 : les règles peuvent vivre en statut `a_valider` et être activées d'un coup.

---

## 5. Plan proposé

L'ordre suit la priorité écrite dans l'étude — qualité des données d'abord — avec une correction : la table d'orthographe passe **avant** la mise en base, sinon on indexe des mots faux.

| Lot | Contenu | Critère de sortie |
|---|---|---|
| **0. Cadrage** | audit corrigé, présent document | fait le 26 octobre 2026 |
| **1. Données** | `pipeline/build_dictionary.py` (lecture `QUOTE_NONE`, hiérarchie, `corrections.csv`, `orthographe.csv` en statut `a_valider`), `dictionnaire.db`, tests de parsing et d'intégrité | **livré** : 6 937 entrées / 15 267 traductions, 19 tests verts, contrôles d'intégrité bloquants (détail §6) |
| **2. Recherche** | `pipeline/recherche.py` : cinq niveaux classés, fiche d'un mot, mot du jour, CLI d'inspection | **livré** : les 5 requêtes du golden set passent, médiane 1,9 ms pour un objectif de 300 ms (détail §7) |
| **3. API** | `/v1/search`, `/entry`, `/word-of-the-day`, `/stats`, `/report` (annexe B durcie), `requirements.txt`, tests `pytest` | tests verts, base ouverte en lecture seule |
| **4. Web** | `tokens.css` (charte §9), 4 écrans (accueil, résultats, fiche, à propos), barre de caractères, Andika auto-hébergée | aucune lettre éwé en carré sur 3 appareils, contrastes AA |
| **5. Qualité et lancement** | échantillon de 200 sens, taux d'erreur, page de transparence, `README`, `LICENCE` | chiffres publiés, attribution en place |
| **6. Apprendre l'éwé** | leçons, quiz depuis les entrées `verifie = 1` | après la v1 |

Réalisme : le calendrier de l'étude (9-10 jours à deux) suppose deux personnes sur les lots 4-5. En solo assisté, compter plutôt 2 à 3 jours par lot de données/API, 3 à 4 pour l'interface.

---

## 6. Lot 1 — import livré le 26 octobre 2026

| Fichier | Rôle |
|---|---|
| `pipeline/build_dictionary.py` | import complet et rejouable ; contrôles d'intégrité bloquants ; compteurs dans la table `meta` |
| `data/orthographe.csv` | 11 règles avec motif et preuve : 4 `valide`, 7 `a_valider` (jamais appliquées) |
| `data/corrections.csv` | corrections ponctuelles, colonne `ewe` ou `fr` (`anyL → anyi`, `de Peau → de l'eau`) |
| `pipeline/tests/` | 19 tests en `unittest` (compatibles pytest), fixture de 10 lignes |
| `dictionnaire.db` | 2,6 Mo, généré à chaque exécution, hors dépôt |

**Résultat de l'import :** 6 937 entrées, 8 574 sens, 15 267 traductions, **4 120 occurrences converties** (`ƒ` 1 384, `ã` 1 012, `ɔ` 724). Contrôles : 0 entrée sans sens, 0 sens sans traduction, 0 clé d'entrée vide.

**Anomalies tracées** (table `anomalies`, une ligne par cas) : 77 symboles suspects, 42 majuscules internes, 4 guillemets parasites, 1 traduction sans aucune lettre (`bouilloire` → `\\`, conservée pour la traçabilité, non indexée).

**Deux décisions d'implémentation à connaître :**

1. `orthographe.csv` et `corrections.csv` acceptent deux colonnes facultatives, `motif` et `colonne` (`ewe` par défaut, `fr` pour corriger les sous-entrées françaises). Le schéma à trois colonnes de l'étude reste valide ; l'ajout sert la traçabilité exigée en §4.2.
2. Une règle `a_valider` n'est jamais appliquée, mais son effectif est compté : la base affiche donc encore `ê`, `ë`, `ï`, `û` et les majuscules `L`/`V`/`W` (≈ 1 000 occurrences). C'est le comportement voulu — aucune correction inventée.

**Commandes :**

```bash
python pipeline/build_dictionary.py                            # reconstruit dictionnaire.db
python -m unittest discover -s pipeline/tests -v               # 19 tests
```

Rien n'est commité : les changements sont dans l'arbre de travail, à relire avant commit.

---

## 7. Lot 2 — moteur de recherche livré le 26 octobre 2026

`pipeline/recherche.py` : connexion en lecture seule (`mode=ro`), cinq niveaux classés, fiche d'un mot dans la forme de l'étude §6.2, mot du jour déterministe, et une CLI d'inspection.

| Niveau | Requête type | Mécanisme |
|---|---|---|
| 1. entrée exacte | `abaisser` | index `mot_fr_cle` |
| 2. expression exacte | `abaisser les prix` | FTS5, phrase entière (≥ 2 mots) |
| 3. préfixe | `abais` | `LIKE 'abais%'`, tri par longueur |
| 4. plein texte | `prix abaisser` | FTS5, chaque jeton en préfixe (≥ 2 mots) |
| 5. approchant | `abaissment` | similarité ≥ 80 et écart de longueur ≤ 34 % |

**Golden set de l'étude §5.4 : les cinq requêtes passent.** `abaisser` sort en tête avec ses expressions, `Abaisser les prix` ramène la collocation `de nu dzi / de asi le nu dzi`, `s'abaisser` est trouvé par les deux saisies, `abaissment` propose `abaissement`, `abandon` donne `gbegblêdi, yametsitsi, beble`.

**Performance :** médiane 1,9 ms, maximum 2,5 ms sur le golden set — l'objectif de l'étude est de 300 ms.

**Trois écarts assumés, chacun couvert par un test :**

1. **Cinq niveaux au lieu de quatre.** L'étude décrit quatre étapes (§5.1) mais range l'expression exacte à part dans son classement (§5.3) ; les deux lectures sont réconciliées, un mot exact sortant avant une expression.
2. **Les niveaux 2 et 4 exigent au moins deux mots.** Avec un seul mot, « l'expression contient ce mot » désigne une autre entrée : `maison` ramenait `démolir`, `abattre`, `accompagner`.
3. **Le niveau 5 n'utilise pas `WRatio`.** Ce score, proposé par l'étude, donnait plus de 80 à `an`, `ban` et `don` pour la requête `abandonner`. `fuzz.ratio` avec un écart de longueur borné ne garde que les vraies variantes.

**Deux notes d'implémentation :**

- SQLite refuse un alias à gauche de `MATCH` (`WHERE f MATCH ?` → « no such column: f »). L'annexe B de l'étude est correcte, elle nomme la table ; le piège est signalé dans le code.
- Le Python du poste tourne en mode isolé (`-I -P`) : le dossier courant n'est jamais dans `sys.path`. `recherche.py` amorce donc le chemin du dépôt, et les tests l'ajoutent eux-mêmes. `rapidfuzz` 3.14.6 est installé et déclaré dans `requirements.txt` ; sans lui, le moteur bascule sur `difflib`.

**45 tests verts :**

```bash
python -m unittest discover -s pipeline/tests -v   # 45 tests
python pipeline/recherche.py maison                # inspection manuelle
```

---

## 8. Suite immédiate

Lot 3 (API) : `api/main.py` avec `/v1/search`, `/v1/entry/{id}`, `/v1/word-of-the-day`, `/v1/stats`, `/v1/report`, `requirements.txt` complété (fastapi, uvicorn, pydantic) et tests HTTP. La couche métier est déjà là : `Moteur.recherche`, `Moteur.fiche`, `Moteur.mot_du_jour` ; il ne reste qu'à exposer, valider les entrées et brancher les signalements.

Une correction de données à prévoir au lot qualité : quelques traductions contiennent des restes de bas de page OCR (`donner` → « na. Vocabulaire don — dos donner qc »). Ils polluent l'affichage des résultats et mériteraient une règle de troncature explicite.
