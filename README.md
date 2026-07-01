# CV Generator — Backend FastAPI + SQLite

API locale pour générer des CV adaptés aux offres via Ollama.

## Installation

```powershell
cd "D:\digital projects\_Projects\cv"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Ollama (recommandé) :

```powershell
ollama pull llama3.2
```

L'app Ollama doit tourner. Vérifie sur http://127.0.0.1:8000/api/llm/status

Config : `config/llm.yaml` — modèle, température (0.45 par défaut, plus fidèle à l'offre).

## Dépendances

### Python (`requirements.txt`)
| Package | Usage |
|---------|--------|
| fastapi, uvicorn | API + interface |
| sqlalchemy | SQLite |
| pydantic, pydantic-settings | Schémas / config |
| pyyaml | `config/*.yaml` |

`python-multipart` retiré — non utilisé (pas d'upload de fichiers).

### Système (optionnel)
| Outil | Usage | Requis si… |
|-------|--------|------------|
| **Ollama** + `llama3.2` | IA (adaptation CV, extraction offre) | Génération avec Ollama coché |
| **Pandoc** + **WeasyPrint** | Export PDF uniquement | Tu cliques « .pdf » |

Pandoc n'est **pas** un package pip : inutile pour Markdown / génération CV. Installe-le seulement si tu exportes en PDF.

```powershell
# PDF sous Windows (exemple)
choco install pandoc
# WeasyPrint : voir https://doc.courtbouillon.org/weasyprint/stable/first_steps.html
```

## Lancer l'API

```powershell
uvicorn app.main:app --reload
```

- Interface : http://127.0.0.1:8000
- Swagger : http://127.0.0.1:8000/docs
- Base SQLite : `data/cv.db`

Au démarrage, le profil en base est **resynchronisé depuis `app/seed.py`**.

## Profil template (`app/seed.py`)

- Titre par défaut : **Développeur fullstack**
- **technos_root** : react, next, vue, nodejs, tailwindcss, mongodb, mysql, postgresql, wordpress, tanstack query, axios, github actions, docker, hooks
- **technos_extended** : TypeScript, JavaScript, Git, REST API, PHP… (dérivées de la stack)
- **competences** : groupées par défaut (Front-end, Back-end, Data, DevOps)

Ollama réorganise titre, profil, compétences et bullets selon l'offre — sans garde-fous stricts.

## Interface web

1. Colle l'offre
2. Coche Ollama (recommandé)
3. **Générer** → aperçu éditable, export MD/PDF
4. Historique des générations

## Exemple rapide

```powershell
# Forcer la resync du seed
Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8000/api/profiles/default/sync-seed"

# Générer un CV
Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8000/api/generations" `
  -ContentType "application/json" `
  -Body '{"job_text": "Développeur web PHP Vue.js H/F...", "use_llm": true}'
```

## Structure

```
app/
  seed.py           Profil template + technos racines
  services/
    llm.py          Prompt Ollama (titre, profil, compétences, bullets)
    renderer.py     Markdown
    analyzer.py     Tags / entreprise depuis l'offre
config/
  analysis.yaml     Tags détectés dans les offres
  llm.yaml          Modèle Ollama
```

PDF : Pandoc + WeasyPrint + `style.css`.
