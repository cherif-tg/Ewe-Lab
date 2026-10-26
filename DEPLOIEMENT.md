# Déploiement — Agbalẽ

Cible : **front sur Cloudflare Workers** (assets statiques), **API sur Render** (offre gratuite), et
la base du dictionnaire **hors du dépôt de code**, dans un dépôt privé dédié.

En production :

| Élément | URL |
|---|---|
| Front | https://agbale.tengacherif.workers.dev |
| API | https://agbale-api.onrender.com |
| Données | dépôt privé `cherif-tg/agble_donnees` |

Pourquoi cette contrainte : `dictionnaire.db` est une œuvre dérivée d'un lexique dont les droits ne
sont pas vérifiés. Elle ne doit être ni versionnée dans le dépôt public, ni téléchargeable, ni
servie comme fichier.

| Élément | Où | Coût |
|---|---|---|
| Front statique (`web/`) | Cloudflare Workers | gratuit |
| API (`api/main.py`) | Render, plan free | gratuit |
| Base `dictionnaire.db` | dépôt privé `cherif-tg/agble_donnees` | gratuit |
| Signalements | `contributions.db` sur Render | **effacés** à chaque redéploiement ou réveil |

L'ordre a compté : connaître l'origine du front avant de la déclarer côté API.

---

## 1. Base de données (en place)

Publiée dans **`cherif-tg/agble_donnees`**, branche `main`, fichier `agbale-dictionnaire.db` —
2 660 Ko, empreinte SHA-256 `B880EBBF…4004` vérifiée après publication.

L'URL à mettre dans `BASE_URL` :

```
https://api.github.com/repos/cherif-tg/agble_donnees/contents/agbale-dictionnaire.db?ref=main
```

Le jeton `GH_TOKEN` est un jeton fin, lecture seule, limité à ce dépôt (*Contents: read*). Il n'est
utilisé qu'à la construction ; il se saisit directement dans les variables d'environnement de
Render, jamais dans un fichier du dépôt.

**Deux pièges à la création du jeton**, tous deux responsables d'un `403 Resource not accessible` :

- *Repository access* doit être **Only select repositories** avec `agble_donnees` coché. En mode
  *Public repositories (read-only)*, GitHub **masque** la section des permissions : il n'y a donc
  rien à régler et aucun accès au dépôt privé.
- La section *Repository permissions* n'apparaît qu'après avoir choisi un accès par dépôt. C'est là
  que `Contents` passe en `Read-only`.

Le quota affiché par le diagnostic distingue les deux familles d'erreur : quelques milliers
restants = jeton reconnu, donc problème de permission ; une valeur proche de 60 = requête anonyme,
donc jeton absent.

Pour le vérifier avant de configurer Render : appeler l'URL ci-dessus avec l'en-tête
`Accept: application/vnd.github.raw` et une authentification `Bearer` portée par `GH_TOKEN`. Le
fichier reçu doit peser 2 660 Ko et avoir l'empreinte SHA-256 `B880EBBF…4004`. Un 404 indique une
sélection de dépôt trop restrictive, un 401 un jeton expiré ou mal copié.

Plus simple, le script sait se diagnostiquer lui-même (avec `BASE_URL` et `GH_TOKEN` définis dans
la session) :

```bash
python scripts/base_de_donnees.py --diagnostic
```

Il affiche le statut, la réponse brute de GitHub et une piste : permission manquante, quota
anonyme, fichier trop gros pour cette API, jeton expiré.

`scripts/base_de_donnees.py` accepte deux formes d'URL et choisit le type de média en conséquence :
fichier versionné (`/contents/…` → `application/vnd.github.raw`) ou asset de release
(`/releases/assets/<id>` → `application/octet-stream`). Se tromper renvoie du JSON ; le script le
détecte et s'arrête au lieu de démarrer sur un fichier corrompu.

## 2. Front sur Cloudflare Workers (en place)

Le site est servi par un **Worker à assets statiques**, racine `web/` :
**https://agbale.tengacherif.workers.dev**.

Un Worker n'est pas un projet Pages : l'origine à autoriser est
`https://agbale.tengacherif.workers.dev`, pas `*.pages.dev`. Les deux reposent sur le même CDN et
le même certificat, mais **les noms de domaine diffèrent** — c'est le piège de ce déploiement, et
il se paie par une erreur CORS silencieuse côté navigateur.

Mise à jour du front : si le Worker est connecté au dépôt, un `git push` le reconstruit ; sinon
`wrangler deploy` depuis la machine, en incluant `styles/`, `js/` et `fonts/`.

## 3. API sur Render

Nouveau *Blueprint* depuis le dépôt (Render lit `render.yaml`), ou service web manuel :

- **Build** : `pip install -r requirements.txt && python scripts/base_de_donnees.py`
- **Start** : `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- **Health check** : `/health`
- **Plan** : Free, région Frankfurt

Variables d'environnement :

| Nom | Valeur |
|---|---|
| `BASE_URL` | l'URL de l'étape 1 |
| `GH_TOKEN` | le jeton fin, lecture seule |
| `CORS_ORIGINS` | `https://agbale.tengacherif.workers.dev` (exactement, sans barre finale) |
| `DICTIONNAIRE_DB` | `dictionnaire.db` (déjà dans `render.yaml`) |

Vérifications une fois le service en ligne :

```bash
curl https://<service>.onrender.com/health
curl "https://<service>.onrender.com/v1/search?q=maison&limit=3"
curl https://<service>.onrender.com/v1/stats
```

`/v1/stats` doit renvoyer 6 937 entrées et 15 267 traductions : c'est la preuve que la base a bien
été récupérée au build.

## 4. Brancher le front sur l'API (fait)

`web/index.html` porte :

```html
<meta name="api-base" content="https://agbale-api.onrender.com">
```

`web/js/app.js` garde un repli sur `http://127.0.0.1:8000` quand la page est ouverte en local, donc
cette valeur ne gêne pas le développement.

## 5. Vérifier le parcours complet

Vérification CORS, la plus utile car elle échoue silencieusement dans le navigateur :

```bash
curl -s -o /dev/null -D - -H "Origin: https://agbale.tengacherif.workers.dev" https://agbale-api.onrender.com/v1/stats
```

La réponse doit contenir `access-control-allow-origin: https://agbale.tengacherif.workers.dev`.

- `https://agbale.tengacherif.workers.dev` : recherche « maison », ouverture d'une fiche, bascule
  « Texte d'origine ».
- Onglet « Apprendre » : les cinq leçons s'ouvrent ; l'exercice affiche « Aucun mot relu pour
  l'instant » (état normal tant que `data/verifications.csv` n'est pas rempli).
- Signalement depuis une fiche : réponse 201 — puis se souvenir qu'il ne survivra pas à un
  redéploiement.
- Console du navigateur : aucune erreur CORS. Une URL de préversion Worker (`<version>-agbale.<compte>.workers.dev`) a une origine différente : l'ajouter à `CORS_ORIGINS` pour la tester.

## 6. Ce que l'offre gratuite ne couvre pas

- **Réveil à froid** : après 15 minutes sans trafic, la première requête prend environ une minute.
  Un ping toutes les 14 minutes garde le service éveillé, dans la limite d'une instance gratuite.
- **Signalements volatils** : pas de disque persistant. Pour les conserver, il faudra une base
  externe (Supabase, Neon) et adapter `POST /v1/report`.
- **Quiz et taux d'erreur** : vides tant que la relecture humaine n'est pas faite. Ce n'est pas un
  problème de déploiement, mais ça se verra en ligne.

## 7. Mettre à jour la base

1. Reconstruire en local : `python pipeline/build_dictionary.py`.
2. Remplacer `agbale-dictionnaire.db` dans le dépôt privé (commit + push).
3. Render → *Manual Deploy* → *Clear build cache & deploy* : la construction retélécharge la base.
4. Vérifier `/v1/stats` : `version_donnees` doit être la date du jour.
