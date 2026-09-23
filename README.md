# CV

Profils SQLite bilingues → markdown → PDF A4 **1 page**.

## Lancer

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd client && npm install && npm run build && cd ..
uvicorn app.main:app --reload
```

Interface : **http://127.0.0.1:8000**

Hot-reload front (React + TypeScript) : `cd client && npm run dev` (port 5173). Après un changement servi par uvicorn : `npm run build`.

L'export PDF nécessite Pandoc + WeasyPrint.

## FastAPI

```
app/main.py                 # app, CORS, static, include_router
app/db.py                   # SQLite (person + markdown FR/EN)
app/selectprofile/          # GET /api/selectprofile
app/applydefault/           # POST /api/applydefault (sauve + traduit l'autre langue via Ollama)
app/export/                 # POST /api/export/pdf
```

Données : `data/cv.sqlite`.

Ollama local : `qwen3.5:2b` (`OLLAMA_HOST`, `OLLAMA_MODEL`).

## Nommage PDF

`lucas-schrever-[poste][-en]`

