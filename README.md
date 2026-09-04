# CV Generator

Génération de CV adaptés aux offres — FastAPI, SQLite, Vue 3, GLM-5.3-Flash (Ollama Cloud).

## Lancer le projet

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd client && npm install && npm run build && cd ..
uvicorn app.main:app --reload
```

Interface : **http://127.0.0.1:8000**

Uvicorn sert l’API et le front compilé (`client/dist`). Pas besoin de `npm run dev`.

Après une modification Vue, reconstruire : `cd client && npm run build` (uvicorn `--reload` ne voit pas le JS).

`npm run dev` (port 5173) n’est utile que pour le hot-reload pendant un gros chantier UI.

Clé API : `OLLAMA_API_KEY` dans un fichier `.env` à la racine (voir `.env.example`).
Pas besoin du daemon Ollama local. Statut LLM : http://127.0.0.1:8000/api/llm/status

Au démarrage, le profil en base est resynchronisé depuis `app/seed.py`.

## Config

| Fichier | Rôle |
|---------|------|
| `config/llm.yaml` | Modèle Ollama Cloud, température, timeout |
| `config/analysis.yaml` | Tags détectés dans les offres |
| `app/seed.py` | Profil template (expériences, compétences, technos) |
| `client/` | App Vue 3 + Vite |

## Utilisation

1. Choisir un profil
2. Coller l'offre d'emploi
3. Cocher **LLM** (recommandé)
4. **Adapter le CV** → markdown éditable, **Exporter le PDF**

L'export PDF nécessite Pandoc + WeasyPrint sur la machine ; l'app affiche un message si l'outil est absent.
