# Charte graphique et couleurs — Dictionnaire français–éwé

TENGA Cherif Abdel Azize — étude de design, version 1.0, 26 octobre 2026. Complète l'étude de mise en place du dictionnaire (sections 7 et 16).

## 1. Intention

L'interface doit être **sobre, calme et lisible** : un outil de recherche d'abord, un support d'apprentissage ensuite. Tout élément qui ne sert ni la recherche ni la compréhension est retiré.

### Cinq principes

1. **La recherche d'abord.** La barre de recherche est l'élément le plus visible de la page d'accueil.
2. **Un seul accent par écran.** Le vert guide l'œil ; le terracotta et l'ocre restent ponctuels.
3. **La couleur porte une information.** Français en anthracite, éwé en vert, statuts en badges : jamais de couleur décorative.
4. **Lisibilité avant décoration.** Grands corps de texte, interlignes généreux, contrastes mesurés.
5. **L'éwé s'affiche toujours correctement.** Le choix de la police est dicté par la couverture des lettres éwés, pas par le style.

### Ce que l'on évite

Dégradés, ombres marquées, motifs en fond de page, animations décoratives, plus d'un accent coloré par écran, illustrations sans fonction, texte sur image, majuscules forcées.

## 2. Lien avec l'identité « Terre & Savoir »

Le dictionnaire reprend la **famille de couleurs** de ta marque personnelle (terre, vert, crème, anthracite) pour que les deux univers se reconnaissent. Mais l'usage est plus calme : la marque LinkedIn est dense et colorée, l'application est aérée et majoritairement neutre.

| Élément | Marque LinkedIn | Application |
| --- | --- | --- |
| Fond | Crème `#F4ECDD` | Ivoire `#FBF8F2` (plus clair, moins fatigant en lecture longue) |
| Accent principal | Terracotta | **Vert profond** (apaisant, bon contraste) |
| Terracotta et ocre | Couleurs dominantes | Touches ponctuelles |
| Polices | Poppins et Lora | **Andika** (voir section 3) |

**Point important :** Poppins et Lora ne conviennent pas à l'application, car elles ne contiennent pas les lettres éwés (voir le test ci-dessous). Elles restent réservées aux visuels LinkedIn en français.

## 3. Typographie

### 3.1 Test de couverture des lettres éwés

J'ai vérifié, dans les versions distribuées par Fontsource (graisse normale 400), si chaque police contient les 14 lettres éwés `ɖ ɛ ƒ ɣ ŋ ɔ ʋ` et leurs majuscules `Ɖ Ɛ Ƒ Ɣ Ŋ Ɔ Ʋ`.

| Police | Lettres éwés | Accents combinants (aigu, grave, tilde, macron) |
| --- | --- | --- |
| **Andika** | Toutes présentes | Présents |
| **Charis SIL** | Toutes présentes | Présents |
| Gentium Plus | Toutes présentes | Présents |
| Noto Sans | Toutes présentes | Présents |
| Noto Serif | Toutes présentes | Présents |
| Inter | Toutes présentes | Présents |
| Source Sans 3 | Manquent `Ɖ`, `Ƒ`, `Ʋ` | Présents |
| Lexend | Manquent `ɖ ɛ ɣ ɔ ʋ` et leurs majuscules | Présents |
| Atkinson Hyperlegible | Manquent presque toutes | Présents |
| Lora | Manquent `ɖ ɛ ɣ ɔ ʋ` et leurs majuscules | Présents |
| **Poppins** | **Aucune** | **Aucun** |

**Limites du test :** il vérifie la présence des glyphes, pas la qualité du rendu (placement d'un accent sur `ɔ` ou `ɛ`, par exemple). Un test visuel sur de vrais appareils reste obligatoire. De plus, le diacritique combinant « caron » (ton montant) est absent de toutes les polices testées : sans conséquence en v1, puisque les tons ne sont pas notés, mais à retenir pour la leçon sur les tons.

### 3.2 Recommandation : Andika, famille unique

**Andika** est une police sans empattement conçue par SIL pour l'alphabétisation et les lecteurs débutants : formes de lettres sans ambiguïté, ce qui est précieux pour distinguer `ɔ`/`o`, `ɛ`/`e` ou `l`/`I`. Elle couvre toutes les lettres éwés, existe en 400 et 700 (normal et italique), et sa licence libre (OFL) permet de l'auto-héberger.

Une **famille unique** pour l'interface, le français, l'éwé et les leçons garantit la sobriété et un chargement léger.

**Alternatives :**

- **Charis SIL** (avec empattements), si tu veux une ambiance plus « livre » pour le texte des leçons.
- **Noto Sans**, comme repli technique à large couverture.

### 3.3 Échelle typographique

| Rôle | Taille | Graisse | Interligne |
| --- | --- | --- | --- |
| Titre de page | 2 rem (32 px) | 700 | 1,2 |
| Titre de section | 1,5 rem | 700 | 1,25 |
| Mot recherché (fiche) | 2 rem | 700 | 1,2 |
| Texte courant | 1,125 rem (18 px) | 400 | 1,6 |
| Traduction éwé | 1,3 rem (≈ 1,15 × le texte) | 700 | 1,5 |
| Texte secondaire, étiquettes | 0,9375 rem (15 px) | 400 | 1,5 |
| Boutons | 1 rem | 700 | 1 |

### 3.4 Règles d'usage

- Le texte éwé est affiché **légèrement plus grand que le français** et en **vert primaire**.
- Balises de langue : `lang="fr"` sur la page et `lang="ee"` sur chaque segment éwé (lecteurs d'écran, césure, correcteurs).
- Pas de majuscules forcées, pas d'espacement de lettres négatif.
- Largeur de ligne limitée à 65-70 caractères dans les leçons.
- Pile de polices : `"Andika", "Charis SIL", "Noto Sans", system-ui, -apple-system, "Segoe UI", sans-serif`.

### 3.5 Chargement

- Auto-héberger via le paquet npm `@fontsource/andika` (fichiers `woff2`), graisses **400 et 700 normales** ; l'italique seulement si une leçon en a besoin.
- Dans les fichiers testés, le sous-ensemble « latin » pèse environ 19 Ko et le sous-ensemble « latin-ext » (celui qui contient les lettres éwés) environ 81 Ko par graisse. Le navigateur ne charge le second que lorsqu'un caractère éwé apparaît.
- `font-display: swap` pour éviter une page vide pendant le chargement (Fontsource l'applique par défaut).

### 3.4 bis Chaîne de test à utiliser sur les appareils

`ɖ ɛ ƒ ɣ ŋ ɔ ʋ Ɖ Ɛ Ƒ Ɣ Ŋ Ɔ Ʋ ɔ́ ɛ̀ ɛ̃ ɔ̄ — gbɔdidi, gbegblɛdi, ɖe, ƒe, ʋu`

À tester sur au moins un Android d'entrée de gamme, un iPhone et un ordinateur, en vérifiant qu'aucun caractère ne s'affiche en carré et que les accents ne chevauchent pas la lettre.

## 4. Palette

### 4.1 Couleurs de base (mode clair)

| Nom | Code | Rôle |
| --- | --- | --- |
| Ivoire | `#FBF8F2` | Fond de page |
| Blanc | `#FFFFFF` | Surface des cartes et des champs |
| Crème | `#F4ECDD` | Zones secondaires (jamais pour du texte discret) |
| Anthracite | `#2A2118` | Texte principal, français |
| Brun doux | `#5B4F42` | Texte secondaire |
| Brun discret | `#7A6C5C` | Étiquettes, aide (uniquement sur ivoire ou blanc) |
| **Vert profond** | `#3F6B4A` | Accent principal : éwé, liens, boutons, focus |
| Vert survol | `#335A3E` | Survol et appui des boutons |
| Vert pâle | `#E4EEE5` | Fond de sélection, « À retenir », bonne réponse |
| Terracotta | `#C0552D` | Accent ponctuel : icônes, filets (éléments graphiques uniquement) |
| Terracotta texte | `#A3441F` | Texte coloré en terracotta |
| Terracotta pâle | `#F8E4DA` | Fond de « mauvaise réponse » (quiz) |
| Ocre | `#D9A441` | Surbrillance décorative (**jamais en texte**) |
| Ocre pâle | `#F6E7C4` | Mot du jour, badge « brouillon » |
| Bordure décorative | `#E3D9C6` | Séparateurs entre lignes |
| Bordure de champ | `#8C7F6E` | Contour des champs, boutons et touches |

### 4.2 Couleurs d'état

| État | Texte | Fond |
| --- | --- | --- |
| Succès | `#2E6B3B` | `#E4EEE5` |
| Erreur système (formulaire, API) | `#B3261E` | `#FBE6E3` |
| Information | `#2F5D7C` | `#FFFFFF` |
| Attention | Anthracite `#2A2118` | Ocre pâle `#F6E7C4` |

### 4.3 Proportions

Vise environ **85 % de neutres** (ivoire, blanc, anthracite), **10 % de vert** et **5 % de terracotta et d'ocre**. Si un écran semble chargé, supprime d'abord de la couleur, pas du contenu.

### 4.4 Rôle de la couleur

| Information | Représentation |
| --- | --- |
| Mot ou texte français | Anthracite |
| Traduction éwé | Vert primaire, gras, légèrement plus grand |
| Nature grammaticale (nom, verbe…) | Petite étiquette neutre (crème, texte brun doux) |
| Contenu relu / en relecture | Badge avec icône et texte (vert pâle / ocre pâle) |
| Bonne / mauvaise réponse | Fond pâle + icône + texte, jamais la couleur seule |

### 4.5 Contrastes mesurés (mode clair)

Calcul selon la formule WCAG 2.1. Seuils visés : **4,5:1** pour le texte courant, **3:1** pour le grand texte, les icônes et les contours de composants.

| Combinaison | Ratio | Verdict |
| --- | --- | --- |
| Anthracite sur ivoire | 14,90 | Excellent |
| Anthracite sur blanc | 15,80 | Excellent |
| Brun doux sur ivoire | 7,50 | Excellent |
| Brun discret sur ivoire | 4,80 | Conforme |
| Brun discret sur crème | 4,33 | **Insuffisant** : interdit sur crème |
| Vert primaire sur ivoire | 5,80 | Conforme |
| Vert primaire sur blanc | 6,15 | Conforme |
| Blanc sur vert primaire (boutons) | 6,15 | Conforme |
| Terracotta de marque `#C0552D` sur ivoire | 4,33 | **Insuffisant pour du texte** ; accepté pour un élément graphique (3:1) |
| Terracotta texte `#A3441F` sur ivoire | 5,82 | Conforme |
| Terracotta texte sur terracotta pâle | 5,02 | Conforme |
| Ocre `#D9A441` sur ivoire | 2,12 | **Interdit en texte et en icône** |
| Anthracite sur ocre | 7,02 | Conforme |
| Anthracite sur ocre pâle | 12,90 | Excellent |
| Succès sur vert pâle | 5,38 | Conforme |
| Erreur `#B3261E` sur ivoire | 6,17 | Conforme |
| Erreur sur son fond pâle | 5,46 | Conforme |
| Bordure de champ `#8C7F6E` sur blanc | 3,91 | Conforme (3:1) |
| Bordure de champ sur ivoire | 3,69 | Conforme (3:1) |

**Conséquence pratique :** le terracotta exact de ta marque ne passe pas en texte sur fond clair (4,33 contre 4,5 requis). On utilise donc `#A3441F` pour tout texte, et `#C0552D` seulement pour des éléments graphiques.

### 4.6 Mode sombre

Proposé dès la v1 via `prefers-color-scheme` : le coût est faible puisque tout passe par des variables.

| Rôle | Code | Contraste sur fond |
| --- | --- | --- |
| Fond | `#1C1712` | : |
| Surface | `#262019` | : |
| Bordure décorative | `#3A3228` | : |
| Bordure de champ | `#8C7F6E` | 4,55 (fond) / 4,13 (surface) |
| Texte | `#F1E9DA` | 14,74 / 13,36 |
| Texte secondaire | `#C9BCA6` | 9,51 / 8,62 |
| Texte discret | `#A19482` | 5,99 / 5,43 |
| Vert primaire | `#8FC09B` | 8,62 / 7,81 |
| Texte des boutons verts | `#1C1712` | 8,62 (sur vert) |
| Vert pâle (fond de sélection) | `#2C3F32` | texte `#F1E9DA` : 9,34 |
| Terracotta | `#E58A62` | 6,90 / 6,25 |
| Terracotta pâle (mauvaise réponse) | `#3A2219` | texte `#E58A62` : 5,72 |
| Ocre | `#E6B65C` | 9,49 |
| Ocre pâle | `#3A2F17` | texte `#F1E9DA` : 10,89 |
| Erreur | `#F2A39C` | 8,89 (fond `#3B1F1C` : 7,50) |

## 5. Mise en page et espacements

- **Mobile d'abord** ; points de rupture indicatifs : 600 px et 960 px.
- Colonne de contenu centrée, **largeur maximale 720 px** (≈ 65-70 caractères).
- Échelle d'espacement : 4, 8, 12, 16, 24, 32, 48, 64 px.
- Rayon des coins : 8 px (boutons, étiquettes) et 12 px (cartes, barre de recherche).
- Bordures de 1 px ; **pas d'ombre** (ou, au plus, un voile très léger sur les cartes survolées).
- Icônes de style contour (trait de 1,75 px, 20-24 px), une seule bibliothèque (par exemple Lucide).
- Zones tactiles d'au moins **44 × 44 px**.
- Animations : 150-200 ms maximum, désactivées si l'utilisateur a demandé `prefers-reduced-motion`.

## 6. Composants clés

### 6.1 Barre de recherche

Hauteur 56 px, rayon 12 px, fond blanc, bordure 1,5 px `#8C7F6E`. Au focus : bordure verte de 2 px et anneau vert léger. Loupe à gauche, bouton d'effacement à droite. Texte de 1,125 rem. Aucune couleur de fond vive.

### 6.2 Barre de caractères éwés

Sept touches `ɖ ɛ ƒ ɣ ŋ ɔ ʋ`, au-dessus du clavier ; majuscules par appui long ou touche Maj. Touches de 44 × 44 px, fond blanc, bordure `#8C7F6E`, caractère en anthracite de 1,25 rem. Défilement horizontal si l'écran est étroit. Les touches ne sont pas colorées : elles sont fonctionnelles, pas décoratives.

### 6.3 Liste de résultats

Une ligne par entrée : mot français en gras anthracite, étiquette de nature en neutre, première traduction en vert. Séparateurs de 1 px `#E3D9C6`, pas de lignes alternées, pas de cartes ombrées.

### 6.4 Fiche d'un mot

Titre du mot (2 rem). Sens regroupés sous trois intitulés discrets : *Sens principal*, *Expressions*, *Précisions de sens*. Traductions éwés en vert gras ; si plusieurs équivalents, séparés par des virgules. Actions (Copier, Partager, Signaler) en boutons à contour, avec icône et texte, jamais l'icône seule.

### 6.5 Mot du jour

Carte à fond ocre pâle `#F6E7C4`, sans bordure, texte anthracite. C'est le seul endroit de l'accueil où l'ocre apparaît comme aplat.

### 6.6 Badges de statut du contenu

- **Relu** : fond vert pâle, texte vert foncé, icône de coche.
- **Brouillon** : fond ocre pâle, texte anthracite, icône de crayon.

Le sens est toujours donné par le texte et l'icône, pas par la couleur seule.

### 6.7 Leçons

Texte de 1,125 rem, interligne 1,65, largeur 65-70 caractères. Encadré **« À retenir »** : filet gauche de 4 px vert, fond vert pâle. Exemples éwés en vert gras avec `lang="ee"`. Pas de bannières ni d'illustrations décoratives.

### 6.8 Exercices et quiz

Options en grands boutons pleine largeur. **Bonne réponse** : fond vert pâle, icône de coche, mention « Bonne réponse ». **Mauvaise réponse** : fond terracotta pâle, icône, mention « Pas tout à fait » et affichage de la bonne réponse. Barre de progression de 8 px en vert. Aucune animation festive.

### 6.9 Navigation

En-tête simple : nom du produit et trois liens (*Dictionnaire*, *Apprendre*, *À propos*). Sur mobile, barre d'onglets en bas avec les mêmes trois entrées. Onglet actif : texte vert gras et filet vert.

## 7. Identité du produit

- **Nom :** à choisir. Si tu retiens un nom en éwé, fais valider son sens et son orthographe par un locuteur natif.
- **Logo :** mot-symbole typographique en Andika 700, anthracite.
- **Monogramme / icône d'application :** une lettre éwé (`ɛ` ou `ɖ`) en vert sur fond ivoire, forme arrondie. À tester en 16 px pour le favicon : la queue du `ɖ` peut devenir illisible, auquel cas `ɛ` est plus sûr.
- **Motifs :** aucun en fond de page. Les arcs concentriques de ta marque LinkedIn peuvent apparaître discrètement dans l'en-tête de l'accueil ou dans les visuels de lancement, pas dans les pages de contenu.

## 8. Accessibilité (liste de contrôle)

- Contrastes conformes aux seuils de la section 4.5.
- L'information n'est jamais portée par la couleur seule (icône ou texte associés).
- Focus clavier visible : contour vert de 2 px.
- Texte courant d'au moins 18 px ; agrandissement à 200 % sans défilement horizontal.
- `lang="fr"` et `lang="ee"` correctement posés.
- Étiquettes accessibles sur les touches de la barre de caractères (par exemple « lettre ɔ »).
- Respect de `prefers-reduced-motion` et `prefers-color-scheme`.

## 9. Variables CSS prêtes à l'emploi

```css
/* npm i @fontsource/andika  puis, dans le point d'entrée : */
/* import "@fontsource/andika/400.css"; import "@fontsource/andika/700.css"; */

:root {
  /* Neutres */
  --fond: #FBF8F2;
  --surface: #FFFFFF;
  --fond-alt: #F4ECDD;
  --texte: #2A2118;
  --texte-sec: #5B4F42;
  --texte-discret: #7A6C5C;   /* uniquement sur --fond et --surface */
  --bordure: #E3D9C6;         /* séparateurs décoratifs */
  --bordure-champ: #8C7F6E;   /* champs, boutons, touches (>= 3:1) */

  /* Accent principal */
  --primaire: #3F6B4A;
  --primaire-hover: #335A3E;
  --primaire-fond: #E4EEE5;
  --sur-primaire: #FFFFFF;

  /* Accents ponctuels */
  --accent: #C0552D;          /* éléments graphiques uniquement */
  --accent-texte: #A3441F;
  --accent-fond: #F8E4DA;
  --ocre: #D9A441;            /* jamais en texte */
  --ocre-fond: #F6E7C4;

  /* États */
  --succes: #2E6B3B;
  --erreur: #B3261E;
  --erreur-fond: #FBE6E3;
  --info: #2F5D7C;

  /* Typographie */
  --police: "Andika", "Charis SIL", "Noto Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --t-base: 1.125rem;
  --t-ewe: 1.3rem;
  --t-petit: 0.9375rem;

  /* Forme */
  --rayon: 8px;
  --rayon-carte: 12px;
  --zone-tactile: 44px;
}

@media (prefers-color-scheme: dark) {
  :root {
    --fond: #1C1712;
    --surface: #262019;
    --fond-alt: #262019;
    --texte: #F1E9DA;
    --texte-sec: #C9BCA6;
    --texte-discret: #A19482;
    --bordure: #3A3228;
    --bordure-champ: #8C7F6E;
    --primaire: #8FC09B;
    --primaire-hover: #A6CFB0;
    --primaire-fond: #2C3F32;
    --sur-primaire: #1C1712;
    --accent: #E58A62;
    --accent-texte: #E58A62;
    --accent-fond: #3A2219;
    --ocre: #E6B65C;
    --ocre-fond: #3A2F17;
    --succes: #8FC09B;
    --erreur: #F2A39C;
    --erreur-fond: #3B1F1C;
    --info: #8DB8D6;
  }
}

html { font-size: 100%; }
body {
  margin: 0;
  background: var(--fond);
  color: var(--texte);
  font-family: var(--police);
  font-size: var(--t-base);
  line-height: 1.6;
}
[lang="ee"] { color: var(--primaire); font-weight: 700; font-size: var(--t-ewe); }
:focus-visible { outline: 2px solid var(--primaire); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
```

Les valeurs `--primaire-hover` et `--info` du mode sombre n'ont pas été mesurées : à vérifier avec un outil de contraste avant de figer les variables.

## 10. Mise en œuvre et validation

1. **Tester les polices** avec la chaîne de la section 3 sur trois appareils (Android d'entrée de gamme, iPhone, ordinateur).
2. **Maquetter quatre écrans** : accueil, résultats, fiche d'un mot, leçon. Le reste en découle.
3. **Figer les variables** dans un fichier `web/styles/tokens.css` du dépôt, et ne plus utiliser de couleur en dur ailleurs.
4. **Test avec 5 personnes** : trouver « abaisser », copier une traduction, faire un quiz. Noter les hésitations.
5. **Vérifier les contrastes** de toute nouvelle couleur avant de l'ajouter.

**Critères de réussite :** aucune lettre éwé en carré sur les appareils testés ; tous les textes au seuil AA ; un mot trouvé en moins de 10 secondes ; page d'accueil sans élément décoratif superflu.

## 11. Décisions à prendre

1. Famille unique **Andika**, ou Andika pour l'interface et Charis SIL pour le texte des leçons ?
2. Nom du produit.
3. Monogramme : `ɛ` ou `ɖ` (après test en 16 px).
4. Mode sombre dès la v1 (recommandé, car les variables sont prêtes) ou en v1.1.
5. Relecture des textes de l'interface par un locuteur natif.
