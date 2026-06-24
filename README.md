# CV Generator — Backend FastAPI + SQLite

API locale pour gérer profils, offres et générations de CV.

## Installation

```powershell
cd "D:\digital projects\_Projects\cv"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Ollama (optionnel, réécriture LLM) :

```powershell
ollama pull llama3.2
```

L'app Ollama doit tourner (icône barre des tâches). Vérifie sur http://127.0.0.1:8000/api/llm/status

Config : `config/llm.yaml` — modèle, URL, température.

## Lancer l'API

```powershell
uvicorn app.main:app --reload
```

- API : http://127.0.0.1:8000
- **Interface web** : http://127.0.0.1:8000
- Swagger : http://127.0.0.1:8000/docs
- Base SQLite : `data/cv.db` (créée automatiquement)

## Modèle de données

| Table | Rôle |
|-------|------|
| `profiles` | Contenu CV (JSON) |
| `job_postings` | Offres collées |
| `generations` | CV générés (markdown) |

## Interface web

Ouvre http://127.0.0.1:8000 après avoir lancé uvicorn :

1. Colle l'offre
2. Coche/décoche Ollama
3. **Générer** → aperçu Markdown, copie, téléchargement
4. Historique des générations précédentes

## Endpoints

### Profils

```
GET    /api/profiles
GET    /api/profiles/{id}
POST   /api/profiles
PATCH  /api/profiles/{id}
DELETE /api/profiles/{id}
```

### Offres

```
GET    /api/jobs
POST   /api/jobs          { "raw_text": "...", "label": "webmaster" }
GET    /api/jobs/{id}
DELETE /api/jobs/{id}
```

### Générations

```
GET    /api/generations
POST   /api/generations   { "job_text": "...", "use_llm": true }
GET    /api/generations/{id}
```

`job_id` + `profile_id` optionnels. Sans profil → profil par défaut (seed au 1er démarrage).

## Exemple rapide

```powershell
# Générer un CV depuis une offre collée
curl -X POST http://127.0.0.1:8000/api/generations `
  -H "Content-Type: application/json" `
  -d '{"job_text": "Développeur Fullstack React NestJS H/F...", "use_llm": true}'
```

## Structure

```
app/
  static/           Interface web
  services/         analyzer, renderer, llm, pdf…
config/             analysis.yaml, llm.yaml
assets/
  lucas-schrever.jpg   Photo profil (PDF)
style.css           Mise en page PDF
data/
  cv.db             SQLite (gitignored)
```

PDF : Pandoc + WeasyPrint + `style.css` + photo dans `assets/`. Markdown seul en base.
