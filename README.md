# CV Generator

Génération de CV adaptés aux offres — FastAPI, SQLite, interface web, Ollama.

## Lancer le projet

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull llama3.2
uvicorn app.main:app --reload
```

Interface : **http://127.0.0.1:8000**

Ollama doit tourner en local. Statut : http://127.0.0.1:8000/api/llm/status

Au démarrage, le profil en base est resynchronisé depuis `app/seed.py`.

## Config

| Fichier | Rôle |
|---------|------|
| `config/llm.yaml` | Modèle Ollama, température, timeout |
| `config/analysis.yaml` | Tags détectés dans les offres |
| `app/seed.py` | Profil template (expériences, compétences, technos) |

## Utilisation

1. Coller l'offre d'emploi
2. Cocher **Ollama** (recommandé)
3. **Générer** → aperçu éditable, export Markdown ou PDF

L'export PDF nécessite Pandoc + WeasyPrint sur la machine ; l'app affiche un message si l'outil est absent.
