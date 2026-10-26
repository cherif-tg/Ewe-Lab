# Déploiement — Agbalẽ

Cible retenue : **front sur Cloudflare Pages**, **API sur Render** (offre gratuite), et la base
du dictionnaire **hors du dépôt**, téléchargée à la construction depuis un asset de release privé.

Pourquoi cette contrainte : `dictionnaire.db` est une œuvre dérivée d'un lexique dont les droits ne
sont pas vérifiés. Elle ne doit être ni versionnée, ni téléchargeable, ni servie comme fichier. Un
hébergement qui publie le dépôt (Space Hugging Face public, Pages avec la base dans le repo)
reviendrait à distribuer la donnée.

| Élément | Où | Coût |
|---|---|---|
| Front statique (`web/`) | Cloudflare Pages | gratuit |
| API (`api/main.py`) | Render, plan free | gratuit |
| Base `dictionnaire.db` | dépôt privé `cherif-tg/agble_donnees` | gratuit |
| Signalements | `contributions.db` sur Render | **effacés** à chaque redéploiement ou réveil |

---

## 1. Préparer la base (en local)

```bash
python pipeline/build_dictionary.py
```

Vérifier qu'elle existe et pèse ~2,6 Mo, puis créer l'archive à déposer en asset :

```bash
python -c "import shutil; shutil.copy('dictionnaire.db', 'agbale-dictionnaire.db')"
```

## 2. Dépôt privé de données (en place)

La base est publiée dans **`cherif-tg/agble_donnees`**, branche `main`, fichier
`agbale-dictionnaire.db` — 2 660 Ko, empreinte SHA-256 vérifiée après publication.

### L'URL à mettre dans `BASE_URL`

```
https://api.github.com/repos/cherif-tg/agble_donnees/contents/agbale-dictionnaire.db?ref=main
```

### Le jeton

Créer un **jeton fin, lecture seule, limité à ce dépôt** (*Contents: read*) — c'est `GH_TOKEN`.
Il ne sert qu'à la construction : ne pas le mettre dans le dépôt.

### Les deux formes d'URL acceptées

`scripts/base_de_donnees.py` choisit le type de média selon l'adresse :

| Forme | Exemple | Média demandé |
|---|---|---|
| fichier versionné | `…/contents/agbale-dictionnaire.db?ref=main` | `application/vnd.github.raw` |
| asset de release | `…/releases/assets/<id>` | `application/octet-stream` |

Se tromper de média renvoie du JSON au lieu de la base ; le script le détecte et s'arrête avec un
message explicite plutôt que de démarrer sur un fichier corrompu.

Un asset de release reste possible et évite de versionner un binaire : joindre
`agbale-dictionnaire.db` à une release, puis relever l'`id` de l'asset.

## 3. API sur Render

Nouveau *Blueprint* à partir du dépôt, ou service web manuel avec :

- **Build** : `pip install -r requirements.txt && python scripts/base_de_donnees.py`
- **Start** : `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- **Health check** : `/health`

Variables :

| Nom | Valeur |
|---|---|
| `BASE_URL` | URL de l'asset de l'étape 2 |
| `GH_TOKEN` | jeton de lecture du dépôt privé |
| `CORS_ORIGINS` | `https://<projet>.pages.dev` (plus le domaine perso s'il existe) |
| `DICTIONNAIRE_DB` | `dictionnaire.db` (déjà dans `render.yaml`) |

Si le build échoue sur la version de Python, ajouter `PYTHON_VERSION` = `3.13.4`.

Vérifications une fois le service en ligne :

```bash
curl https://<service>.onrender.com/health
curl "https://<service>.onrender.com/v1/search?q=maison&limit=3"
curl https://<service>.onrender.com/v1/stats
```

## 4. Front sur Cloudflare Pages

1. *Pages* → *Connect to Git* → le dépôt `Ewe_Lab`.
2. Framework preset : **None**. Commande de build : **aucune**. Répertoire de sortie : `web`.
3. Domaine fourni : `https://<projet>.pages.dev`.

Avant de déployer, renseigner l'adresse de l'API dans la page :

```html
<meta name="api-base" content="https://<service>.onrender.com">
```

`web/js/app.js` retombe sur `http://127.0.0.1:8000` quand la page est ouverte en local, donc cette
valeur ne gêne pas le développement.

## 5. Vérifier le parcours complet

- `https://<projet>.pages.dev` : recherche « maison », ouverture d'une fiche, bascule
  « Texte d'origine ».
- Onglet « Apprendre » : les cinq leçons s'ouvrent, l'exercice affiche « Aucun mot relu pour
  l'instant » (état normal tant que `data/verifications.csv` n'est pas rempli).
- Signalement depuis une fiche : réponse 201, puis **vérifier qu'il a bien été écrit** — sur
  l'offre gratuite Render, il disparaît au redéploiement.
- Console du navigateur : aucune erreur CORS. Les URL de préversion
  (`https://<commit>.<projet>.pages.dev`) ont une origine différente : les ajouter à
  `CORS_ORIGINS` pour les tester.

## 6. Ce que l'offre gratuite ne couvre pas

- **Réveil à froid** : après 15 minutes sans trafic, la première requête prend environ une minute.
  Un ping toutes les 14 minutes garde le service éveillé, dans la limite d'une instance gratuite.
- **Signalements volatils** : pas de disque persistant sur le plan gratuit. Pour les conserver, il
  faudra une base externe (Supabase, Neon) et adapter `POST /v1/report` — c'est le prochain
  chantier si la bêta prend.
- **Taux d'erreur et quiz** : les deux restent vides tant que la relecture humaine n'est pas faite.
  Ce n'est pas un problème de déploiement, mais ça se verra en ligne.

## 7. Mise à jour d'une nouvelle version de la base

1. Reconstruire en local : `python pipeline/build_dictionary.py`.
2. Remplacer l'asset de release (nouvelle release, même nom de fichier).
3. Render → *Manual Deploy* → *Clear build cache & deploy*. La construction retélécharge la base.
4. Vérifier `/v1/stats` : `version_donnees` doit être la date du jour.
