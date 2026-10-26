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
| `pipeline/` | `build_dictionary.py`, `recherche.py`, 45 tests | import et moteur (lots 1-2) |
| `api/` | `main.py`, 21 tests | service HTTP (lot 3) |
| `web/` | **vide** | lot 4 |
| `README.md` | **vide** | doit porter les chiffres d'audit, le schéma, la licence (étude §10) |
| `LICENCE.md` | **vide** | dépend de la vérification des droits (étude §9) |
| Git | 3 commits, branche `main` | architecture, pipeline, moteur |
| `.venv`, `requirements*.txt` | environnement `uv` (Python 3.14) | runtime et tests séparés |

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
| 3 | Monogramme (`ɛ` ou `ɖ`) | favicon | nom tranché le 26 octobre 2026 : **Agbalẽ** (voir §12) ; reste le monogramme, à tester en 16 px |
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
| **3. API** | `api/main.py` : six routes `/v1`, CORS restreint, limiteur sur `/report`, `contributions.db` séparée | **livré** : 21 tests verts + serveur réel vérifié (détail §8) |
| **4. Web** | `web/` : jetons de la charte, quatre écrans, barre de caractères, Andika auto-hébergée | **livré** : parcours complet vérifié sous jsdom contre l'API réelle ; reste le test visuel sur appareils (détail §9) |
| **5. Qualité et lancement** | échantillon de 200 sens, taux d'erreur, page de transparence, `README`, `LICENCE` | **partiel** : échantillon et circuit du taux livrés, `README` et `LICENCE` écrits ; taux en attente de relecture humaine (détail §10) |
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

## 8. Lot 3 — API livrée le 26 octobre 2026

`api/main.py` : application FastAPI construite par une fabrique (`creer_app`), pour que les tests injectent une base temporaire sans toucher aux variables d'environnement.

| Route | Rôle |
|---|---|
| `GET /health` | disponibilité et version |
| `GET /v1/search?q=&limit=` | cascade ; `results` (niveaux 1 à 4) et `suggestions` (niveau 5) séparés |
| `GET /v1/entry/{id}?brut=` | fiche ; `brut=true` ajoute la graphie numérisée (étude §7.2) |
| `GET /v1/word-of-the-day?jour=` | mot du jour, déterministe par date |
| `GET /v1/stats` | compteurs de `meta` ; `taux_erreur_estime` reste `null` tant que l'échantillon n'est pas fait |
| `POST /v1/report` | signalement (201), limité à 5 envois par tranche de 10 minutes et par IP |

**Cinq choix à connaître :**

1. `results` ne contient que les niveaux 1 à 4 ; les mots approchants partent dans `suggestions` (3 au plus), selon la lecture de l'étude §7.2. Conséquence assumée : `abaissment` renvoie `count: 0` et `suggestions: ["abaissement", …]` — l'interface affiche « Vouliez-vous dire ? ».
2. La base du dictionnaire reste ouverte en **lecture seule** ; `contributions.db` est un fichier distinct, créé au démarrage (étude §3.3).
3. Un contact vide n'est pas stocké (`""` → `NULL`) : pas de donnée personnelle inutile (étude §9).
4. `/v1/report` refuse une entrée inconnue et un texte vide **avant** d'écrire, en 422.
5. CORS limité par défaut aux ports locaux 8000 et 5173, surchargeable par `CORS_ORIGINS`.

**Vérifications :** 21 tests API verts, avec une application neuve par test pour que le limiteur reparte de zéro. Serveur réel démarré sur un port de test : `/health`, `/v1/search`, `/v1/stats`, `/v1/word-of-the-day`, `/v1/report` et un 404 vérifiés à la main, journal uvicorn sans avertissement.

Dépendances ajoutées : `fastapi` 0.162, `uvicorn[standard]` 0.54, `pydantic` 2.14, et `httpx2` 2.16 côté tests — Starlette 1.10 déprécie `httpx` pour son client de test.

**Lancement :**

```bash
python -m uvicorn api.main:app --reload          # http://127.0.0.1:8000/docs
python -m unittest discover -s api/tests -v      # 21 tests
```

---

## 9. Lot 4 — interface livrée le 26 octobre 2026

Site statique, sans framework ni étape de build : `web/index.html` charge `styles/polices.css`, `styles/tokens.css`, `styles/app.css` et `js/app.js`.

| Fichier | Rôle |
|---|---|
| `web/styles/tokens.css` | jetons de la charte §9, recopiés tels quels (clair + sombre) |
| `web/styles/app.css` | mise en page et composants ; aucune couleur ni taille en dur |
| `web/styles/polices.css` | deux `@font-face` Andika (sous-ensembles fusionnés, voir §12) |
| `web/js/app.js` | routeur par ancre, recherche différée de 200 ms, fiche, signalement |
| `web/fonts/` | Andika 400 et 700, 70,3 Ko par graisse (sous-ensembles fusionnés) |

**Écrans :** accueil (recherche, barre de caractères, mot du jour en ocre pâle), résultats avec « Vouliez-vous dire ? », fiche groupée en *Sens principal / Expressions / Précisions de sens*, à propos avec les chiffres de `/v1/stats`. Routes : `#/`, `#/recherche/<q>`, `#/mot/<id>`, `#/apprendre`, `#/a-propos`.

**Conforme à la charte :** barre de recherche de 56 px, touches éwés de 44 × 44 px avec touche Maj et appui long, traductions éwés en vert et plus grandes, étiquette de nature neutre, actions en boutons à contour avec icône **et** texte, aucune ombre, mode sombre par `prefers-color-scheme`, focus visible, `lang="fr"` / `lang="ee"`, titres de vue en `sr-only` et annonces par région `aria-live` dédiée.

**Poids : 40 Ko hors polices** (objectif de l'étude : 200 Ko). Les 79,5 Ko du sous-ensemble étendu ne se téléchargent que si un caractère éwé apparaît, grâce aux plages calculées.

**Vérification :** le navigateur intégré refuse les adresses locales, la page a donc été exécutée sous **jsdom** avec le vrai HTML et la vraie API. Parcours déroulé : mot du jour affiché, recherche « abaisser » → 2 résultats, fiche → h1, trois groupes, expressions complètes (« abaisser les prix »), bascule du texte d'origine (« di gbô ame »), dialogue de signalement ouvert puis envoyé (201), touche `ɔ` insérée, suggestions sur « abaissment », chiffres de la page à propos, liste des 5 leçons. Aucune erreur dans le journal uvicorn.

**Quatre limites assumées :**

1. **Routage par ancre**, pas par chemin : `#/mot/2` au lieu de `/mot/abaisser`. Les liens sont partageables, mais le référencement et les URL lisibles demanderont un rendu par page (lot 5).
2. **`ẽ` (U+1EBD) est absent des deux sous-ensembles Andika** — mesuré, la charte ne l'avait pas relevé. Résolu au moment du choix du nom : les sous-ensembles sont fusionnés et le tilde se compose (voir §12).
3. **La barre de caractères est peu utile en v1** : la recherche ne va que du français vers l'éwé. Elle reste en place comme le demande la charte et deviendra fonctionnelle avec la recherche inverse (v2).
4. **Nom du produit et monogramme encore provisoires** : « Dictionnaire français–éwé » et `ɛ` sur ivoire. Les décisions 2 et 3 de la charte restent ouvertes.

**Lancement (deux terminaux) :**

```bash
python -m uvicorn api.main:app --reload                        # API sur 8000
python -m http.server 5173 --directory web                     # front sur 5173
```

Le test visuel sur appareils réels reste à faire : chaîne de contrôle de la charte §3.4 bis (`ɖ ɛ ƒ ɣ ŋ ɔ ʋ Ɖ Ɛ Ƒ Ɣ Ŋ Ɔ Ʋ ɔ́ ɛ̀ ɛ̃ ɔ̄ — gbɔdidi, gbegblɛdi, ɖe, ƒe, ʋu`) sur un Android d'entrée de gamme, un iPhone et un ordinateur.

---

## 10. Lot 5 — accueil, FAQ, qualité et documents (26 octobre 2026)

### Page d'accueil

Un héros au-dessus du champ de recherche : surtitre, titre de promesse (« Cherche un mot français, obtiens l'éwé »), texte court, bouton **Commencer** et bouton *Questions fréquentes*, puis les chiffres de la base (6 937 entrées, 15 267 traductions). Sous le champ, quatre exemples cliquables (eau, maison, abaisser, lumière).

Sous la ligne de flottaison : le mot du jour, un bloc **Comment ça marche** en trois étapes (chercher, lire, corriger) et un aperçu de la FAQ avec trois questions et un lien vers la page complète. Le bouton **Commencer** amène le focus dans le champ de recherche et fait défiler la page, en respectant `prefers-reduced-motion`.

### FAQ

Page `#/faq`, **douze questions** en `<details>` natifs — donc accessibles au clavier sans JavaScript, uniquement stylés. Elles répondent sur : l'origine des données, les erreurs de transcription, le bouton « Texte d'origine », les graphies encore en attente (`ê`, `ë`, `ï`, `û`), l'ancienneté des mots, le signalement, la gratuité et l'absence de compte, le téléchargement impossible tant que les droits ne sont pas vérifiés, l'absence d'éwé → français et d'audio, la saisie des lettres éwés, l'accessibilité.

La charte fixe trois entrées de navigation ; la FAQ n'en ajoute pas une quatrième : elle est atteignable par le héros, le pied de page et un renvoi depuis « À propos ».

### Qualité et documents

- **`pipeline/echantillon.py`** — tirage reproductible de 200 sens (graine 42) vers `audit_out/echantillon_200.csv`, colonnes à remplir ; puis `--depouiller` qui compte les verdicts, calcule le taux et l'écrit dans `data/qualite.csv`.
- **Circuit du taux** — `build_dictionary.py` lit le dernier taux mesuré et le stocke dans `meta` ; `/v1/stats` le publie ; l'interface affiche « en cours de mesure » tant qu'il vaut `null`.
- **`README.md`** — démarrage, organisation, chiffres d'audit, règles d'orthographe, niveaux de recherche, routes, tests, limites connues.
- **`LICENCE.md`** — statut réel : licence du code non choisie, droits du lexique non vérifiés (consultation seule, pas d'export), Andika sous SIL OFL 1.1 avec le texte intégral dans `web/fonts/OFL.txt`.

### Vérifications

**73 tests verts** (51 pipeline + 22 API). Le parcours de la page a été rejoué sous jsdom contre l'API réelle : héros et chiffres affichés, **Commencer** place le focus dans le champ, un exemple lance la recherche (maison → 2 résultats), fiche et titre de page corrects, FAQ à 12 questions avec héros masqué, signalement général ouvert depuis le pied de page, retour à l'accueil qui rétablit héros et exemples.

Poids de la page : **55 Ko hors polices** (objectif : 200 Ko).

### Ce qui reste

Le taux d'erreur ne peut pas être calculé sans relecture humaine de l'échantillon : les 200 lignes sont prêtes dans `audit_out/echantillon_200.csv`. Restent aussi les URL lisibles, la troncature des restes de bas de page OCR, le test sur appareils réels, le nom du produit, le monogramme et la vérification des droits.

---

## 11. Avant publication

Quatre choses bloquent une mise en ligne sérieuse, dans cet ordre :

1. **Droits du lexique** — sans vérification, pas de dépôt public du fichier ni d'export. C'est la seule inconnue juridique du projet.
2. **Taux d'erreur** — les 200 lignes sont prêtes ; il faut une relecture humaine (idéalement un locuteur natif) pour remplir la colonne `verdict`, puis :
   ```bash
   python pipeline/echantillon.py --depouiller audit_out/echantillon_200.csv
   python pipeline/build_dictionary.py
   ```
   Le taux apparaît alors dans `/v1/stats` et sur la page « À propos ».
3. **Test sur appareils réels** — la chaîne de contrôle de la charte (`ɖ ɛ ƒ ɣ ŋ ɔ ʋ Ɖ Ɛ Ƒ Ɣ Ŋ Ɔ Ʋ ɔ́ ɛ̀ ɛ̃ ɔ̄`) sur un Android d'entrée de gamme, un iPhone et un ordinateur, pour vérifier qu'aucune lettre éwé ne sort en carré.
4. **Nom du produit et monogramme** — décisions 2 et 3 de la charte, encore ouvertes ; le nom actuel est un intitulé de travail.

Ensuite seulement : déploiement (API + front séparés), URL lisibles par rendu de page, et les trois publications de lancement prévues par l'étude §15.

---

## 12. Nom du produit : Agbalẽ (26 octobre 2026)

**Décision :** le dictionnaire s'appelle **Agbalẽ**, mot éwé pour « livre » (entrée `livre` du lexique : `agbalê`). L'atelier reste *Ewe Lab* ; le produit a son nom propre.

### La graphie : `ẽ`, pas `é`

Trois candidats ont été écartés : *Nunya* (déjà pris par le tuteur IA du même auteur), *Lexi* (au moins sept produits homonymes dans la catégorie dictionnaire/apprentissage), *Nya* (trop proche de *Nunya* à l'oreille).

Le mot s'écrit `agbalẽ` avec un **tilde** : `ẽ` est la voyelle nasale. `Agbalé`, avec un accent aigu, n'est pas un mot éwé — c'est précisément le type d'erreur que le projet corrige. Le nom est donc écrit `Agbalẽ` partout, y compris dans le mot-symbole.

### Conséquence technique : fusion des sous-ensembles de police

Le glyphe précomposé U+1EBD n'existe dans aucun des deux sous-ensembles Andika (mesuré au lot 4). Le rendu dépend donc de la décomposition `e` + tilde combinant (U+0303).

Or le découpage `unicode-range` du lot 4 plaçait `e` et `̃` dans des fichiers différents : **deux fichiers distincts ne composent pas un accent**. Le tilde se serait posé au hasard.

Décision : les sous-ensembles latin et latin-ext sont **fusionnés** en un seul fichier par graisse (`web/fonts/andika-400.woff2`, `andika-700.woff2`, 70,3 Ko chacun, 1 322 points de code). Écart assumé par rapport à la charte §3.5, qui voyait dans le découpage une économie : ici le texte éwé est présent sur presque tous les écrans, et le découpage cassait le rendu.

Bilan de poids : 140 Ko de polices au total au lieu de 197 Ko avec les quatre fichiers, et une composition correcte.

**Vérifié** par façonnage HarfBuzz sur la police fusionnée : `Agbalẽ` produit `A g b a l e + tildecomb` avec une avance nulle pour le tilde, donc attaché à la lettre ; le texte en NFC (U+1EBD) est décomposé automatiquement par HarfBuzz, ce qui rend le rendu indépendant de la forme saisie.

### Ce qui a changé

`<title>` et description, mot-symbole `Agbalẽ` avec sous-titre « dictionnaire français–éwé », titres de page (`abaisser — Agbalẽ`), titre de l'API FastAPI, `README.md`, `LICENCE.md`, libellé du favicon. Le monogramme reste `ɛ` : la décision 3 de la charte n'est pas tranchée.
