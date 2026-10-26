# Étude de mise en place — Dictionnaire français–éwé

**Projet :** application web de dictionnaire français → éwé
**Source de données :** `riebstein-lexique-v2.tsv` (dataset Hugging Face `cheriftenga/tg-nlp-toolkit-fr-ewe-v0.3`)
**Auteur :** TENGA Cherif Abdel Azize — Data Scientist & AI Engineer
**Date :** 26 octobre 2026
**Statut :** étude de cadrage, prête pour l'implémentation
**Version :** 1.1 — décisions du 26 octobre 2026 : orthographe éwé standard, dépôt séparé, module « Apprendre l'éwé »

---

## 0. Fiche synthèse

| Élément | Décision |
|---|---|
| Promesse | « Cherche un mot français, obtiens l'éwé, avec ses sens et expressions. » |
| Sens de la v1 | Français → éwé uniquement (l'éwé → français est une v2) |
| Données | Lexique numérisé, structure hiérarchique à reconstruire (entrée → sens/expressions → traductions) |
| Base de données | SQLite + recherche plein texte FTS5 |
| API | FastAPI (réutilisable par le site, le bot WhatsApp et OpenMind) |
| Interface | Web mobile-first, légère, avec barre de caractères éwés |
| Recherche | Cascade : exacte → préfixe → plein texte → approximative (fautes de frappe) |
| Hébergement | Gratuit au départ (API + front séparés) |
| Orthographe | Affichage en caractères éwé standard (`ô → ɔ`, `ê → ɛ`, règles validées) ; texte d'origine conservé |
| Dépôt | Dépôt séparé du toolkit (`dictionnaire-ewe`) ; données propres publiées sur Hugging Face |
| Module « Apprendre » | Mini-parcours d'apprentissage de l'éwé (écriture, lecture), livré juste après la v1 (section 16) |
| Durée estimée | v1 : 9 à 10 jours ; module « Apprendre » : 4 à 5 jours en plus |
| Priorité absolue | **Qualité du nettoyage des données**, avant le code web |

---

## 1. Contexte et objectifs

### 1.1 Pourquoi ce projet

- **Utilité publique :** peu d'outils numériques de qualité existent pour l'éwé.
- **Visibilité :** un dictionnaire se partage facilement (mot du jour, liens directs vers un mot).
- **Cohérence du portfolio :** il prolonge le toolkit NLP éwé/kabiyè et nourrit les projets suivants (OpenMind, bot WhatsApp).
- **Collecte de données :** les signalements et propositions des utilisateurs alimenteront un futur corpus d'éwé contemporain.

### 1.2 Objectifs mesurables de la v1

1. 100 % des entrées du lexique importées avec leur structure (entrée, sens, traductions).
2. Réponse de recherche inférieure à 300 ms pour une requête courante.
3. Taux d'erreurs de transcription **mesuré** sur un échantillon et **affiché** dans l'application.
4. Un mécanisme de signalement d'erreur fonctionnel.
5. Un lancement public accompagné de 3 publications.

### 1.3 Hors périmètre de la v1

Éwé → français, audio et prononciation, mode hors-ligne, comptes utilisateurs, application mobile native.

Le module « Apprendre l'éwé » est prévu **juste après la v1** (voir section 16).

---

## 2. Analyse du lexique numérisé

### 2.1 Format observé

Colonnes : `section ; entree ; nature ; sous_entree ; traduction_ewe`.

Remarque : le fichier est nommé `.tsv`, mais l'extrait fourni utilise le **point-virgule** comme séparateur. Le script de lecture détecte automatiquement le séparateur (point-virgule ou tabulation).

### 2.2 Extrait annoté

| section | entree | nature | sous_entree | traduction_ewe | Rôle de la ligne |
|---|---|---|---|---|---|
| A | abaissement | m | | bobodeanyi | **Entrée principale** (nom masculin) |
| A | | | des prix | asidzidede, nudzidede | Expression : « abaissement des prix » |
| A | | | de Peau | tsimiemie, emedzedze | Expression (⚠ probable erreur OCR : « de l'eau ») |
| A | | | du sol | wedzedze, abudidi | Expression : « abaissement du sol » |
| A | | | (diminution) | dede, wewowo, … | **Glose** : précise le sens |
| A | | | (humiliation) | vlododo, bobodeanyi, … | **Glose** : autre sens |
| A | abaisser | vt | | didi nu de anyi, … | Entrée principale (verbe transitif) |
| A | | | les prix | de nu dzi, … | Expression : « abaisser les prix » |
| A | | | quelqu'un | do vlo ame, … | Expression : « abaisser quelqu'un » |
| A | | | (diminuer) | de nu le nu nu, … | Glose |
| A | s'abaisser | v | | bobo amedokui de anyi, … | Entrée principale (verbe pronominal, nature `v`) |
| A | | | (devenir plus bas) | dze we, de do, wo do | Glose |
| A | abandon | m | | gbegblêdi, yametsitsi, beble | Entrée principale |

### 2.3 Règles de lecture déduites

1. **Ligne d'entrée :** `entree` non vide. Elle porte la `nature` et éventuellement une traduction principale.
2. **Ligne de sous-entrée :** `entree` vide. Elle appartient à la dernière entrée rencontrée (**propagation vers le bas**, ou *forward fill*).
3. **Trois types de sens**, déterminés par `sous_entree` :
   - vide → `principal` ;
   - entre parenthèses, par exemple `(diminution)` → `glose` (précision de sens) ;
   - autre texte, par exemple `des prix` → `collocation` (expression complète : « abaissement **des prix** »).
4. **Traductions multiples :** plusieurs équivalents séparés par des virgules → un enregistrement par équivalent, avec son rang d'apparition.
5. **Expression reconstruite :** pour la recherche et l'affichage, on compose `mot_fr + sous_entree` (ex. « abaisser les prix »), pour qu'une recherche sur l'expression complète aboutisse.

### 2.4 Anomalies détectées dès l'extrait

| Constat | Exemple | Traitement proposé |
|---|---|---|
| Probable erreur OCR | `de Peau` (→ « de l'eau ») | Table de corrections versionnée |
| Majuscule parasite au milieu d'un mot | `anyL` (la forme `anyi` apparaît ailleurs) | Détection automatique, correction après relecture |
| Espacement incohérent | `bobodeanyi` et `bobo ... de anyi` | Conserver la forme brute, signaler, ne pas fusionner automatiquement |
| Voyelles à accent circonflexe | `gbegblêdi`, `gbôdidi` | **À clarifier** (voir 2.5) |
| Apostrophes | `quelqu'un`, `s'abaisser` | Normaliser `’` en `'` dans la clé de recherche |

### 2.5 Décision : les caractères `ô` et `ê`

**Hypothèse retenue :** dans la colonne éwé, `ô` et `ê` représentent les voyelles `ɔ` et `ɛ` de l'éwé classique. **L'application affichera ses sorties en caractères éwé standard.**

| Brut | Standard | Statut |
|---|---|---|
| `ô` / `Ô` | `ɔ` / `Ɔ` | à valider |
| `ê` / `Ê` | `ɛ` / `Ɛ` | à valider |

**Règles d'application :**
- Valider d'abord sur **30 à 50 occurrences** (l'audit fournit un échantillon prêt à relire), puis passer les règles au statut `valide`.
- Convertir **uniquement la colonne éwé** : dans les colonnes françaises, `ô` et `ê` sont normaux.
- Stocker trois formes : `ewe_brut` (tel que numérisé), `ewe` (standard, affichée) et `ewe_cle` (clé de recherche). La recherche reste tolérante : `ô`, `ɔ` et `o` donnent la même clé.
- Les règles vivent dans un fichier versionné (`orthographe.csv`) ; seules celles marquées `valide` sont appliquées.

**Point de vigilance : les consonnes `ɖ`, `ƒ`, `ʋ`.** La conversion des voyelles est mécanique, pas celle des consonnes : l'éwé distingue `d`/`ɖ`, `f`/`ƒ` et `v`/`ʋ`. Si la numérisation a écrit des `d`, `f`, `v` simples, **aucune règle automatique ne peut les restaurer** (par exemple `de` et `ɖe` sont deux mots différents). L'audit indique si ces lettres sont présentes. Si elles sont absentes, une **restauration assistée** sera nécessaire : propositions de candidats à partir des fréquences du corpus fr↔éwé du toolkit, puis validation humaine.

### 2.6 Indicateurs à calculer avant tout développement

Le script d'audit (annexe A) fournit : nombre d'entrées, nombre de sens, nombre de traductions, inventaire des valeurs de `nature`, inventaire des caractères de la colonne éwé, nombre d'anomalies par type. **Ces chiffres seront publiés dans le README** et servent de base au suivi qualité.

### 2.7 Codes de nature

Valeurs vues : `m`, `vt`, `v`. Interprétation probable : nom masculin, verbe transitif, verbe. **À confirmer avec la liste des abréviations du lexique source**, puis à compléter avec toutes les valeurs trouvées par l'audit (`f`, `adj`, `adv`, `vi`, etc.).

---

## 3. Modèle de données

### 3.1 Schéma conceptuel

```
entrees (1) ──< sens (1) ──< traductions
                  │
                  ├─ type : principal | collocation | glose
                  └─ phrase_fr : expression complète reconstruite
```

### 3.2 Schéma SQL (SQLite)

```sql
PRAGMA journal_mode = WAL;

CREATE TABLE entrees (
  id           INTEGER PRIMARY KEY,
  section      TEXT NOT NULL,
  mot_fr       TEXT NOT NULL,            -- forme d'affichage (« s'abaisser »)
  mot_fr_cle   TEXT NOT NULL,            -- clé de recherche (« abaisser »)
  nature       TEXT,
  ligne_source INTEGER NOT NULL          -- traçabilité vers le fichier d'origine
);
CREATE INDEX idx_entrees_cle ON entrees(mot_fr_cle);

CREATE TABLE sens (
  id           INTEGER PRIMARY KEY,
  entree_id    INTEGER NOT NULL REFERENCES entrees(id),
  ordre        INTEGER NOT NULL,
  type         TEXT NOT NULL CHECK (type IN ('principal','collocation','glose')),
  libelle_fr   TEXT,                     -- « des prix » ou « diminution »
  phrase_fr    TEXT NOT NULL,            -- « abaissement des prix »
  ligne_source INTEGER NOT NULL
);
CREATE INDEX idx_sens_entree ON sens(entree_id, ordre);

CREATE TABLE traductions (
  id        INTEGER PRIMARY KEY,
  sens_id   INTEGER NOT NULL REFERENCES sens(id),
  rang      INTEGER NOT NULL,
  ewe_brut  TEXT NOT NULL,               -- tel que numérisé
  ewe       TEXT NOT NULL,               -- forme affichée : corrections + caractères éwé standard
  ewe_cle   TEXT NOT NULL,               -- clé de recherche (sans accents)
  verifie   INTEGER NOT NULL DEFAULT 0   -- 1 = relu par un humain
);
CREATE INDEX idx_trad_sens ON traductions(sens_id, rang);

-- Recherche plein texte (français) et inverse (éwé, pour la v2)
CREATE VIRTUAL TABLE fts_fr  USING fts5(texte, sens_id UNINDEXED,
  tokenize = "unicode61 remove_diacritics 2");
CREATE VIRTUAL TABLE fts_ewe USING fts5(texte, sens_id UNINDEXED,
  tokenize = "unicode61 remove_diacritics 2");

CREATE TABLE anomalies (
  id           INTEGER PRIMARY KEY,
  ligne_source INTEGER,
  type         TEXT NOT NULL,
  detail       TEXT
);
```

### 3.3 Base séparée pour les contributions

Les signalements sont stockés dans **un second fichier** (`contributions.db`), pour que la base du dictionnaire reste en lecture seule et reproductible.

```sql
CREATE TABLE signalements (
  id          INTEGER PRIMARY KEY,
  entree_id   INTEGER,
  type        TEXT NOT NULL CHECK (type IN ('erreur','proposition','usage')),
  texte       TEXT NOT NULL,
  contact     TEXT,
  cree_le     TEXT NOT NULL DEFAULT (datetime('now')),
  statut      TEXT NOT NULL DEFAULT 'nouveau'
);
```

---

## 4. Pipeline de nettoyage et d'import

### 4.1 Étapes

1. **Lecture** : détection du séparateur, encodage UTF-8 (avec BOM éventuel), comptage des lignes.
2. **Normalisation Unicode (NFC)** : indispensable pour que les caractères éwés composés soient stockés de façon unique.
3. **Reconstruction de la hiérarchie** : propagation de l'entrée courante vers les lignes suivantes.
4. **Classification des sous-entrées** : `principal`, `glose` ou `collocation`.
5. **Séparation des traductions** sur la virgule, en ignorant les virgules entre parenthèses.
6. **Corrections et orthographe standard** : table `corrections.csv` (colonnes `brut;corrige;motif`), puis conversion des caractères via `orthographe.csv` (colonnes `brut;standard;statut`, règles `valide` uniquement).
7. **Calcul des clés de recherche** (minuscules, sans accents, `ɖ→d`, `ɛ→e`, `ɔ→o`, `ƒ→f`, `ŋ→n`, `ʋ→v`, `ɣ→g`, apostrophes unifiées).
8. **Détection d'anomalies** (traduction vide, majuscule interne, symbole suspect, ligne orpheline).
9. **Écriture en base** et indexation plein texte.
10. **Rapport d'import** : comptages, inventaires, anomalies.

### 4.2 Principes

- **Ne jamais écraser la donnée brute** : `ewe_brut` est conservé.
- **Tout est rejouable** : le script reconstruit la base depuis zéro à chaque exécution.
- **Chaque correction est tracée** dans `corrections.csv`, versionné dans Git avec un motif.
- **Traçabilité** : chaque enregistrement garde le numéro de ligne source.

Le script complet figure en **annexe A**.

---

## 5. Moteur de recherche

### 5.1 Stratégie en cascade

| Niveau | Technique | Exemple |
|---|---|---|
| 1 | Égalité sur la clé | « abaisser » → entrée `abaisser` |
| 2 | Préfixe | « abais » → abaissement, abaisser… |
| 3 | Plein texte FTS5 (expressions) | « abaisser les prix » |
| 4 | Approximative (RapidFuzz, seuil 80) | « abaissment » → abaissement |

On s'arrête dès qu'un niveau renvoie assez de résultats, et on dédoublonne par entrée.

### 5.2 Normalisation de la requête

- Casse et accents ignorés.
- Apostrophe typographique ou droite équivalentes.
- Articles et marques pronominales initiaux ignorés pour la clé d'entrée (`s'abaisser` est trouvé aussi par « abaisser »).
- Saisie d'éwé tolérante : `d` accepté pour `ɖ`, `e` pour `ɛ`, `o` pour `ɔ`, etc.

### 5.3 Classement des résultats

1. Correspondance exacte de l'entrée.
2. Correspondance exacte d'une expression (`phrase_fr`).
3. Préfixe, trié par longueur croissante.
4. Approximatif, trié par score.

### 5.4 Jeu de tests de référence (« golden set »)

À partir de l'extrait, voici des tests prêts à automatiser :

| Requête | Résultat attendu |
|---|---|
| `abaisser` | entrée `abaisser`, avec ses expressions |
| `Abaisser les prix` | `de nu dzi, de asi le nu dzi` |
| `s'abaisser` et `abaisser` | l'entrée `s'abaisser` est trouvée dans les deux cas |
| `abaissment` (faute) | suggestion `abaissement` |
| `abandon` | `gbegblêdi, yametsitsi, beble` |

---

## 6. API

### 6.1 Endpoints de la v1

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/search?q=...&limit=20` | Recherche en cascade |
| GET | `/entry/{id}` | Fiche complète d'une entrée |
| GET | `/word-of-the-day` | Mot du jour (déterministe par date) |
| POST | `/report` | Signalement ou proposition |
| GET | `/stats` | Chiffres publics (entrées, taux d'erreur estimé, version) |
| GET | `/health` | Vérification de disponibilité |

### 6.2 Exemple de réponse `/entry/{id}`

```json
{
  "id": 2,
  "mot": "abaisser",
  "nature": "vt",
  "sens": [
    {"type": "principal",   "libelle": null,
     "traductions": ["didi nu de anyi", "bobo nu de anyi"]},
    {"type": "collocation", "libelle": "les prix",
     "traductions": ["de nu dzi", "de asi le nu dzi"]},
    {"type": "glose",       "libelle": "diminuer",
     "traductions": ["de nu le nu nu", "de nu da", "de nu dzi suso"]}
  ]
}
```

### 6.3 Bonnes pratiques

- Base du dictionnaire en **lecture seule**.
- Limitation de débit sur `/report` (anti-spam).
- CORS restreint au domaine du front.
- Versionner l'API (`/v1/...`) dès le départ : le bot WhatsApp et OpenMind en dépendront.

Squelette complet en **annexe B**.

---

## 7. Interface utilisateur

### 7.1 Écrans

1. **Accueil :** champ de recherche, barre de caractères éwés, mot du jour.
2. **Résultats :** liste (mot français, nature, première traduction), suggestions « Vouliez-vous dire ? ».
3. **Fiche d'un mot :** entrée, sens regroupés (sens principal, expressions, précisions de sens), boutons Copier / Partager / Signaler.
4. **À propos :** sources, attribution, taux d'erreur estimé, version des données.
5. **Signaler / proposer :** formulaire court (erreur, proposition, « ce mot est-il utilisé aujourd'hui ? »).

### 7.2 Exigences de conception

- **Mobile d'abord** : la majorité des utilisateurs seront sur téléphone.
- Recherche instantanée avec délai de 200 ms avant envoi.
- **Barre de caractères spéciaux** (ɖ ɛ ƒ ɣ ŋ ɔ ʋ) au-dessus du clavier.
- **Sorties en caractères éwé standard** : l'affichage, la copie et le partage utilisent la forme standard ; une option « Voir le texte d'origine » montre `ewe_brut`.
- Liens directs par mot (`/mot/abaisser`) pour le partage et le référencement.
- Partage via l'API Web Share quand elle est disponible, sinon copie du lien.
- Page légère (objectif : moins de 200 Ko hors polices), police **auto-hébergée** couvrant les caractères éwés (Charis SIL ou Noto Sans, à tester avec : `ɖ ɛ ƒ ɣ ŋ ɔ ʋ Ɖ Ɛ Ƒ Ɣ Ŋ Ɔ Ʋ ɔ́ ɛ̀ ɛ̃`). Les lettres suivies d'un accent combiné s'affichent parfois mal selon la police.
- Accessibilité : contrastes suffisants, tailles de texte lisibles, navigation clavier.

### 7.3 Mention de transparence

Sur la fiche et la page « À propos » : *« Données issues d'un lexique numérisé. Des erreurs de transcription sont possibles (taux estimé : X %). Certains termes peuvent être anciens. Aidez-nous à corriger. »*

---

## 8. Qualité et validation

### 8.1 Échantillonnage manuel

- Tirer **200 sens au hasard** (graine fixée), les comparer à la source, classer les erreurs : caractère, espacement, mot manquant, mauvaise ligne.
- Calculer le taux d'erreur par type, publier le chiffre global.
- Prioriser la correction des erreurs **systématiques** (une règle peut en corriger des centaines).

### 8.2 Tests automatiques

- Tests unitaires du parsing (hiérarchie, gloses, séparation des traductions).
- Golden set de recherche (section 5.4).
- Contrôles d'intégrité : aucune entrée sans sens, aucun sens sans traduction, clés de recherche non vides.

### 8.3 Boucle d'amélioration continue

Signalements → relecture → `corrections.csv` → reconstruction de la base → nouvelle version publiée avec un journal des changements.

---

## 9. Aspects juridiques et attribution

- Le nom du fichier renvoie à une source nommée (Riebstein). **Vérifier l'auteur, l'année, le statut des droits et la licence du dataset** avant publication.
- Afficher l'**attribution** dans l'application et dans le README.
- Si le statut juridique est incertain : proposer la recherche mais ne pas offrir le téléchargement complet de la base, et chercher à contacter les ayants droit.
- Informer les contributeurs de l'usage de leurs propositions (mention sur le formulaire).
- Ne pas collecter de données personnelles superflues (le contact est facultatif).

---

## 10. Déploiement

| Composant | Option recommandée | Remarque |
|---|---|---|
| Base | Fichier SQLite livré avec l'API | Petit, en lecture seule |
| API | Conteneur Docker (Hugging Face Space ou service équivalent) | Vérifier les limites du plan gratuit (mise en veille possible) |
| Front | Hébergement statique (même plateforme que le portfolio) | Déploiement continu depuis GitHub |
| Contributions | `contributions.db` sur un volume persistant, ou table dans un service gratuit | Sauvegarde régulière |

**Variante v2 :** embarquer la base dans le navigateur (SQLite compilé en WebAssembly) pour un fonctionnement hors-ligne, utile dans les zones à connexion faible.

### Organisation du dépôt

Le dictionnaire vit dans **un dépôt séparé du toolkit** : le toolkit est un paquet Python de NLP, le dictionnaire est une application (données, API, interface). Avantages : déploiements simples, API légère (sans torch ni transformers), carte de projet distincte dans le portfolio, droits ciblés pour l'équipe.

```
dictionnaire-ewe/
├─ data/
│  ├─ corrections.csv
│  └─ orthographe.csv
├─ pipeline/
│  ├─ audit.py
│  └─ build_dictionary.py
├─ api/
│  ├─ main.py
│  └─ tests/
├─ web/
├─ content/              (module « Apprendre », section 16)
│  ├─ lecons/
│  └─ themes.csv
├─ docs/
│  └─ etude_dictionnaire_francais_ewe.md
├─ README.md
└─ LICENSE               (+ attribution de la source)
```

**Passerelle avec le toolkit :**
- Les données propres sont publiées sur Hugging Face (nouvelle version du dataset ou dataset dédié), avec fiche de données, attribution et journal des corrections. Le toolkit et OpenMind les utilisent comme glossaire.
- Une fois stable, le module d'orthographe (conversion en caractères standard, normalisation) peut être déplacé dans le toolkit, **sans dépendance lourde**, pour servir aussi à la post-édition des traductions.
- Le fichier brut du lexique n'est pas versionné dans le dépôt tant que le statut juridique n'est pas vérifié : le README indique où le récupérer.

Le `README` contient : captures, chiffres de l'audit, schéma de données, instructions de reconstruction, licence et attribution.

---

## 11. Calendrier (9 à 10 jours)

| Jour | Tâches | Livrable |
|---|---|---|
| 1 | Audit du fichier, inventaires (natures, caractères), décision `ô/ê` | Rapport d'audit |
| 2 | Parsing, schéma SQLite, premières corrections | `dictionnaire.db` v0 |
| 3 | Échantillon de 200 sens, relecture, table de corrections | Taux d'erreur mesuré |
| 4 | API : recherche en cascade, fiche d'entrée | API locale fonctionnelle |
| 5 | Golden set, tests, mot du jour, signalements | Tests verts |
| 6-7 | Interface : accueil, résultats, fiche, barre de caractères | Front fonctionnel |
| 8 | Partage, page « À propos », transparence, accessibilité | Version bêta |
| 9 | Déploiement, README, captures, vidéo de démo | Lien public |
| 10 | Lancement (3 publications) et collecte des premiers retours | Lancement |

L'équipe de deux personnes peut prendre en charge l'interface (jours 6 à 8) pendant que tu traites les données et l'API.

---

## 12. Contributions et corpus d'éwé contemporain

- Chaque fiche propose trois actions : **« Utilisé aujourd'hui »**, **« Vieilli »**, **« Incorrect »**, et un champ « proposer une autre traduction ».
- Ces retours sont une **source de données précieuse** : ils indiquent quels termes sont vivants et alimentent le futur corpus d'éwé moderne (ce qui répond à la limite actuelle du modèle de traduction, entraîné surtout sur du texte biblique).
- Toute proposition passe par une **validation humaine** avant d'entrer dans la base.

---

## 13. Intégration avec les projets suivants

### 13.1 OpenMind (RAG)

- Exposer le dictionnaire comme **outil** de l'assistant : vérifier ou proposer la terminologie lors de la sortie en éwé.
- Utiliser les entrées comme **glossaire** pour contrôler les termes clés après la traduction automatique.
- Ces usages sont à valider par des tests comparatifs avant de les annoncer.

### 13.2 Bot WhatsApp

- Message type : l'utilisateur envoie un mot, le bot renvoie les 2 ou 3 premières traductions, une expression utile et un lien vers la fiche.
- L'envoi de messages sortants (mot du jour) suppose le respect des règles de la plateforme WhatsApp (consentement, modèles de messages) : à vérifier avant de concevoir cette fonction.
- Le bot appelle simplement l'API `/search` : **aucune logique n'est dupliquée**.

---

## 14. Risques et parades

| Risque | Impact | Parade |
|---|---|---|
| Erreurs OCR plus nombreuses qu'attendu | Perte de confiance | Mesure sur échantillon, mention publique, boucle de correction |
| Incertitude sur `ô/ê` et l'orthographe | Données faussées | Conserver le brut, recherche tolérante, décision documentée |
| Registre ancien du lexique | Mots peu utilisés aujourd'hui | Marquage « vieilli », retours utilisateurs |
| Droits d'auteur incertains | Blocage de publication | Vérification précoce, publication partielle si besoin |
| Hébergement gratuit instable | Indisponibilité | Page de secours, option de base embarquée (v2) |
| Dispersion entre projets | Retard | Périmètre v1 strict, calendrier fixe |
| Consonnes `ɖ`, `ƒ`, `ʋ` absentes de la numérisation | Affichage incomplet | Audit, puis restauration assistée avec validation humaine |
| Contenu pédagogique inexact | Perte de crédibilité, apprentissage erroné | Relecture par locuteur natif, statut de chaque leçon, sources citées |
| Extension du périmètre (module « Apprendre ») | Retard du lancement | Livraison après la v1, contenu minimal |
| Spam sur les signalements | Pollution | Limitation de débit, validation manuelle |

---

## 15. Plan de lancement

1. **Teaser :** « J'ai numérisé un dictionnaire français–éwé. Voici pourquoi c'était un vrai défi. » (avant/après d'une page)
2. **Coulisses :** les problèmes d'encodage, de structure et d'OCR, avec un exemple concret (`de Peau` → `de l'eau`).
3. **Lancement :** lien, vidéo de démo de 30 secondes, appel à signaler des erreurs et à proposer des mots.
4. **Suite régulière :** « mot éwé de la semaine », bilan chiffré à 30 jours (recherches, contributions, mots corrigés).

**Indicateurs de suivi :** nombre de recherches, mots les plus demandés, mots introuvables (liste de manques), signalements reçus, partages.

---

## 16. Module « Apprendre l'éwé » (v1.1)

### 16.1 Intention

Prolonger la recherche d'un mot par une petite direction pédagogique : **écrire, lire, retenir**. Public : débutants francophones, élèves, diaspora. Le module est livré **après la v1**, pour ne pas retarder le lancement du dictionnaire.

### 16.2 Parcours de la v1.1

| Leçon | Contenu | Exercice |
|---|---|---|
| 1. L'alphabet éwé | Lettres spéciales (`ɖ ɛ ƒ ɣ ŋ ɔ ʋ`), digraphes courants, majuscules | Associer une lettre à un mot exemple (QCM) |
| 2. Écrire l'éwé | Saisir les caractères (barre de caractères, claviers), pourquoi `d` et `ɖ` sont deux lettres différentes | Recopier des mots avec les bons caractères |
| 3. Lire l'éwé | Syllabes et mots simples, repères de prononciation par comparaison (sans audio en v1) | Relier un mot écrit à son sens |
| 4. Les tons (introduction) | L'éwé est une langue tonale ; les tons ne sont généralement pas notés dans l'écriture courante | Sensibilisation uniquement, sans évaluation |
| 5. Vocabulaire par thèmes | Salutations, nombres, famille, marché… tirés du dictionnaire | Fiches de révision et quiz |

### 16.3 Exercices générés depuis le dictionnaire

- QCM français → éwé et éwé → français, avec des distracteurs de même nature grammaticale.
- Fiches de révision avec répétition espacée simple (boîtes de Leitner), progression stockée **dans le navigateur** (pas de compte en v1).
- Exercice de saisie avec la barre de caractères éwés.
- **Porte qualité :** seules les entrées relues (`verifie = 1`) alimentent les exercices, pour qu'un apprenant ne retienne jamais une erreur de numérisation.

### 16.4 Données et structure

```sql
CREATE TABLE themes (id INTEGER PRIMARY KEY, nom TEXT NOT NULL UNIQUE);
CREATE TABLE entree_theme (
  entree_id INTEGER NOT NULL REFERENCES entrees(id),
  theme_id  INTEGER NOT NULL REFERENCES themes(id),
  PRIMARY KEY (entree_id, theme_id)
);
-- v2 : enregistrements audio de locuteurs natifs, avec consentement écrit
CREATE TABLE audios (
  id INTEGER PRIMARY KEY,
  traduction_id INTEGER NOT NULL REFERENCES traductions(id),
  url TEXT NOT NULL, locuteur TEXT, consentement INTEGER NOT NULL DEFAULT 0
);
```

Les leçons sont des fichiers Markdown dans `content/lecons/`, avec un en-tête :

```yaml
---
titre: "L'alphabet éwé"
statut: brouillon        # brouillon | relu
relu_par: ""
sources: []
---
```

`content/themes.csv` associe une centaine de mots du dictionnaire à des thèmes, à constituer à la main au départ.

### 16.5 API

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/v1/learn/lessons` | Liste des leçons et de leur statut |
| GET | `/v1/learn/lessons/{slug}` | Contenu d'une leçon |
| GET | `/v1/learn/quiz?theme=...&n=10` | Quiz généré depuis les entrées relues |

### 16.6 Exactitude du contenu

- Chaque leçon est relue par **au moins un locuteur natif** ou s'appuie sur une référence citée (orthographe officielle, grammaire publiée).
- Tant qu'une leçon est au statut `brouillon`, l'application affiche « contenu en cours de relecture ».
- Pas d'audio en v1. En v2, uniquement des enregistrements de locuteurs identifiés ayant donné leur consentement.

### 16.7 Calendrier (4 à 5 jours après la v1)

| Jour | Tâches |
|---|---|
| 1 | Format des leçons, rédaction des leçons 1 et 2 |
| 2 | Thèmes, quiz généré depuis l'API |
| 3 | Pages de leçons et exercices dans l'interface |
| 4 | Fiches de révision et progression locale |
| 5 | Relecture, corrections, lancement |

### 16.8 Valeur pour le branding

Le module renforce ton positionnement de **vulgarisateur** : mini-série « L'éwé en 5 leçons », publication « Écrire l'éwé avec les bons caractères », et passerelle naturelle vers tes formations et ton coaching.

---

## 17. Prochaines actions

- [ ] Exécuter le script d'audit sur le fichier complet et noter les chiffres
- [ ] Valider `ô → ɔ` et `ê → ɛ` sur 30 à 50 occurrences (échantillon fourni par `audit.py`) et vérifier la présence de `ɖ`, `ƒ`, `ʋ` dans l'inventaire
- [ ] Vérifier les droits et la licence du lexique
- [ ] Confirmer la liste des abréviations de `nature`
- [ ] Construire `dictionnaire.db` et mesurer le taux d'erreur sur 200 sens
- [ ] Mettre en place l'API et le golden set
- [ ] Concevoir l'interface mobile
- [ ] Créer le dépôt séparé et publier les données propres sur Hugging Face
- [ ] Déployer et lancer la v1
- [ ] Démarrer le module « Apprendre l'éwé » (section 16)

---

## Annexe A — Script de construction de la base (`build_dictionary.py`)

```python
#!/usr/bin/env python3
"""Construit dictionnaire.db à partir du lexique numérisé
(colonnes : section;entree;nature;sous_entree;traduction_ewe)."""
import csv
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "riebstein-lexique-v2.tsv")
DB = Path("dictionnaire.db")
CORRECTIONS = Path("corrections.csv")  # colonnes : brut;corrige;motif (facultatif)
ORTHO = Path("orthographe.csv")        # colonnes : brut;standard;statut (facultatif)

EWE_FOLD = str.maketrans(
    {"ɖ": "d", "ɛ": "e", "ɔ": "o", "ƒ": "f", "ŋ": "n", "ʋ": "v", "ɣ": "g"}
)

SCHEMA = """
PRAGMA journal_mode = WAL;
CREATE TABLE entrees (
  id INTEGER PRIMARY KEY, section TEXT NOT NULL, mot_fr TEXT NOT NULL,
  mot_fr_cle TEXT NOT NULL, nature TEXT, ligne_source INTEGER NOT NULL);
CREATE INDEX idx_entrees_cle ON entrees(mot_fr_cle);
CREATE TABLE sens (
  id INTEGER PRIMARY KEY, entree_id INTEGER NOT NULL REFERENCES entrees(id),
  ordre INTEGER NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('principal','collocation','glose')),
  libelle_fr TEXT, phrase_fr TEXT NOT NULL, ligne_source INTEGER NOT NULL);
CREATE INDEX idx_sens_entree ON sens(entree_id, ordre);
CREATE TABLE traductions (
  id INTEGER PRIMARY KEY, sens_id INTEGER NOT NULL REFERENCES sens(id),
  rang INTEGER NOT NULL, ewe_brut TEXT NOT NULL, ewe TEXT NOT NULL,
  ewe_cle TEXT NOT NULL, verifie INTEGER NOT NULL DEFAULT 0);
CREATE INDEX idx_trad_sens ON traductions(sens_id, rang);
CREATE VIRTUAL TABLE fts_fr USING fts5(
  texte, sens_id UNINDEXED, tokenize = "unicode61 remove_diacritics 2");
CREATE VIRTUAL TABLE fts_ewe USING fts5(
  texte, sens_id UNINDEXED, tokenize = "unicode61 remove_diacritics 2");
CREATE TABLE anomalies (
  id INTEGER PRIMARY KEY, ligne_source INTEGER, type TEXT NOT NULL, detail TEXT);
"""


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s).strip()


def fold(s: str) -> str:
    """Clé de recherche : minuscules, sans accents, lettres éwés ramenées à l'ASCII."""
    s = nfc(s).lower().replace("’", "'").translate(EWE_FOLD)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s']|_", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def lemma_key(fr: str) -> str:
    """Clé d'entrée : ignore « s' », « se », articles initiaux."""
    return re.sub(r"^(s'|se |l'|la |le |les |un |une )", "", fold(fr))


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


def load_corrections() -> dict[str, str]:
    if not CORRECTIONS.exists():
        return {}
    with open(CORRECTIONS, encoding="utf-8", newline="") as f:
        return {r["brut"]: r["corrige"] for r in csv.DictReader(f, delimiter=";")}


def apply_corrections(s: str, corr: dict[str, str]) -> str:
    """Correction sur la traduction entière, sinon mot par mot."""
    if s in corr:
        return corr[s]
    return " ".join(corr.get(tok, tok) for tok in s.split(" "))


def load_ortho() -> dict[int, str]:
    """Règles d'orthographe validées uniquement, sous forme de table pour str.translate."""
    if not ORTHO.exists():
        return {}
    with open(ORTHO, encoding="utf-8", newline="") as f:
        return {
            ord(r["brut"]): r["standard"]
            for r in csv.DictReader(f, delimiter=";")
            if r["statut"].strip() == "valide" and len(r["brut"]) == 1
        }


def to_standard(s: str, table: dict[int, str]) -> str:
    """Convertit vers les caractères éwé standard (NFC d'abord : « o + ^ » devient « ô »)."""
    return nfc(s).translate(table)


def read_rows(path: Path):
    """Itère (numéro_de_ligne, dict, colonnes_en_trop) ; détecte le séparateur."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        head = f.read(4096)
        f.seek(0)
        delim = ";" if head.count(";") >= head.count("\t") else "\t"
        reader = csv.DictReader(f, delimiter=delim)
        for row in reader:
            clean, extra = {}, False
            for k, v in row.items():
                if k is None:          # colonnes en trop
                    extra = True
                    continue
                clean[k] = (v or "").strip() if isinstance(v, str) or v is None else ""
            yield reader.line_num, clean, extra


def main() -> None:
    corr = load_corrections()
    ortho = load_ortho()
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    cur = con.cursor()

    entry_id, mot, ordre = None, "", 0
    nb_entrees = nb_sens = nb_trad = 0
    chars: Counter = Counter()
    natures: Counter = Counter()
    anomalies: Counter = Counter()

    def anomalie(line: int, kind: str, detail: str) -> None:
        anomalies[kind] += 1
        cur.execute(
            "INSERT INTO anomalies(ligne_source, type, detail) VALUES (?,?,?)",
            (line, kind, detail),
        )

    for line, r, extra in read_rows(SRC):
        if extra:
            anomalie(line, "colonnes_en_trop", str(r))

        entree = nfc(r.get("entree", ""))
        if entree:
            nature = r.get("nature", "")
            natures[nature] += 1
            cur.execute(
                "INSERT INTO entrees(section, mot_fr, mot_fr_cle, nature, ligne_source)"
                " VALUES (?,?,?,?,?)",
                (r.get("section", ""), entree, lemma_key(entree), nature, line),
            )
            entry_id, mot, ordre = cur.lastrowid, entree, 0
            nb_entrees += 1
        elif entry_id is None:
            anomalie(line, "ligne_orpheline", str(r))
            continue

        sous = nfc(r.get("sous_entree", ""))
        if not sous:
            typ, libelle, phrase = "principal", None, mot
        elif re.fullmatch(r"\(.*\)", sous):
            typ = "glose"
            libelle = sous[1:-1].strip()
            phrase = f"{mot} ({libelle})"
        else:
            typ, libelle, phrase = "collocation", sous, f"{mot} {sous}"

        ordre += 1
        cur.execute(
            "INSERT INTO sens(entree_id, ordre, type, libelle_fr, phrase_fr, ligne_source)"
            " VALUES (?,?,?,?,?,?)",
            (entry_id, ordre, typ, libelle, phrase, line),
        )
        sens_id = cur.lastrowid
        nb_sens += 1
        cur.execute(
            "INSERT INTO fts_fr(texte, sens_id) VALUES (?,?)", (fold(phrase), sens_id)
        )

        traductions = split_translations(r.get("traduction_ewe", ""))
        if not traductions:
            anomalie(line, "traduction_vide", phrase)

        for rang, brut in enumerate(traductions, 1):
            ewe = to_standard(apply_corrections(brut, corr), ortho)
            chars.update(ewe)
            if re.search(r"[a-zà-ÿɖɛɔƒŋʋɣ][A-Z]", ewe):
                anomalie(line, "majuscule_interne", ewe)
            if re.search(r"[0-9|\\/_@#]", ewe):
                anomalie(line, "symbole_suspect", ewe)
            cur.execute(
                "INSERT INTO traductions(sens_id, rang, ewe_brut, ewe, ewe_cle)"
                " VALUES (?,?,?,?,?)",
                (sens_id, rang, brut, ewe, fold(ewe)),
            )
            cur.execute(
                "INSERT INTO fts_ewe(texte, sens_id) VALUES (?,?)", (fold(ewe), sens_id)
            )
            nb_trad += 1

    cur.execute("INSERT INTO fts_fr(fts_fr) VALUES ('optimize')")
    cur.execute("INSERT INTO fts_ewe(fts_ewe) VALUES ('optimize')")
    con.commit()
    con.close()

    print(f"Entrées      : {nb_entrees}")
    print(f"Sens         : {nb_sens}")
    print(f"Traductions  : {nb_trad}")
    print(f"Natures      : {dict(natures)}")
    print(f"Anomalies    : {dict(anomalies)}")
    print("Caractères non ASCII de la colonne éwé :")
    for c, n in sorted(chars.items(), key=lambda x: -x[1]):
        if ord(c) > 127:
            print(f"  {c!r} U+{ord(c):04X} : {n}")


if __name__ == "__main__":
    main()
```

**Exemple de `corrections.csv`** (à enrichir après relecture ; une correction s'applique à la traduction entière ou, à défaut, à un mot isolé) :

```csv
brut;corrige;motif
anyL;anyi;majuscule parasite (OCR), forme confirmée ailleurs dans le lexique
```

**Exemple de `orthographe.csv`** (à passer en `valide` après vérification sur échantillon) :

```csv
brut;standard;statut
ô;ɔ;valide
Ô;Ɔ;valide
ê;ɛ;valide
Ê;Ɛ;valide
```

> Les corrections portant sur le **français** (par exemple `de Peau` → `de l'eau` dans `sous_entree`) nécessitent une petite extension du script (même mécanisme appliqué à la colonne `sous_entree`). À ajouter lors du jour 2.

---

## Annexe B — Squelette de l'API (`main.py`)

```python
import datetime as dt
import hashlib
import sqlite3
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from build_dictionary import fold, lemma_key  # même normalisation que l'import

DB_PATH = "dictionnaire.db"
CONTRIB_PATH = "contributions.db"

app = FastAPI(title="API Dictionnaire français–éwé", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ton-domaine.example"],   # à remplacer
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
con.row_factory = sqlite3.Row


@lru_cache(maxsize=1)
def lemmes() -> list[tuple[int, str]]:
    rows = con.execute("SELECT id, mot_fr_cle FROM entrees").fetchall()
    return [(r["id"], r["mot_fr_cle"]) for r in rows]


def fetch_entry(entry_id: int) -> dict | None:
    e = con.execute("SELECT * FROM entrees WHERE id = ?", (entry_id,)).fetchone()
    if not e:
        return None
    sens = []
    for s in con.execute(
        "SELECT * FROM sens WHERE entree_id = ? ORDER BY ordre", (entry_id,)
    ):
        trads = [
            t["ewe"]
            for t in con.execute(
                "SELECT ewe FROM traductions WHERE sens_id = ? ORDER BY rang", (s["id"],)
            )
        ]
        sens.append({"type": s["type"], "libelle": s["libelle_fr"], "traductions": trads})
    return {"id": e["id"], "mot": e["mot_fr"], "nature": e["nature"], "sens": sens}


def search_ids(q: str, limit: int) -> list[int]:
    k = lemma_key(q)
    if not k:
        return []
    ids: list[int] = []

    def add(rows) -> None:
        for r in rows:
            if r[0] not in ids:
                ids.append(r[0])

    # 1. exacte
    add(con.execute("SELECT id FROM entrees WHERE mot_fr_cle = ?", (k,)))
    # 2. préfixe
    if len(ids) < limit:
        add(con.execute(
            "SELECT id FROM entrees WHERE mot_fr_cle LIKE ? ORDER BY length(mot_fr_cle) LIMIT ?",
            (k + "%", limit),
        ))
    # 3. plein texte (expressions complètes)
    if len(ids) < limit:
        tokens = fold(q).split()
        if tokens:
            match = " ".join(f'"{t}"*' for t in tokens)
            add(con.execute(
                "SELECT DISTINCT s.entree_id FROM fts_fr f JOIN sens s ON s.id = f.sens_id "
                "WHERE fts_fr MATCH ? LIMIT ?",
                (match, limit),
            ))
    # 4. approximative (fautes de frappe)
    if len(ids) < limit:
        choices = lemmes()
        for _, score, idx in process.extract(
            k, [c[1] for c in choices], scorer=fuzz.WRatio, limit=limit, score_cutoff=80
        ):
            if choices[idx][0] not in ids:
                ids.append(choices[idx][0])
    return ids[:limit]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/search")
def search(q: str = Query(..., min_length=1, max_length=80), limit: int = Query(20, le=50)):
    results = [fetch_entry(i) for i in search_ids(q, limit)]
    return {"query": q, "count": len(results), "results": [r for r in results if r]}


@app.get("/v1/entry/{entry_id}")
def entry(entry_id: int):
    e = fetch_entry(entry_id)
    if not e:
        raise HTTPException(status_code=404, detail="Entrée introuvable")
    return e


@app.get("/v1/word-of-the-day")
def word_of_the_day():
    total = con.execute("SELECT COUNT(*) FROM entrees").fetchone()[0]
    day = dt.date.today().isoformat()
    index = int(hashlib.sha256(day.encode()).hexdigest(), 16) % total
    row = con.execute("SELECT id FROM entrees ORDER BY id LIMIT 1 OFFSET ?", (index,)).fetchone()
    return fetch_entry(row["id"])


class Report(BaseModel):
    entree_id: int | None = None
    type: str = Field(pattern="^(erreur|proposition|usage)$")
    texte: str = Field(min_length=2, max_length=500)
    contact: str | None = Field(default=None, max_length=100)


@app.post("/v1/report", status_code=201)
def report(r: Report):
    c = sqlite3.connect(CONTRIB_PATH)
    c.execute(
        "CREATE TABLE IF NOT EXISTS signalements ("
        "id INTEGER PRIMARY KEY, entree_id INTEGER, type TEXT NOT NULL, texte TEXT NOT NULL,"
        "contact TEXT, cree_le TEXT NOT NULL DEFAULT (datetime('now')),"
        "statut TEXT NOT NULL DEFAULT 'nouveau')"
    )
    c.execute(
        "INSERT INTO signalements(entree_id, type, texte, contact) VALUES (?,?,?,?)",
        (r.entree_id, r.type, r.texte, r.contact),
    )
    c.commit()
    c.close()
    return {"status": "recu"}
```

**Dépendances :** `fastapi`, `uvicorn`, `rapidfuzz`, `pydantic`.
**Lancement local :** `uvicorn main:app --reload`.

> À ajouter avant la mise en ligne : limitation de débit sur `/v1/report` et endpoint `/v1/stats`.
